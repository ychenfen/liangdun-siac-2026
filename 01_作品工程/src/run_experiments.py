from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from liangdun.model import load_weather, make_scenario, scenario_to_frame  # noqa: E402
from liangdun.simulation import run_simulation  # noqa: E402


RAW_WEATHER = ROOT / "data/raw/nasa_power_harbin_20251001_20251007.json"
PROCESSED = ROOT / "data/processed"
RESULTS = ROOT / "results"
RAW_RESULTS = RESULTS / "raw"


def save_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    RAW_RESULTS.mkdir(parents=True, exist_ok=True)
    weather = load_weather(RAW_WEATHER)
    save_frame(weather, PROCESSED / "weather_hourly.csv")

    policies = ["B0_RULE_UNCAPPED", "B1_FCFS", "B2_TEMP_GREEDY", "OURS"]
    main_rows = []
    all_series = []
    all_bin_series = []
    for seed in range(10):
        scenario = make_scenario(weather, seed=seed, n_bins=24)
        save_frame(scenario_to_frame(scenario), PROCESSED / f"bins_seed_{seed}.csv")
        for policy in policies:
            result = run_simulation(scenario, policy=policy, power_cap_kw=240.0)
            main_rows.append(result.summary)
            if seed == 0:
                all_series.append(result.timeseries)
                all_bin_series.append(result.bin_timeseries)
                save_frame(result.bin_final, RAW_RESULTS / f"final_bins_{policy}.csv")
    main = pd.DataFrame(main_rows)
    save_frame(main, RESULTS / "main_by_seed.csv")
    save_frame(pd.concat(all_series, ignore_index=True), RESULTS / "timeseries_seed0.csv")
    save_frame(pd.concat(all_bin_series, ignore_index=True), RESULTS / "bin_timeseries_seed0.csv")

    aggregate = (
        main.groupby("policy", as_index=False)
        .agg(
            risk_exposure_mean=("risk_exposure", "mean"),
            risk_exposure_std=("risk_exposure", "std"),
            high_risk_bin_hours_mean=("high_risk_bin_hours", "mean"),
            energy_kwh_mean=("energy_kwh", "mean"),
            peak_power_kw_mean=("peak_power_kw", "mean"),
            cap_violation_hours_mean=("cap_violation_hours", "mean"),
            final_weighted_risk_mean=("final_weighted_risk", "mean"),
            max_wait_hours_mean=("max_wait_hours", "mean"),
        )
        .sort_values("policy")
    )
    save_frame(aggregate, RESULTS / "main_aggregate.csv")

    scenario0 = make_scenario(weather, seed=0, n_bins=24)
    ablation_rows = []
    for policy in ["OURS", "OURS_NO_FORECAST", "OURS_NO_MOISTURE", "OURS_NO_FAIRNESS"]:
        ablation_rows.append(run_simulation(scenario0, policy=policy, power_cap_kw=240.0).summary)
    save_frame(pd.DataFrame(ablation_rows), RESULTS / "ablation_seed0.csv")

    scale_rows = []
    for n_bins in [12, 24, 36, 48]:
        for seed in range(5):
            scenario = make_scenario(weather, seed=100 + seed, n_bins=n_bins)
            for policy in ["B1_FCFS", "B2_TEMP_GREEDY", "OURS"]:
                scale_rows.append(run_simulation(scenario, policy=policy, power_cap_kw=240.0).summary)
    save_frame(pd.DataFrame(scale_rows), RESULTS / "scale.csv")

    weather_rows = []
    for label, temp_offset, rh_offset in [
        ("observed", 0.0, 0.0),
        ("warmer_plus2C", 2.0, 0.0),
        ("humid_plus10pct", 0.0, 10.0),
        ("warm_humid", 2.0, 10.0),
    ]:
        for policy in ["B2_TEMP_GREEDY", "OURS"]:
            summary = run_simulation(
                scenario0,
                policy=policy,
                power_cap_kw=240.0,
                weather_temp_offset_c=temp_offset,
                weather_rh_offset_pct=rh_offset,
            ).summary
            summary["weather_case"] = label
            summary["temp_offset_c"] = temp_offset
            summary["rh_offset_pct"] = rh_offset
            weather_rows.append(summary)
    save_frame(pd.DataFrame(weather_rows), RESULTS / "weather_stress_seed0.csv")

    manifest = {
        "project": "粮盾：面向寒地粮库的多仓温湿耦合预测与通风协同决策平台",
        "weather_source": "NASA POWER Hourly API, MERRA2/POWER",
        "weather_period": "2025-10-01 to 2025-10-07, LST",
        "coordinates": [126.535, 45.804],
        "weather_records": len(weather),
        "main_seeds": list(range(10)),
        "main_bins": 24,
        "power_cap_kw": 240,
        "disclosure": "仓群、初始粮温、含水率、热点系数和风机配置为合成数据；结果仅用于模型比较。",
    }
    (RESULTS / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(aggregate.to_string(index=False))


if __name__ == "__main__":
    main()
