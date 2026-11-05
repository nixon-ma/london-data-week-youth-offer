"""Descriptive KS4 destination pathways from the frozen 2023/24 DfE release.

These tables are not person-level data or measures of programme impact.
"""

import pandas as pd

from youth_offer.model_tables import (
    PRIMARY_POPULATION,
    SUSTAINED,
    NOT_RECORDED,
    ACTIVITY_NOT_CAPTURED,
)

EDUCATION = "Sustained education destination"
EMPLOYMENT = "Sustained employment destination"
APPRENTICESHIPS = "Sustained apprenticeships"
DESTINATIONS = (
    EDUCATION,
    EMPLOYMENT,
    APPRENTICESHIPS,
    NOT_RECORDED,
    ACTIVITY_NOT_CAPTURED,
)

# Each family is an alternative view of the same pupils, not an extra population.
EXACT_FAMILIES = {
    "Overall": (None, None, ("Total",)),
    "FSM": ("breakdown", "FSM status", ("FSM eligible", "Not known to be FSM eligible")),
    "SEN": ("breakdown", "SEN provision", ("Identified SEN", "No identified SEN")),
    "SEN detail": ("breakdown", "SEN provision", ("SEN support", "SEN with EHC plan or statement")),
    "Sex": ("sex", None, ("Female", "Male")),
    "Ethnicity": ("ethnicity_major", None, (
        "Asian / Asian British", "Black / African / Caribbean / Black British",
        "Mixed / Multiple ethnic groups", "Other ethnic group", "Unknown", "White",
    )),
}
DISADVANTAGE_GROUPS = ("Disadvantaged", "Not known to be disadvantaged")
TOTAL_FIELDS = (
    "sex", "ethnicity_major", "ethnicity_minor",
    "disadvantage_status", "breakdown_topic", "breakdown",
)
KEY = ("time_period", "new_la_code", "family", "group")


def _select_family(source: pd.DataFrame, family: str) -> pd.DataFrame:
    field, topic, values = EXACT_FAMILIES[family]
    varying = {field} if field else set()
    if topic is not None:
        varying.add("breakdown_topic")

    mask = source["establishment_type_group"].eq(PRIMARY_POPULATION)
    mask &= source["destination_description"].isin(DESTINATIONS)
    for column in TOTAL_FIELDS:
        if column not in varying:
            mask &= source[column].eq("Total")
    if field:
        mask &= source[field].isin(values)
    if topic:
        mask &= source["breakdown_topic"].eq(topic)

    frame = source.loc[mask, [
        "time_period", "new_la_code", "la_name", "cohort_count",
        "destination_description", "pupil_count", "pupil_percent",
    ] + ([field] if field else [])].copy()
    frame["family"] = family
    frame["group"] = frame[field] if field else "All pupils"

    return frame.drop(columns=[field] if field else [])


