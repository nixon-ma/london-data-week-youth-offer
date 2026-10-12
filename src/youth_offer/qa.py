import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor

from youth_offer.predictive import M1_FEATURE_COLUMNS

EXPECTED_YEARS = {
    "201617",
    "201718",
    "201819",
    "201920",
    "202021",
    "202122",
    "202223",
}

EXPECTED_BOROUGHS = 32
EXPECTED_ROWS = 224

PRIMARY_POPULATION = "State-funded mainstream and special"
MAINSTREAM_POPULATION = "State-funded mainstream schools"
SPECIAL_POPULATION = "State-funded (inc. non-maintained) special"

SUSTAINED = "Sustained education, employment & apprenticeships"
NOT_RECORDED = "Not recorded as a sustained destination"
ACTIVITY_NOT_CAPTURED = "Activity not captured"

EXPECTED_TRANSITION_PAIRS = {
    ("201617", "201718"),
    ("201718", "201819"),
    ("201819", "201920"),
    ("201920", "202021"),
    ("202021", "202122"),
}

EXPECTED_TRANSITION_ROWS = 160

M1_DEVELOPMENT_TRAIN_SIZES = {
    "201819": 32,
    "201920": 64,
    "202021": 96,
    "202122": 128,
}


def assert_headline_outcome_table(outcome: pd.DataFrame) -> None:
    """
    Fail loudly if the headline borough × cohort table violates
    the frozen analytical structure.
    """

    key = ["time_period", "new_la_code"]

    # Basic table size
    assert len(outcome) == EXPECTED_ROWS, (
        f"Expected {EXPECTED_ROWS} borough-years, got {len(outcome)}."
    )

    # Frozen cohort coverage
    observed_years = set(outcome["time_period"])
    assert observed_years == EXPECTED_YEARS, (
        f"Unexpected cohort years: {sorted(observed_years)}"
    )

    # Assert that there are no duplicate rows at:
    #
    #     time_period × new_la_code
    duplicated_rows = outcome.duplicated(subset=key)
    assert duplicated_rows.sum() == 0, (
        f"Got {duplicated_rows.sum()} duplicated rows."
    )

    # For each time_period, count the number of unique new_la_code values.
    # Assert that EVERY year contains exactly EXPECTED_BOROUGHS.
    unique_la_per_year = outcome.groupby('time_period')['new_la_code'].nunique()
    bad_years = unique_la_per_year[unique_la_per_year != EXPECTED_BOROUGHS]
    assert bad_years.empty, (
        f"Expected {EXPECTED_BOROUGHS} boroughs each year. Check: {bad_years.to_dict()}."
    )


    required_columns = [
        "time_period",
        "new_la_code",
        "la_name",
        "cohort_count",
        SUSTAINED,
        NOT_RECORDED,
        ACTIVITY_NOT_CAPTURED,
        "adverse_count",
        "adverse_rate",
    ]

    assert outcome[required_columns].notna().all().all(), (
        "Missing values found in required headline fields."
    )

    assert (outcome["cohort_count"] > 0).all(), (
        "Non-positive cohort denominator found."
    )

    # Exact headline accounting
    accounting_error = (
        outcome["cohort_count"]
        - outcome[SUSTAINED]
        - outcome[NOT_RECORDED]
        - outcome[ACTIVITY_NOT_CAPTURED]
    )

    assert accounting_error.eq(0).all(), (
        "Headline destination accounting identity failed."
    )

    # Check derived adverse count independently
    expected_adverse = (
        outcome[NOT_RECORDED]
        + outcome[ACTIVITY_NOT_CAPTURED]
    )

    assert outcome["adverse_count"].eq(expected_adverse).all(), (
        "Derived adverse_count is inconsistent."
    )

    # Rate must match exact counts
    expected_rate = (
        outcome["adverse_count"] / outcome["cohort_count"]
    )

    assert outcome["adverse_rate"].eq(expected_rate).all(), (
        "Derived adverse_rate is inconsistent."
    )

    assert outcome["adverse_rate"].between(0, 1).all(), (
        "Adverse rate outside [0, 1]."
    )


