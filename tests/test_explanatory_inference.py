"""Deterministic synthetic QA for the frozen D9e3 explanatory inference.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_explanatory_inference.py' -v
Never reads the real data or runs the predictive final evaluation.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t
from statsmodels.stats.sandwich_covariance import cov_cluster

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from youth_offer import explanatory_inference as inf


def make_panel():
    """Full balanced but synthetic E4 borough panel with real temporal variation."""
    rng = np.random.default_rng(41)
    rows = []
    for b in range(32):
        code = f"E0900{b:04d}"
        for y, year in enumerate(inf.COHORT_YEARS):
            n = 1100 + b * 17 + y * 14
            fsm = 0.11 + b * .005 + y * .004 + .012 * np.sin((b + 2) * (y + 1))
            sen = 0.09 + b * .002 + y * .003 + .008 * np.cos((b + 3) * (y + 2))
            special = .015 + .0004 * b + .0005 * y + .003 * np.sin((b + 4) * (y + 3))
            eta = -3.1 + .023 * b + .045 * np.sin(y) + .65 * fsm - .3 * sen + .6 * special
            rows.append({
                "new_la_code": code, "time_period": year, "cohort_count": n,
                "adverse_count": rng.binomial(n, expit(eta)),
                "fsm_share": fsm, "identified_sen_share": sen,
                "special_school_share": special,
            })
    # Nonstandard index/order must not break pairing or cohort histories.
    panel = pd.DataFrame(rows).sample(frac=1, random_state=6)
    panel.index = np.arange(10000, 10224)
    return panel


class PredeterminedLogit:
    def __init__(self, columns, beta):
        self.params = pd.Series(beta, index=columns)
        self.model = SimpleNamespace(exog_names=list(columns))

    def predict(self, X):
        return pd.Series(expit(X.to_numpy(dtype=float) @ self.params.to_numpy()), index=X.index)


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = make_panel()
        cls.boroughs = sorted(cls.panel.new_la_code.unique())
        cls.unrepeated_sample = inf.build_borough_bootstrap_sample(cls.panel, cls.boroughs)
        cls.fitted, cls.X = inf._fit_sampled_e4(cls.unrepeated_sample)

    def test_duplicate_draws_get_distinct_fe_ids_and_identical_source_data(self):
        draw = [self.boroughs[4]] * 2 + [b for b in self.boroughs if b != self.boroughs[4]][:30]
        sample = inf.build_borough_bootstrap_sample(self.panel, draw)
        self.assertEqual(len(sample), 224)
        self.assertEqual(sample.new_la_code.nunique(), 32)
        self.assertEqual(sample._source_la_code.nunique(), 31)
        self.assertTrue(sample.groupby("new_la_code").size().eq(7).all())
        a, b = sample.iloc[:7], sample.iloc[7:14]
        self.assertNotEqual(a.new_la_code.iloc[0], b.new_la_code.iloc[0])
        pd.testing.assert_frame_equal(
            a.drop(columns=["new_la_code", "_draw_index"]).reset_index(drop=True),
            b.drop(columns=["new_la_code", "_draw_index"]).reset_index(drop=True),
        )
        columns = ["adverse_count", "cohort_count", *inf.COMPOSITION_COLUMNS, "time_period"]
        original = self.panel[self.panel.new_la_code.eq(self.boroughs[4])][columns].reset_index(drop=True)
        pd.testing.assert_frame_equal(a[columns].reset_index(drop=True), original)
        self.assertTrue(self.panel.index.min() >= 10000)  # untouched original
        self.assertFalse("_draw_index" in self.panel.columns)

    def test_sample_fit_structure_and_estimates(self):
        result, X = self.fitted, self.X
        self.assertEqual(X.shape, (224, 41))
        self.assertEqual(list(X.columns)[-3:], list(inf.COMPOSITION_COLUMNS))
        self.assertTrue(result.converged)
        self.assertEqual(np.linalg.matrix_rank(X), 41)
        point = inf.calculate_d9e_estimates(result, X)
        self.assertEqual(len(point), 22)
        self.assertEqual(point.index[0], "rate_pct:201617")
        self.assertEqual(point.index[-1], "composition_pp:special_school_share")
        self.assertAlmostEqual(point["baseline_pp:202223"], point["rate_pct:202223"] - point["rate_pct:201617"])
        self.assertTrue((point.filter(like="rate_pct:") > 0).all())

    def test_invalid_or_unbalanced_inputs_rejected(self):
        bad = self.panel.drop(index=self.panel.index[0])
        with self.assertRaises(ValueError):
            inf.build_borough_bootstrap_sample(bad, self.boroughs)
        with self.assertRaises(ValueError):
            inf.build_borough_bootstrap_sample(self.panel, ["not_a_borough"] * 32)
        with self.assertRaises(ValueError):
            inf.run_e4_borough_bootstrap(self.panel, n_attempts=0)

    def test_bootstrap_seed_reproducibility_and_percentiles(self):
        one = inf.run_e4_borough_bootstrap(self.panel, n_attempts=3, seed=91)
        two = inf.run_e4_borough_bootstrap(self.panel, n_attempts=3, seed=91)
        pd.testing.assert_frame_equal(one.estimates, two.estimates)
        pd.testing.assert_frame_equal(one.intervals, two.intervals)
        self.assertEqual((one.attempted, one.successful, one.failed), (3, 3, 0))
        self.assertEqual(set(one.estimates.replicate), {0, 1, 2})
        for key in ("baseline_pp:202223", "composition_pp:fsm_share"):
            values = one.estimates[key].to_numpy()
            got = one.intervals.set_index("estimate_key").loc[key]
            np.testing.assert_allclose([got.lower_95, got.upper_95], np.quantile(values, [.025, .975]), atol=1e-12)

    def test_failed_attempts_are_reported_not_replaced(self):
        real_fit = inf._fit_sampled_e4
        calls = [0]

        def sometimes_fails(sample):
            calls[0] += 1
            if calls[0] == 1:
                raise ValueError("Intentional synthetic fit failure")
            return real_fit(sample)

        with patch.object(inf, "_fit_sampled_e4", side_effect=sometimes_fails):
            result = inf.run_e4_borough_bootstrap(self.panel, n_attempts=3, seed=91)
        self.assertEqual(calls[0], 3)
        self.assertEqual((result.attempted, result.successful, result.failed), (3, 2, 1))
        self.assertEqual(result.failures.replicate.tolist(), [0])
        self.assertEqual(result.estimates.replicate.tolist(), [1, 2])
        self.assertIn("Intentional", result.failures.detail.iloc[0])

    def test_delta_gradients_match_finite_differences(self):
        result, X = self.fitted, self.X
        betas = result.params.to_numpy(dtype=float)
        grads = inf._e4_delta_gradients(result, X)
        keys = ["rate_pct:202223", "baseline_pp:202223", "adjacent_pp:201920", "composition_pp:fsm_share"]
        eps = 1e-6
        for col_index in (0, 3, 30, 36, 38, 39, 40):
            positive, negative = betas.copy(), betas.copy()
            positive[col_index] += eps
            negative[col_index] -= eps
            values_pos = inf.calculate_d9e_estimates(PredeterminedLogit(X.columns, positive), X)
            values_neg = inf.calculate_d9e_estimates(PredeterminedLogit(X.columns, negative), X)
            finite_difference = (values_pos[keys] - values_neg[keys]) / (2 * eps)
            np.testing.assert_allclose(grads.loc[keys].iloc[:, col_index], finite_difference, rtol=5e-5, atol=5e-8)

    def test_clustered_delta_uses_corrected_covariance_and_t_interval(self):
        result, X = self.fitted, self.X
        groups = self.unrepeated_sample.new_la_code
        result_table = inf.calculate_cluster_delta_intervals(result, X, groups)
        self.assertEqual(len(result_table), 22)
        self.assertTrue(np.isfinite(result_table.cluster_se).all())
        cov_corrected = cov_cluster(result, groups.to_numpy(), use_correction=True)
        cov_uncorrected = cov_cluster(result, groups.to_numpy(), use_correction=False)
        factor = (32 / 31) * ((224 - 1) / (224 - 41))
        np.testing.assert_allclose(cov_corrected, cov_uncorrected * factor, rtol=1e-9, atol=1e-9)
        grads = inf._e4_delta_gradients(result, X)
        key = "baseline_pp:202223"
        g = grads.loc[key].to_numpy(dtype=float)
        expected_se = np.sqrt(max(g @ cov_corrected @ g, 0))
        row = result_table.set_index("estimate_key").loc[key]
        self.assertAlmostEqual(row.cluster_se, expected_se)
        self.assertAlmostEqual(row.upper_95 - row.estimate, t.ppf(.975, 31) * expected_se)
        with self.assertRaises(ValueError):
            inf.calculate_cluster_delta_intervals(result, X, groups.iloc[::-1])


if __name__ == "__main__":
    unittest.main()
