"""D9f: historically bounded final-prediction preflight and explicitly gated scoring.

The preflight does not construct, read or score the 2022/23 predictive target.
Only the separately called score_released_final() accepts the 2022/23 source.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from youth_offer import baselines, evaluation, model_tables, predictive, qa


HISTORY_YEARS = frozenset({
    "201617", "201718", "201819", "201920", "202021", "202122",
})
FINAL_FEATURE_YEAR = "202122"
LOCKED_TARGET_YEAR = "202223"
EXPECTED_BOROUGHS = 32
EXPECTED_HISTORY_ROWS = 6 * EXPECTED_BOROUGHS
EXPECTED_TRAINING_ROWS = 5 * EXPECTED_BOROUGHS
FINAL_PREDICTION_COLUMNS = (
    "b1_borough_persistence",
    "b2_london_persistence",
    "b3_london_plus_borough_offset",
    "m1_prediction",
)


def build_historical_table(london_historical_rows: pd.DataFrame) -> pd.DataFrame:
    """Derive only historic outcomes and lagged composition from a six-cohort slice.

    Caller must remove 2022/23 *before* entering any outcome constructor.
    Fail rather than silently trimming unexpected/locked input here.
    """
    if set(london_historical_rows["time_period"]) != HISTORY_YEARS:
        raise AssertionError("Historical raw slice must contain exactly 2016/17–2021/22.")

    headline = model_tables.build_headline_outcome_table(london_historical_rows)
    # The existing source-accounting QA also works on the historical-only slice.
    qa.assert_fsm_sen_source_accounting(london_historical_rows, headline)
    if not (
        headline[model_tables.SUSTAINED]
        + headline[model_tables.NOT_RECORDED]
        + headline[model_tables.ACTIVITY_NOT_CAPTURED]
    ).eq(headline["cohort_count"]).all():
        raise AssertionError("Historical headline destination counts do not reconcile.")
    composition = model_tables.build_fsm_sen_composition(
        london_historical_rows, headline
    )
    history = headline.merge(
        composition[[
            "time_period", "new_la_code", "fsm_eligible_count",
            "identified_sen_count", "fsm_share", "identified_sen_share",
        ]],
        on=["time_period", "new_la_code"],
        how="left",
        validate="one_to_one",
    )
    validate_historical_table(history)
    return history


def validate_historical_table(history: pd.DataFrame) -> None:
    """Guard the exact, complete, historical-only 32-borough × 6-cohort panel."""
    key = ["new_la_code", "time_period"]
    if len(history) != EXPECTED_HISTORY_ROWS:
        raise AssertionError("Historical panel must contain exactly 192 rows.")
    if set(history["time_period"]) != HISTORY_YEARS:
        raise AssertionError("Historical panel has missing, extra or locked years.")
    if history.duplicated(key).any():
        raise AssertionError("Duplicate historical borough/year key.")
    if not history.groupby("time_period")["new_la_code"].nunique().eq(32).all():
        raise AssertionError("Historical panel lacks 32 boroughs in every year.")
    if history["new_la_code"].nunique() != EXPECTED_BOROUGHS:
        raise AssertionError("Borough identities change between historical cohorts.")
    if not history.groupby("new_la_code")["time_period"].nunique().eq(6).all():
        raise AssertionError("Incomplete borough history.")

    numeric = [
        "adverse_rate", "adverse_count", "cohort_count",
        "fsm_eligible_count", "identified_sen_count",
        "fsm_share", "identified_sen_share",
    ]
    values = history[numeric].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise AssertionError("Missing/nonfinite historical model input.")
    if not history["cohort_count"].gt(0).all():
        raise AssertionError("Nonpositive historical cohort size.")
    if not history[["adverse_rate", "fsm_share", "identified_sen_share"]].ge(0).all().all():
        raise AssertionError("Negative historical proportion.")
    if not history[["adverse_rate", "fsm_share", "identified_sen_share"]].le(1).all().all():
        raise AssertionError("Historical proportion exceeds one.")
    for count, rate in (
        ("adverse_count", "adverse_rate"),
        ("fsm_eligible_count", "fsm_share"),
        ("identified_sen_count", "identified_sen_share"),
    ):
        np.testing.assert_allclose(
            history[count].to_numpy(dtype=float) / history["cohort_count"].to_numpy(dtype=float),
            history[rate].to_numpy(dtype=float), rtol=1e-12, atol=1e-12,
        )


def prepare_unscored_final_forecasts(
    history: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Return 32 *unscored* forecasts from six historical cohorts only.

    Uses D9a's five training transitions, frozen B1–B3 and M1. No target
    from 2022/23 is accepted or constructed by this function.
    """
    validate_historical_table(history)
    transitions = model_tables.build_development_transition_table(history)
    qa.assert_development_transition_table(transitions)
    qa.assert_transition_source_alignment(transitions, history)
    if len(transitions) != EXPECTED_TRAINING_ROWS:
        raise AssertionError("Final M1 requires exactly five past transitions.")
    if transitions["target_year"].max() != FINAL_FEATURE_YEAR:
        raise AssertionError("Final M1 training includes an unexpected target year.")

    origin = (
        history.loc[
            history["time_period"].eq(FINAL_FEATURE_YEAR),
            [
                "new_la_code", "la_name", "time_period", "adverse_rate",
                "fsm_share", "identified_sen_share",
            ],
        ]
        .rename(columns={
            "time_period": "feature_year",
            "adverse_rate": "feature_adverse_rate",
            "fsm_share": "feature_fsm_share",
            "identified_sen_share": "feature_identified_sen_share",
        })
        .sort_values("new_la_code")
        .reset_index(drop=True)
    )
    if len(origin) != EXPECTED_BOROUGHS or origin["new_la_code"].duplicated().any():
        raise AssertionError("Final feature-origin boroughs are incomplete.")

    benchmark = baselines.add_baseline_predictions(origin, history)
    qa.assert_baseline_predictions(benchmark, history)
    fitted, predictions = predictive.fit_m1_fold(transitions, benchmark)
    qa.assert_m1_fit(transitions, benchmark, predictions, fitted)

    forecast = benchmark[[
        "new_la_code", "la_name", "feature_year",
        "b1_borough_persistence", "b2_london_persistence",
        "b3_london_plus_borough_offset",
    ]].copy()
    forecast["m1_prediction"] = predictions
    forecast_values = forecast[list(FINAL_PREDICTION_COLUMNS)].to_numpy(dtype=float)
    if not np.isfinite(forecast_values).all():
        raise AssertionError("Nonfinite final preflight forecasts.")
    if not forecast["new_la_code"].is_unique:
        raise AssertionError("Duplicate final preflight borough.")
    if set(forecast["new_la_code"]) != set(origin["new_la_code"]):
        raise AssertionError("Final preflight borough set changed.")

    x = np.column_stack([
        np.ones(len(transitions)),
        transitions[predictive.M1_FEATURE_COLUMNS].to_numpy(dtype=float),
    ])
    invalid_forecasts = int(((forecast_values < 0) | (forecast_values > 1)).sum())
    report = {
        "stage": "historical_only_preflight_no_202223_targets",
        "training_rows": int(len(transitions)),
        "training_target_max": str(transitions["target_year"].max()),
        "feature_origin_year": FINAL_FEATURE_YEAR,
        "forecast_boroughs": int(len(forecast)),
        "design_rank": int(np.linalg.matrix_rank(x)),
        "coefficients_finite": bool(np.isfinite(fitted.intercept_) and np.isfinite(fitted.coef_).all()),
        "forecast_values_finite": True,
        "forecasts_outside_unit_interval": invalid_forecasts,
    }
    # Diagnostic trigger from D9a10: never clip invalid forecasts.
    if invalid_forecasts:
        raise AssertionError("Invalid probability forecasts: investigate before releasing the holdout.")
    return forecast, report


