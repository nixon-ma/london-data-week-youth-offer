from pathlib import Path
import sys

import matplotlib
import pandas as pd

# This executable lives in scripts/; reusable modules remain in src/youth_offer/.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Select a noninteractive backend before importing plotting modules.
matplotlib.use("Agg")

from youth_offer import data, model_tables, baselines, predictive, evaluation, explanatory, explanatory_diagnostics, explanatory_plots, qa
from youth_offer.predictive import DEVELOPMENT_TARGET_YEARS
from youth_offer.explanatory_reporting import run_d9e_reporting


def main() -> None:
    df = data.load_london_la_slice(
        Path("data/raw/key-stage-4-destination-measures_2023-24.zip")
    )

    headline = model_tables.build_headline_outcome_table(df)

    qa.assert_headline_outcome_table(headline)
    print("Headline QA passed.")

    composition = model_tables.build_fsm_sen_composition(df, headline)

    qa.assert_fsm_sen_source_accounting(df, headline)
    print("FSM/SEN source accounting QA passed.")

    special = model_tables.build_special_school_composition(df, headline)

    qa.assert_population_accounting(df)
    print("Population accounting QA passed.")

    disadvantaged = model_tables.build_disadvantage_composition(df, headline)

    explanatory_table = model_tables.build_explanatory_model_table(
        headline,
        composition,
        special,
        disadvantaged,
    )

    qa.assert_explanatory_model_table(explanatory_table)
    print("Explanatory modelling-table QA passed.")

    result_e1, X_e1 = explanatory.fit_e1(explanatory_table)
    qa.assert_explanatory_glm_structure(result_e1, X_e1, "E1")
    qa.assert_e1_fitted_rates(explanatory_table, result_e1, X_e1)

    result_e2, X_e2 = explanatory.fit_e2(explanatory_table)
    qa.assert_explanatory_glm_structure(result_e2, X_e2, "E2")
    qa.assert_e2_fitted_rates(explanatory_table, result_e2, X_e2)

    result_e3, X_e3 = explanatory.fit_e3(explanatory_table)
    qa.assert_explanatory_glm_structure(result_e3, X_e3, "E3")
    qa.assert_e3_fitted_counts(explanatory_table, result_e3, X_e3)

    result_e4, X_e4 = explanatory.fit_e4(explanatory_table)
    qa.assert_explanatory_glm_structure(result_e4, X_e4, "E4")
    qa.assert_e4_score_equations(explanatory_table, result_e4, X_e4)

    print("E1-E4 QA passed.")

    # D9e: frozen explanatory inference and robustness; no predictive final evaluation.
    run_d9e_reporting(
        explanatory_table, result_e4, X_e4, Path("outputs/explanatory/d9e")
    )

    deviance_reduction_E1_E3 = explanatory_diagnostics.calculate_deviance_reduction(result_e1, result_e3)
    print(deviance_reduction_E1_E3)

    deviance_reduction_E2_E3 = explanatory_diagnostics.calculate_deviance_reduction(result_e2, result_e3)
    print(deviance_reduction_E2_E3)

    deviance_reduction_E3_E4 = explanatory_diagnostics.calculate_deviance_reduction(result_e3, result_e4)
    print(deviance_reduction_E3_E4)

    rate_errors_e1 = explanatory_diagnostics.calculate_rate_errors(explanatory_table, result_e1, X_e1)
    print(rate_errors_e1)
    rate_errors_e2 = explanatory_diagnostics.calculate_rate_errors(explanatory_table, result_e2, X_e2)
    print(rate_errors_e2)
    rate_errors_e3 = explanatory_diagnostics.calculate_rate_errors(explanatory_table, result_e3, X_e3)
    print(rate_errors_e3)
    rate_errors_e4 = explanatory_diagnostics.calculate_rate_errors(explanatory_table, result_e4, X_e4)
    print(rate_errors_e4)

    # Export existing in-sample diagnostics; no additional model fitting.
    fit_metrics = pd.DataFrame(
        [
            {"model": model, **errors}
            for model, errors in (
                ("E1", rate_errors_e1),
                ("E2", rate_errors_e2),
                ("E3", rate_errors_e3),
                ("E4", rate_errors_e4),
            )
        ]
    )
    fit_metrics_path = Path("outputs/explanatory/e1_e4_fit_metrics.csv")
    fit_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    fit_metrics.to_csv(fit_metrics_path, index=False)
    print(f"E1–E4 in-sample fit metrics saved to {fit_metrics_path}")

    pearson_residuals_e4 = explanatory_diagnostics.calculate_pearson_residuals(explanatory_table, result_e4, X_e4)
    qa.assert_explanatory_pearson_residuals(
        result_e4, pearson_residuals_e4
    )
    print("E4 Pearson residual QA passed.")

    pearson_dispersion_e4 = explanatory_diagnostics.calculate_pearson_dispersion(pearson_residuals_e4, result_e4.df_resid)
    print(f"E4 pearson dispersion ratio: {pearson_dispersion_e4}")

    e4_residual_table = explanatory_diagnostics.build_explanatory_residual_table(
        explanatory_table, result_e4, X_e4
    )

    qa.assert_explanatory_residual_table(
        e4_residual_table,
        explanatory_table,
        result_e4,
        X_e4,
        rate_errors_e4,
    )

    print("E4 residual-table QA passed.")

    pairs = explanatory_diagnostics.build_lagged_residual_pairs(e4_residual_table)
    correlation_coeff = explanatory_diagnostics.calculate_lag1_residual_correlation(pairs)
    print(correlation_coeff)

    plot_path = explanatory_plots.plot_pearson_residuals(
        e4_residual_table,
        Path("outputs/explanatory/e4_pearson_residuals.png"),
    )

    print(f"E4 residual plots saved to {plot_path}")

    heatmap_path = explanatory_plots.plot_borough_year_residuals(
        e4_residual_table,
        Path("outputs/explanatory/e4_borough_year_residuals.png"),
    )

    print(f"E4 borough-year residual heatmap saved to {heatmap_path}")

    influence_table = explanatory_diagnostics.build_explanatory_influence_table(e4_residual_table, result_e4)
    qa.assert_explanatory_influence_table(influence_table, result_e4)
    print("Influence table QA passed")

    top_influential = influence_table.nlargest(10, "cooks_d")

    print(
        top_influential[
            [
                "la_name",
                "time_period",
                "cohort_count",
                "pearson_residual",
                "hat_diag",
                "cooks_d",
            ]
        ].to_string(index=False)
    )



    transitions = model_tables.build_development_transition_table(explanatory_table)

    qa.assert_development_transition_table(transitions)
    print("Development transition QA passed.")

    qa.assert_transition_source_alignment(transitions, explanatory_table)
    print("Transition source-alignment QA passed.")

    baseline_predictions = baselines.add_baseline_predictions(transitions, explanatory_table)
    qa.assert_baseline_predictions(baseline_predictions, explanatory_table)
    print("Baseline QA passed.")

    development_predictions = []
    fold_diagnostics = []

    for target_year in DEVELOPMENT_TARGET_YEARS:
        train, test = predictive.split_development_fold(transitions, target_year)
        qa.assert_m1_development_fold(train, test, target_year)

        estimator, predictions = predictive.fit_m1_fold(train, test)
        qa.assert_m1_fit(train, test, predictions, estimator)

        fold_diagnostics.append({
            "target_year": target_year,
            "n_train": len(train),
            "n_test": len(test),
            "last_training_target_year": train["target_year"].max(),
            "intercept": estimator.intercept_,
            "coef_adverse_rate": estimator.coef_[0],
            "coef_fsm_share": estimator.coef_[1],
            "coef_sen_share": estimator.coef_[2],
            "prediction_min": predictions.min(),
            "prediction_max": predictions.max(),
            "n_outside_range": ((predictions < 0) | (predictions > 1)).sum()
        })

        # Preserve the test rows alongside their held-out predictions.
        test_with_predictions = test.assign(m1_prediction=predictions)
        development_predictions.append(test_with_predictions)

    m1_predictions = pd.concat(
        development_predictions,
        ignore_index=True,
    )

    m1_diagnostics = pd.DataFrame(fold_diagnostics)

    qa.assert_m1_development_predictions(m1_predictions, transitions)

    output_dir = Path("outputs/development")
    output_dir.mkdir(parents=True, exist_ok=True)

    m1_predictions.to_csv(
        output_dir / "m1_predictions.csv",
        index=False,
    )

    m1_diagnostics.to_csv(
        output_dir / "m1_diagnostics.csv",
        index=False,
    )

    print(m1_diagnostics.to_string(index=False))
    print("Assembled M1 predictions QA passed.")

    # Assemble B1-B3 and M1 on identical held-out observations.
    evaluation_table = evaluation.build_development_evaluation_table(baseline_predictions, m1_predictions)
    qa.assert_development_evaluation_table(evaluation_table, baseline_predictions, m1_predictions)

    evaluation_table.to_csv(
        output_dir / "evaluation_table.csv",
        index=False,
    )

    print("Development evaluation-table QA passed.")


    # Calculate performance by development target year.
    annual_metrics = evaluation.calculate_development_annual_metrics(
        evaluation_table
    )

    qa.assert_development_annual_metrics(
        annual_metrics,
        evaluation_table,
    )

    print("Annual development metric QA passed.")

    # Average performance equally across development years.
    summary_metrics = evaluation.summarize_development_metrics(
        annual_metrics
    )

    qa.assert_development_summary_metrics(
        summary_metrics,
        annual_metrics,
    )

    annual_metrics.to_csv(
        output_dir / "annual_metrics.csv",
        index=False,
    )

    summary_metrics.to_csv(
        output_dir / "summary_metrics.csv",
        index=False,
    )

    print("Development summary metric QA passed.")




if __name__ == "__main__":
    main()