from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .model import equilibrium_moisture, risk_score, valid_ventilation_window


@dataclass(frozen=True)
class DecisionContext:
    hour: int
    weather: pd.DataFrame
    temp: np.ndarray
    moisture: np.ndarray
    hotspot: np.ndarray
    fan_kw: np.ndarray
    wait_hours: np.ndarray
    power_cap_kw: float


def _fit_to_cap(order: np.ndarray, fan_kw: np.ndarray, cap_kw: float) -> np.ndarray:
    active = np.zeros(len(fan_kw), dtype=bool)
    used = 0.0
    for idx in order:
        if used + fan_kw[idx] <= cap_kw + 1e-9:
            active[idx] = True
            used += fan_kw[idx]
    return active


def decide(policy: str, ctx: DecisionContext) -> np.ndarray:
    weather_now = ctx.weather.iloc[ctx.hour]
    valid = valid_ventilation_window(
        ctx.temp,
        ctx.moisture,
        float(weather_now.temp_c),
        float(weather_now.rh_pct),
    )
    risk = risk_score(ctx.temp, ctx.moisture, ctx.hotspot)
    need = (ctx.temp > 18.0) | (ctx.moisture > 14.35) | (risk > 0.43)
    candidates = np.flatnonzero(valid & need)

    if policy == "B0_RULE_UNCAPPED":
        active = np.zeros(len(ctx.temp), dtype=bool)
        active[candidates] = True
        return active

    if policy == "B1_FCFS":
        return _fit_to_cap(candidates, ctx.fan_kw, ctx.power_cap_kw)

    if policy == "B2_TEMP_GREEDY":
        score = np.maximum(ctx.temp - 18.0, 0.0) / ctx.fan_kw
        order = candidates[np.argsort(score[candidates])[::-1]]
        return _fit_to_cap(order, ctx.fan_kw, ctx.power_cap_kw)

    if policy not in {
        "OURS",
        "OURS_NO_FORECAST",
        "OURS_NO_MOISTURE",
        "OURS_NO_FAIRNESS",
    }:
        raise ValueError(f"Unknown policy: {policy}")

    eq_now = float(equilibrium_moisture(float(weather_now.rh_pct)))
    cooling_gain = np.maximum(ctx.temp - float(weather_now.temp_c), 0.0)
    drying_gain = np.maximum(ctx.moisture - eq_now, 0.0)
    if policy == "OURS_NO_MOISTURE":
        drying_gain = np.zeros_like(drying_gain)

    horizon = ctx.weather.iloc[ctx.hour : min(ctx.hour + 12, len(ctx.weather))]
    future_count = np.zeros(len(ctx.temp), dtype=float)
    for row in horizon.itertuples(index=False):
        future_count += valid_ventilation_window(
            ctx.temp, ctx.moisture, float(row.temp_c), float(row.rh_pct)
        )
    if policy == "OURS_NO_FORECAST":
        opportunity = np.ones(len(ctx.temp), dtype=float)
    else:
        opportunity = 1.0 + 1.2 / (future_count + 1.0)

    fairness = np.zeros(len(ctx.temp), dtype=float)
    if policy != "OURS_NO_FAIRNESS":
        fairness = 0.024 * np.minimum(ctx.wait_hours, 24.0)

    score = (
        (1.8 * risk + fairness)
        * (1.2 * cooling_gain + 1.8 * drying_gain + 0.25)
        * opportunity
        / ctx.fan_kw
    )
    score[risk < 0.18] *= 0.2
    positive = candidates[score[candidates] > 0.0008]
    order = positive[np.argsort(score[positive])[::-1]]
    return _fit_to_cap(order, ctx.fan_kw, ctx.power_cap_kw)
