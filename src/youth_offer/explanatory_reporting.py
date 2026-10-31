"""Run and save the frozen D9e explanatory estimands, inference and robustness.

Only uses the fitted explanatory E4 model and explanatory borough-year panel.
Never constructs, evaluates, or reads the locked predictive final target.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from youth_offer.explanatory_estimands import (
    COHORT_YEARS,
    calculate_adjusted_year_rates,
    calculate_composition_associations,
    summarise_adjusted_year_rates,
)
from youth_offer.explanatory_inference import (
    BOOTSTRAP_ATTEMPTS,
    BOOTSTRAP_SEED,
    calculate_cluster_delta_intervals,
    calculate_d9e_estimates,
    run_e4_borough_bootstrap,
)
from youth_offer.explanatory_robustness import run_d9e4_robustness


def run_d9e_reporting(
    explanatory_table: pd.DataFrame,
    result_e4,
    X_e4: pd.DataFrame,
    output_dir: Path,
    *,
    n_bootstrap_attempts: int = BOOTSTRAP_ATTEMPTS,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, int]:
    """Compute and save the frozen D9e1–D9e4 explanatory results.

    Default: 2,000 fixed-seed bootstrap attempts. A smaller number can be
    supplied for explicitly labelled smoke tests, not final inference.
    """
    if not explanatory_table.index.equals(X_e4.index):
        raise ValueError("Explanatory rows and E4 design must be aligned.")
    if not np.array_equal(X_e4.to_numpy(dtype=float), result_e4.model.exog):
        raise ValueError("E4 design values do not match the fitted model.")
    if len(explanatory_table) != 224 or explanatory_table.new_la_code.nunique() != 32:
        raise ValueError("D9e reporting expects the 224-row original explanatory panel.")

    point = calculate_d9e_estimates(result_e4, X_e4)
    rates = summarise_adjusted_year_rates(
        calculate_adjusted_year_rates(result_e4, X_e4, COHORT_YEARS)
    )
    associations = calculate_composition_associations(result_e4, X_e4)
    clustered = calculate_cluster_delta_intervals(
        result_e4, X_e4, explanatory_table["new_la_code"]
    )
    robustness = run_d9e4_robustness(explanatory_table, result_e4, X_e4)

    if len(point) != 22 or len(robustness) != 43 * 22 + 1:
        raise ValueError("Unexpected number of frozen estimands or robustness comparisons.")
    if set(point.index) != set(clustered.estimate_key):
        raise ValueError("Cluster cross-check and D9e estimands do not match.")

    print(f"D9e bootstrap: {n_bootstrap_attempts} predeclared attempts, seed={bootstrap_seed}.", flush=True)
    bootstrap = run_e4_borough_bootstrap(
        explanatory_table, n_attempts=n_bootstrap_attempts, seed=bootstrap_seed
    )
    if (
        bootstrap.attempted != bootstrap.successful + bootstrap.failed
        or set(bootstrap.intervals.estimate_key) != set(point.index)
    ):
        raise ValueError("Bootstrap attempt counts or estimand keys are inconsistent.")

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    point.rename_axis("estimate_key").reset_index().to_csv(
        directory / "d9e_point_estimates.csv", index=False
    )
    rates.to_csv(directory / "d9e_adjusted_years.csv")
    associations.rename_axis("composition_variable").reset_index().to_csv(
        directory / "d9e_composition_associations.csv", index=False
    )
    clustered.to_csv(directory / "d9e_cluster_delta_intervals.csv", index=False)
    bootstrap.intervals.to_csv(directory / "d9e_bootstrap_intervals.csv", index=False)
    bootstrap.estimates.to_csv(directory / "d9e_bootstrap_replicates.csv", index=False)
    bootstrap.failures.to_csv(directory / "d9e_bootstrap_failures.csv", index=False)
    robustness.to_csv(directory / "d9e_robustness.csv", index=False)

    summary = {
        "seed": bootstrap.seed,
        "attempted": bootstrap.attempted,
        "successful": bootstrap.successful,
        "failed": bootstrap.failed,
        "reference_profiles": len(explanatory_table),
        "boroughs": int(explanatory_table.new_la_code.nunique()),
        "full_attempt_count": bootstrap.attempted == BOOTSTRAP_ATTEMPTS,
        "failure_reasons": bootstrap.failures.reason.value_counts().to_dict(),
    }
    (directory / "d9e_bootstrap_run.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"D9e complete: {bootstrap.successful} successful / {bootstrap.attempted} attempted bootstrap refits.")
    return summary
