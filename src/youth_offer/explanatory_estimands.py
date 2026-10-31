"""Probability-scale summaries of the frozen explanatory E4 model.

This module concerns explanatory associations, not predictive evaluation.
"""

import numpy as np
import pandas as pd


COHORT_YEARS = (
    "201617", "201718", "201819", "201920",
    "202021", "202122", "202223",
)


def calculate_adjusted_year_rates(
    result,
    X: pd.DataFrame,
    model_years: tuple[str, ...],
    ) -> pd.Series:
    """Return adjusted adverse rates (%) for every year in a categorical-year fit.

    X is the reference-profile design matrix: the original 224 rows for the
    main fit, or the appropriate sampled/retained profiles for other fits.
    Every row receives equal weight, regardless of cohort denominator.

    model_years lists *all* years in the fitted model, in chronological order.
    The first year is its omitted/reference category. The design matrix must
    contain an indicator for every subsequent year, and no others.
    """
    # Routine safeguards: prevent partial year lists or incorrect column order.
    if (
        len(model_years) < 2
        or model_years != tuple(y for y in COHORT_YEARS if y in model_years)
    ):
        raise ValueError("model_years must contain fitted years in chronological order.")

    year_columns = list(model_years[1:])
    actual_year_columns = [c for c in X.columns if c in COHORT_YEARS]
    if set(actual_year_columns) != set(year_columns):
        raise ValueError("model_years does not match the fitted year indicators in X.")
    if list(X.columns) != list(result.model.exog_names):
        raise ValueError("X columns differ from the fitted model's design matrix.")

    base_X = X.copy()

    # Set every fitted year-indicator column in base_X to 0.0.
    base_X[year_columns] = 0.0

    adjusted_rates = {}

    for year in model_years:
        # Every scenario begins with the same borough/composition profiles.
        scenario_X = base_X.copy()

        # Activate the indicator for 'year', if it is not the
        # reference year (model_years[0]). Do not modify other columns.
        if year != model_years[0]:
            scenario_X[year] = 1.0

        # Predict an adverse probability for every profile using
        # the fitted result and scenario_X (NOT the original X).
        scenario_rates = result.predict(scenario_X)

        # Give every predicted probability equal weight, convert
        # the mean to percent, and save it under adjusted_rates[year].
        adjusted_rates[year] = 100 * np.mean(scenario_rates)

    return pd.Series(adjusted_rates, name="adjusted_rate_pct")


def summarise_adjusted_year_rates(adjusted_rates: pd.Series) -> pd.DataFrame:
    """Report adjusted rates and identifiable cohort contrasts in percentage points.

    Years omitted from a reduced categorical-year fit remain unavailable (NaN).
    In particular, removing 2016/17 cannot redefine the frozen baseline contrast.
    """
    if (
        adjusted_rates.empty
        or not adjusted_rates.index.is_unique
        or not set(adjusted_rates.index).issubset(COHORT_YEARS)
    ):
        raise ValueError("Expected unique, recognised cohort years.")

    rates = adjusted_rates.astype(float)
    if not np.isfinite(rates.to_numpy()).all():
        raise ValueError("Adjusted rates must be finite.")

    rates = rates.reindex(COHORT_YEARS)
    baseline = rates.loc["201617"]

    summary = pd.DataFrame({
        "adjusted_rate_pct": rates,
        "vs_201617_pp": rates - baseline,
        "vs_previous_pp": rates - rates.shift(1),
    })
    summary.index.name = "time_period"
    return summary


# Frozen D9e2 increments are expressed as fractions, not percentages.
COMPOSITION_INCREMENTS = {
    "fsm_share": 0.02,
    "identified_sen_share": 0.02,
    "special_school_share": 0.0025,
}


def _predict_rate_vector(result, design: pd.DataFrame) -> np.ndarray:
    """Obtain aligned, finite predictions; do not clip linear-rate sensitivities."""
    predictions = result.predict(design)
    if isinstance(predictions, pd.Series) and not predictions.index.equals(design.index):
        raise ValueError("Prediction rows are not aligned with reference profiles.")

    rates = np.asarray(predictions, dtype=float)
    if rates.shape != (len(design),):
        raise ValueError("Expected one predicted rate per profile.")
    if not np.isfinite(rates).all():
        raise ValueError("Predicted rates must be finite.")
    return rates


def calculate_composition_associations(
    result,
    X: pd.DataFrame,
    increments: dict[str, float] | None = None,
) -> pd.Series:
    """Average paired E4 probability differences, in percentage points.

    Preserve each profile's borough, year, and unmodified composition shares.
    The default increments are the three predeclared D9e2 comparisons.
    An explicit replacement map supports the frozen disadvantage sensitivity.
    Linear-rate robustness predictions are not clipped; inspect their range in QA.
    """
    changes = COMPOSITION_INCREMENTS if increments is None else increments

    if X.empty or list(X.columns) != list(result.model.exog_names):
        raise ValueError("Reference design matrix is empty or has incorrect columns.")
    if not changes:
        raise ValueError("At least one composition increment is required.")

    original_probabilities = _predict_rate_vector(result, X)
    associations = {}

    for column, increment in changes.items():
        if column not in X.columns:
            raise ValueError(f"Missing composition column: {column}")
        if not np.isfinite(increment) or increment <= 0 or increment >= 1:
            raise ValueError(f"Invalid composition increment for {column}.")

        original_share = X[column].to_numpy(dtype=float)
        changed_share = original_share + increment
        if (
            not np.isfinite(original_share).all()
            or ((original_share < 0) | (changed_share > 1)).any()
        ):
            raise ValueError(f"Composition comparison exceeds [0, 1]: {column}")

        scenario = X.copy()
        scenario[column] = changed_share
        changed_probabilities = _predict_rate_vector(result, scenario)

        # Subtract paired predictions BEFORE averaging; every profile has weight 1/N.
        associations[column] = 100.0 * np.mean(
            changed_probabilities - original_probabilities
        )

    return pd.Series(associations, name="difference_pp")