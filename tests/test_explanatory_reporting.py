"""Synthetic-only integration checks for frozen D9e explanatory reporting."""

import json
import sys
import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from youth_offer import explanatory_reporting, explanatory_robustness


def synthetic_panel():
    rng = np.random.default_rng(224)
    rows = []
    for b in range(32):
        for y, yr in enumerate(explanatory_reporting.COHORT_YEARS):
            n = 950 + 9 * b + y * 11
            fsm = .15 + .003 * b + .004 * y + .012 * np.sin((b + 1) * (y + 2))
            sen = .09 + .002 * b + .002 * y + .008 * np.cos((b + 3) * (y + 1))
            special = .015 + .0002 * b + .0006 * y + .002 * np.sin((b + 2) * (y + 3))
            disadvantage = fsm + .04 + .01 * np.cos((b + 4) * (y + 2))
            p = expit(-3.25 + .02 * b + .06 * np.sin(y) + 1.1 * fsm - .4 * sen + .5 * special)
            rows.append({"new_la_code": f"B{b:02d}", "time_period": yr,
                         "cohort_count": n, "adverse_count": rng.binomial(n, p),
                         "fsm_share": fsm, "identified_sen_share": sen,
                         "special_school_share": special,
                         "disadvantaged_share_approx": disadvantage})
    panel = pd.DataFrame(rows).sample(frac=1, random_state=3)
    panel.index = np.arange(700, 924)
    return panel


class D9eReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = synthetic_panel()
        cls.fit, cls.design, _ = explanatory_robustness._fit_sensitivity(cls.panel)

    def test_outputs_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as path:
            out = Path(path)
            summary = explanatory_reporting.run_d9e_reporting(
                self.panel, self.fit, self.design, out, n_bootstrap_attempts=5, bootstrap_seed=88
            )
            self.assertEqual(summary["attempted"], 5)
            self.assertEqual(summary["successful"] + summary["failed"], 5)
            self.assertFalse(summary["full_attempt_count"])
            filenames = {
                "d9e_point_estimates.csv", "d9e_adjusted_years.csv",
                "d9e_composition_associations.csv", "d9e_cluster_delta_intervals.csv",
                "d9e_bootstrap_intervals.csv", "d9e_bootstrap_replicates.csv",
                "d9e_bootstrap_failures.csv", "d9e_robustness.csv",
                "d9e_bootstrap_run.json",
            }
            self.assertEqual({p.name for p in out.iterdir()}, filenames)
            self.assertEqual(len(pd.read_csv(out / "d9e_point_estimates.csv")), 22)
            self.assertEqual(len(pd.read_csv(out / "d9e_robustness.csv")), 43 * 22 + 1)
            with (out / "d9e_bootstrap_run.json").open() as handle:
                self.assertEqual(json.load(handle), summary)
            old = pd.read_csv(out / "d9e_bootstrap_replicates.csv")
            explanatory_reporting.run_d9e_reporting(
                self.panel, self.fit, self.design, out, n_bootstrap_attempts=5, bootstrap_seed=88
            )
            pd.testing.assert_frame_equal(
                old, pd.read_csv(out / "d9e_bootstrap_replicates.csv")
            )

    def test_changed_design_rejected(self):
        bad = self.design.copy()
        bad["fsm_share"] += .01
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(ValueError):
                explanatory_reporting.run_d9e_reporting(
                    self.panel, self.fit, bad, Path(path), n_bootstrap_attempts=2
                )


if __name__ == "__main__":
    unittest.main()