def assert_fsm_sen_source_accounting(
    london_la: pd.DataFrame,
    headline: pd.DataFrame,
    ) -> None:
    """
    Verify that the raw FSM and top-level SEN cohort categories
    reconcile exactly to the headline cohort denominator.
    """

    base_mask = (
        (london_la["establishment_type_group"] == PRIMARY_POPULATION)
        & (london_la["sex"] == "Total")
        & (london_la["ethnicity_major"] == "Total")
        & (london_la["ethnicity_minor"] == "Total")
        & (london_la["disadvantage_status"] == "Total")
        & (london_la["destination_description"] == SUSTAINED)
    )

    subgroup = london_la.loc[base_mask].copy()

    allowed_rows = (
        (
            (subgroup["breakdown_topic"] == "FSM status")
            & subgroup["breakdown"].isin(
                [
                    "FSM eligible",
                    "Not known to be FSM eligible",
                ]
            )
        )
        |
        (
            (subgroup["breakdown_topic"] == "SEN provision")
            & subgroup["breakdown"].isin(
                [
                    "Identified SEN",
                    "No identified SEN",
                ]
            )
        )
    )

    subgroup = subgroup.loc[allowed_rows].copy()

    subgroup["cohort_count"] = pd.to_numeric(
        subgroup["cohort_count"],
        errors="raise",
    )

    counts = (
        subgroup.pivot(
            index=["time_period", "new_la_code", "la_name"],
            columns="breakdown",
            values="cohort_count",
        )
        .reset_index()
    )

    counts = counts.merge(
        headline[
            [
                "time_period",
                "new_la_code",
                "cohort_count",
            ]
        ],
        on=["time_period", "new_la_code"],
        how="left",
        validate="one_to_one",
    )

    # Construct the total represented by the two top-level FSM categories.
    fsm_total = counts["FSM eligible"] + counts["Not known to be FSM eligible"]

    # Construct the total represented by the two top-level SEN categories.
    sen_total = counts["Identified SEN"] + counts["No identified SEN"]

    assert fsm_total.eq(counts["cohort_count"]).all(), (
        "FSM categories do not reconcile to headline cohort."
    )

    assert sen_total.eq(counts["cohort_count"]).all(), (
        "Top-level SEN categories do not reconcile to headline cohort."
    )

def assert_population_accounting(
    london_la: pd.DataFrame,
    ) -> None:
    """
    Verify that combined cohort =
    mainstream cohort + standalone-special cohort.
    """

    base_mask = (
        (london_la["sex"] == "Total")
        & (london_la["ethnicity_major"] == "Total")
        & (london_la["ethnicity_minor"] == "Total")
        & (london_la["disadvantage_status"] == "Total")
        & (london_la["breakdown_topic"] == "Total")
        & (london_la["breakdown"] == "Total")
        & (london_la["destination_description"] == SUSTAINED)
        & london_la["establishment_type_group"].isin(
            [
                PRIMARY_POPULATION,
                MAINSTREAM_POPULATION,
                SPECIAL_POPULATION,
            ]
        )
    )

    population = london_la.loc[
        base_mask,
        [
            "time_period",
            "new_la_code",
            "la_name",
            "establishment_type_group",
            "cohort_count",
        ],
    ].copy()

    population["cohort_count"] = pd.to_numeric(
        population["cohort_count"],
        errors="raise",
    )

    population = (
        population.pivot(
            index=["time_period", "new_la_code", "la_name"],
            columns="establishment_type_group",
            values="cohort_count",
        )
        .reset_index()
    )

    # Reconstruct the combined cohort from:
    #
    # mainstream cohort + standalone-special cohort
    reconstructed_combined = population[MAINSTREAM_POPULATION] + population[SPECIAL_POPULATION]

    assert reconstructed_combined.eq(
        population[PRIMARY_POPULATION]
    ).all(), (
        "Combined population does not equal "
        "mainstream + standalone special."
    )


