"""Synthetic regression tests for the frozen E1-E4 explanatory GLMs.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_explanatory.py' -v

These tests use generated data only; they do not access predictive evaluation data.
"""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from youth_offer import explanatory, qa


YEARS = ["201617", "201718", "201819", "201920", "202021", "202122", "202223"]
BOROUGHS = [f"E090000{i:02d}" for i in range(2, 34)]


def make_synthetic_panel() -> pd.DataFrame:
    """Generate a reproducible 32-borough x 7-year grouped-binomial panel."""
    rng = np.random.default_rng(2026)
    year_effects = [0.00, 0.04, -0.08, -0.15, -0.20, -0.07, 0.11]
    rows = []

    for t, year in enumerate(YEARS):
        for b, borough in enumerate(BOROUGHS):
            cohort = 900 + 20 * b + 15 * t
            fsm = 0.18 + 0.005 * b + 0.006 * t + 0.008 * np.sin((b + 1) * (t + 2))
            sen = 0.11 + 0.0015 * b + 0.003 * t + 0.004 * np.cos((b + 2) * (t + 1))
            special = 0.02 + 0.0004 * b + 0.001 * t + 0.003 * np.sin(0.4 * (b + 3) * (t + 1))

            log_odds = (
                -3.0 + 0.022 * (b - 16) + year_effects[t]
                + 0.7 * (fsm - 0.25) + 0.5 * (sen - 0.18)
                - 0.4 * (special - 0.025)
            )
            probability = 1.0 / (1.0 + np.exp(-log_odds))
            adverse = rng.binomial(cohort, probability)
            rows.append({
                "new_la_code": borough,
                "time_period": year,
                "cohort_count": cohort,
                "adverse_count": adverse,
                "fsm_share": fsm,
                "identified_sen_share": sen,
                "special_school_share": special,
            })

    # Exercise row alignment independently of sorted/default-index assumptions.
    panel = pd.DataFrame(rows).sample(frac=1, random_state=17)
    panel.index = np.arange(5000, 5000 + len(panel))
    panel["fsm_share"] = panel["fsm_share"].astype("Float64")
    return panel


class ExplanatoryGLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = make_synthetic_panel()
        cls.fits = {
            "E1": explanatory.fit_e1(cls.panel),
            "E2": explanatory.fit_e2(cls.panel),
            "E3": explanatory.fit_e3(cls.panel),
            "E4": explanatory.fit_e4(cls.panel),
        }

    def test_fits_and_numerical_identities(self):
        """All specifications fit and satisfy their known numerical identities."""
        checks = {
            "E1": qa.assert_e1_fitted_rates,
            "E2": qa.assert_e2_fitted_rates,
            "E3": qa.assert_e3_fitted_counts,
            "E4": qa.assert_e4_score_equations,
        }
        for name, check in checks.items():
            with self.subTest(model=name):
                result, X = self.fits[name]
                qa.assert_explanatory_glm_structure(result, X, name)
                check(self.panel, result, X)

    def test_frozen_predictor_columns_and_row_alignment(self):
        """Reference categories, indicators, composition and row order are fixed."""
        expected = {
            "E1": ["const", *YEARS[1:]],
            "E2": ["const", *BOROUGHS[1:]],
            "E3": ["const", *BOROUGHS[1:], *YEARS[1:]],
            "E4": ["const", *BOROUGHS[1:], *YEARS[1:],
                   "fsm_share", "identified_sen_share", "special_school_share"],
        }
        for name, (_, X) in self.fits.items():
            with self.subTest(model=name):
                self.assertEqual(list(X.columns), expected[name])
                self.assertTrue(X.index.equals(self.panel.index))
                np.testing.assert_array_equal(X["const"].to_numpy(), np.ones(len(X)))
                for year in YEARS[1:] if name in ("E1", "E3", "E4") else []:
                    np.testing.assert_array_equal(
                        X[year].to_numpy(),
                        self.panel["time_period"].eq(year).to_numpy(dtype=float),
                    )
                for borough in BOROUGHS[1:] if name in ("E2", "E3", "E4") else []:
                    np.testing.assert_array_equal(
                        X[borough].to_numpy(),
                        self.panel["new_la_code"].eq(borough).to_numpy(dtype=float),
                    )
                if name == "E4":
                    for column in ("fsm_share", "identified_sen_share", "special_school_share"):
                        np.testing.assert_allclose(
                            X[column].to_numpy(dtype=float),
                            self.panel[column].to_numpy(dtype=float),
                            rtol=0, atol=0,
                        )

    def test_corrupted_adverse_count_is_rejected(self):
        """Numerical QA must reject altered outcomes after fitting."""
        corrupted = self.panel.copy()
        corrupted.loc[corrupted.index[0], "adverse_count"] += 50
        checks = {
            "E1": qa.assert_e1_fitted_rates,
            "E2": qa.assert_e2_fitted_rates,
            "E3": qa.assert_e3_fitted_counts,
            "E4": qa.assert_e4_score_equations,
        }
        for name, check in checks.items():
            with self.subTest(model=name):
                result, X = self.fits[name]
                with self.assertRaises(AssertionError):
                    check(corrupted, result, X)

    def test_rank_deficiency_is_rejected(self):
        """A duplicated predictor must fail full-column-rank QA."""
        result, X = self.fits["E4"]
        broken = X.copy()
        broken["special_school_share"] = broken["fsm_share"]
        self.assertLess(np.linalg.matrix_rank(broken.to_numpy(dtype=float)), broken.shape[1])
        with self.assertRaises(AssertionError):
            qa.assert_explanatory_glm_structure(result, broken, "E4")


if __name__ == "__main__":
    unittest.main()
