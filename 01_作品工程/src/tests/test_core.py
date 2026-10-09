from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from liangdun.model import load_weather, make_scenario  # noqa: E402
from liangdun.simulation import run_simulation  # noqa: E402


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.weather = load_weather(ROOT / "data/raw/nasa_power_harbin_20251001_20251007.json")

    def test_weather_complete(self) -> None:
        self.assertEqual(len(self.weather), 168)
        self.assertFalse(self.weather.isna().any().any())

    def test_deterministic(self) -> None:
        first = run_simulation(make_scenario(self.weather, 3), "OURS")
        second = run_simulation(make_scenario(self.weather, 3), "OURS")
        self.assertEqual(first.summary, second.summary)

    def test_feasible_policies_respect_power_cap(self) -> None:
        scenario = make_scenario(self.weather, 0)
        for policy in ["B1_FCFS", "B2_TEMP_GREEDY", "OURS"]:
            result = run_simulation(scenario, policy)
            self.assertEqual(result.summary["cap_violation_hours"], 0)
            self.assertEqual(result.summary["unsafe_ventilation_events"], 0)

    def test_uncapped_baseline_exposes_constraint(self) -> None:
        result = run_simulation(make_scenario(self.weather, 0), "B0_RULE_UNCAPPED")
        self.assertGreater(result.summary["cap_violation_hours"], 0)


if __name__ == "__main__":
    unittest.main()
