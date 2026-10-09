from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PROCESSED = ROOT / "data" / "processed"
WEB = ROOT / "web"


def records(path: Path) -> list[dict]:
    frame = pd.read_csv(path)
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def main() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    policies = ["B0_RULE_UNCAPPED", "B1_FCFS", "B2_TEMP_GREEDY", "OURS"]
    payload = {
        "meta": {
            "project": "粮盾",
            "subtitle": "面向寒地粮库的多仓温湿耦合预测与通风协同决策平台",
            "scenario": "哈尔滨 24 仓 · 168 小时 · 随机种子 0",
            "power_cap_kw": 240,
            "disclosure": "仓群和初始粮情为可复现合成数据，天气来自 NASA POWER；结果只用于仿真方案比较。",
        },
        "aggregate": records(RESULTS / "main_aggregate.csv"),
        "timeseries": records(RESULTS / "timeseries_seed0.csv"),
        "bin_timeseries": records(RESULTS / "bin_timeseries_seed0.csv"),
        "weather": records(PROCESSED / "weather_hourly.csv"),
        "bins": {
            policy: records(RESULTS / "raw" / f"final_bins_{policy}.csv")
            for policy in policies
        },
    }
    (WEB / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(WEB / "data.json")


if __name__ == "__main__":
    main()
