import pandas as pd


PRIMARY_POPULATION = "State-funded mainstream and special"
SPECIAL_POPULATION = "State-funded (inc. non-maintained) special"

SUSTAINED = "Sustained education, employment & apprenticeships"
NOT_RECORDED = "Not recorded as a sustained destination"
ACTIVITY_NOT_CAPTURED = "Activity not captured"

OUTCOME_DESTINATIONS = [
    SUSTAINED,
    NOT_RECORDED,
    ACTIVITY_NOT_CAPTURED,
]

DEVELOPMENT_MAX_TARGET_YEAR = "202122"

PREDICTIVE_FEATURES = [
    "adverse_rate",
    "fsm_share",
    "identified_sen_share",
]


def build_headline_outcome_table(london_la: pd.DataFrame) -> pd.DataFrame:
    """
    Build one row per borough × cohort for the primary population.

    Returns exact headline cohort and adverse-outcome counts.
    """

    # Build a Boolean mask selecting:
    #   establishment_type_group == PRIMARY_POPULATION
    # and ALL of these == "Total":
    #   sex
    #   ethnicity_major
    #   ethnicity_minor
    #   disadvantage_status
    #   breakdown_topic
    #   breakdown
    #
    # Then keep only OUTCOME_DESTINATIONS.

    est_type_mask = london_la["establishment_type_group"] == PRIMARY_POPULATION
    sex_mask = london_la["sex"] == "Total"
    ethnicity_major_mask = london_la["ethnicity_major"] == "Total"
    ethnicity_minor_mask = london_la["ethnicity_minor"] == "Total"
    disadvantage_status_mask = london_la["disadvantage_status"] == "Total"
    breakdown_topic_mask = london_la["breakdown_topic"] == "Total"
    breakdown_mask = london_la["breakdown"] == "Total"
    destination_description_mask = london_la["destination_description"].isin(OUTCOME_DESTINATIONS)

    headline = london_la[
        est_type_mask
        & sex_mask
        & ethnicity_major_mask
        & ethnicity_minor_mask
        & disadvantage_status_mask
        & breakdown_topic_mask
        & breakdown_mask
        & destination_description_mask
    ].copy()

    # Publication codes must not be silently converted to NaN.
    # These headline values are expected to be exact numeric counts,
    # so conversion should fail loudly if that assumption is violated.
    headline["cohort_count"] = pd.to_numeric(
        headline["cohort_count"],
        errors="raise",
    )
    headline["pupil_count"] = pd.to_numeric(
        headline["pupil_count"],
        errors="raise",
    )


    # Pivot pupil_count so that each row is:
    #
    #   time_period × new_la_code × la_name
    #
    # and each of the three destination descriptions becomes a column.

    outcome_wide = headline.pivot(
        index = ["time_period","new_la_code","la_name"],
        columns = "destination_description",
        values = "pupil_count"
    ).reset_index()


    # cohort_count is repeated across the three destination rows.
    denominators = (
        headline[
            ["time_period", "new_la_code", "la_name", "cohort_count"]
        ]
        .drop_duplicates()
    )

    outcome = outcome_wide.merge(
        denominators,
        on=["time_period", "new_la_code", "la_name"],
        how="left",
        validate="one_to_one",
    )

    outcome["adverse_count"] = (
        outcome[NOT_RECORDED]
        + outcome[ACTIVITY_NOT_CAPTURED]
    )

    outcome["adverse_rate"] = (
        outcome["adverse_count"] / outcome["cohort_count"]
    )

    return outcome.sort_values(
        ["time_period", "new_la_code"]
    ).reset_index(drop=True)


