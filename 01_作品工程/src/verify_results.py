from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    main = pd.read_csv(RESULTS / "main_by_seed.csv")
    aggregate = pd.read_csv(RESULTS / "main_aggregate.csv")
    timeseries = pd.read_csv(RESULTS / "timeseries_seed0.csv")
    bin_timeseries = pd.read_csv(RESULTS / "bin_timeseries_seed0.csv")
    manifest = json.loads((RESULTS / "experiment_manifest.json").read_text(encoding="utf-8"))

    assert len(main) == 40
    assert set(main["seed"]) == set(range(10))
    assert set(main["policy"]) == {
        "B0_RULE_UNCAPPED",
        "B1_FCFS",
        "B2_TEMP_GREEDY",
        "OURS",
    }
    assert len(timeseries) == 168 * 4
    assert len(bin_timeseries) == 168 * 24 * 4
    assert set(bin_timeseries["policy"]) == set(main["policy"])
    fan_counts = (
        bin_timeseries.groupby(["policy", "hour"], as_index=False)["fan_active"].sum()
        .rename(columns={"fan_active": "bin_fan_count"})
    )
    merged_counts = timeseries.merge(fan_counts, on=["policy", "hour"], how="left")
    assert (merged_counts["active_fans"] == merged_counts["bin_fan_count"]).all()
    assert manifest["weather_records"] == 168
    assert (main.loc[main.policy != "B0_RULE_UNCAPPED", "cap_violation_hours"] == 0).all()
    assert (main["unsafe_ventilation_events"] == 0).all()
    assert (main["risk_exposure"] >= 0).all()
    assert (main["energy_kwh"] >= 0).all()
    assert set(path.name for path in (RESULTS / "raw").glob("final_bins_*.csv")) == {
        "final_bins_B0_RULE_UNCAPPED.csv",
        "final_bins_B1_FCFS.csv",
        "final_bins_B2_TEMP_GREEDY.csv",
        "final_bins_OURS.csv",
    }

    weather_path = RAW / "nasa_power_harbin_20251001_20251007.json"
    expected_weather_sha256 = "381d0b056d623b965c80645c6a165495f13ecb7f556f2aec156bcef4f00fac80"
    assert sha256(weather_path) == expected_weather_sha256

    ours = aggregate.set_index("policy").loc["OURS"]
    fcfs = aggregate.set_index("policy").loc["B1_FCFS"]
    greedy = aggregate.set_index("policy").loc["B2_TEMP_GREEDY"]
    assert ours["risk_exposure_mean"] < fcfs["risk_exposure_mean"]
    assert ours["risk_exposure_mean"] <= greedy["risk_exposure_mean"] * 1.03

    print("verification_ok")
    print(
        json.dumps(
            {
                "rows": len(main),
                "seeds": 10,
                "weather_hours": 168,
                "ours_risk_exposure_mean": float(ours["risk_exposure_mean"]),
                "fcfs_risk_exposure_mean": float(fcfs["risk_exposure_mean"]),
                "greedy_risk_exposure_mean": float(greedy["risk_exposure_mean"]),
                "weather_sha256": expected_weather_sha256,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
