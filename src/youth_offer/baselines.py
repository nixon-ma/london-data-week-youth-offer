import pandas as pd


DEVELOPMENT_YEARS = {
    "201617",
    "201718",
    "201819",
    "201920",
    "202021",
    "202122",
}


def add_baseline_predictions(
    transitions: pd.DataFrame,
    model_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add the three predeclared one-cohort-ahead baseline predictions.
    """

    source = model_table.loc[
        model_table["time_period"].isin(DEVELOPMENT_YEARS)
    ].copy()

    # Calculate London's exact adverse rate separately for each cohort year.
    # We aggregate counts first rather than averaging borough percentages,
    # because borough cohort sizes differ.
    london_by_year = (
        source
        .groupby("time_period", as_index=False)
        .agg(
            london_adverse_count=("adverse_count", "sum"),
            london_cohort_count=("cohort_count", "sum"),
        )
    )

    # Calculate London's adverse rate:
    #
    #   total adverse count / total cohort count
    london_by_year["london_adverse_rate"] = london_by_year["london_adverse_count"] / london_by_year["london_cohort_count"]

    # Attach that year's London rate to every borough-year source row.
    source = source.merge(
        london_by_year[
            ["time_period", "london_adverse_rate"]
        ],
        on="time_period",
        how="left",
        validate="many_to_one",
    )

    # How far above/below London was this borough in this particular year?
    source["borough_offset"] = (
        source["adverse_rate"]
        - source["london_adverse_rate"]
    )

    source = source.sort_values(
        ["new_la_code", "time_period"]
    ).reset_index(drop=True)

    # B3 must use only this borough's offsets observed up to and including
    # the current feature year.
    #
    # Example:
    #
    # 201617 offset ────────────────┐
    # 201718 offset ────────────┐   │
    # 201819 offset ────────┐   │   │
    #                       ▼   ▼   ▼
    # B3 at 201819 uses mean(201617, 201718, 201819)
    #
    # It must NOT use 201920 or any later offset.

    # For each borough, calculate the expanding mean of borough_offset.
    #
    # Useful pieces:
    #
    # source.groupby("new_la_code")["borough_offset"]
    #       .expanding()
    #       .mean()
    #
    # groupby(...).expanding() creates an extra group-index level,
    # so you will need to remove that level afterwards.
    source["historical_borough_offset"] = (
        source
        .groupby("new_la_code")["borough_offset"]
        .expanding()
        .mean()
        .droplevel("new_la_code")
    )

    baseline_lookup = source[
        [
            "new_la_code",
            "time_period",
            "london_adverse_rate",
            "historical_borough_offset",
        ]
    ].rename(
        columns={"time_period": "feature_year"}
    )

    result = transitions.merge(
        baseline_lookup,
        on=["new_la_code", "feature_year"],
        how="left",
        validate="one_to_one",
    )

    # B1: this borough's current adverse rate.
    result["b1_borough_persistence"] = (
        result["feature_adverse_rate"]
    )

    # B2: London's current adverse rate.
    result["b2_london_persistence"] = (
        result["london_adverse_rate"]
    )

    # B3: current London level plus this borough's historical average offset.
    result["b3_london_plus_borough_offset"] = (
        result["london_adverse_rate"]
        + result["historical_borough_offset"]
    )

    return result