"""D9f synthetic-only guard tests. NO genuine 2022/23 target is loaded.

Run from repository root:
    python -m unittest discover -s tests -p 'test_final_gate.py' -v
"""

from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from youth_offer import final_gate, model_tables
import run_final_predictive


YEARS = ["201617", "201718", "201819", "201920", "202021", "202122"]


def synthetic_history() -> pd.DataFrame:
    """Invented complete historical panel, not extracted from any DfE year."""
    rows = []
    for t, year in enumerate(YEARS):
        for b in range(32):
            cohort = 800 + 17 * b + 11 * t
            fsm = 150 + 4 * b + 3 * t + (b * t) % 11
            sen = 100 + 2 * b + 5 * t + (2 * b + 3 * t) % 17
            adverse = 35 + b + 2 * t + (3 * b + t * t) % 13
            rows.append({
                "time_period": year,
                "new_la_code": f"E0900{b:04d}",
                "la_name": f"Synthetic Borough {b}",
                "cohort_count": cohort,
                "adverse_count": adverse,
                "adverse_rate": adverse / cohort,
                "fsm_eligible_count": fsm,
                "fsm_share": fsm / cohort,
                "identified_sen_count": sen,
                "identified_sen_share": sen / cohort,
            })
    return pd.DataFrame(rows)


def synthetic_release_raw(history: pd.DataFrame) -> pd.DataFrame:
    """Invented three-destination rows matching the DfE extraction schema."""
    rows = []
    cohort_origin = history.loc[history["time_period"].eq("202122")]
    for b, origin in enumerate(cohort_origin.itertuples(index=False)):
        cohort = 1000 + b * 13
        n_recorded = 44 + b
        not_captured = 6 + b % 3
        for destination, pupil_count in (
            (model_tables.SUSTAINED, cohort - n_recorded - not_captured),
            (model_tables.NOT_RECORDED, n_recorded),
            (model_tables.ACTIVITY_NOT_CAPTURED, not_captured),
        ):
            rows.append({
                "time_period": "202223",
                "new_la_code": origin.new_la_code,
                "la_name": origin.la_name,
                "establishment_type_group": model_tables.PRIMARY_POPULATION,
                "sex": "Total", "ethnicity_major": "Total", "ethnicity_minor": "Total",
                "disadvantage_status": "Total", "breakdown_topic": "Total",
                "breakdown": "Total", "destination_description": destination,
                "cohort_count": str(cohort), "pupil_count": str(pupil_count),
            })
    return pd.DataFrame(rows)


def synthetic_historical_raw(history: pd.DataFrame) -> pd.DataFrame:
    """Invented headline and top-level FSM/SEN source rows for six past years."""
    rows = []
    for rec in history.itertuples(index=False):
        base = {
            "time_period": rec.time_period,
            "new_la_code": rec.new_la_code,
            "la_name": rec.la_name,
            "establishment_type_group": model_tables.PRIMARY_POPULATION,
            "sex": "Total", "ethnicity_major": "Total", "ethnicity_minor": "Total",
            "disadvantage_status": "Total",
        }
        for destination, count in (
            (model_tables.SUSTAINED, rec.cohort_count - rec.adverse_count),
            (model_tables.NOT_RECORDED, rec.adverse_count - 3),
            (model_tables.ACTIVITY_NOT_CAPTURED, 3),
        ):
            rows.append({
                **base, "breakdown_topic": "Total", "breakdown": "Total",
                "destination_description": destination, "cohort_count": str(rec.cohort_count),
                "pupil_count": str(count),
            })
        for topic, subgroup, count in (
            ("FSM status", "FSM eligible", rec.fsm_eligible_count),
            ("FSM status", "Not known to be FSM eligible", rec.cohort_count - rec.fsm_eligible_count),
            ("SEN provision", "Identified SEN", rec.identified_sen_count),
            ("SEN provision", "No identified SEN", rec.cohort_count - rec.identified_sen_count),
        ):
            rows.append({
                **base, "breakdown_topic": topic, "breakdown": subgroup,
                "destination_description": model_tables.SUSTAINED,
                "cohort_count": str(count), "pupil_count": "0",
            })
    return pd.DataFrame(rows)


