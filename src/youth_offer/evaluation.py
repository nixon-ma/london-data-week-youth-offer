import pandas as pd
import numpy as np
from youth_offer.predictive import DEVELOPMENT_TARGET_YEARS


KEY_COLUMNS = [
    "new_la_code",
    "feature_year",
    "target_year",
]

BASELINE_COLUMNS = [
    "b1_borough_persistence",
    "b2_london_persistence",
    "b3_london_plus_borough_offset",
]

METHOD_COLUMNS = {
    "B1": "b1_borough_persistence",
    "B2": "b2_london_persistence",
    "B3": "b3_london_plus_borough_offset",
    "M1": "m1_prediction",
}


def build_development_evaluation_table(
    baseline_predictions: pd.DataFrame,
    m1_predictions: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Align B1-B3 and M1 on the same held-out development observations.

    One row per borough and development target year.
    No performance metrics are calculated here.
    """

    # Only evaluate the four predeclared development target years.
    baseline_rows = baseline_predictions.loc[
        baseline_predictions["target_year"].isin(
            DEVELOPMENT_TARGET_YEARS
        ),
        KEY_COLUMNS
        + ["target_adverse_rate", "target_cohort_count"]
        + BASELINE_COLUMNS,
    ].copy()

    m1_rows = m1_predictions[
        KEY_COLUMNS
        + ["target_adverse_rate", "target_cohort_count", "m1_prediction"]
    ].copy()

    # Merge baselines and m1 using KEY_COLUMNS.
    #
    # Requirements:
    # 1. Match on all three key columns.
    # 2. Use an inner join.
    # 3. Require one-to-one matching.
    # 4. Add suffixes to distinguish duplicated target columns.
    evaluation = baseline_rows.merge(
        m1_rows,
        how="inner",
        on=KEY_COLUMNS,
        validate="one_to_one",
        suffixes=("_baseline", "_m1")
    )

    return evaluation.sort_values(
        ["target_year", "new_la_code"]
    ).reset_index(drop=True)


def calculate_development_annual_metrics(
    evaluation_table: pd.DataFrame,
    ) -> pd.DataFrame:
    """Calculate development forecast errors by target year and method."""

    results = []

    # Loop over each year
    for target_year, rows in evaluation_table.groupby("target_year"):
        actual = rows["target_adverse_rate_baseline"].to_numpy(
            dtype=float
        )
        target_cohort_counts = rows["target_cohort_count_baseline"].to_numpy(
            dtype=float
        )

        # Loop over each method. Calculate metrics for each method in a particular year, averaged across 32 boroughs
        for method, prediction_column in METHOD_COLUMNS.items():
            predicted = rows[prediction_column].to_numpy(dtype=float)

            errors = predicted - actual
            absolute_errors = np.abs(errors)

            # Calculate MAE, RMSE and weighted MAE.
            # All three are expressed in percentage points.
            mae_pp = np.mean(absolute_errors) * 100
            rmse_pp = np.sqrt(np.mean(errors**2)) * 100
            weighted_mae_pp = np.average(absolute_errors, weights=target_cohort_counts) * 100

            results.append({
                "target_year": target_year,
                "method": method,
                "mae_pp": mae_pp,
                "rmse_pp": rmse_pp,
                "weighted_mae_pp": weighted_mae_pp,
            })

    annual = pd.DataFrame(results)

    # B1-relative difference: positive means worse than B1.
    b1_mae_by_year = (
        annual.loc[annual["method"] == "B1"]
        .set_index("target_year")["mae_pp"]
    )

    annual["mae_minus_b1_pp"] = (
        annual["mae_pp"]
        - annual["target_year"].map(b1_mae_by_year)
    )

    return annual.sort_values(
        ["target_year", "method"]
    ).reset_index(drop=True)


def summarize_development_metrics(
    annual_metrics: pd.DataFrame,
    ) -> pd.DataFrame:
    """Compute equal-year development mean metrics for each method."""

    metric_columns = [
        "mae_pp",
        "rmse_pp",
        "weighted_mae_pp",
        "mae_minus_b1_pp",
    ]

    # Group by method, take the arithmetic mean of each
    # metric column, and return method as an ordinary column.
    summary = annual_metrics.groupby("method", as_index=False)[metric_columns].mean()

    return summary.sort_values("method").reset_index(drop=True)