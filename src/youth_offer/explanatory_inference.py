"""D9e3 inference for the frozen E4 explanatory grouped-binomial model.

Primary: whole-borough-trajectory pairs bootstrap with replacement.
Secondary: borough-clustered CR1 covariance and probability-scale delta intervals.
This module never imports or evaluates the predictive track.
"""

from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit
from scipy.stats import t
from statsmodels.stats.sandwich_covariance import cov_cluster
from statsmodels.tools.sm_exceptions import PerfectSeparationError

from youth_offer.explanatory_estimands import (
    COHORT_YEARS,
    COMPOSITION_INCREMENTS,
    calculate_adjusted_year_rates,
    calculate_composition_associations,
    summarise_adjusted_year_rates,
)

# Frozen in code before any real-data bootstrap estimates are calculated.
BOOTSTRAP_SEED = 20261030
BOOTSTRAP_ATTEMPTS = 2000
COMPOSITION_COLUMNS = tuple(COMPOSITION_INCREMENTS)


@dataclass(frozen=True)
class BoroughBootstrapResult:
    """Successful refit estimates, percentile summaries and explicit failures."""

    estimates: pd.DataFrame
    intervals: pd.DataFrame
    failures: pd.DataFrame
    attempted: int
    successful: int
    failed: int
    seed: int


def calculate_d9e_estimates(result, X: pd.DataFrame) -> pd.Series:
    """Return the 22 frozen D9e1/D9e2 quantities, in % or percentage points.

    The supplied X defines the equally weighted reference multiset. For a
    bootstrap refit, X MUST be the sampled design matrix, not the original X.
    """
    year_rates = calculate_adjusted_year_rates(result, X, COHORT_YEARS)
    summary = summarise_adjusted_year_rates(year_rates)
    composition = calculate_composition_associations(result, X)

    estimates = {}
    for year in COHORT_YEARS:
        estimates[f"rate_pct:{year}"] = summary.at[year, "adjusted_rate_pct"]
    for year in COHORT_YEARS[1:]:
        estimates[f"baseline_pp:{year}"] = summary.at[year, "vs_201617_pp"]
        estimates[f"adjacent_pp:{year}"] = summary.at[year, "vs_previous_pp"]
    for column in COMPOSITION_COLUMNS:
        estimates[f"composition_pp:{column}"] = composition.loc[column]
    out = pd.Series(estimates, name="estimate")
    if not np.isfinite(out.to_numpy(dtype=float)).all():
        raise ValueError("D9e estimates must all be finite.")
    return out


def _validate_complete_panel(panel: pd.DataFrame) -> list[str]:
    """Validate the balanced original 32-borough by 7-cohort E4 inputs."""
    required = {"new_la_code", "time_period", "adverse_count", "cohort_count", *COMPOSITION_COLUMNS}
    if required.difference(panel.columns):
        raise ValueError(f"Missing bootstrap input columns: {sorted(required.difference(panel.columns))}")
    if panel[list(required)].isna().any().any():
        raise ValueError("Missing E4 bootstrap inputs.")
    boroughs = sorted(panel["new_la_code"].unique())
    if len(boroughs) != 32 or len(panel) != 224:
        raise ValueError("Bootstrap input must contain 32 boroughs × 7 cohorts.")
    years = set(COHORT_YEARS)
    if set(panel["time_period"]) != years or panel.duplicated(["new_la_code", "time_period"]).any():
        raise ValueError("Expected unique observations for all seven cohorts.")
    for _, group in panel.groupby("new_la_code"):
        if set(group["time_period"]) != years or len(group) != 7:
            raise ValueError("Each borough must have a complete seven-cohort history.")
    counts = panel[["adverse_count", "cohort_count"]].to_numpy(dtype=float)
    shares = panel[list(COMPOSITION_COLUMNS)].to_numpy(dtype=float)
    if (
        not np.isfinite(counts).all() or not np.isfinite(shares).all()
        or (counts[:, 1] <= 0).any() or (counts[:, 0] < 0).any()
        or (counts[:, 0] > counts[:, 1]).any()
        or ((shares < 0) | (shares > 1)).any()
    ):
        raise ValueError("Invalid grouped-binomial counts or composition shares.")
    return boroughs


