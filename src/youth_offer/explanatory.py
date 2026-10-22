import numpy as np
import pandas as pd
import statsmodels.api as sm


def fit_e1(model_table: pd.DataFrame):
    """Fit the cohort-year-only grouped-binomial GLM."""

    adverse = model_table["adverse_count"].to_numpy(dtype=float)
    cohort = model_table["cohort_count"].to_numpy(dtype=float)

    # Construct the two-column binomial outcome.
    # Columns: adverse count, non-adverse count.
    outcome_counts = np.column_stack([
        adverse,
        cohort-adverse
    ])

    # Construct categorical cohort-year predictors.
    # Use 2016/17 (201617) as the reference year.
    # Include an intercept and six year indicators.
    # All design-matrix values must be numeric floats.
    years = pd.Series(
                pd.Categorical(
                    model_table["time_period"],
                    categories=["201617", "201718", "201819", "201920", "202021", "202122", "202223"],
                    ordered=True
                ),
                index=model_table.index
            )

    X = pd.get_dummies(
            years,
            drop_first=True,
            dtype=float
        )
    X = sm.add_constant(X)

    # Fit the grouped-binomial GLM with a logit link.
    model = sm.GLM(
                outcome_counts,
                X,
                family=sm.families.Binomial())
    result = model.fit()

    return result, X


def fit_e2(model_table: pd.DataFrame):
    """Fit the borough-only grouped-binomial GLM."""

    adverse = model_table["adverse_count"].to_numpy(dtype=float)
    cohort = model_table["cohort_count"].to_numpy(dtype=float)

    # Construct the two-column binomial outcome.
    # Columns: adverse count, non-adverse count.
    outcome_counts = np.column_stack([
        adverse,
        cohort-adverse
    ])

    # Construct categorical borough predictors.
    # Use the first borough sorted by new_la_code in ascending order as the reference borough.
    # Include an intercept and 31 borough indicators.
    # All design-matrix values must be numeric floats.
    boroughs = pd.Series(
                pd.Categorical(
                    model_table["new_la_code"],
                    categories=sorted(model_table['new_la_code'].unique()),
                    ordered=True
                ),
                index=model_table.index
            )

    X = pd.get_dummies(
            boroughs,
            drop_first=True,
            dtype=float
        )
    X = sm.add_constant(X)

    # Fit the grouped-binomial GLM with a logit link.
    model = sm.GLM(
                outcome_counts,
                X,
                family=sm.families.Binomial())
    result = model.fit()

    return result, X


def fit_e3(model_table: pd.DataFrame):
    """Fit the borough + cohort-year grouped-binomial GLM."""

    # Construct grouped-binomial outcome.
    adverse = model_table["adverse_count"].to_numpy(dtype=float)
    cohort = model_table["cohort_count"].to_numpy(dtype=float)
    outcome_counts = np.column_stack([
        adverse,
        cohort-adverse
    ])

    # Construct 31 borough indicators.
    # Use the same reference borough as E2.
    boroughs = pd.Series(
                    pd.Categorical(
                        model_table["new_la_code"],
                        categories=sorted(model_table['new_la_code'].unique()),
                        ordered=True
                    ),
                    index=model_table.index
                )

    borough_indicators = pd.get_dummies(
                            boroughs,
                            drop_first=True,
                            dtype=float
                         )

    # Construct 6 cohort-year indicators.
    # Use 201617 as the reference year.
    years = pd.Series(
                pd.Categorical(
                    model_table["time_period"],
                    categories=["201617", "201718", "201819", "201920", "202021", "202122", "202223"],
                    ordered=True
                ),
                index=model_table.index
            )

    year_indicators = pd.get_dummies(
                        years,
                        drop_first=True,
                        dtype=float
                        )

    # Combine indicators into one design matrix.
    # Add one intercept.
    X = pd.concat([borough_indicators,year_indicators], axis=1)
    X = sm.add_constant(X)

    # Fit grouped-binomial logistic GLM.
    model = sm.GLM(
                outcome_counts,
                X,
                family=sm.families.Binomial())
    result = model.fit()

    return result, X


def fit_e4(model_table: pd.DataFrame):
    """Fit the borough + cohort-year + FSM + SEN + Special grouped-binomial GLM."""

    # Construct grouped-binomial outcome.
    adverse = model_table["adverse_count"].to_numpy(dtype=float)
    cohort = model_table["cohort_count"].to_numpy(dtype=float)
    outcome_counts = np.column_stack([
        adverse,
        cohort-adverse
    ])

    # Construct 31 borough indicators.
    # Use the same reference borough as E2.
    boroughs = pd.Series(
                    pd.Categorical(
                        model_table["new_la_code"],
                        categories=sorted(model_table['new_la_code'].unique()),
                        ordered=True
                    ),
                    index=model_table.index
                )

    borough_indicators = pd.get_dummies(
                            boroughs,
                            drop_first=True,
                            dtype=float
                         )

    # Construct 6 cohort-year indicators.
    # Use 201617 as the reference year.
    years = pd.Series(
                pd.Categorical(
                    model_table["time_period"],
                    categories=["201617", "201718", "201819", "201920", "202021", "202122", "202223"],
                    ordered=True
                ),
                index=model_table.index
            )

    year_indicators = pd.get_dummies(
                        years,
                        drop_first=True,
                        dtype=float
                        )

    # Extract fsm, sen and special share
    composition_columns = [
        "fsm_share",
        "identified_sen_share",
        "special_school_share",
    ]

    composition_df = model_table[composition_columns].astype("float64")

    # Combine indicators into one design matrix.
    # Add one intercept.
    X = pd.concat([borough_indicators, year_indicators, composition_df], axis=1)
    X = sm.add_constant(X)

    # Fit grouped-binomial logistic GLM.
    model = sm.GLM(
                outcome_counts,
                X,
                family=sm.families.Binomial())
    result = model.fit()

    return result, X
