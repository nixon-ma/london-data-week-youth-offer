"""Historical adverse-outcome counts and subgroup comparisons after KS4."""

import pandas as pd
import numpy as np

from youth_offer import pathways

CELL_KEY = ("time_period", "new_la_code", "la_name", "family", "group")
GROUP_KEY = ("new_la_code", "la_name", "family", "group")
COUNT_COLUMNS = (
    "not_recorded_count",
    "activity_not_captured_count",
    "adverse_count",
    "cohort_count",
)
PERIOD_YEARS = {
    "2022/23": ("202223",),
    "2021/22–2022/23": ("202122", "202223"),
    "2020/21–2022/23": ("202021", "202122", "202223"),
}
GAP_GROUPS = {
    "FSM": ("FSM eligible", "Not known to be FSM eligible"),
    "SEN": ("Identified SEN", "No identified SEN"),
}
PERSISTENCE_YEARS = (
    "201617", "201718", "201819", "201920", "202021", "202122", "202223",
)
PERSISTENCE_KEY = ("new_la_code", "la_name", "family")


def build_adverse_cells(exact: pd.DataFrame) -> pd.DataFrame:
    """Reduce five exclusive pathways to one exact adverse row per group/cohort."""
    selected = exact.loc[exact.destination.isin((
        pathways.NOT_RECORDED, pathways.ACTIVITY_NOT_CAPTURED
    ))]
    counts = selected.pivot(
        index=[*CELL_KEY, "cohort_count"],
        columns="destination",
        values="pupil_count",
    ).reset_index()
    if (counts[[pathways.NOT_RECORDED, pathways.ACTIVITY_NOT_CAPTURED]]
            .isna().any().any()):
        raise ValueError("Missing adverse destination component")

    cells = counts.rename(columns={
        pathways.NOT_RECORDED: "not_recorded_count",
        pathways.ACTIVITY_NOT_CAPTURED: "activity_not_captured_count",
    })
    cells["adverse_count"] = (
        cells["not_recorded_count"] + cells["activity_not_captured_count"]
    )
    cells["adverse_rate_pct"] = 100 * cells["adverse_count"] / cells["cohort_count"]
    cells["one_pupil_pp"] = 100 / cells["cohort_count"]
    return cells.sort_values(list(CELL_KEY)).reset_index(drop=True)


def pool_adverse_cells(
    cells: pd.DataFrame, period: str
) -> pd.DataFrame:
    """Pool exact counts and denominators across complete historical cohorts."""

    years = PERIOD_YEARS[period]

    selected = cells.loc[cells["time_period"].isin(years)].copy()
    base_keys = set(cells[list(GROUP_KEY)].itertuples(index=False, name=None))
    expected = {(year, *group) for year in years for group in base_keys}
    observed_rows = selected[list(CELL_KEY)]
    observed = set(observed_rows.itertuples(index=False, name=None))
    if (observed != expected or len(selected) != len(expected)):
        raise ValueError("Incomplete or duplicated pooling cohort/group coverage")

    selected_pooled = (
        selected.groupby(list(GROUP_KEY), as_index=False)[list(COUNT_COLUMNS)]
        .sum()
    )
    selected_pooled["adverse_rate_pct"] = 100 * selected_pooled["adverse_count"] / selected_pooled["cohort_count"]
    selected_pooled["one_pupil_pp"] = 100 / selected_pooled["cohort_count"]
    selected_pooled["period"] = period

    return selected_pooled.sort_values(list(GROUP_KEY)).reset_index(drop=True)


def calculate_fsm_sen_gaps(cells: pd.DataFrame, period_column: str) -> pd.DataFrame:
    """Compare the two groups within each borough and annual or pooled period."""
    if period_column not in ("time_period", "period"):
        raise ValueError("Expected time_period or period")

    location_key = [period_column, "new_la_code", "la_name"]
    borough_periods = set(cells[location_key].itertuples(index=False, name=None))
    expected = {
        (*key, family, group)
        for key in borough_periods
        for family, groups in GAP_GROUPS.items()
        for group in groups
    }
    selected = cells.loc[cells["family"].isin(GAP_GROUPS)]
    observed = set(
        selected[[*location_key, "family", "group"]]
        .itertuples(index=False, name=None)
    )
    if observed != expected or len(selected) != len(expected):
        raise ValueError("Incomplete or duplicated FSM/SEN comparison groups")

    results = []
    for family, (focus_group, comparison_group) in GAP_GROUPS.items():
        family_cells = selected.loc[selected["family"].eq(family)]
        measures = [*location_key, "adverse_count", "cohort_count"]
        focus = family_cells.loc[
            family_cells["group"].eq(focus_group), measures
        ].rename(columns={
            "adverse_count": "focus_adverse_count",
            "cohort_count": "focus_cohort_count",
        })
        comparison = family_cells.loc[
            family_cells["group"].eq(comparison_group), measures
        ].rename(columns={
            "adverse_count": "comparison_adverse_count",
            "cohort_count": "comparison_cohort_count",
        })
        pairs = focus.merge(comparison, on=location_key, validate="one_to_one")
        pairs["family"] = family
        pairs["focus_group"] = focus_group
        pairs["comparison_group"] = comparison_group

        # Calculate gap_pp from the two exact rates.
        focus_rate = 100 * pairs["focus_adverse_count"] / pairs["focus_cohort_count"]
        comparison_rate = 100 * pairs["comparison_adverse_count"] / pairs["comparison_cohort_count"]
        pairs["gap_pp"] = focus_rate - comparison_rate

        # Determine gap_sign (+1, 0, -1). Use integer cross-products to classify exact ties and small gaps.
        x_product_difference = (
            pairs["focus_adverse_count"] * pairs["comparison_cohort_count"]
            - pairs["comparison_adverse_count"] * pairs["focus_cohort_count"]
        )
        pairs["gap_sign"] = np.sign(x_product_difference).astype(int)

        results.append(pairs)

    return (pd.concat(results, ignore_index=True)
            .sort_values([*location_key, "family"]).reset_index(drop=True))