def build_exact_pathways(source: pd.DataFrame) -> pd.DataFrame:
    """One row per borough/cohort/family/group/exclusive destination."""
    result = pd.concat(
        [_select_family(source, family) for family in EXACT_FAMILIES],
        ignore_index=True,
    ).rename(columns={"destination_description": "destination"})

    if result.duplicated([*KEY, "destination"]).any():
        raise ValueError("Non-unique exact destination-pathway keys")

    for column in ("cohort_count", "pupil_count"):
        result[column] = pd.to_numeric(result[column], errors="raise").astype("int64")
        if result[column].lt(0).any():
            raise ValueError(f"Negative {column}")
    if result.cohort_count.le(0).any():
        raise ValueError("Non-positive cohort denominator")

    result["published_percent_status"] = _code_status(result["pupil_percent"])
    numeric = result.published_percent_status.eq("numeric")
    published_numeric = pd.to_numeric(result.pupil_percent.where(numeric), errors="coerce")
    exact_pct = 100 * result.pupil_count / result.cohort_count
    if (published_numeric[numeric] - exact_pct[numeric]).abs().gt(0.050001).any():
        raise ValueError("Exact pathway counts disagree with published rounded percentages")
    low = result.published_percent_status.eq("low")
    if (low & (~exact_pct.gt(0) | ~exact_pct.lt(.5))).any():
        raise ValueError("Published low percentage is not strictly between 0 and 0.5")
    if (~result.published_percent_status.isin(["numeric", "low"])).any():
        raise ValueError("Unexpected disclosure status for exact-count pathway")

    result = result.rename(columns={"pupil_percent": "published_percent_token"})

    # Within a cohort/group, each of the five mutually exclusive outcomes
    # uses the same denominator: never add the denominator over destinations.
    summary = result.groupby(list(KEY), dropna=False).agg(
        n_destinations=("destination", "nunique"),
        denominator_versions=("cohort_count", "nunique"),
        destination_total=("pupil_count", "sum"),
        cohort=("cohort_count", "first"),
    )
    bad = (summary.n_destinations.ne(len(DESTINATIONS))
           | summary.denominator_versions.ne(1)
           | summary.destination_total.ne(summary.cohort))
    if bad.any():
        raise ValueError(f"Five-way cohort accounting failed for {int(bad.sum())} groups")

    # Compare complete borough/cohort/group keys directly. A groupby reduction
    # is unnecessary here and can obscure which source cells are missing.
    overall_keys = set(
        result.loc[result.family.eq("Overall"), ["time_period", "new_la_code"]]
        .itertuples(index=False, name=None)
    )
    for family, (_, _, allowed) in EXACT_FAMILIES.items():
        expected_groups = ("All pupils",) if family == "Overall" else allowed
        expected_keys = {
            (year, borough, group)
            for year, borough in overall_keys
            for group in expected_groups
        }
        observed_keys = set(
            result.loc[result.family.eq(family), ["time_period", "new_la_code", "group"]]
            .itertuples(index=False, name=None)
        )
        if observed_keys != expected_keys:
            missing = expected_keys - observed_keys
            extra = observed_keys - expected_keys
            raise ValueError(
                f"Incomplete borough/cohort subgroup coverage: {family}; "
                f"missing={len(missing)}, unexpected={len(extra)}; "
                f"examples missing={sorted(missing)[:3]}, unexpected={sorted(extra)[:3]}"
            )

    result["share_pct"] = 100 * result.pupil_count / result.cohort_count
    return result.sort_values([*KEY, "destination"]).reset_index(drop=True)


def summarise_london_pathways(exact: pd.DataFrame) -> pd.DataFrame:
    """Pupil-weighted London shares, never an unweighted borough-rate mean."""
    grain = ["time_period", "family", "group"]
    denominators = (exact.drop_duplicates(list(KEY))
                    .groupby(grain, as_index=False)["cohort_count"].sum())
    outcomes = (exact.groupby([*grain, "destination"], as_index=False)
                ["pupil_count"].sum())
    london = outcomes.merge(denominators, on=grain, validate="many_to_one")

    london["share_pct"] = 100 * london.pupil_count / london.cohort_count
    london = london.sort_values(["family", "group", "destination", "time_period"])
    london["annual_change_pp"] = (london.groupby(["family", "group", "destination"])
                                  ["share_pct"].diff())

    return london.reset_index(drop=True)


def endpoint_comparison(london: pd.DataFrame) -> pd.DataFrame:
    """2016/17 to 2022/23 comparison, in percentage points."""
    key = ["family", "group", "destination"]
    first = london.loc[london.time_period.eq("201617"), [*key, "share_pct"]]
    last = london.loc[london.time_period.eq("202223"), [*key, "share_pct"]]
    result = first.merge(last, on=key, how="outer", validate="one_to_one",
                         suffixes=("_201617", "_202223"))

    if result[["share_pct_201617", "share_pct_202223"]].isna().any().any():
        raise ValueError("Incomplete pathway endpoint comparison")

    result["change_pp"] = result.share_pct_202223 - result.share_pct_201617
    return result