def assert_explanatory_model_table(model_table: pd.DataFrame) -> None:
    """
    Verify the final explanatory borough × cohort modelling table.
    """

    key = ["time_period", "new_la_code"]

    required_columns = [
        "time_period",
        "new_la_code",
        "la_name",
        "cohort_count",
        "adverse_count",
        "adverse_rate",
        "fsm_eligible_count",
        "fsm_share",
        "identified_sen_count",
        "identified_sen_share",
        "special_school_count",
        "special_school_share",
        "disadvantaged_count_approx",
        "disadvantaged_share_approx",
    ]

    # Required schema
    missing_columns = [
        column
        for column in required_columns
        if column not in model_table.columns
    ]

    assert not missing_columns, (
        f"Missing required columns: {missing_columns}"
    )

    # Expected 32 boroughs × 7 cohorts
    assert len(model_table) == EXPECTED_ROWS, (
        f"Expected {EXPECTED_ROWS} rows, got {len(model_table)}."
    )

    observed_years = set(model_table["time_period"])

    assert observed_years == EXPECTED_YEARS, (
        f"Unexpected cohort years: {sorted(observed_years)}"
    )

    # One row per borough × cohort
    duplicated_rows = model_table.duplicated(subset=key)

    assert not duplicated_rows.any(), (
        f"Found {duplicated_rows.sum()} duplicate borough × cohort rows."
    )

    # Complete 32-borough panel in every cohort
    boroughs_per_year = (
        model_table
        .groupby("time_period")["new_la_code"]
        .nunique()
    )

    bad_years = boroughs_per_year[
        boroughs_per_year != EXPECTED_BOROUGHS
    ]

    assert bad_years.empty, (
        f"Expected {EXPECTED_BOROUGHS} boroughs per cohort. "
        f"Failures: {bad_years.to_dict()}"
    )

    # Borough code/name mapping must remain one-to-one
    names_per_code = (
        model_table
        .groupby("new_la_code")["la_name"]
        .nunique()
    )

    codes_per_name = (
        model_table
        .groupby("la_name")["new_la_code"]
        .nunique()
    )

    assert names_per_code.eq(1).all(), (
        "At least one LA code maps to multiple LA names."
    )

    assert codes_per_name.eq(1).all(), (
        "At least one LA name maps to multiple LA codes."
    )

    # No required modelling input may be missing
    assert model_table[required_columns].notna().all().all(), (
        "Missing required explanatory-model inputs."
    )

    # Exact headline denominator must be positive
    assert model_table["cohort_count"].gt(0).all(), (
        "Non-positive cohort denominator found."
    )

    # Exact component counts must be valid relative to the headline cohort
    exact_counts = [
        "adverse_count",
        "fsm_eligible_count",
        "identified_sen_count",
        "special_school_count",
    ]

    for column in exact_counts:
        assert model_table[column].ge(0).all(), (
            f"{column} contains negative values."
        )

        assert model_table[column].le(
            model_table["cohort_count"]
        ).all(), (
            f"{column} exceeds the headline cohort denominator."
        )

    # Disclosure-rounded disadvantage count is approximate,
    # but must still be a sensible non-negative cohort count.
    assert model_table["disadvantaged_count_approx"].ge(0).all(), (
        "Approximate disadvantage count contains negative values."
    )

    assert model_table["disadvantaged_count_approx"].le(
        model_table["cohort_count"]
    ).all(), (
        "Approximate disadvantage count exceeds headline cohort."
    )

    # Rates/shares must be valid proportions
    rate_columns = [
        "adverse_rate",
        "fsm_share",
        "identified_sen_share",
        "special_school_share",
        "disadvantaged_share_approx",
    ]

    for column in rate_columns:
        assert model_table[column].between(0, 1).all(), (
            f"{column} contains values outside [0, 1]."
        )


