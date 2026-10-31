"""Deterministic synthetic tests for D9e1 adjusted-year standardisation.

Place in tests/test_explanatory_estimands.py in the project checkout.
From the project root: python -m unittest discover -s tests -p 'test_explanatory_estimands.py' -v
No project raw data or predictive evaluation is accessed.
"""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.special import expit
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from youth_offer.explanatory_estimands import (
    COHORT_YEARS,
    calculate_adjusted_year_rates,
)


class KnownLogitResult:
    """Known-parameter logistic model; tests scenario construction independently."""

    def __init__(self, columns, betas):
        self.model = SimpleNamespace(exog_names=list(columns))
        self.betas = np.array([betas[c] for c in columns], dtype=float)
        self.prediction_inputs = []

    def predict(self, design):
        self.prediction_inputs.append(design.copy())
        return pd.Series(
            expit(design.to_numpy(dtype=float) @ self.betas),
            index=design.index,
        )


def make_profiles(model_years):
    """Unsorted, non-default index; profiles have deliberately different shares."""
    original_years = [model_years[i % len(model_years)] for i in [0, 1, 2, 3]]
    X = pd.DataFrame(index=[107, 49, 612, 22])
    X["const"] = 1.0
    X["B2"] = [0.0, 1.0, 1.0, 0.0]
    for year in model_years[1:]:
        X[year] = [float(y == year) for y in original_years]
    X["fsm_share"] = [0.10, 0.25, 0.45, 0.30]
    X["identified_sen_share"] = [0.08, 0.12, 0.20, 0.15]
    X["special_school_share"] = [0.01, 0.02, 0.04, 0.03]
    return X


def make_known_result(X):
    betas = {
        "const": -3.0,
        "B2": 0.4,
        "fsm_share": 1.2,
        "identified_sen_share": -0.5,
        "special_school_share": 0.8,
        **{year: 0.11 * (i + 1) for i, year in enumerate(COHORT_YEARS[1:])},
    }
    return KnownLogitResult(X.columns, betas), betas


