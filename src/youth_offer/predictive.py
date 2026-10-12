import pandas as pd
from sklearn.linear_model import QuantileRegressor


M1_FEATURE_COLUMNS = [
    "feature_adverse_rate",
    "feature_fsm_share",
    "feature_identified_sen_share",
]

DEVELOPMENT_TARGET_YEARS = [
    "201819",
    "201920",
    "202021",
    "202122",
]


def build_m1_estimator() -> QuantileRegressor:
    """Construct the frozen M1 estimator."""

    return QuantileRegressor(
        quantile=0.5,
        alpha=0.0,
        fit_intercept=True,
        solver="highs",
    )


def split_development_fold(
    transitions: pd.DataFrame,
    target_year: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create one expanding-window development fold.

    Training:
        transitions whose target year is strictly earlier
        than target_year.

    Test:
        transitions whose target year equals target_year.
    """

    # 1. Select all rows with target_year strictly before target_year.
    # 2. Select all rows with target_year equal to target_year.
    # 3. Return copies of both DataFrames.
    train = transitions.loc[transitions["target_year"] < target_year].copy()
    test = transitions.loc[transitions["target_year"] == target_year].copy()

    return train, test


def fit_m1_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    ) -> tuple[QuantileRegressor, pd.Series]:

    x_train = train[M1_FEATURE_COLUMNS]
    y_train = train["target_adverse_rate"]
    x_test = test[M1_FEATURE_COLUMNS]

    estimator = build_m1_estimator()

    # Fit estimator using x_train and y_train.
    estimator.fit(x_train, y_train)

    # Generate predictions for x_test.
    predictions = estimator.predict(x_test)

    # Convert predictions to a Series aligned with the test rows.
    predictions = pd.Series(
        predictions,
        index=test.index,
        name="m1_prediction",
    )

    return estimator, predictions