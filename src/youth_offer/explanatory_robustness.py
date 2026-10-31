"""D9e4: six frozen explanatory robustness checks, never predictive evaluation.

For deletions, compare full/reduced model predictions on the identical retained
reference profiles. Unidentified year contrasts are explicitly unavailable.
"""

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from youth_offer.explanatory_estimands import (
    COHORT_YEARS,
    COMPOSITION_INCREMENTS,
    calculate_adjusted_year_rates,
    calculate_composition_associations,
    summarise_adjusted_year_rates,
)

BOROUGH_COLUMN = "new_la_code"
YEAR_COLUMN = "time_period"
DISADVANTAGE_COLUMN = "disadvantaged_share_approx"
TREND_COLUMN = "cohort_trend"
REGIME_YEARS = ("201920", "202021")


def _make_design(panel: pd.DataFrame, *, proxy: str = "fsm_share", trend: bool = False):
    """Build an E4-equivalent design, omitting only absent borough/year levels."""
    years = tuple(y for y in COHORT_YEARS if y in set(panel[YEAR_COLUMN]))
    if len(years) < 2 or not panel[YEAR_COLUMN].isin(years).all():
        raise ValueError("Expected at least two recognised cohort years.")

    boroughs = pd.Series(
        pd.Categorical(
            panel[BOROUGH_COLUMN],
            categories=sorted(panel[BOROUGH_COLUMN].unique()),
        ),
        index=panel.index,
    )
    borough_dummies = pd.get_dummies(boroughs, drop_first=True, dtype=float)
    if trend:
        trend_values = panel[YEAR_COLUMN].map(
            {year: index for index, year in enumerate(COHORT_YEARS)}
        ).astype(float)
        year_design = pd.DataFrame({TREND_COLUMN: trend_values}, index=panel.index)
    else:
        year = pd.Series(
            pd.Categorical(panel[YEAR_COLUMN], categories=years, ordered=True),
            index=panel.index,
        )
        year_design = pd.get_dummies(year, drop_first=True, dtype=float)

    shares = panel[[proxy, "identified_sen_share", "special_school_share"]].astype(float)
    X = pd.concat([borough_dummies, year_design, shares], axis=1)
    X = sm.add_constant(X, has_constant="add")
    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Explanatory design contains non-finite values.")
    if np.linalg.matrix_rank(X.to_numpy(dtype=float)) != X.shape[1]:
        raise ValueError("Reduced explanatory design is rank deficient.")
    return X, years


def _fit_sensitivity(panel: pd.DataFrame, *, proxy="fsm_share", trend=False, ols=False):
    X, years = _make_design(panel, proxy=proxy, trend=trend)
    counts = panel[["adverse_count", "cohort_count"]].to_numpy(dtype=float)
    if (
        not np.isfinite(counts).all()
        or (counts[:, 1] <= 0).any()
        or (counts[:, 0] < 0).any()
        or (counts[:, 0] > counts[:, 1]).any()
    ):
        raise ValueError("Invalid grouped outcome counts.")
    if ols:
        fitted = sm.OLS(counts[:, 0] / counts[:, 1], X).fit()
    else:
        endog = np.column_stack([counts[:, 0], counts[:, 1] - counts[:, 0]])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fitted = sm.GLM(endog, X, family=sm.families.Binomial()).fit(maxiter=100)
        flagged = [
            warning for warning in caught
            if issubclass(warning.category, RuntimeWarning)
            or warning.category.__name__ in {
                "PerfectSeparationWarning", "ConvergenceWarning"
            }
        ]
        if flagged or not fitted.converged:
            messages = [str(warning.message) for warning in flagged[:2]]
            raise ValueError(f"Non-converged/warned sensitivity fit: {messages}")
    if not np.isfinite(np.asarray(fitted.params, dtype=float)).all():
        raise ValueError("Non-finite sensitivity coefficients.")
    return fitted, X, years


def _estimates(result, X: pd.DataFrame, *, years=COHORT_YEARS, trend=False, proxy="fsm_share") -> pd.Series:
    """Apply the SAME paired standardisation definitions to each fitted model."""
    if trend:
        year_rates = {}
        for index, year in enumerate(COHORT_YEARS):
            scenario = X.copy()
            scenario[TREND_COLUMN] = float(index)
            pred = np.asarray(result.predict(scenario), dtype=float)
            if pred.shape != (len(X),) or not np.isfinite(pred).all():
                raise ValueError("Invalid trend-scenario predictions.")
            year_rates[year] = 100 * pred.mean()
        year_rates = pd.Series(year_rates)
    else:
        year_rates = calculate_adjusted_year_rates(result, X, years)
    summary = summarise_adjusted_year_rates(year_rates)
    increments = dict(COMPOSITION_INCREMENTS)
    if proxy != "fsm_share":
        increments[proxy] = increments.pop("fsm_share")
    composition = calculate_composition_associations(result, X, increments=increments)

    out = {}
    for year in COHORT_YEARS:
        out[f"rate_pct:{year}"] = summary.at[year, "adjusted_rate_pct"]
    for year in COHORT_YEARS[1:]:
        out[f"baseline_pp:{year}"] = summary.at[year, "vs_201617_pp"]
        out[f"adjacent_pp:{year}"] = summary.at[year, "vs_previous_pp"]
    for column in increments:
        out[f"composition_pp:{column}"] = composition.at[column]
    return pd.Series(out, dtype=float)