class AdjustedYearRateTests(unittest.TestCase):
    def test_all_years_match_independent_known_logit_calculation(self):
        X = make_profiles(COHORT_YEARS)
        before = X.copy(deep=True)
        result, beta = make_known_result(X)
        actual = calculate_adjusted_year_rates(result, X, COHORT_YEARS)

        # Independently derive each profile's linear predictor (no year effects).
        eta_base = (
            beta["const"] + beta["B2"] * X["B2"].to_numpy()
            + beta["fsm_share"] * X["fsm_share"].to_numpy()
            + beta["identified_sen_share"] * X["identified_sen_share"].to_numpy()
            + beta["special_school_share"] * X["special_school_share"].to_numpy()
        )
        expected = {
            year: 100.0 * expit(eta_base + (0.0 if year == COHORT_YEARS[0] else beta[year])).mean()
            for year in COHORT_YEARS
        }
        self.assertEqual(actual.name, "adjusted_rate_pct")
        self.assertEqual(list(actual.index), list(COHORT_YEARS))
        np.testing.assert_allclose(actual.to_numpy(), list(expected.values()), rtol=0, atol=1e-12)
        pd.testing.assert_frame_equal(X, before)
        self.assertEqual(len(result.prediction_inputs), len(COHORT_YEARS))

        # Same borough/composition profiles in every counterfactual year.
        unaffected = ["const", "B2", "fsm_share", "identified_sen_share", "special_school_share"]
        for year, scenario in zip(COHORT_YEARS, result.prediction_inputs):
            self.assertTrue(scenario.index.equals(X.index))
            pd.testing.assert_frame_equal(scenario[unaffected], X[unaffected])
            active_years = [col for col in COHORT_YEARS[1:] if (scenario[col] == 1.0).all()]
            self.assertEqual(active_years, [] if year == COHORT_YEARS[0] else [year])
            for col in COHORT_YEARS[1:]:
                self.assertTrue((scenario[col] == float(col == year)).all())

    def test_with_actual_statsmodels_grouped_binomial_fit(self):
        """Smoke-test counterfactual predictions with a genuine GLMResults."""
        years = ("201617", "201718", "201819")
        rows, success, total = [], [], []
        for b in range(4):
            for t, year in enumerate(years):
                row = {
                    "const": 1.0,
                    "B1": float(b == 1),
                    "B2": float(b == 2),
                    "B3": float(b == 3),
                    "201718": float(year == "201718"),
                    "201819": float(year == "201819"),
                    "fsm_share": 0.15 + 0.025 * b + 0.009 * t + 0.01 * np.sin(2 * b + t),
                    "identified_sen_share": 0.10 + 0.006 * b + 0.012 * t + 0.005 * np.cos(b + 2 * t),
                    "special_school_share": 0.02 + 0.002 * b + 0.002 * t + 0.001 * np.sin(3 * b + t),
                }
                eta = (
                    -3.0 + 0.15 * b + [0.0, 0.09, -0.08][t]
                    + 0.5 * row["fsm_share"] - 0.4 * row["identified_sen_share"]
                    + 0.3 * row["special_school_share"]
                )
                n = 1000 + 10 * b + 3 * t
                rows.append(row)
                success.append(round(n * expit(eta)))
                total.append(n)
        X = pd.DataFrame(rows, index=range(600, 612))
        y = np.column_stack([success, np.asarray(total) - np.asarray(success)])
        result = sm.GLM(y, X, family=sm.families.Binomial()).fit()
        self.assertTrue(result.converged)

        actual = calculate_adjusted_year_rates(result, X, years)
        for year in years:
            scenario = X.copy()
            scenario[["201718", "201819"]] = 0.0
            if year != "201617":
                scenario[year] = 1.0
            expected = 100.0 * result.predict(scenario).mean()
            np.testing.assert_allclose(actual.loc[year], expected, atol=1e-12)

    def test_reference_year_can_change_when_fitted_years_change(self):
        # A reduced fit excludes 2016/17; 2017/18 is now the omitted reference.
        years = ("201718", "201819", "202223")
        X = make_profiles(years)
        result, beta = make_known_result(X)
        actual = calculate_adjusted_year_rates(result, X, years)
        eta_base = (
            beta["const"] + beta["B2"] * X["B2"].to_numpy()
            + beta["fsm_share"] * X["fsm_share"].to_numpy()
            + beta["identified_sen_share"] * X["identified_sen_share"].to_numpy()
            + beta["special_school_share"] * X["special_school_share"].to_numpy()
        )
        self.assertEqual(list(actual.index), list(years))
        np.testing.assert_allclose(actual.loc["201718"], 100 * expit(eta_base).mean(), atol=1e-12)
        np.testing.assert_allclose(actual.loc["201819"], 100 * expit(eta_base + beta["201819"]).mean(), atol=1e-12)
        np.testing.assert_allclose(actual.loc["202223"], 100 * expit(eta_base + beta["202223"]).mean(), atol=1e-12)

    def test_reject_partial_unsorted_or_mismatched_fitted_years(self):
        X = make_profiles(COHORT_YEARS)
        result, _ = make_known_result(X)
        bad_years = [
            ("201617", "202223"),                 # partial list for full fit
            ("201718", "201617", "202223"),       # out of order
            ("201617", "201718", "201718"),       # duplicate
            ("201617",),                          # too short
            ("201617", "unknown"),                # unknown cohort
        ]
        for years in bad_years:
            with self.subTest(years=years), self.assertRaises(ValueError):
                calculate_adjusted_year_rates(result, X, years)

        bad_X = X[X.columns[::-1]]
        with self.assertRaisesRegex(ValueError, "X columns differ"):
            calculate_adjusted_year_rates(result, bad_X, COHORT_YEARS)


if __name__ == "__main__":
    unittest.main()