def build_fsm_sen_composition(
    london_la: pd.DataFrame,
    headline: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construct exact FSM-eligible and Identified-SEN cohort shares
    for each borough × cohort.
    """

    # Keep one destination only because cohort_count is repeated
    # across destination rows.
    base_mask = (
        (london_la["establishment_type_group"] == PRIMARY_POPULATION)
        & (london_la["sex"] == "Total")
        & (london_la["ethnicity_major"] == "Total")
        & (london_la["ethnicity_minor"] == "Total")
        & (london_la["disadvantage_status"] == "Total")
        & (london_la["destination_description"] == SUSTAINED)
    )

    subgroup = london_la.loc[base_mask].copy()

    # Select exactly these two subgroup rows:
    #
    # FSM:
    #   breakdown_topic == "FSM status"
    #   breakdown == "FSM eligible"
    #
    # SEN:
    #   breakdown_topic == "SEN provision"
    #   breakdown == "Identified SEN"
    #
    # Build one Boolean mask that keeps both valid combination.
    composition = subgroup.loc[((subgroup["breakdown_topic"] == "FSM status") & (subgroup["breakdown"] == "FSM eligible"))
                                | ((subgroup["breakdown_topic"] == "SEN provision") & (subgroup["breakdown"] == "Identified SEN"))
                               ].copy()

    composition["cohort_count"] = pd.to_numeric(
        composition["cohort_count"],
        errors="raise",
    )

    # Routine reshaping: one row per borough × cohort.
    composition = (
        composition.pivot(
            index=["time_period", "new_la_code", "la_name"],
            columns="breakdown",
            values="cohort_count",
        )
        .reset_index()
        .rename(
            columns={
                "FSM eligible": "fsm_eligible_count",
                "Identified SEN": "identified_sen_count",
            }
        )
    )

    # Bring in the independently constructed exact headline denominator.
    composition = composition.merge(
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

    composition["fsm_share"] = (
        composition["fsm_eligible_count"]
        / composition["cohort_count"]
    )

    composition["identified_sen_share"] = (
        composition["identified_sen_count"]
        / composition["cohort_count"]
    )

    return composition


def build_special_school_composition(
    london_la: pd.DataFrame,
    headline: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Construct standalone special-school cohort share
    within the combined mainstream + special population.
    """

    special_mask = (
        (london_la["establishment_type_group"] == SPECIAL_POPULATION)
        & (london_la["sex"] == "Total")
        & (london_la["ethnicity_major"] == "Total")
        & (london_la["ethnicity_minor"] == "Total")
        & (london_la["disadvantage_status"] == "Total")
        & (london_la["breakdown_topic"] == "Total")
        & (london_la["breakdown"] == "Total")
        & (london_la["destination_description"] == SUSTAINED)
    )

    special = london_la.loc[
        special_mask,
        [
            "time_period",
            "new_la_code",
            "la_name",
            "cohort_count",
        ],
    ].copy()

    special["cohort_count"] = pd.to_numeric(
        special["cohort_count"],
        errors="raise",
    )

    special = special.rename(
        columns={"cohort_count": "special_school_count"}
    )

    # Merge the exact combined-population headline denominator onto
    # `special`.
    special = special.merge(
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

    # Calculate:
    # special_school_share =
    #     special_school_count / cohort_count
    special["special_school_share"] = special["special_school_count"] / special["cohort_count"]

    return special


def build_disadvantage_composition(
    london_la: pd.DataFrame,
    headline: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Construct approximate disadvantaged cohort share.

    Public disadvantage cohort counts are disclosure-rounded,
    so this share is approximate and used only for sensitivity analysis.
    """

    disadvantaged_mask = (
        (london_la["establishment_type_group"] == PRIMARY_POPULATION)
        & (london_la["sex"] == "Total")
        & (london_la["ethnicity_major"] == "Total")
        & (london_la["ethnicity_minor"] == "Total")
        & (london_la["disadvantage_status"] == "Disadvantaged")
        & (london_la["breakdown_topic"] == "Total")
        & (london_la["breakdown"] == "Total")
        & (london_la["destination_description"] == SUSTAINED)
    )

    disadvantaged = london_la.loc[
        disadvantaged_mask,
        [
            "time_period",
            "new_la_code",
            "la_name",
            "cohort_count",
        ],
    ].copy()

    disadvantaged["cohort_count"] = pd.to_numeric(
        disadvantaged["cohort_count"],
        errors="raise",
    )

    disadvantaged = disadvantaged.rename(
        columns={
            "cohort_count": "disadvantaged_count_approx",
        }
    )

    disadvantaged = disadvantaged.merge(
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

    # Construct the approximate disadvantage share.
    disadvantaged["disadvantaged_share_approx"] = disadvantaged["disadvantaged_count_approx"] / disadvantaged["cohort_count"]

    return disadvantaged


def build_explanatory_model_table(
    headline: pd.DataFrame,
    fsm_sen: pd.DataFrame,
    special: pd.DataFrame,
    disadvantage: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Assemble the frozen explanatory borough × cohort modelling table.
    """

    model_table = headline.copy()

    model_table = model_table.merge(
        fsm_sen[
            [
                "time_period",
                "new_la_code",
                "fsm_eligible_count",
                "identified_sen_count",
                "fsm_share",
                "identified_sen_share",
            ]
        ],
        on=["time_period", "new_la_code"],
        how="left",
        validate="one_to_one",
    )

    # Merge in:
    #   special_school_count
    #   special_school_share
    #
    # using the same borough × cohort keys
    # and validate="one_to_one".
    model_table = model_table.merge(
        special[
            [
                "time_period",
                "new_la_code",
                "special_school_count",
                "special_school_share",
            ]
        ],
        on=["time_period", "new_la_code"],
        how="left",
        validate="one_to_one",
    )

    # Merge in:
    #   disadvantaged_count_approx
    #   disadvantaged_share_approx
    #
    # again using the same keys.
    model_table = model_table.merge(
        disadvantage[
            [
                "time_period",
                "new_la_code",
                "disadvantaged_count_approx",
                "disadvantaged_share_approx",
            ]
        ],
        on=["time_period", "new_la_code"],
        how="left",
        validate="one_to_one",
    )

    return model_table.sort_values(
        ["time_period", "new_la_code"]
    ).reset_index(drop=True)


def build_development_transition_table(
    model_table: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Construct one-cohort-ahead predictive transitions through 2021/22.

    2022/23 is deliberately excluded from this development table.
    """

    # Prevent the locked final predictive target from entering this
    # development-stage transformation at all.
    development = model_table.loc[
        model_table["time_period"] <= DEVELOPMENT_MAX_TARGET_YEAR
    ].copy()

    development = development.sort_values(
        ["new_la_code", "time_period"]
    ).reset_index(drop=True)

    # Within each borough, create:
    #
    #   target_year
    #
    # by taking the NEXT row's time_period.

    development["target_year"] = development.groupby("new_la_code")["time_period"].shift(-1)

    # Within each borough, create:
    #
    #   target_adverse_rate
    #
    # from the NEXT row's adverse_rate.

    development["target_adverse_rate"] = development.groupby("new_la_code")["adverse_rate"].shift(-1)


    # Target cohort denominator is NOT a predictor.
    # We retain it only for the predeclared weighted-MAE evaluation.
    development["target_cohort_count"] = (
        development
        .groupby("new_la_code")["cohort_count"]
        .shift(-1)
    )

    # Rows corresponding to the final available origin (2021/22)
    # have no permitted development target and are removed.
    transitions = development.loc[
        development["target_year"].notna()
    ].copy()

    transitions = transitions.rename(
        columns={
            "time_period": "feature_year",
            "adverse_rate": "feature_adverse_rate",
            "fsm_share": "feature_fsm_share",
            "identified_sen_share": "feature_identified_sen_share",
        }
    )

    keep_columns = [
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

    return transitions[keep_columns].reset_index(drop=True)