def summarise_gap_persistence(annual_gaps: pd.DataFrame) -> pd.DataFrame:
    """Summarise seven annual gap signs and the range of observed magnitudes."""
    required = [
        "time_period", *PERSISTENCE_KEY, "gap_pp", "gap_sign",
        "focus_cohort_count", "comparison_cohort_count",
    ]
    if annual_gaps.empty or annual_gaps[required].isna().any().any():
        raise ValueError("Missing annual gap values")
    if not annual_gaps["gap_sign"].isin((-1, 0, 1)).all():
        raise ValueError("Gap signs must be -1, 0 or 1")
    if (annual_gaps[["focus_cohort_count", "comparison_cohort_count"]] <= 0).any().any():
        raise ValueError("Non-positive gap subgroup denominator")

    boroughs = set(
        annual_gaps[["new_la_code", "la_name"]].itertuples(index=False, name=None)
    )
    expected = {
        (year, *borough, family)
        for year in PERSISTENCE_YEARS
        for borough in boroughs
        for family in GAP_GROUPS
    }
    observed = set(
        annual_gaps[["time_period", *PERSISTENCE_KEY]]
        .itertuples(index=False, name=None)
    )
    if observed != expected or len(annual_gaps) != len(expected):
        raise ValueError("Incomplete or duplicated seven-cohort gap coverage")

    # Range of observed gaps and smallest subgroup denominator are useful
    # context, especially when annual group sizes are small.
    magnitudes = annual_gaps.groupby(list(PERSISTENCE_KEY), as_index=False).agg(
        min_gap_pp=("gap_pp", "min"),
        max_gap_pp=("gap_pp", "max"),
        min_focus_cohort_count=("focus_cohort_count", "min"),
        min_comparison_cohort_count=("comparison_cohort_count", "min"),
    )

    # Count annual gap_sign values of +1, 0 and -1 separately
    # for each borough/family.
    annual_gaps = annual_gaps.copy()
    annual_gaps["positive"] = annual_gaps["gap_sign"].eq(1)
    annual_gaps["zero"] = annual_gaps["gap_sign"].eq(0)
    annual_gaps["negative"] = annual_gaps["gap_sign"].eq(-1)
    sign_columns = ("positive", "zero", "negative")
    sign_counts = (
        annual_gaps.groupby(list(PERSISTENCE_KEY), as_index=False)[list(sign_columns)]
        .sum()
    )
    sign_counts = sign_counts.rename(columns={
        "positive": "positive_years",
        "zero": "zero_years",
        "negative": "negative_years",
    })

    summary = magnitudes.merge(
        sign_counts,
        on=list(PERSISTENCE_KEY),
        validate="one_to_one"
        )

    return summary.sort_values(list(PERSISTENCE_KEY)).reset_index(drop=True)


PARTITION_FAMILIES = ("FSM", "SEN", "Sex", "Ethnicity")


def add_group_burden_shares(cells: pd.DataFrame, period_column: str) -> pd.DataFrame:
    """Share of adverse pupils within each complete, non-overlapping family."""
    keys = [period_column, "new_la_code", "la_name"]
    if cells.duplicated([*keys, "family", "group"]).any():
        raise ValueError("Duplicate adverse subgroup cells")

    overall = cells.loc[cells["family"].eq("Overall"), [*keys, "adverse_count", "cohort_count"]]
    if overall.duplicated(keys).any():
        raise ValueError("Duplicate overall adverse cells")
    total = overall.rename(columns={
        "adverse_count": "overall_adverse_count",
        "cohort_count": "overall_cohort_count",
    })
    partition = cells.loc[cells["family"].isin(PARTITION_FAMILIES)].copy()
    groups = partition.groupby([*keys, "family"], as_index=False)[
        ["adverse_count", "cohort_count"]
    ].sum()
    groups = groups.merge(total, on=keys, how="left", validate="many_to_one", indicator=True)
    if (groups["_merge"].ne("both").any()
            or groups["adverse_count"].ne(groups["overall_adverse_count"]).any()
            or groups["cohort_count"].ne(groups["overall_cohort_count"]).any()):
        raise ValueError("Adverse-count subgroup partition does not reconcile")

    partition = partition.merge(
        total[[*keys, "overall_adverse_count"]],
        on=keys, validate="many_to_one", how="left",
    )
    partition["share_of_adverse_pct"] = np.where(
        partition["overall_adverse_count"].gt(0),
        100 * partition["adverse_count"] / partition["overall_adverse_count"],
        np.nan,
    )
    result = cells.merge(
        partition[[*keys, "family", "group", "share_of_adverse_pct"]],
        on=[*keys, "family", "group"], how="left", validate="one_to_one",
    )

    return result


