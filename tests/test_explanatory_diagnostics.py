
"""Synthetic tests for explanatory model diagnostics.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_explanatory_diagnostics.py' -v
"""

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from youth_offer import explanatory_diagnostics


class ExplanatoryDiagnosticsTests(unittest.TestCase):

    def test_rate_errors_known_values(self):
        """Verify MAE/RMSE against independently known values."""

        model_table = pd.DataFrame(
            {
                "adverse_count": [10, 40],
                "cohort_count": [100, 200],
            },
            index=[101, 205],
        )

        X = pd.DataFrame(
            {"const": [1.0, 1.0]},
            index=model_table.index,
        )

        # Predetermined fitted probabilities: 11% and 18%.
        result = Mock()
        result.predict.return_value = pd.Series(
            [0.11, 0.18],
            index=model_table.index,
        )

        metrics = explanatory_diagnostics.calculate_rate_errors(
            model_table, result, X
        )

        # Observed rates: 10% and 20%.
        # Absolute errors: 1 and 2 percentage points.
        expected_mae = (1 + 2) / 2
        expected_rmse = np.sqrt((1**2 + 2**2) / 2)

        np.testing.assert_allclose(
            metrics["mae_pp"], expected_mae,
            rtol=0, atol=1e-12,
        )

        np.testing.assert_allclose(
            metrics["rmse_pp"], expected_rmse,
            rtol=0, atol=1e-12,
        )

        result.predict.assert_called_once()
        self.assertIs(result.predict.call_args.args[0], X)

    def test_rate_errors_reject_misaligned_indices(self):
        """Reject mismatched model-table and design-matrix indices."""

        model_table = pd.DataFrame(
            {
                "adverse_count": [10, 40],
                "cohort_count": [100, 200],
            },
            index=[101, 205],
        )

        # Same number of rows, but different index order.
        X = pd.DataFrame(
            {"const": [1.0, 1.0]},
            index=[205, 101],
        )

        result = Mock()

        with self.assertRaises(AssertionError):
            explanatory_diagnostics.calculate_rate_errors(
                model_table, result, X
            )

        # Prediction should never be attempted.
        result.predict.assert_not_called()

    def test_deviance_reduction(self):
        """Verify known deviance reduction and invalid comparisons."""

        # Controlled fitted-result substitutes.
        reduced = SimpleNamespace(
            deviance=120.0,
            df_model=6,
            nobs=224,
        )

        full = SimpleNamespace(
            deviance=80.0,
            df_model=9,
            nobs=224,
        )

        metrics = explanatory_diagnostics.calculate_deviance_reduction(
            reduced, full
        )

        self.assertEqual(metrics["reduced_deviance"], 120.0)
        self.assertEqual(metrics["full_deviance"], 80.0)
        self.assertEqual(metrics["deviance_reduction"], 40.0)
        self.assertEqual(metrics["additional_parameters"], 3)

        # Case 1: A full model with greater deviance.
        invalid_deviance = SimpleNamespace(
            deviance=130.0,
            df_model=9,
            nobs=224,
        )

        # Case 2: No additional parameters.
        invalid_parameters = SimpleNamespace(
            deviance=80.0,
            df_model=6,
            nobs=224,
        )

        # Case 3: Different number of observations.
        invalid_sample = SimpleNamespace(
            deviance=80.0,
            df_model=9,
            nobs=223,
        )

        for invalid_result in (
            invalid_deviance,
            invalid_parameters,
            invalid_sample,
        ):
            with self.subTest(invalid_result=invalid_result):
                with self.assertRaises(AssertionError):
                    explanatory_diagnostics.calculate_deviance_reduction(
                        reduced, invalid_result
                    )


    def test_rate_errors_reject_misaligned_predictions(self):
        """Reject predictions whose indices differ from the source rows."""

        model_table = pd.DataFrame(
            {"adverse_count": [10, 40], "cohort_count": [100, 200]},
            index=[101, 205],
        )
        X = pd.DataFrame({"const": [1.0, 1.0]}, index=model_table.index)

        # Test both missing labels and reversed row order.
        for prediction_index in ([101, 999], [205, 101]):
            with self.subTest(prediction_index=prediction_index):
                result = Mock()
                result.predict.return_value = pd.Series(
                    [0.11, 0.18], index=prediction_index
                )

                with self.assertRaises(AssertionError):
                    explanatory_diagnostics.calculate_rate_errors(
                        model_table, result, X
                    )

    def test_pearson_residuals_and_dispersion(self):
        """Verify known Pearson residuals and invalid dispersion inputs."""

        model_table = pd.DataFrame(
            {"adverse_count": [10, 40], "cohort_count": [100, 200]},
            index=[101, 205],
        )
        X = pd.DataFrame({"const": [1.0, 1.0]}, index=model_table.index)

        result = Mock()
        result.predict.return_value = pd.Series(
            [0.11, 0.18], index=model_table.index
        )

        residuals = explanatory_diagnostics.calculate_pearson_residuals(
            model_table, result, X
        )

        # Expected counts: 11 and 36.
        # Binomial variances: 9.79 and 29.52.
        expected = np.array([
            -1 / np.sqrt(9.79),
            4 / np.sqrt(29.52),
        ])

        self.assertTrue(residuals.index.equals(model_table.index))

        np.testing.assert_allclose(
            residuals, expected, rtol=0, atol=1e-12
        )

        # Two observations, one fitted parameter: df_resid = 1.
        dispersion = explanatory_diagnostics.calculate_pearson_dispersion(
            residuals, df_resid=1
        )

        np.testing.assert_allclose(
            dispersion,
            1 / 9.79 + 16 / 29.52,
            rtol=0,
            atol=1e-12,
        )

        # Reject invalid residual degrees of freedom.
        for invalid_df in (0, -1):
            with self.subTest(df_resid=invalid_df):
                with self.assertRaises(AssertionError):
                    explanatory_diagnostics.calculate_pearson_dispersion(
                        residuals, invalid_df
                    )

        # Reject missing or infinite residuals.
        for invalid_residuals in ([np.nan, 1.0], [np.inf, 1.0]):
            with self.subTest(residuals=invalid_residuals):
                with self.assertRaises(AssertionError):
                    explanatory_diagnostics.calculate_pearson_dispersion(
                        pd.Series(invalid_residuals), df_resid=1
                    )

    def test_lagged_pairs_shuffled_panel(self):
        """Verify adjacent-cohort pairing with shuffled observations."""

        years = [
            "201617", "201718", "201819", "201920",
            "202021", "202122", "202223",
        ]

        # Construct 32 boroughs × 7 cohorts with known residuals.
        rows = [
            {
                "new_la_code": f"B{b:02d}",
                "la_name": f"Borough {b:02d}",
                "time_period": year,
                "pearson_residual": float(10 * b + year_position),
            }
            for b in range(32)
            for year_position, year in enumerate(years)
        ]

        # Use non-default indices and shuffle the observation order.
        residual_table = pd.DataFrame(rows, index=range(1000, 1224))
        residual_table = residual_table.sample(frac=1, random_state=42)

        pairs = explanatory_diagnostics.build_lagged_residual_pairs(
            residual_table
        )

        # 32 boroughs × 6 adjacent-cohort pairs.
        self.assertEqual(len(pairs), 192)

        # Every borough must contribute exactly six pairs.
        self.assertTrue(
            pairs.groupby("new_la_code").size().eq(6).all()
        )

        # No duplicated borough-year observations.
        self.assertFalse(
            pairs.duplicated(["new_la_code", "time_period"]).any()
        )

        # The first cohort has no preceding observation.
        self.assertEqual(set(pairs["time_period"]), set(years[1:]))

        # Synthetic residuals increase by exactly one per cohort.
        # Therefore, each preceding residual must equal current - 1.
        np.testing.assert_allclose(
            pairs["previous_pearson_residual"].to_numpy(dtype=float),
            pairs["pearson_residual"].to_numpy(dtype=float) - 1,
            rtol=0,
            atol=0,
        )


if __name__ == "__main__":
    unittest.main()
