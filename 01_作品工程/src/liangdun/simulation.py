from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .model import Scenario, equilibrium_moisture, risk_score, valid_ventilation_window
from .policies import DecisionContext, decide


@dataclass(frozen=True)
class SimulationResult:
    summary: dict[str, float | int | str]
    timeseries: pd.DataFrame
    bin_final: pd.DataFrame
    bin_timeseries: pd.DataFrame


def run_simulation(
    scenario: Scenario,
    policy: str,
    power_cap_kw: float = 240.0,
    weather_temp_offset_c: float = 0.0,
    weather_rh_offset_pct: float = 0.0,
) -> SimulationResult:
    weather = scenario.weather.copy()
    weather["temp_c"] += weather_temp_offset_c
    weather["rh_pct"] = np.clip(weather["rh_pct"] + weather_rh_offset_pct, 5.0, 100.0)

    bins = scenario.bins.copy()
    temp = bins["grain_temp_c"].to_numpy(float).copy()
    moisture = bins["moisture_pct"].to_numpy(float).copy()
    hotspot = bins["hotspot"].to_numpy(float)
    fan_kw = bins["fan_kw"].to_numpy(float)
    capacity = bins["capacity_t"].to_numpy(float)
    wait_hours = np.zeros(len(bins), dtype=float)
    records: list[dict[str, float | int | str]] = []
    bin_records: list[dict[str, float | int | str | bool]] = []

    for hour, row in enumerate(weather.itertuples(index=False)):
        risk_before = risk_score(temp, moisture, hotspot)
        ctx = DecisionContext(
            hour=hour,
            weather=weather,
            temp=temp.copy(),
            moisture=moisture.copy(),
            hotspot=hotspot,
            fan_kw=fan_kw,
            wait_hours=wait_hours.copy(),
            power_cap_kw=power_cap_kw,
        )
        active = decide(policy, ctx)
        valid = valid_ventilation_window(temp, moisture, float(row.temp_c), float(row.rh_pct))

        metabolic_heat = 0.012 + 0.025 * hotspot + 0.018 * np.maximum(moisture - 14.0, 0.0)
        passive_temp = 0.004 * (float(row.temp_c) - temp)
        fan_temp = active * 0.105 * (float(row.temp_c) - temp)
        temp = temp + metabolic_heat + passive_temp + fan_temp + scenario.temp_noise[hour]

        eq = float(equilibrium_moisture(float(row.rh_pct)))
        passive_moisture = 0.0015 * (eq - moisture)
        fan_moisture = active * 0.035 * (eq - moisture)
        moisture = moisture + passive_moisture + fan_moisture + scenario.moisture_noise[hour]
        moisture = np.clip(moisture, 10.0, 18.0)

        risk_after = risk_score(temp, moisture, hotspot)
        power_kw = float(np.sum(fan_kw[active]))
        wait_hours = np.where((risk_after > 0.42) & ~active, wait_hours + 1.0, 0.0)
        weighted_risk = float(np.average(risk_after, weights=capacity))
        unsafe = int(np.count_nonzero(active & ~valid))

        records.append(
            {
                "seed": scenario.seed,
                "policy": policy,
                "hour": hour,
                "timestamp": row.timestamp.isoformat(),
                "outside_temp_c": float(row.temp_c),
                "outside_rh_pct": float(row.rh_pct),
                "active_fans": int(np.count_nonzero(active)),
                "power_kw": power_kw,
                "weighted_risk": weighted_risk,
                "high_risk_bins": int(np.count_nonzero(risk_after >= 0.65)),
                "unsafe_ventilation": unsafe,
                "mean_grain_temp_c": float(np.mean(temp)),
                "max_grain_temp_c": float(np.max(temp)),
                "mean_moisture_pct": float(np.mean(moisture)),
                "max_moisture_pct": float(np.max(moisture)),
                "max_wait_hours": float(np.max(wait_hours)),
            }
        )
        for idx, bin_id in enumerate(bins["bin_id"]):
            bin_records.append(
                {
                    "seed": scenario.seed,
                    "policy": policy,
                    "hour": hour,
                    "timestamp": row.timestamp.isoformat(),
                    "bin_id": bin_id,
                    "temp_c": float(temp[idx]),
                    "moisture_pct": float(moisture[idx]),
                    "risk": float(risk_after[idx]),
                    "fan_active": bool(active[idx]),
                    "wait_hours": float(wait_hours[idx]),
                }
            )

    timeseries = pd.DataFrame(records)
    final_risk = risk_score(temp, moisture, hotspot)
    bin_final = bins[["bin_id", "capacity_t", "fan_kw", "hotspot"]].copy()
    bin_final["final_temp_c"] = temp
    bin_final["final_moisture_pct"] = moisture
    bin_final["final_risk"] = final_risk

    total_capacity = float(np.sum(capacity))
    summary: dict[str, float | int | str] = {
        "seed": scenario.seed,
        "policy": policy,
        "n_bins": len(bins),
        "total_capacity_t": total_capacity,
        "hours": len(weather),
        "power_cap_kw": power_cap_kw,
        "risk_exposure": float(timeseries["weighted_risk"].sum()),
        "high_risk_bin_hours": int(timeseries["high_risk_bins"].sum()),
        "energy_kwh": float(timeseries["power_kw"].sum()),
        "peak_power_kw": float(timeseries["power_kw"].max()),
        "cap_violation_hours": int((timeseries["power_kw"] > power_cap_kw + 1e-9).sum()),
        "unsafe_ventilation_events": int(timeseries["unsafe_ventilation"].sum()),
        "final_weighted_risk": float(np.average(final_risk, weights=capacity)),
        "final_mean_temp_c": float(np.mean(temp)),
        "final_max_temp_c": float(np.max(temp)),
        "final_mean_moisture_pct": float(np.mean(moisture)),
        "final_max_moisture_pct": float(np.max(moisture)),
        "max_wait_hours": float(timeseries["max_wait_hours"].max()),
    }
    return SimulationResult(summary, timeseries, bin_final, pd.DataFrame(bin_records))