def _comparison(check: str, case: str, full: pd.Series, alternative: pd.Series, reference_rows: int) -> pd.DataFrame:
    """Tidy paired comparison; never equate FSM and disadvantage effects."""
    rows = []
    for estimand in list(dict.fromkeys([*full.index, *alternative.index])):
        original = full.get(estimand, np.nan)
        changed = alternative.get(estimand, np.nan)
        if estimand in ("composition_pp:fsm_share", f"composition_pp:{DISADVANTAGE_COLUMN}") and check == "disadvantage_proxy":
            status = "different_proxy"
            # Report the two associations separately, without subtracting them.
            if estimand == "composition_pp:fsm_share":
                changed = np.nan
            else:
                original = np.nan
        elif not (np.isfinite(original) and np.isfinite(changed)):
            status = "not_estimable"
            original, changed = np.nan, np.nan
        else:
            status = "comparable"
        rows.append({
            "check": check, "case": case, "estimand": estimand,
            "full_on_retained": original,
            "sensitivity_on_retained": changed,
            "difference_sensitivity_minus_full": changed - original if status == "comparable" else np.nan,
            "status": status, "reference_rows": reference_rows,
        })
    return pd.DataFrame(rows)


def run_d9e4_robustness(panel: pd.DataFrame, result_e4, X_e4: pd.DataFrame) -> pd.DataFrame:
    """Run all six predeclared robustness groups; return every case/estimand.

    Required inputs are the actual explanatory modelling panel and its verified
    *full* E4 result/design. All model fits remain explanatory, including 2022/23.
    """
    required = {
        BOROUGH_COLUMN, YEAR_COLUMN, "adverse_count", "cohort_count",
        "fsm_share", "identified_sen_share", "special_school_share", DISADVANTAGE_COLUMN,
    }
    if required.difference(panel.columns):
        raise ValueError(f"Missing robustness columns: {sorted(required.difference(panel.columns))}")
    if (
        len(panel) != 224
        or panel[BOROUGH_COLUMN].nunique() != 32
        or set(panel[YEAR_COLUMN]) != set(COHORT_YEARS)
    ):
        raise ValueError("Expected original 32-borough, seven-cohort explanatory panel.")
    if panel.duplicated([BOROUGH_COLUMN, YEAR_COLUMN]).any() or panel[list(required)].isna().any().any():
        raise ValueError("Duplicate/missing explanatory observations.")
    if not X_e4.index.equals(panel.index) or list(X_e4.columns) != list(result_e4.model.exog_names):
        raise ValueError("Original fitted E4 design must align with model-table rows and coefficients.")
    if not np.array_equal(
        X_e4.to_numpy(dtype=float), np.asarray(result_e4.model.exog, dtype=float)
    ):
        raise ValueError("Original E4 matrix values must match fitted data.")

    results = []
    full_original = _estimates(result_e4, X_e4)

    # 1. Rate-scale OLS, equal weights. No clipping of linear predictions.
    fitted, X, years = _fit_sensitivity(panel, ols=True)
    results.append(_comparison("equal_weight_ols", "all", full_original, _estimates(fitted, X, years=years), len(panel)))

    # 2. Alternative approximate disadvantage proxy, NOT the same FSM effect.
    fitted, X, years = _fit_sensitivity(panel, proxy=DISADVANTAGE_COLUMN)
    results.append(_comparison("disadvantage_proxy", "all", full_original,
                               _estimates(fitted, X, years=years, proxy=DISADVANTAGE_COLUMN), len(panel)))

    # 3. Leave one borough out, refit E4; both evaluations use retained profiles.
    for borough in sorted(panel[BOROUGH_COLUMN].unique()):
        kept = panel[BOROUGH_COLUMN] != borough
        retained = panel.loc[kept]
        fitted, X, years = _fit_sensitivity(retained)
        results.append(_comparison("leave_one_borough_out", borough,
                                   _estimates(result_e4, X_e4.loc[kept]),
                                   _estimates(fitted, X, years=years), len(retained)))

    # 4. Leave one cohort out; missing-year contrasts must not be extrapolated.
    for year in COHORT_YEARS:
        kept = panel[YEAR_COLUMN] != year
        retained = panel.loc[kept]
        fitted, X, years = _fit_sensitivity(retained)
        results.append(_comparison("leave_one_cohort_out", year,
                                   _estimates(result_e4, X_e4.loc[kept]),
                                   _estimates(fitted, X, years=years), len(retained)))

    # 5. Exclude BOTH unusual years, not individually selected alternatives.
    kept = ~panel[YEAR_COLUMN].isin(REGIME_YEARS)
    retained = panel.loc[kept]
    fitted, X, years = _fit_sensitivity(retained)
    results.append(_comparison("exclude_201920_202021", "joint", _estimates(result_e4, X_e4.loc[kept]),
                               _estimates(fitted, X, years=years), len(retained)))

    # 6. Linear cohort trend rather than categorical year fixed effects.
    fitted, X, years = _fit_sensitivity(panel, trend=True)
    results.append(_comparison("linear_cohort_trend", "all", full_original,
                               _estimates(fitted, X, trend=True), len(panel)))
    return pd.concat(results, ignore_index=True)