def _code_status(raw: pd.Series) -> pd.Series:
    """Preserve disclosure tokens even when a numeric value is unavailable."""
    raw = raw.astype("string")
    valid_numeric = raw.str.fullmatch(r"\d+(?:\.\d+)?", na=False)

    codes = {"c": "suppressed_c", "low": "low", "z": "not_applicable_z", "x": "unavailable_x"}
    result = raw.map(codes).astype("string")
    result = result.mask(valid_numeric, "numeric")

    if result.isna().any():
        raise ValueError("Unexpected publication code")
    return result


def build_disadvantage_published(source: pd.DataFrame) -> pd.DataFrame:
    """Disadvantage pathway data: published percentages, never exact counts."""
    mask = (source.establishment_type_group.eq(PRIMARY_POPULATION)
            & source.destination_description.isin(DESTINATIONS)
            & source.sex.eq("Total") & source.ethnicity_major.eq("Total")
            & source.ethnicity_minor.eq("Total")
            & source.disadvantage_status.isin(DISADVANTAGE_GROUPS)
            & source.breakdown_topic.eq("Total") & source.breakdown.eq("Total"))

    published = source.loc[mask, [
        "time_period", "new_la_code", "la_name", "disadvantage_status",
        "cohort_count", "destination_description", "pupil_count", "pupil_percent",
    ]].copy()
    published = published.rename(columns={
        "disadvantage_status": "group", "destination_description": "destination",
        "cohort_count": "cohort_count_disclosure_rounded",
        "pupil_count": "published_pupil_count",
        "pupil_percent": "published_pupil_percent",
    })

    if published.duplicated(["time_period", "new_la_code", "group", "destination"]).any():
        raise ValueError("Non-unique disadvantage pathway keys")

    published["count_status"] = _code_status(published.published_pupil_count)
    published["percent_status"] = _code_status(published.published_pupil_percent)
    published["cohort_count_disclosure_rounded"] = pd.to_numeric(
        published.cohort_count_disclosure_rounded, errors="raise"
    ).astype("int64")
    published["reported_share_pct"] = pd.to_numeric(
        published.published_pupil_percent.where(published.percent_status.eq("numeric")),
        errors="coerce",
    )

    if (published.cohort_count_disclosure_rounded.le(0).any()
            or not published.reported_share_pct.dropna().between(0, 100).all()):
        raise ValueError("Invalid published disadvantage denominator or percentage")

    key = ["time_period", "new_la_code", "group"]
    qa = published.groupby(key).agg(
        categories=("destination", "nunique"),
        denominators=("cohort_count_disclosure_rounded", "nunique"),
    )
    if qa.categories.ne(5).any() or qa.denominators.ne(1).any():
        raise ValueError("Incomplete or inconsistent disadvantage pathway cells")

    return published.sort_values([*key, "destination"]).reset_index(drop=True)


def summarise_disadvantage_coverage(published: pd.DataFrame) -> pd.DataFrame:
    """Only report approximate London rate when all 32 boroughs are published."""
    values = []
    for (year, group, destination), g in published.groupby(
        ["time_period", "group", "destination"], sort=True
    ):
        complete = g.percent_status.eq("numeric")
        weight = g.cohort_count_disclosure_rounded
        complete_panel = (len(g) == 32 and complete.all())

        rate = (float((g.reported_share_pct * weight).sum() / weight.sum())
                if complete_panel else float("nan"))
        values.append({
            "time_period": year, "group": group, "destination": destination,
            "boroughs_total": len(g), "boroughs_published": int(complete.sum()),
            "approx_cohort_coverage_pct": 100 * weight[complete].sum() / weight.sum(),
            "london_share_pct_approx_only_if_complete": rate,
        })

    return pd.DataFrame(values)
