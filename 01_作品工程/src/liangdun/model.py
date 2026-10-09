from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    weather: pd.DataFrame
    bins: pd.DataFrame
    temp_noise: np.ndarray
    moisture_noise: np.ndarray
    seed: int


def load_weather(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parameters = payload["properties"]["parameter"]
    keys = sorted(parameters["T2M"])
    rows = []
    for key in keys:
        rows.append(
            {
                "timestamp": pd.to_datetime(key, format="%Y%m%d%H"),
                "temp_c": float(parameters["T2M"][key]),
                "rh_pct": float(parameters["RH2M"][key]),
                "wind_ms": float(parameters["WS10M"][key]),
            }
        )
    weather = pd.DataFrame(rows)
    if len(weather) != 168:
        raise ValueError(f"Expected 168 hourly records, got {len(weather)}")
    if weather[["temp_c", "rh_pct", "wind_ms"]].isna().any().any():
        raise ValueError("Weather contains missing values")
    return weather


def make_scenario(weather: pd.DataFrame, seed: int, n_bins: int = 24) -> Scenario:
    rng = np.random.default_rng(seed)
    capacity = rng.integers(1800, 3601, size=n_bins).astype(float)
    grain_temp = rng.uniform(18.5, 27.5, size=n_bins)
    moisture = rng.uniform(13.0, 15.6, size=n_bins)
    hotspot = rng.beta(2.0, 5.0, size=n_bins)
    hotspot[rng.choice(n_bins, size=max(2, n_bins // 8), replace=False)] += rng.uniform(
        0.6, 1.1, size=max(2, n_bins // 8)
    )
    hotspot = np.clip(hotspot, 0.0, 1.5)
    fan_kw = rng.choice(np.array([22.0, 30.0, 37.0]), size=n_bins, p=[0.25, 0.5, 0.25])
    bins = pd.DataFrame(
        {
            "bin_id": [f"C{i + 1:02d}" for i in range(n_bins)],
            "capacity_t": capacity,
            "grain_temp_c": grain_temp,
            "moisture_pct": moisture,
            "hotspot": hotspot,
            "fan_kw": fan_kw,
        }
    )
    hours = len(weather)
    temp_noise = rng.normal(0.0, 0.025, size=(hours, n_bins))
    moisture_noise = rng.normal(0.0, 0.006, size=(hours, n_bins))
    return Scenario(weather.copy(), bins, temp_noise, moisture_noise, seed)


def equilibrium_moisture(rh_pct: np.ndarray | float) -> np.ndarray:
    """用于策略比较的简化平衡水分代理，不作为真实玉米等温线。"""
    return np.clip(8.5 + 0.08 * np.asarray(rh_pct, dtype=float), 10.5, 16.5)


def risk_score(temp_c: np.ndarray, moisture_pct: np.ndarray, hotspot: np.ndarray) -> np.ndarray:
    """将温度、水分和局部热点映射为 0-1 的相对风险指数。"""
    z = (temp_c - 18.0) / 3.0 + (moisture_pct - 14.0) / 0.75 + 0.9 * hotspot - 1.25
    return 1.0 / (1.0 + np.exp(-z))


def valid_ventilation_window(
    grain_temp_c: np.ndarray,
    moisture_pct: np.ndarray,
    outside_temp_c: float,
    outside_rh_pct: float,
) -> np.ndarray:
    eq = equilibrium_moisture(outside_rh_pct)
    cooling_ok = outside_temp_c <= grain_temp_c - 1.5
    moisture_ok = (outside_rh_pct <= 82.0) & (eq <= moisture_pct + 0.25)
    return cooling_ok & moisture_ok


def scenario_to_frame(scenario: Scenario) -> pd.DataFrame:
    frame = scenario.bins.copy()
    frame.insert(0, "seed", scenario.seed)
    return frame