def score_released_final(
    forecasts: pd.DataFrame,
    released_202223_raw_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """PERMISSION-GATED BY CALLER: score against the final cohort.

    This function must be called *only after explicit user authorisation*.
    Its unit tests use invented synthetic data, never genuine 2022/23 results.
    """
    if set(released_202223_raw_rows["time_period"]) != {LOCKED_TARGET_YEAR}:
        raise AssertionError("Release source must be the single locked target cohort.")
    if len(forecasts) != EXPECTED_BOROUGHS or not forecasts["new_la_code"].is_unique:
        raise AssertionError("Expected one frozen forecast per borough.")
    if set(forecasts["feature_year"]) != {FINAL_FEATURE_YEAR}:
        raise AssertionError("Frozen forecasts have the wrong feature-year origin.")
    target = model_tables.build_headline_outcome_table(released_202223_raw_rows)
    if len(target) != EXPECTED_BOROUGHS or not target["new_la_code"].is_unique:
        raise AssertionError("Final target requires 32 unique boroughs.")
    if not (
        target[model_tables.SUSTAINED]
        + target[model_tables.NOT_RECORDED]
        + target[model_tables.ACTIVITY_NOT_CAPTURED]
    ).eq(target["cohort_count"]).all():
        raise AssertionError("Released target destination counts do not reconcile.")
    if set(target["new_la_code"]) != set(forecasts["new_la_code"]):
        raise AssertionError("Final targets do not match the frozen forecast boroughs.")

    paired = forecasts.merge(
        target[["new_la_code", "la_name", "adverse_rate", "cohort_count"]],
        on="new_la_code", how="inner", validate="one_to_one",
        suffixes=("_forecast", "_target"),
    )
    if not paired["la_name_forecast"].eq(paired["la_name_target"]).all():
        raise AssertionError("Forecast/target borough names differ.")
    if not np.isfinite(paired[[
        "adverse_rate", "cohort_count", *FINAL_PREDICTION_COLUMNS,
    ]].to_numpy(dtype=float)).all():
        raise AssertionError("Nonfinite final scoring values.")
    if not paired["cohort_count"].gt(0).all():
        raise AssertionError("Invalid final evaluation cohort denominator.")
    if not paired["adverse_rate"].between(0, 1).all():
        raise AssertionError("Invalid final target adverse rate.")

    scoring_input = paired.rename(columns={
        "adverse_rate": "target_adverse_rate_baseline",
        "cohort_count": "target_cohort_count_baseline",
    }).copy()
    scoring_input["target_year"] = LOCKED_TARGET_YEAR
    annual = evaluation.calculate_development_annual_metrics(scoring_input)
    if len(annual) != 4 or set(annual["method"]) != {"B1", "B2", "B3", "M1"}:
        raise AssertionError("Final scoring requires exactly the four frozen methods.")
    if set(annual["target_year"]) != {LOCKED_TARGET_YEAR}:
        raise AssertionError("Final scoring has an unexpected target-year label.")
    return scoring_input.sort_values("new_la_code").reset_index(drop=True), annual
