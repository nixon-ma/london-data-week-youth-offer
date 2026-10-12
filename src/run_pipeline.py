from pathlib import Path
import pandas as pd
from youth_offer import data, model_tables, baselines, predictive, qa
from youth_offer.predictive import DEVELOPMENT_TARGET_YEARS


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

    explanatory = model_tables.build_explanatory_model_table(
        headline,
        composition,
        special,
        disadvantaged,
    )

    qa.assert_explanatory_model_table(explanatory)
    print("Explanatory modelling-table QA passed.")

    transitions = model_tables.build_development_transition_table(explanatory)

    qa.assert_development_transition_table(transitions)
    print("Development transition QA passed.")

    qa.assert_transition_source_alignment(transitions, explanatory)
    print("Transition source-alignment QA passed.")

    baseline_predictions = baselines.add_baseline_predictions(transitions, explanatory)
    qa.assert_baseline_predictions(baseline_predictions, explanatory)
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


if __name__ == "__main__":
    main()