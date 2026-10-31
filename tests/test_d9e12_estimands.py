"""Synthetic QA for D9e1 year contrasts and D9e2 paired composition differences.

No raw youth data or predictive final evaluation is accessed.
"""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from youth_offer.explanatory_estimands import (
    COHORT_YEARS,
    COMPOSITION_INCREMENTS,
    calculate_composition_associations,
    summarise_adjusted_year_rates,
)


class KnownLogit:
    """Known logit coefficients so expectations are independently computable."""

    def __init__(self, columns, coefficients):
        self.model = SimpleNamespace(exog_names=list(columns))
        self.coefficients = np.array([coefficients[name] for name in columns])
        self.inputs = []

    def predict(self, design):
        self.inputs.append(design.copy(deep=True))
        return pd.Series(expit(design.to_numpy(dtype=float) @ self.coefficients), index=design.index)


class D9e12EstimandTests(unittest.TestCase):
    def test_year_contrasts_and_endpoint(self):
        rates = pd.Series(
            [5.2, 5.4, 4.8, 4.3, 4.0, 4.9, 6.5],
            index=['201617', '201718', '201819', '201920', '202021', '202122', '202223'],
        )
        actual = summarise_adjusted_year_rates(rates)
        np.testing.assert_allclose(actual['adjusted_rate_pct'], rates, atol=1e-12)
        np.testing.assert_allclose(actual['vs_201617_pp'].to_numpy(), rates.to_numpy() - 5.2, atol=1e-12)
        np.testing.assert_allclose(actual['vs_previous_pp'].iloc[1:].to_numpy(), np.diff(rates.to_numpy()), atol=1e-12)
        self.assertTrue(np.isnan(actual.loc['201617', 'vs_previous_pp']))
        self.assertAlmostEqual(actual.loc['202223', 'vs_201617_pp'], 1.3)

    def test_missing_year_contrasts_are_not_imputed_or_crossed(self):
        reduced = pd.Series([5.2, 5.4, 4.3, 4.0, 4.9, 6.5],
                            index=['201617', '201718', '201920', '202021', '202122', '202223'])
        summary = summarise_adjusted_year_rates(reduced)
        self.assertTrue(summary.loc['201819'].isna().all())
        self.assertTrue(np.isnan(summary.loc['201920', 'vs_previous_pp']))
        self.assertAlmostEqual(summary.loc['201920', 'vs_201617_pp'], -0.9)
        without_baseline = summarise_adjusted_year_rates(reduced.drop('201617'))
        self.assertTrue(without_baseline['vs_201617_pp'].isna().all())

    def test_composition_associations_are_equal_weight_paired_effects(self):
        X = pd.DataFrame({
            'const': [1.0] * 4,
            'B2': [0., 1., 0., 1.],
            '201718': [0., 0., 1., 1.],
            'fsm_share': [0.07, 0.30, 0.44, 0.10],
            'identified_sen_share': [0.08, 0.10, 0.23, 0.17],
            'special_school_share': [0.005, 0.012, 0.050, 0.020],
        }, index=[801, 20, 908, 57])
        before = X.copy(deep=True)
        beta = {'const': -3., 'B2': 0.4, '201718': 0.15,
                'fsm_share': 1.2, 'identified_sen_share': -0.5,
                'special_school_share': 0.8}
        fit = KnownLogit(X.columns, beta)
        actual = calculate_composition_associations(fit, X)
        eta = X.to_numpy(dtype=float) @ np.array([beta[name] for name in X.columns])
        for name, increment in COMPOSITION_INCREMENTS.items():
            expected = 100 * np.mean(expit(eta + beta[name] * increment) - expit(eta))
            self.assertAlmostEqual(actual[name], expected, places=12)
        pd.testing.assert_frame_equal(X, before)
        self.assertEqual(len(fit.inputs), 4)  # one baseline + three scenarios
        for changed_name, scenario in zip(COMPOSITION_INCREMENTS, fit.inputs[1:]):
            self.assertTrue(scenario.index.equals(X.index))
            for col in X.columns:
                expected = X[col].to_numpy() + (COMPOSITION_INCREMENTS[col] if col == changed_name else 0)
                np.testing.assert_allclose(scenario[col].to_numpy(), expected, rtol=0, atol=1e-12)

    def test_year_contrasts_are_order_invariant_and_leave_gaps_unestimated(self):
        rates = pd.Series([6.5, 5.2, 4.3], index=['202223', '201617', '201920'])
        output = summarise_adjusted_year_rates(rates)
        self.assertEqual(list(output.index), list(COHORT_YEARS))
        self.assertAlmostEqual(output.loc['202223', 'vs_201617_pp'], 1.3)
        self.assertTrue(np.isnan(output.loc['201920', 'vs_previous_pp']))
        self.assertTrue(np.isnan(output.loc['202223', 'vs_previous_pp']))

    def test_linear_rate_robustness_is_not_silently_clipped(self):
        X = pd.DataFrame({'const': [1.0, 1.0], 'fsm_share': [0.02, 0.98]}, index=[41, 12])
        class KnownLinear:
            model = SimpleNamespace(exog_names=['const', 'fsm_share'])
            def predict(self, design):
                return pd.Series(-0.25 + 1.25 * design['fsm_share'], index=design.index)
        fit = KnownLinear()
        # Some predictions are negative or above one: report separately in
        # robustness QA, but do not change the frozen linear rate estimator.
        out = calculate_composition_associations(fit, X, {'fsm_share': 0.01})
        self.assertAlmostEqual(out['fsm_share'], 1.25, places=12)

    def test_prediction_row_misalignment_and_nan_are_rejected(self):
        X = pd.DataFrame({'const': [1., 1.], 'fsm_share': [0.1, 0.2]}, index=[11, 19])
        class IncorrectResult:
            model = SimpleNamespace(exog_names=['const', 'fsm_share'])
            def __init__(self, invalid):
                self.invalid = invalid
            def predict(self, design):
                if self.invalid == 'row_index':
                    return pd.Series([0.1, 0.2], index=design.index[::-1])
                return pd.Series([0.1, np.nan], index=design.index)
        for invalid in ('row_index', 'nonfinite'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                calculate_composition_associations(
                    IncorrectResult(invalid), X, {'fsm_share': 0.02}
                )

    def test_replacement_proxy_can_be_specified_explicitly(self):
        X = pd.DataFrame({'const': [1.0, 1.0], 'disadvantaged_share_approx': [0.1, 0.3]}, index=[32, 7])
        fit = KnownLogit(X.columns, {'const': -2.8, 'disadvantaged_share_approx': 0.6})
        out = calculate_composition_associations(fit, X, {'disadvantaged_share_approx': 0.02})
        self.assertEqual(list(out.index), ['disadvantaged_share_approx'])
        self.assertGreater(out.iloc[0], 0)

    def test_incorrect_support_and_inputs_are_rejected(self):
        X = pd.DataFrame({'const': [1., 1.], 'fsm_share': [0.30, 0.99]}, index=[5, 8])
        fit = KnownLogit(X.columns, {'const': -2, 'fsm_share': 1})
        for changes in ({'fsm_share': 0.02}, {'missing': 0.02}, {'fsm_share': 0.0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                calculate_composition_associations(fit, X, changes)
        with self.assertRaises(ValueError):
            summarise_adjusted_year_rates(pd.Series([5, 6], index=['201617', '201617']))
        with self.assertRaises(ValueError):
            summarise_adjusted_year_rates(pd.Series([5, 6], index=['201617', 'invalid']))


if __name__ == '__main__':
    unittest.main()