def summarise_london_adverse(cells: pd.DataFrame, period_column: str) -> pd.DataFrame:
    """Pupil-weighted London counts/rates, separately for each subgroup family."""
    keys = [period_column, "new_la_code", "family", "group"]
    if cells.duplicated(keys).any():
        raise ValueError("Duplicate borough adverse cells in London summary")

    london = cells.groupby([period_column, "family", "group"], as_index=False)[
        list(COUNT_COLUMNS)
    ].sum()
    if london["cohort_count"].le(0).any():
        raise ValueError("Non-positive London cohort count")
    london["adverse_rate_pct"] = 100 * london["adverse_count"] / london["cohort_count"]
    london["one_pupil_pp"] = 100 / london["cohort_count"]

    return london.sort_values([period_column, "family", "group"]).reset_index(drop=True)


def build_disadvantage_adverse(published: pd.DataFrame) -> pd.DataFrame:
    """Adverse percentages from published sustained percentages; no exact counts."""
    result = published[[
        "time_period", "new_la_code", "la_name", "group",
        "cohort_count_disclosure_rounded", "sustained_pct_published",
    ]].copy()
    if (result.duplicated(["time_period", "new_la_code", "group"]).any()
            or result[["cohort_count_disclosure_rounded", "sustained_pct_published"]].isna().any().any()
            or result["cohort_count_disclosure_rounded"].le(0).any()
            or not result["sustained_pct_published"].between(0, 100).all()):
        raise ValueError("Invalid published disadvantage sustained rows")
    result["adverse_rate_pct_approx"] = 100 - result["sustained_pct_published"]

    return result.sort_values(["time_period", "new_la_code", "group"]).reset_index(drop=True)


def pool_disadvantage_adverse(
    annual: pd.DataFrame, period: str, *, london: bool = False,
) -> pd.DataFrame:
    """Approximate rate weighted by disclosure-rounded group cohort sizes."""
    years = PERIOD_YEARS[period]
    borough_key = ["new_la_code", "la_name", "group"]
    groups = ["group"] if london else borough_key
    selected = annual.loc[annual["time_period"].isin(years)].copy()
    base = set(annual[borough_key].itertuples(index=False, name=None))
    expected = {(year, *group) for year in years for group in base}
    observed = set(selected[["time_period", *borough_key]].itertuples(index=False, name=None))
    if observed != expected or len(selected) != len(expected):
        raise ValueError("Incomplete or duplicated disadvantage pooling coverage")

    selected["weighted_rate"] = (
        selected["adverse_rate_pct_approx"] * selected["cohort_count_disclosure_rounded"]
    )
    pooled = selected.groupby(groups, as_index=False).agg(
        weighted_rate=("weighted_rate", "sum"),
        rounded_cohort_weight_sum=("cohort_count_disclosure_rounded", "sum"),
    )
    pooled["adverse_rate_pct_approx"] = (
        pooled["weighted_rate"] / pooled["rounded_cohort_weight_sum"]
    )
    pooled["period"] = period

    return (pooled.drop(columns="weighted_rate")
            .sort_values(groups).reset_index(drop=True))


def calculate_disadvantage_gaps(pooled: pd.DataFrame) -> pd.DataFrame:
    """Approximate published-percentage disadvantage gap, without exact counts."""
    keys = ["period"]
    if "new_la_code" in pooled.columns:
        keys.extend(["new_la_code", "la_name"])
    if pooled.duplicated([*keys, "group"]).any():
        raise ValueError("Duplicate disadvantage group cells")

    comparison = "Not known to be disadvantaged"
    columns = [*keys, "adverse_rate_pct_approx", "rounded_cohort_weight_sum"]
    focus = pooled.loc[pooled["group"].eq("Disadvantaged"), columns].rename(columns={
        "adverse_rate_pct_approx": "disadvantaged_rate_pct_approx",
        "rounded_cohort_weight_sum": "disadvantaged_rounded_cohort_weight",
    })
    other = pooled.loc[pooled["group"].eq(comparison), columns].rename(columns={
        "adverse_rate_pct_approx": "not_known_disadvantaged_rate_pct_approx",
        "rounded_cohort_weight_sum": "not_known_rounded_cohort_weight",
    })
    paired = focus.merge(other, on=keys, how="outer", validate="one_to_one", indicator=True)
    if paired["_merge"].ne("both").any():
        raise ValueError("Incomplete disadvantage comparison groups")
    paired["gap_pp_approx"] = (
        paired["disadvantaged_rate_pct_approx"]
        - paired["not_known_disadvantaged_rate_pct_approx"]
    )

    return paired.drop(columns="_merge").sort_values(keys).reset_index(drop=True)
