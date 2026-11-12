"""Exact descriptive accounting of changes in London's KS4 adverse rate."""

import numpy as np
import pandas as pd

from youth_offer import need, pathways


PARTITIONS = need.GAP_GROUPS
COMPARISONS = {
    "2016/17 to 2022/23": (("201617",), ("202223",)),
    "Early pooled to recent pooled": (
        ("201617", "201718", "201819"), ("202122", "202223")
    ),
    "2021/22 to 2022/23": (("202122",), ("202223",)),
}
KEY = ("time_period", "new_la_code")
COUNT_COLUMNS = need.COUNT_COLUMNS
NOT_RECORDED = pathways.NOT_RECORDED
ACTIVITY_NOT_CAPTURED = pathways.ACTIVITY_NOT_CAPTURED
TOLERANCE_PP = 1e-10


def _exact_counts(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    """Reject disclosure tokens, missing values, and fractional/negative counts."""
    frame = frame.copy()
    for column in columns:
        try:
            values = pd.to_numeric(frame[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Non-numeric exact count: {column}") from exc
        if (values.isna().any() or (~np.isfinite(values)).any()
                or values.lt(0).any() or values.mod(1).ne(0).any()):
            raise ValueError(f"Invalid exact count: {column}")
        frame[column] = values.astype("int64")

    return frame


def _validated_cells(
    cells: pd.DataFrame, headline: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconcile every borough/cohort and each complete partition to the headline."""
    headline_columns = ("cohort_count", "adverse_count", NOT_RECORDED, ACTIVITY_NOT_CAPTURED)
    reference = _exact_counts(headline[[*KEY, *headline_columns]], headline_columns)
    if (reference[list(KEY)].isna().any().any()
            or reference.duplicated(list(KEY)).any() or reference.empty):
        raise ValueError("Missing or duplicated headline borough/cohort keys")
    if (reference["cohort_count"].le(0).any()
            or reference["adverse_count"].gt(reference["cohort_count"]).any()
            or not reference["adverse_count"].eq(
                reference[NOT_RECORDED] + reference[ACTIVITY_NOT_CAPTURED]
            ).all()):
        raise ValueError("Invalid headline adverse accounting")

    selected = cells.loc[cells["family"].isin(("Overall", *PARTITIONS))].copy()
    selected = _exact_counts(selected, COUNT_COLUMNS)
    if (selected[[*KEY, "family", "group"]].isna().any().any()
            or selected["cohort_count"].le(0).any()
            or selected["adverse_count"].gt(selected["cohort_count"]).any()
            or not selected["adverse_count"].eq(
                selected["not_recorded_count"] + selected["activity_not_captured_count"]
            ).all()):
        raise ValueError("Invalid subgroup adverse accounting")

    base_keys = set(reference[list(KEY)].itertuples(index=False, name=None))
    expected = {
        (year, borough, family, group)
        for year, borough in base_keys
        for family, groups in (("Overall", ("All pupils",)), *PARTITIONS.items())
        for group in groups
    }
    observed = set(
        selected[[*KEY, "family", "group"]].itertuples(index=False, name=None)
    )
    if observed != expected or len(selected) != len(expected):
        raise ValueError("Incomplete or duplicated historical subgroup cells")

    # The two alternative partitions must each reconstruct both adverse
    # components and the once-counted denominator in every borough/cohort.
    reference = reference.set_index(list(KEY)).sort_index()
    for family in ("Overall", *PARTITIONS):
        grouped = (selected.loc[selected["family"].eq(family)]
                   .groupby(list(KEY))[list(COUNT_COLUMNS)].sum().sort_index())
        for cell_column, headline_column in (
            ("cohort_count", "cohort_count"),
            ("adverse_count", "adverse_count"),
            ("not_recorded_count", NOT_RECORDED),
            ("activity_not_captured_count", ACTIVITY_NOT_CAPTURED),
        ):
            if not grouped[cell_column].equals(reference[headline_column]):
                raise ValueError(f"{family} partition disagrees with headline: {cell_column}")

    return selected, reference.reset_index()


def decompose_historical_change(
    cells: pd.DataFrame,
    headline: pd.DataFrame,
    comparisons: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return London comparisons and their exact group-level contributions.

    Each partition is an alternative accounting of the same overall change;
    FSM and SEN contributions must not be added across partitions.
    """
    selected, reference = _validated_cells(cells, headline)
    comparisons = COMPARISONS if comparisons is None else comparisons
    observed_years = set(reference["time_period"])
    summaries = []
    details = []

    for comparison, (start_years, end_years) in comparisons.items():
        if (not start_years or not end_years
                or len(set(start_years)) != len(start_years)
                or len(set(end_years)) != len(end_years)
                or set(start_years) & set(end_years)
                or not (set(start_years) | set(end_years)) <= observed_years):
            raise ValueError(f"Invalid or unavailable comparison periods: {comparison}")

        endpoints = []
        for years in (start_years, end_years):
            overall = reference.loc[reference["time_period"].isin(years)]
            endpoints.append((int(overall["adverse_count"].sum()),
                              int(overall["cohort_count"].sum())))
        (a0, n0), (a1, n1) = endpoints
        rate0, rate1 = a0 / n0, a1 / n1
        total_pp = 100 * (rate1 - rate0)

        for family, groups in PARTITIONS.items():
            subgroup = selected.loc[selected["family"].eq(family)]
            periods = []
            for years in (start_years, end_years):
                pooled = (subgroup.loc[subgroup["time_period"].isin(years)]
                          .groupby("group")[list(COUNT_COLUMNS)].sum()
                          .loc[list(groups)])
                periods.append(pooled)
            start, end = periods
            start_share = start["cohort_count"] / n0
            end_share = end["cohort_count"] / n1
            start_rate = start["adverse_count"] / start["cohort_count"]
            end_rate = end["adverse_count"] / end["cohort_count"]
            composition = 100 * (end_share - start_share) * (start_rate + end_rate) / 2
            within = 100 * (end_rate - start_rate) * (start_share + end_share) / 2

            if (abs(100 * ((start_share * start_rate).sum() - rate0)) > TOLERANCE_PP
                    or abs(100 * ((end_share * end_rate).sum() - rate1)) > TOLERANCE_PP
                    or abs(float(composition.sum() + within.sum()) - total_pp) > TOLERANCE_PP):
                raise AssertionError(f"Historical-change identity failed: {comparison}, {family}")

            summaries.append({
                "comparison": comparison, "partition": family,
                "composition_pp": float(composition.sum()),
                "within_group_pp": float(within.sum()),
                "observed_change_pp": total_pp,
            })
            for group in groups:
                details.append({
                    "comparison": comparison, "partition": family, "group": group,
                    "start_cohort_count": int(start.loc[group, "cohort_count"]),
                    "start_not_recorded_count": int(start.loc[group, "not_recorded_count"]),
                    "start_activity_not_captured_count": int(
                        start.loc[group, "activity_not_captured_count"]
                    ),
                    "start_adverse_count": int(start.loc[group, "adverse_count"]),
                    "start_share_pct": 100 * float(start_share.loc[group]),
                    "start_adverse_rate_pct": 100 * float(start_rate.loc[group]),
                    "end_cohort_count": int(end.loc[group, "cohort_count"]),
                    "end_not_recorded_count": int(end.loc[group, "not_recorded_count"]),
                    "end_activity_not_captured_count": int(
                        end.loc[group, "activity_not_captured_count"]
                    ),
                    "end_adverse_count": int(end.loc[group, "adverse_count"]),
                    "end_share_pct": 100 * float(end_share.loc[group]),
                    "end_adverse_rate_pct": 100 * float(end_rate.loc[group]),
                    "composition_pp": float(composition.loc[group]),
                    "within_group_pp": float(within.loc[group]),
                })

    return pd.DataFrame(summaries), pd.DataFrame(details)