def assert_development_transition_table(
    transitions: pd.DataFrame,
    ) -> None:
    """
    Verify grain, chronological alignment and leakage boundaries
    of the development predictive transition table.
    """

    key = ["new_la_code", "feature_year", "target_year"]

    required_columns = [
        "new_la_code",
        "la_name",
        "feature_year",
        "target_year",
        "feature_adverse_rate",
        "feature_fsm_share",
        "feature_identified_sen_share",
        "target_adverse_rate",
        "target_cohort_count",
    ]

    assert len(transitions) == EXPECTED_TRANSITION_ROWS, (
        f"Expected {EXPECTED_TRANSITION_ROWS} rows, "
        f"got {len(transitions)}."
    )

    assert not transitions.duplicated(subset=key).any(), (
        "Duplicate borough-transition rows found."
    )

    assert transitions[required_columns].notna().all().all(), (
        "Missing predictive inputs or targets."
    )

    # Construct the observed set of:
    #
    #     (feature_year, target_year)

    observed_pairs_df = transitions[["feature_year","target_year"]].drop_duplicates()
    observed_pairs = set(observed_pairs_df.itertuples(index=False,name=None))

    assert observed_pairs == EXPECTED_TRANSITION_PAIRS, (
        f"Unexpected transition pairs: {observed_pairs}"
    )

    # Every transition must contain all 32 boroughs.
    boroughs_per_transition = (
        transitions
        .groupby(["feature_year", "target_year"])["new_la_code"]
        .nunique()
    )

    assert boroughs_per_transition.eq(EXPECTED_BOROUGHS).all(), (
        f"Incomplete transition(s): "
        f"{boroughs_per_transition.to_dict()}"
    )

    # Hard lock: 2022/23 must not enter development prediction data.
    assert "202223" not in set(transitions["target_year"]), (
        "Locked 2022/23 target entered development transitions."
    )

    assert "202223" not in set(transitions["feature_year"]), (
        "2022/23 entered development features unexpectedly."
    )

    feature_columns = [
        "feature_adverse_rate",
        "feature_fsm_share",
        "feature_identified_sen_share",
    ]

    for column in feature_columns:
        assert transitions[column].between(0, 1).all(), (
            f"{column} contains values outside [0, 1]."
        )

    assert transitions["target_adverse_rate"].between(0, 1).all()
    assert transitions["target_cohort_count"].gt(0).all()