class FinalGateTests(unittest.TestCase):
    def test_synthetic_raw_history_construction_and_accounting(self):
        history = synthetic_history()
        raw = synthetic_historical_raw(history)
        reconstructed = final_gate.build_historical_table(raw)
        self.assertEqual(len(reconstructed), 192)
        for field in ("adverse_rate", "fsm_share", "identified_sen_share"):
            expected = history.sort_values(["time_period", "new_la_code"])[field].to_numpy(dtype=float)
            actual = reconstructed.sort_values(["time_period", "new_la_code"])[field].to_numpy(dtype=float)
            np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_preflight_has_five_transitions_and_no_final_targets(self):
        historical = synthetic_history().sample(frac=1, random_state=2026)
        forecasts, report = final_gate.prepare_unscored_final_forecasts(historical)
        self.assertEqual(report["training_rows"], 160)
        self.assertEqual(report["training_target_max"], "202122")
        self.assertEqual(report["forecast_boroughs"], 32)
        self.assertEqual(report["design_rank"], 4)
        self.assertEqual(report["forecasts_outside_unit_interval"], 0)
        self.assertEqual(set(forecasts["feature_year"]), {"202122"})
        self.assertEqual(forecasts["new_la_code"].nunique(), 32)
        self.assertNotIn("target_adverse_rate", forecasts.columns)
        self.assertNotIn("target_cohort_count", forecasts.columns)
        self.assertNotIn("202223", set(historical["time_period"]))

    def test_preflight_rejects_locked_or_incomplete_history(self):
        history = synthetic_history()
        corrupted = pd.concat([
            history,
            history.iloc[[0]].assign(time_period="202223"),
        ], ignore_index=True)
        with self.assertRaises(AssertionError):
            final_gate.prepare_unscored_final_forecasts(corrupted)
        with self.assertRaises(AssertionError):
            final_gate.prepare_unscored_final_forecasts(history.iloc[1:])
        corrupted = history.copy()
        corrupted.loc[0, "fsm_share"] += 0.1
        with self.assertRaises(AssertionError):
            final_gate.prepare_unscored_final_forecasts(corrupted)

    def test_benchmarks_use_correct_six_year_origin(self):
        history = synthetic_history()
        forecasts, _ = final_gate.prepare_unscored_final_forecasts(history)
        for rec in forecasts.itertuples(index=False):
            borough_history = history.loc[history["new_la_code"].eq(rec.new_la_code)]
            origin = borough_history.loc[
                borough_history["time_period"].eq("202122")
            ].iloc[0]
            self.assertAlmostEqual(rec.b1_borough_persistence, origin["adverse_rate"])
            current = history.loc[history["time_period"].eq("202122")]
            london = current["adverse_count"].sum() / current["cohort_count"].sum()
            self.assertAlmostEqual(rec.b2_london_persistence, london)
            offsets = []
            for yr in YEARS:
                all_year = history.loc[history["time_period"].eq(yr)]
                london_year = all_year["adverse_count"].sum() / all_year["cohort_count"].sum()
                row = borough_history.loc[borough_history["time_period"].eq(yr)].iloc[0]
                offsets.append(row["adverse_rate"] - london_year)
            self.assertAlmostEqual(rec.b3_london_plus_borough_offset, london + np.mean(offsets))

    def test_explicit_scoring_function_known_synthetic_answers(self):
        history = synthetic_history()
        forecasts, _ = final_gate.prepare_unscored_final_forecasts(history)
        raw = synthetic_release_raw(history)
        scored, metrics = final_gate.score_released_final(forecasts, raw)
        self.assertEqual(len(scored), 32)
        self.assertEqual(set(metrics["method"]), {"B1", "B2", "B3", "M1"})
        actual = scored["target_adverse_rate_baseline"].to_numpy(dtype=float)
        sizes = scored["target_cohort_count_baseline"].to_numpy(dtype=float)
        for method, field in (
            ("B1", "b1_borough_persistence"),
            ("B2", "b2_london_persistence"),
            ("B3", "b3_london_plus_borough_offset"),
            ("M1", "m1_prediction"),
        ):
            row = metrics.loc[metrics["method"].eq(method)].iloc[0]
            err = scored[field].to_numpy(dtype=float) - actual
            self.assertAlmostEqual(row["mae_pp"], 100 * np.abs(err).mean())
            self.assertAlmostEqual(row["rmse_pp"], 100 * np.sqrt(np.mean(err ** 2)))
            self.assertAlmostEqual(row["weighted_mae_pp"], 100 * np.average(np.abs(err), weights=sizes))
        bad = raw.copy()
        bad.loc[bad["new_la_code"].eq(bad["new_la_code"].iloc[0]), "new_la_code"] = "BAD_CODE"
        with self.assertRaises(AssertionError):
            final_gate.score_released_final(forecasts, bad)

    def test_default_runner_never_calls_scoring_or_passes_final_rows_to_builder(self):
        raw = pd.DataFrame({
            "time_period": ["201617", "202122", "202223"],
            "sentinel": [1, 2, 999],
        })
        with tempfile.TemporaryDirectory() as tempdir:
            previous = Path.cwd()
            try:
                os.chdir(tempdir)
                with (
                    patch.object(run_final_predictive.data, "load_london_la_slice", return_value=raw),
                    patch.object(run_final_predictive, "build_historical_table", return_value=synthetic_history()) as build,
                    patch.object(run_final_predictive, "prepare_unscored_final_forecasts", return_value=(pd.DataFrame(), {"ok": True})),
                    patch.object(run_final_predictive, "score_released_final", side_effect=AssertionError("LOCK VIOLATED")) as score,
                ):
                    run_final_predictive.run(raw_zip=Path("synthetic.zip"))
                    received = build.call_args.args[0]
                    self.assertEqual(set(received["time_period"]), {"201617", "202122"})
                    self.assertEqual(set(received["sentinel"]), {1, 2})
                    score.assert_not_called()
                report_file = Path("outputs/predictive_final_gate/historical_preflight.json")
                self.assertTrue(report_file.exists())
                self.assertFalse(Path("outputs/predictive_final_gate/released_annual_metrics.csv").exists())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
