"""Diagnostics for the E1–E4 explanatory grouped-binomial GLMs.

These are in-sample explanatory diagnostics, not predictive evaluations.
"""

import numpy as np

def calculate_deviance_reduction(reduced_result, full_result):
    """
    Compare two nested explanatory GLMs fitted to identical observations.

    Parameters
    ----------
    reduced_result:
        Fitted GLM with fewer predictors.
    full_result:
        Fitted GLM containing all predictors of the reduced model,
        plus additional predictors.

    Returns
    -------
    dict
        Deviances, deviance reduction and additional model parameters.
    """

    # Extract the fitted model deviances.
    reduced_deviance = reduced_result.deviance
    full_deviance = full_result.deviance

    # Calculate the deviance reduction.
    deviance_reduction = reduced_deviance - full_deviance

    # Calculate the number of additional parameters.
    additional_parameters = full_result.df_model - reduced_result.df_model

    assert reduced_result.nobs == full_result.nobs, (
        "Models must use the same number of observations."
    )

    # Verify that the deviance reduction is not negative,
    # allowing for a small numerical tolerance.
    assert deviance_reduction >= -1e-8, (
        "Full model deviance exceeds reduced model deviance."
    )

    assert additional_parameters > 0, (
        "Full model must have more parameters."
    )

    # Return a dictionary containing:
    # "reduced_deviance"
    # "full_deviance"
    # "deviance_reduction"
    # "additional_parameters"
    results = {
        "reduced_deviance": reduced_deviance,
        "full_deviance": full_deviance,
        "deviance_reduction": deviance_reduction,
        "additional_parameters": additional_parameters
    }

    return results


def calculate_rate_errors(model_table, result, X):
    """
    Calculate in-sample explanatory MAE and RMSE
    in percentage points.

    Each borough-year receives equal weight.
    """

    assert model_table.index.equals(X.index), (
        "Model table and design matrix indices do not match."
    )

    observed_rate = model_table["adverse_count"] / model_table["cohort_count"]

    fitted_rate = result.predict(X)

    assert fitted_rate.index.equals(model_table.index), (
        "Fitted probabilities and model table indices do not match."
    )

    residuals = observed_rate - fitted_rate

    mae_pp = 100* residuals.abs().mean()
    rmse_pp = 100 * np.sqrt((residuals**2).mean())

    return {
        "mae_pp": mae_pp,
        "rmse_pp": rmse_pp
    }


def calculate_pearson_residuals(model_table, result, X):
    """
    Calculate borough-year Pearson residuals using
    observed adverse counts and fitted probabilities.

    Return a pandas Series preserving the original row index.
    """

    # Verify row alignment.
    assert model_table.index.equals(X.index), (
        "Model table and design matrix indices do not match."
    )

    # Extract observed adverse counts
    # and cohort denominators.
    adverse = model_table["adverse_count"].copy()
    cohort = model_table["cohort_count"].copy()

    # Obtain fitted probabilities.
    fitted_adverse_rate = result.predict(X)

    assert fitted_adverse_rate.index.equals(model_table.index), (
        "Fitted probabilities and model table indices do not match."
    )

    # Calculate expected adverse counts
    # and their binomial variances.
    expected_adverse_count = cohort * fitted_adverse_rate
    binomial_variance = cohort * fitted_adverse_rate * (1 - fitted_adverse_rate)

    assert (binomial_variance > 0).all(), (
        "Binomial variance must be positive."
    )

    # Calculate Pearson residuals.
    pearson_residuals = (adverse - expected_adverse_count) / np.sqrt(binomial_variance)

    return pearson_residuals


def calculate_pearson_dispersion(pearson_residuals, df_resid):
    """Calculate Pearson dispersion from residuals and residual degrees of freedom."""

    assert df_resid > 0, (
        "Residual degrees of freedom must be positive."
    )

    assert np.isfinite(
        np.asarray(pearson_residuals, dtype=float)
    ).all(), "Pearson residuals must be finite."

    # Calculate the Pearson chi-square statistic.
    pearson_chi2 = (pearson_residuals**2).sum()

    # Divide by the residual degrees of freedom.
    pearson_dispersion_ratio = pearson_chi2 / df_resid

    return pearson_dispersion_ratio