def assert_transition_source_alignment(
    transitions: pd.DataFrame,
    model_table: pd.DataFrame,
    ) -> None:
    """
    Verify that every predictive transition contains feature values
    from cohort t and target values from the same borough at t+1.
    """

    # Keep the final locked predictive cohort out of this QA entirely.
    source = model_table.loc[
        model_table["time_period"].isin(
            {
                "201617",
                "201718",
                "201819",
                "201920",
                "202021",
                "202122",
            }
        )
    ].copy()

    # Build an independent lookup table for feature-year values.
    feature_source = source[
        [
            "new_la_code",
            "time_period",
            "adverse_rate",
            "fsm_share",
            "identified_sen_share",
        ]
    ].rename(
        columns={
            "time_period": "feature_year",
            "adverse_rate": "source_feature_adverse_rate",
            "fsm_share": "source_feature_fsm_share",
            "identified_sen_share": "source_feature_identified_sen_share",
        }
    )

    # Merge feature_source onto transitions using:
    #
    #   new_la_code
    #   feature_year

    checked = transitions.merge(
        feature_source,
        on=["new_la_code","feature_year"],
        how="left",
        validate="one_to_one"
    )

    # transitions already contains BOTH years:
    #
    #   borough   feature_year   target_year
    #   Camden       201819         201920
    #
    # feature_source contains only the source time_period renamed as feature_year:
    #
    #   borough   feature_year
    #   Camden      201617
    #   Camden      201718
    #   Camden      201819
    #   Camden      201920
    #   ...
    #
    # feature_source is then merged into transitions based on **feature_year** and borough

    # Build independent lookup table for target-year values.
    target_source = source[
        [
            "new_la_code",
            "time_period",
            "adverse_rate",
            "cohort_count",
        ]
    ].rename(
        columns={
            "time_period": "target_year",
            "adverse_rate": "source_target_adverse_rate",
            "cohort_count": "source_target_cohort_count",
        }
    )

    # Merge target_source onto checked using:
    #
    #   new_la_code
    #   target_year

    checked = checked.merge(
        target_source,
        on=["new_la_code","target_year"],
        how="left",
        validate="one_to_one"
    )

    # checked already contains BOTH years:
    #
    #   borough   feature_year   target_year
    #   Camden       201819         201920
    #
    # target_source contains only the source time_period renamed as target_year:
    #
    #   borough   target_year
    #   Camden      201617
    #   Camden      201718
    #   Camden      201819
    #   Camden      201920
    #   ...
    #
    # target_source is then merged into checked based on **target_year** and borough
    #
    # Therefore, the same original borough-year source row can be merged into
    # different checked rows depending on which year key is used

    # Now compare the transition values against the independently
    # retrieved source values.
    assert np.allclose(
        checked["feature_adverse_rate"],
        checked["source_feature_adverse_rate"],
    ), "Feature adverse rate is misaligned."

    assert np.allclose(
        checked["feature_fsm_share"],
        checked["source_feature_fsm_share"],
    ), "FSM feature is misaligned."

    assert np.allclose(
        checked["feature_identified_sen_share"],
        checked["source_feature_identified_sen_share"],
    ), "SEN feature is misaligned."

    assert np.allclose(
        checked["target_adverse_rate"],
        checked["source_target_adverse_rate"],
    ), "Target adverse rate is misaligned."

    assert checked["target_cohort_count"].eq(
        checked["source_target_cohort_count"]
    ).all(), "Target cohort denominator is misaligned."


