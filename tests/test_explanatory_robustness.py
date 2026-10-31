"""Synthetic-only D9e4 QA. Never touches predictive final evaluation."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from youth_offer import explanatory, explanatory_robustness as rb


def make_panel():
    rng = np.random.default_rng(76)
    rows = []
    for b in range(32):
        for y, year in enumerate(rb.COHORT_YEARS):
            n = 1100 + 23 * b + 13 * y
            fsm = .13 + .004 * b + .004 * y + .01 * np.sin((b + 2) * (y + 1))
            sen = .10 + .0016 * b + .002 * y + .006 * np.cos((b + 3) * (y + 2))
            special = .013 + .0003 * b + .0005 * y + .002 * np.sin(.5 * (b + 3) * (y + 2))
            disadvantage = fsm + .03 + .007 * np.cos((b + 1) * (y + 4))
            eta = -3.3 + .018 * b + .09 * np.sin(y) + .65 * fsm - .24 * sen + .41 * special
            rows.append({"new_la_code": f"B{b:02d}", "time_period": year, "cohort_count": n,
                         "adverse_count": rng.binomial(n, expit(eta)), "fsm_share": fsm,
                         "identified_sen_share": sen, "special_school_share": special,
                         "disadvantaged_share_approx": disadvantage})
    df = pd.DataFrame(rows).sample(frac=1, random_state=13)
    df.index = np.arange(1000, 1224)
    return df


class RobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = make_panel()
        cls.original = cls.panel.copy(deep=True)
        cls.result, cls.X = explanatory.fit_e4(cls.panel)
        cls.results = rb.run_d9e4_robustness(cls.panel, cls.result, cls.X)

    def case(self, check, case):
        return self.results.loc[(self.results.check == check) & (self.results.case == case)].set_index("estimand")

    def test_all_six_frozen_checks_and_reference_counts(self):
        self.assertEqual(set(self.results.check), {
            "equal_weight_ols", "disadvantage_proxy", "leave_one_borough_out",
            "leave_one_cohort_out", "exclude_201920_202021", "linear_cohort_trend"})
        self.assertEqual(self.results.groupby("check").case.nunique().to_dict(), {
            "equal_weight_ols": 1, "disadvantage_proxy": 1,
            "leave_one_borough_out": 32, "leave_one_cohort_out": 7,
            "exclude_201920_202021": 1, "linear_cohort_trend": 1})
        self.assertEqual(len(self.results), 43*22+1)
        self.assertTrue(self.results.groupby(["check", "case"]).reference_rows.nunique().eq(1).all())
        self.assertTrue((self.results.loc[self.results.check.eq("leave_one_borough_out"), "reference_rows"] == 217).all())
        self.assertTrue((self.results.loc[self.results.check.eq("leave_one_cohort_out"), "reference_rows"] == 192).all())
        self.assertTrue((self.results.loc[self.results.check.eq("exclude_201920_202021"), "reference_rows"] == 160).all())

    def test_design_matches_existing_frozen_e4(self):
        X, years = rb._make_design(self.panel)
        self.assertEqual(years, rb.COHORT_YEARS)
        pd.testing.assert_frame_equal(X, self.X)
        pd.testing.assert_frame_equal(self.panel, self.original)

    def test_ols_rates_are_fit_with_equal_row_weights(self):
        row = self.case("equal_weight_ols", "all")
        ols = sm.OLS(self.panel.adverse_count.to_numpy() / self.panel.cohort_count.to_numpy(), self.X).fit()
        # Independently standardise a single E4 year on the same 224 profiles.
        ref = self.X.copy()
        ref[list(rb.COHORT_YEARS[1:])] = 0.0
        expected = 100 * np.mean(ols.predict(ref))
        self.assertAlmostEqual(row.loc["rate_pct:201617", "sensitivity_on_retained"], expected)
        self.assertTrue(row.status.eq("comparable").all())

    def test_leave_borough_out_common_reference(self):
        retained = self.panel.new_la_code.ne("B09")
        row = self.case("leave_one_borough_out", "B09")
        original_ref = self.X.loc[retained].copy()
        original_ref[list(rb.COHORT_YEARS[1:])] = 0.0
        expected = 100 * np.mean(self.result.predict(original_ref))
        self.assertAlmostEqual(row.loc["rate_pct:201617", "full_on_retained"], expected)
        self.assertEqual(row.loc["composition_pp:fsm_share", "status"], "comparable")

    def test_deleted_year_not_estimable_without_extrapolation(self):
        deleted = self.case("leave_one_cohort_out", "201920")
        for key in ("rate_pct:201920", "baseline_pp:201920", "adjacent_pp:201920", "adjacent_pp:202021"):
            self.assertEqual(deleted.loc[key, "status"], "not_estimable")
            self.assertTrue(np.isnan(deleted.loc[key, "sensitivity_on_retained"]))
        self.assertEqual(deleted.loc["baseline_pp:202223", "status"], "comparable")
        first = self.case("leave_one_cohort_out", "201617")
        self.assertTrue(first.loc[first.index.str.startswith("baseline_pp:"), "status"].eq("not_estimable").all())
        self.assertEqual(first.loc["adjacent_pp:201718", "status"], "not_estimable")
        self.assertEqual(first.loc["adjacent_pp:201819", "status"], "comparable")

    def test_regime_joint_deletion_removes_both_years(self):
        group = self.case("exclude_201920_202021", "joint")
        for year in ("201920", "202021"):
            self.assertEqual(group.loc[f"rate_pct:{year}", "status"], "not_estimable")
        self.assertEqual(group.loc["baseline_pp:202223", "status"], "comparable")

    def test_disadvantage_not_mislabeled_as_fsm_effect(self):
        alt = self.case("disadvantage_proxy", "all")
        for key in ("composition_pp:fsm_share", "composition_pp:disadvantaged_share_approx"):
            self.assertEqual(alt.loc[key, "status"], "different_proxy")
            self.assertTrue(np.isnan(alt.loc[key, "difference_sensitivity_minus_full"]))
        self.assertTrue(np.isfinite(alt.loc["composition_pp:fsm_share", "full_on_retained"]))
        self.assertTrue(np.isfinite(alt.loc["composition_pp:disadvantaged_share_approx", "sensitivity_on_retained"]))
        self.assertEqual(alt.loc["composition_pp:identified_sen_share", "status"], "comparable")

    def test_linear_trend_is_constrained_on_same_reference(self):
        row = self.case("linear_cohort_trend", "all")
        fit, X, _ = rb._fit_sensitivity(self.panel, trend=True)
        self.assertIn("cohort_trend", X.columns)
        endpoint = X.copy()
        endpoint["cohort_trend"] = 6.0
        baseline = X.copy()
        baseline["cohort_trend"] = 0.0
        expected = 100 * (fit.predict(endpoint).mean() - fit.predict(baseline).mean())
        self.assertAlmostEqual(row.loc["baseline_pp:202223", "sensitivity_on_retained"], expected)

    def test_invalid_original_design_rejected(self):
        bad = self.X.copy()
        bad["fsm_share"] += .01
        with self.assertRaises(ValueError):
            rb.run_d9e4_robustness(self.panel, self.result, bad)
        with self.assertRaises(ValueError):
            rb.run_d9e4_robustness(self.panel.drop(index=self.panel.index[0]), self.result, self.X)


if __name__ == "__main__":
    unittest.main()
