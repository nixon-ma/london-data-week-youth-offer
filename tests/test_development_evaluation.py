"""Development-only, known-answer and failure-detection tests for D9c.

Run from repository root:
    python -m unittest discover -s tests -p 'test_development_evaluation.py' -v

Never constructs or evaluates the locked 2022/23 predictive target.
"""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from youth_offer import evaluation, qa


class DevelopmentEvaluationTests(unittest.TestCase):
    def test_known_answers_for_metrics_and_aggregation(self):
        toy = pd.DataFrame({
            "target_year": ["201819", "201819", "201920", "201920"],
            "target_adverse_rate_baseline": [0.10, 0.20, 0.10, 0.20],
            "target_cohort_count_baseline": [100, 300, 10, 30],
            "b1_borough_persistence": [0.12, 0.16, 0.10, 0.20],
            "b2_london_persistence": [0.10, 0.10, 0.10, 0.10],
            "b3_london_plus_borough_offset": [0.10, 0.20, 0.11, 0.19],
            "m1_prediction": [0.11, 0.19, 0.10, 0.20],
        })
        annual = evaluation.calculate_development_annual_metrics(toy)
        summary = evaluation.summarize_development_metrics(annual)
        metric_columns = ["mae_pp", "rmse_pp", "weighted_mae_pp", "mae_minus_b1_pp"]
        expected_201819 = {
            "B1": (3.0, np.sqrt(10), 3.5, 0.0),
            "B2": (5.0, np.sqrt(50), 7.5, 2.0),
            "B3": (0.0, 0.0, 0.0, -3.0),
            "M1": (1.0, 1.0, 1.0, -2.0),
        }
        for method, expected in expected_201819.items():
            with self.subTest(method=method):
                row = annual.loc[
                    (annual["target_year"] == "201819") & (annual["method"] == method)
                ].iloc[0]
                np.testing.assert_allclose(
                    row[metric_columns].to_numpy(dtype=float), expected, atol=1e-10
                )
        expected_201920 = {
            "B1": (0.0, 0.0, 0.0, 0.0),
            "B2": (5.0, np.sqrt(50), 7.5, 5.0),
            "B3": (1.0, 1.0, 1.0, 1.0),
            "M1": (0.0, 0.0, 0.0, 0.0),
        }
        for method, expected in expected_201920.items():
            with self.subTest(year="201920", method=method):
                row = annual.loc[
                    (annual["target_year"] == "201920") & (annual["method"] == method)
                ].iloc[0]
                np.testing.assert_allclose(
                    row[metric_columns].to_numpy(dtype=float), expected, atol=1e-10
                )

        # These means deliberately differ from pooling observations across years:
        # target-cohort totals differ by a factor of 10 across the toy years.
        expected_summary = {
            "B1": (1.5, np.sqrt(10) / 2, 1.75, 0.0),
            "B2": (5.0, np.sqrt(50), 7.5, 3.5),
            "B3": (0.5, 0.5, 0.5, -1.0),
            "M1": (0.5, 0.5, 0.5, -1.0),
        }
        for method, expected in expected_summary.items():
            with self.subTest(method=method):
                row = summary.loc[summary["method"] == method].iloc[0]
                np.testing.assert_allclose(
                    row[metric_columns].to_numpy(dtype=float), expected, atol=1e-10
                )

    @staticmethod
    def make_full_synthetic_tables():
        years = [("201718", "201819"), ("201819", "201920"),
                 ("201920", "202021"), ("202021", "202122")]
        baseline_rows, m1_rows = [], []
        for year_index, (feature_year, target_year) in enumerate(years):
            for borough_index in range(32):
                key = {
                    "new_la_code": f"E0900{borough_index:04d}",
                    "feature_year": feature_year,
                    "target_year": target_year,
                }
                actual = 0.05 + 0.0005 * borough_index + 0.002 * year_index
                cohort = 100 + 10 * borough_index
                baseline_rows.append({
                    **key, "target_adverse_rate": actual,
                    "target_cohort_count": cohort,
                    "b1_borough_persistence": actual + 0.002,
                    "b2_london_persistence": 0.06 + 0.001 * year_index,
                    "b3_london_plus_borough_offset": actual - 0.001,
                })
                m1_rows.append({
                    **key, "target_adverse_rate": actual,
                    "target_cohort_count": cohort,
                    "m1_prediction": actual + 0.003,
                })
        return pd.DataFrame(baseline_rows), pd.DataFrame(m1_rows)

    def test_structural_qa_and_corruption_detection(self):
        baselines, m1 = self.make_full_synthetic_tables()
        combined = evaluation.build_development_evaluation_table(baselines, m1)
        qa.assert_development_evaluation_table(combined, baselines, m1)
        annual = evaluation.calculate_development_annual_metrics(combined)
        summary = evaluation.summarize_development_metrics(annual)
        qa.assert_development_annual_metrics(annual, combined)
        qa.assert_development_summary_metrics(summary, annual)

        corrupted = combined.copy()
        corrupted.loc[0, "m1_prediction"] += 0.01
        with self.assertRaises(AssertionError):
            qa.assert_development_evaluation_table(corrupted, baselines, m1)

        corrupted = combined.copy()
        corrupted.loc[0, "target_adverse_rate_baseline"] += 0.01
        corrupted.loc[0, "target_adverse_rate_m1"] += 0.01
        with self.assertRaises(AssertionError):
            qa.assert_development_evaluation_table(corrupted, baselines, m1)

        corrupted_annual = annual.copy()
        corrupted_annual.loc[0, "rmse_pp"] += 0.1
        with self.assertRaises(AssertionError):
            qa.assert_development_annual_metrics(corrupted_annual, combined)

        corrupted_summary = summary.copy()
        corrupted_summary.loc[0, "mae_pp"] += 0.1
        with self.assertRaises(AssertionError):
            qa.assert_development_summary_metrics(corrupted_summary, annual)


if __name__ == "__main__":
    unittest.main()