def assert_baseline_predictions(
    baseline_predictions: pd.DataFrame,
    model_table: pd.DataFrame,
    ) -> None:
    """
    Verify B1-B3 and ensure B3 uses only information available
    by each transition's feature year.
    """

    required_columns = [
        "b1_borough_persistence",
        "b2_london_persistence",
        "b3_london_plus_borough_offset",
    ]

    assert baseline_predictions[required_columns].notna().all().all(), (
        "Missing baseline predictions."
    )

    # ------------------------------------------------------------------
    # B1: borough persistence
    # ------------------------------------------------------------------
    # By definition, B1 predicts next year's rate using the borough's
    # current feature-year adverse rate.
    assert np.allclose(
        baseline_predictions["b1_borough_persistence"],
        baseline_predictions["feature_adverse_rate"],
    ), "B1 is not borough persistence."

    # ------------------------------------------------------------------
    # Development source data
    # ------------------------------------------------------------------
    source = model_table.loc[
        model_table["time_period"].isin(
            {
                "201617",
                "201718",
                "201819",
                "201920",
                "202021",
                "202122",
            }
        )
    ].copy()

    # ------------------------------------------------------------------
    # B2: London persistence
    # ------------------------------------------------------------------
    # Independently reconstruct London's rate using the cohort-size-weighted
    # average of borough adverse rates.
    #
    # This differs from the implementation, which aggregates adverse counts
    # and cohort counts first and then divides.

    expected_london_rows = []

    for year, group in source.groupby("time_period"):
        expected_london_rows.append(
            {
                "feature_year": year,
                "expected_london_rate": np.average(
                    group["adverse_rate"],
                    weights=group["cohort_count"],
                ),
            }
        )

    expected_london = pd.DataFrame(expected_london_rows)

    checked = baseline_predictions.merge(
        expected_london,
        on="feature_year",
        how="left",
        validate="many_to_one",
    )

    assert np.allclose(
        checked["b2_london_persistence"],
        checked["expected_london_rate"],
    ), "B2 London persistence is incorrect."

    # Every borough in a given feature year should receive exactly
    # the same London-level B2 prediction.
    b2_values_per_year = (
        baseline_predictions
        .groupby("feature_year")["b2_london_persistence"]
        .nunique()
    )

    assert b2_values_per_year.eq(1).all(), (
        "B2 should have exactly one London prediction per feature year."
    )

    # ------------------------------------------------------------------
    # B3: London level + historical borough offset
    # ------------------------------------------------------------------
    # Check B3 independently, without repeating groupby().expanding().
    #
    # For each transition:
    #
    #   feature_year = t
    #
    # use only that borough's source rows from years <= t.
    #
    # Example for 201920:
    #
    #   201617
    #   201718
    #   201819
    #   201920   <- included
    #   202021   <- forbidden
    #   202122   <- forbidden

    london_rate_by_year = dict(
        zip(
            expected_london["feature_year"],
            expected_london["expected_london_rate"],
        )
    )

    expected_b3_predictions = []

    for _, row in baseline_predictions.iterrows():
        borough = row["new_la_code"]
        feature_year = row["feature_year"]

        # Select only source rows that:
        #
        # 1. belong to this borough, AND
        # 2. have time_period <= feature_year
        #
        # This is the key leakage-control step.
        history = source.loc[
            (source["new_la_code"] == borough)
            & (source["time_period"] <= feature_year)
        ].copy()

        # Calculate the borough-minus-London offset independently
        # for every historically available year.
        history["expected_london_rate"] = (
            history["time_period"].map(london_rate_by_year)
        )

        history["expected_offset"] = (
            history["adverse_rate"]
            - history["expected_london_rate"]
        )

        historical_mean_offset = history["expected_offset"].mean()

        # B3 prediction:
        # current London rate + historical borough-specific mean offset.
        expected_b3 = (
            london_rate_by_year[feature_year]
            + historical_mean_offset
        )

        expected_b3_predictions.append(expected_b3)

    assert np.allclose(
        baseline_predictions["b3_london_plus_borough_offset"],
        expected_b3_predictions,
    ), (
        "B3 is incorrect or uses information unavailable "
        "at the feature year."
    )


def assert_m1_development_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target_year: str,
    ) -> None:
    """Verify one M1 rolling-origin development fold."""

    expected_train_size = M1_DEVELOPMENT_TRAIN_SIZES[target_year]

    assert len(train) == expected_train_size, (
        f"{target_year}: expected {expected_train_size} training rows, "
        f"got {len(train)}."
    )

    assert len(test) == EXPECTED_BOROUGHS, (
        f"{target_year}: expected {EXPECTED_BOROUGHS} test rows, "
        f"got {len(test)}."
    )

    # Assert that EVERY training target year is strictly before target_year.
    train_target_year_mask = train["target_year"].lt(target_year)
    assert train_target_year_mask.all(), (
        f"{target_year}: training set contains non-earlier target years: "
        f"{train.loc[~train_target_year_mask,'target_year'].tolist()}"
    )

    # Assert that EVERY test row has target_year equal to target_year.
    test_target_year_mask = test["target_year"].eq(target_year)
    assert test_target_year_mask.all(), (
        f"{target_year}: test set contains different target years: "
        f"{test.loc[~test_target_year_mask, 'target_year'].tolist()}"
    )

    # Assert that none of the three M1 feature columns are missing
    # in either train or test.
    assert train[M1_FEATURE_COLUMNS].notna().all().all(), (
        f"{target_year}: Missing values detected in training set"
    )

    assert test[M1_FEATURE_COLUMNS].notna().all().all(), (
        f"{target_year}: Missing values detected in test set"
    )