def build_borough_bootstrap_sample(
    panel: pd.DataFrame, sampled_boroughs: list[str] | np.ndarray,
) -> pd.DataFrame:
    """Copy entire seven-year histories, giving EACH draw a distinct FE identity.

    Original outcomes, denominators and shares are unchanged. Columns
    '_source_la_code' and '_draw_index' are audit-only, never model predictors.
    """
    boroughs = _validate_complete_panel(panel)
    if len(sampled_boroughs) != len(boroughs) or not set(sampled_boroughs).issubset(boroughs):
        raise ValueError("Exactly 32 valid borough draws are required.")
    by_borough = {b: g for b, g in panel.groupby("new_la_code", sort=False)}
    pieces = []
    for draw_index, source in enumerate(sampled_boroughs):
        copy = by_borough[source].copy()
        copy["_source_la_code"] = source
        copy["_draw_index"] = draw_index
        copy["new_la_code"] = f"bootstrap_{draw_index:02d}"
        pieces.append(copy)
    return pd.concat(pieces, ignore_index=True)


def _fit_sampled_e4(sample: pd.DataFrame):
    """Refit exactly E4's grouped-binomial mean terms using temporary FE IDs."""
    boroughs = pd.Series(
        pd.Categorical(sample["new_la_code"], categories=sorted(sample["new_la_code"].unique())),
        index=sample.index,
    )
    years = pd.Series(
        pd.Categorical(sample["time_period"], categories=COHORT_YEARS, ordered=True),
        index=sample.index,
    )
    X = pd.concat(
        [pd.get_dummies(boroughs, drop_first=True, dtype=float),
         pd.get_dummies(years, drop_first=True, dtype=float),
         sample[list(COMPOSITION_COLUMNS)].astype(float)],
        axis=1,
    )
    X = sm.add_constant(X, has_constant="add")
    if X.shape != (224, 41) or np.linalg.matrix_rank(X.to_numpy(dtype=float)) != 41:
        raise ValueError("Sampled E4 design matrix is rank deficient or malformed.")

    outcome = sample[["adverse_count", "cohort_count"]].to_numpy(dtype=float)
    endog = np.column_stack([outcome[:, 0], outcome[:, 1] - outcome[:, 0]])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fitted = sm.GLM(endog, X, family=sm.families.Binomial()).fit(maxiter=100)
    problematic = [w for w in caught if issubclass(w.category, RuntimeWarning)
                   or w.category.__name__ in {"PerfectSeparationWarning", "ConvergenceWarning"}]
    if problematic:
        raise ValueError("Fit warning: " + "; ".join(str(w.message) for w in problematic[:2]))
    if not fitted.converged or not np.isfinite(np.asarray(fitted.params, dtype=float)).all():
        raise ValueError("Sampled E4 failed convergence/finite-coefficient checks.")
    return fitted, X


def run_e4_borough_bootstrap(
    panel: pd.DataFrame,
    *,
    n_attempts: int = BOOTSTRAP_ATTEMPTS,
    seed: int = BOOTSTRAP_SEED,
) -> BoroughBootstrapResult:
    """Attempt a predeclared number of refits; do not replace failed draws.

    Percentile intervals estimate variability of the sample-standardised
    statistic under borough resampling, not a fixed-reference standard error.
    """
    boroughs = _validate_complete_panel(panel)
    if not isinstance(n_attempts, int) or n_attempts < 1:
        raise ValueError("n_attempts must be a positive integer.")
    rng = np.random.default_rng(seed)
    successful = []
    failures = []

    for replicate in range(n_attempts):
        drawn = rng.choice(boroughs, size=len(boroughs), replace=True)
        try:
            sample = build_borough_bootstrap_sample(panel, drawn)
            fitted, X = _fit_sampled_e4(sample)
            estimates = calculate_d9e_estimates(fitted, X)
            successful.append({"replicate": replicate, **estimates.to_dict()})
        except (ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError, PerfectSeparationError) as exc:
            failures.append({"replicate": replicate, "reason": type(exc).__name__, "detail": str(exc)})

    estimates_df = pd.DataFrame(successful)
    failures_df = pd.DataFrame(failures, columns=["replicate", "reason", "detail"])
    if len(estimates_df) < 2:
        raise RuntimeError(
            f"Only {len(estimates_df)} successful bootstrap refits in {n_attempts} "
            f"attempts; review failure diagnostics: {failures_df.to_dict('records')[:5]}"
        )
    values = estimates_df.drop(columns="replicate")
    intervals = pd.DataFrame({
        "estimate_key": values.columns,
        "lower_95": values.quantile(0.025).to_numpy(),
        "upper_95": values.quantile(0.975).to_numpy(),
        "bootstrap_sd": values.std(ddof=1).to_numpy(),
    })
    return BoroughBootstrapResult(
        estimates=estimates_df,
        intervals=intervals,
        failures=failures_df,
        attempted=n_attempts,
        successful=len(estimates_df),
        failed=len(failures_df),
        seed=seed,
    )