def build_explanatory_residual_table(model_table, result, X):
    """
    Build a borough-year residual diagnostics table.

    Preserve the original row index and ordering.
    All rate residuals are observed minus fitted.
    """

    # Verify row alignment.
    assert model_table.index.equals(X.index), (
        "Model table and design matrix indices do not match."
    )

    # Start with identifying information and observed counts.
    residual_table = model_table[
        [
            "new_la_code",
            "la_name",
            "time_period",
            "cohort_count",
            "adverse_count",
        ]
    ].copy()

    # Calculate the observed adverse rate.
    residual_table["observed_adverse_rate"] = residual_table["adverse_count"] / residual_table["cohort_count"]

    # Obtain the fitted adverse probabilities.
    fitted_rate = result.predict(X)

    assert fitted_rate.index.equals(residual_table.index), (
        "Fitted probabilities and residual table indices do not match."
    )

    residual_table["fitted_adverse_rate"] = fitted_rate

    # Calculate the rate residual in percentage points.
    # Positive means the model underestimates the adverse rate.
    residual_table["rate_residual_pp"] = 100 * (residual_table["observed_adverse_rate"] - residual_table["fitted_adverse_rate"])

    # Obtain Pearson residuals
    residual_table["pearson_residual"] = calculate_pearson_residuals(model_table, result, X)

    return residual_table


def build_lagged_residual_pairs(residual_table):
    """
    Pair each borough's Pearson residual with its
    residual from the immediately preceding cohort.

    Return one row per borough × adjacent-cohort pair.
    """

    # Select the columns needed for temporal diagnostics.
    columns = [
        "new_la_code",
        "la_name",
        "time_period",
        "pearson_residual",
    ]

    pairs = residual_table[columns].copy()

    # Sort by borough code and cohort year,
    # ensuring chronological ordering.
    pairs = pairs.sort_values(["new_la_code","time_period"])

    # Within each borough, create a new column:
    # "previous_pearson_residual"
    # containing the preceding cohort's residual.
    pairs["previous_pearson_residual"] = pairs.groupby("new_la_code")["pearson_residual"].shift(1)

    # Remove rows without a preceding cohort.
    pairs = pairs.dropna(subset=["previous_pearson_residual"])

    # Verify that exactly 192 adjacent-cohort
    # pairs remain.
    assert len(pairs) == 192, (
        f"Expected 192 pairs, got {len(pairs)}."
    )

    return pairs


def calculate_lag1_residual_correlation(pairs):
    """
    Calculate the descriptive Pearson correlation between
    consecutive within-borough residuals.
    """

    correlation_coeff = pairs["previous_pearson_residual"].corr(pairs["pearson_residual"])

    return correlation_coeff


def build_explanatory_influence_table(residual_table, result):
    """
    Combine borough-year residual diagnostics with
    GLM leverage and Cook's distance.

    Preserve the original observation index.
    """

    # Obtain influence diagnostics from statsmodels.
    influence = result.get_influence()
    influence_frame = influence.summary_frame()

    # Verify influence_frame has the same index
    # as residual_table.
    assert influence_frame.index.equals(residual_table.index), (
        "Influence statistics and residual table indices do not match."
    )

    # Copy the relevant columns from residual_table:
    columns = [
        "new_la_code",
        "la_name",
        "time_period",
        "cohort_count",
        "fitted_adverse_rate",
        "rate_residual_pp",
        "pearson_residual"
    ]
    influence_table = residual_table[columns].copy()

    # Add leverage from influence_frame["hat_diag"].
    influence_table["hat_diag"] = influence_frame["hat_diag"]

    # Add Cook's distance from influence_frame["cooks_d"].
    influence_table["cooks_d"] = influence_frame["cooks_d"]

    return influence_table