def assert_m1_fit(
    train: pd.DataFrame,
    test: pd.DataFrame,
    predictions: pd.Series,
    estimator: QuantileRegressor,
    ) -> None:
    """Verify numerical validity of one fitted M1 development fold."""

    # Frozen feature specification.
    assert M1_FEATURE_COLUMNS == [
        "feature_adverse_rate",
        "feature_fsm_share",
        "feature_identified_sen_share",
    ]

    # There must be one prediction for every test borough.
    assert len(predictions) == EXPECTED_BOROUGHS, (
        f"Expected {EXPECTED_BOROUGHS} M1 predictions, "
        f"got {len(predictions)}."
    )

    # Exactly one coefficient per frozen feature.
    assert len(estimator.coef_) == len(M1_FEATURE_COLUMNS), (
        f"Expected {len(M1_FEATURE_COLUMNS)} coefficients, "
        f"got {len(estimator.coef_)}."
    )

    # Check that the intercept and all three coefficients are finite.
    assert np.isfinite(estimator.intercept_), (
        "intercept is non-finite."
    )

    assert np.isfinite(estimator.coef_).all(), (
        "at least 1 coefficient is non-finite."
    )

    assert estimator.get_params()["quantile"] == 0.5
    assert estimator.get_params()["alpha"] == 0.0
    assert estimator.get_params()["fit_intercept"] is True
    assert estimator.get_params()["solver"] == "highs"

    # Check that every prediction is finite.
    predictions_finite_mask = np.isfinite(predictions.to_numpy())
    assert predictions_finite_mask.all(), (
        "non-finite predictions at positions: "
        f"{np.where(~predictions_finite_mask)[0].tolist()}"
    )

    assert predictions.index.equals(test.index), (
        "Prediction indices do not match test rows."
    )

    np.testing.assert_allclose(
        predictions.to_numpy(dtype=float),
        estimator.predict(test[M1_FEATURE_COLUMNS]),
        rtol=1e-12,
        atol=1e-12,
    )

    # Construct the training design matrix INCLUDING an intercept column,
    # then assert that its rank is 4.
    train_matrix = np.ones(len(train))
    train_matrix = np.column_stack(
        (train_matrix, train[M1_FEATURE_COLUMNS].to_numpy(dtype=float))
        )

    matrix_rank = np.linalg.matrix_rank(train_matrix)
    expected_rank = len(M1_FEATURE_COLUMNS) + 1

    assert matrix_rank == expected_rank, (
        f"expected design matrix rank {expected_rank}, got rank {matrix_rank}."
    )


def assert_m1_development_predictions(
    m1_predictions: pd.DataFrame,
    transitions: pd.DataFrame,
    ) -> None:
    """Verify the assembled M1 development predictions."""

    expected_counts = {
        year: EXPECTED_BOROUGHS
        for year in M1_DEVELOPMENT_TRAIN_SIZES
    }

    actual_counts = (
        m1_predictions.groupby("target_year")
        .size()
        .to_dict()
    )

    assert actual_counts == expected_counts, (
        f"Expected {expected_counts}, got {actual_counts}."
    )

    # Assert that no (new_la_code, target_year) pair is duplicated.
    duplicate_mask = m1_predictions.duplicated(subset=["new_la_code","target_year"])
    assert not duplicate_mask.any(), (
        f"Found {duplicate_mask.sum()} duplicate borough-year rows."
    )

    assert np.isfinite(
        m1_predictions["m1_prediction"].to_numpy(dtype=float)
    ).all(), "Non-finite M1 predictions found."

    # Select the original 128 development evaluation rows.
    expected = (
        transitions.loc[
            transitions["target_year"].isin(
                list(M1_DEVELOPMENT_TRAIN_SIZES)
            )
        ]
        .sort_values(["target_year", "new_la_code"])
        .reset_index(drop=True)
    )

    # Select the same original columns from the assembled predictions.
    actual = (
        m1_predictions[transitions.columns]
        .sort_values(["target_year", "new_la_code"])
        .reset_index(drop=True)
    )

    # Assert that actual and expected DataFrames are identical.
    pd.testing.assert_frame_equal(expected, actual)