def _e4_delta_gradients(result, X: pd.DataFrame) -> pd.DataFrame:
    """Gradient of each probability-scale estimand with respect to E4 beta."""
    if list(X.columns) != list(result.model.exog_names):
        raise ValueError("Reference design columns differ from E4 coefficient order.")
    coefficients = np.asarray(result.params, dtype=float)
    if len(coefficients) != X.shape[1] or not np.isfinite(coefficients).all():
        raise ValueError("Invalid E4 coefficient vector.")
    year_columns = list(COHORT_YEARS[1:])
    if not set(year_columns).issubset(X.columns):
        raise ValueError("Full seven-year E4 required for covariance cross-check.")
    base = X.copy()
    base[year_columns] = 0.0

    def gradient(design: pd.DataFrame) -> np.ndarray:
        x = design.to_numpy(dtype=float)
        p = expit(x @ coefficients)
        return 100.0 * np.mean((p * (1.0 - p))[:, None] * x, axis=0)

    year_gradients = {}
    for year in COHORT_YEARS:
        scenario = base.copy()
        if year != COHORT_YEARS[0]:
            scenario[year] = 1.0
        year_gradients[year] = gradient(scenario)

    gradients = {f"rate_pct:{year}": year_gradients[year] for year in COHORT_YEARS}
    for previous, year in zip(COHORT_YEARS, COHORT_YEARS[1:]):
        gradients[f"baseline_pp:{year}"] = year_gradients[year] - year_gradients[COHORT_YEARS[0]]
        gradients[f"adjacent_pp:{year}"] = year_gradients[year] - year_gradients[previous]

    baseline_grad = gradient(X)
    for column, increment in COMPOSITION_INCREMENTS.items():
        scenario = X.copy()
        scenario[column] = scenario[column].astype(float) + increment
        if (scenario[column] > 1).any() or (scenario[column] < 0).any():
            raise ValueError(f"Composition increment is outside support: {column}")
        gradients[f"composition_pp:{column}"] = gradient(scenario) - baseline_grad
    return pd.DataFrame.from_dict(gradients, orient="index", columns=X.columns)


def calculate_cluster_delta_intervals(result, X: pd.DataFrame, borough_ids: pd.Series) -> pd.DataFrame:
    """Secondary CR1 borough-clustered delta-method 95% intervals.

    cov_cluster(..., use_correction=True) applies the finite-cluster CR1
    multiplier G/(G-1) * (N-1)/(N-K). Use t_(G-1) critical values.
    These model-conditional Wald intervals are not substitutes for bootstrap
    or uncertainty across the seven common year regimes.
    """
    if not borough_ids.index.equals(X.index):
        raise ValueError("Borough groups must align exactly with the design rows.")
    if len(X) != result.nobs or X.empty:
        raise ValueError("Cluster covariance requires the original fitted observations.")
    clusters = borough_ids.nunique()
    if clusters != 32 or borough_ids.isna().any():
        raise ValueError("Expected 32 non-missing borough clusters.")
    if list(X.columns) != list(result.model.exog_names):
        raise ValueError("Cluster reference must match fitted E4 predictors.")
    if not np.array_equal(
        X.to_numpy(dtype=float),
        np.asarray(result.model.exog, dtype=float),
    ):
        raise ValueError("X must match the fitted model's design matrix.")

    # cov_cluster uses the fitted model's original row order for the scores.
    covariance = np.asarray(cov_cluster(result, borough_ids.to_numpy(), use_correction=True), dtype=float)
    gradients = _e4_delta_gradients(result, X)
    points = calculate_d9e_estimates(result, X)
    if list(gradients.index) != list(points.index):
        raise ValueError("Estimand/gradient key mismatch.")
    if not np.isfinite(covariance).all():
        raise ValueError("Non-finite cluster covariance.")

    grad = gradients.to_numpy(dtype=float)
    variances = np.einsum("ij,jk,ik->i", grad, covariance, grad)
    if (variances < -1e-10).any():
        raise ValueError("Negative delta-method variance beyond numerical tolerance.")
    se = np.sqrt(np.maximum(variances, 0))
    critical = t.ppf(0.975, df=clusters - 1)
    return pd.DataFrame({
        "estimate_key": points.index,
        "estimate": points.to_numpy(dtype=float),
        "cluster_se": se,
        "lower_95": points.to_numpy(dtype=float) - critical * se,
        "upper_95": points.to_numpy(dtype=float) + critical * se,
    })
