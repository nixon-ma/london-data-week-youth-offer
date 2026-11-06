"""Historical adverse burden and subgroup persistence from the frozen DfE release."""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from youth_offer.data import load_london_la_slice  # noqa: E402
from youth_offer import model_tables, need, pathways, qa  # noqa: E402

RAW = ROOT / "data/raw/key-stage-4-destination-measures_2023-24.zip"
OUTPUT = ROOT / "outputs/destination_need"
FIGURE = ROOT / "docs/figures/09_borough_fsm_sen_gaps.svg"
PRIMARY_PERIOD = "2021/22–2022/23"


def plot_borough_gaps(pooled_gaps: pd.DataFrame, destination: Path) -> None:
    """Aligned alphabetical borough views; no targeting order or ranking."""
    selected = pooled_gaps.loc[pooled_gaps["period"].eq(PRIMARY_PERIOD)]
    wide = selected.pivot(index=["new_la_code", "la_name"],
                          columns="family", values="gap_pp")
    if len(wide) != 32 or wide[["FSM", "SEN"]].isna().any().any():
        raise ValueError("Figure 9 requires complete pooled FSM/SEN borough gaps")

    wide = wide.reset_index().sort_values(["la_name", "new_la_code"])
    y = np.arange(len(wide))
    lo = min(0.0, float(wide[["FSM", "SEN"]].min().min()))
    hi = max(0.0, float(wide[["FSM", "SEN"]].max().max()))
    spread = max(hi - lo, 1.0)
    limits = (lo - 0.06 * spread, hi + 0.08 * spread)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 11.5), sharex=True, sharey=True)
    for ax, family, title, color in [
        (axes[0], "FSM", "FSM eligible − not known eligible", "#3074a4"),
        (axes[1], "SEN", "Identified SEN − no identified SEN", "#11867d"),
    ]:
        values = wide[family].to_numpy(dtype=float)
        ax.axvline(0, color="#607080", lw=1.2)
        ax.hlines(y, 0, values, color=color, alpha=.42, lw=1.3)
        ax.scatter(values, y, color=color, s=26, zorder=3)
        ax.set_xlim(*limits)
        ax.set_title(title, loc="left", fontsize=11, pad=10)
        ax.set_xlabel("Adverse-rate gap (percentage points)")
        ax.set_yticks(y)
        ax.grid(axis="x", color="#e5eaef", lw=.65)
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)

    axes[0].set_yticklabels(wide["la_name"], fontsize=8)
    axes[0].invert_yaxis()
    axes[1].tick_params(axis="y", labelleft=False)
    fig.suptitle(
        "FSM and SEN adverse-rate gaps across London boroughs, 2021/22–2022/23 pooled",
        fontsize=14, y=.992,
    )
    fig.text(
        .04, .947,
        "Within-borough differences (percentage points); combined mainstream + special-school KS4 cohorts.",
        fontsize=9, color="#526475",
    )
    fig.text(
        .04, .015,
        "Rates use pooled adverse counts and cohort denominators, not averages of annual rates. "
        "DfE 2023/24 release; school-location boroughs; not a NEET or causal measure.",
        fontsize=8, color="#526475",
    )
    fig.tight_layout(rect=(0, .035, 1, .915), w_pad=2.0)

    destination.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["svg.hashsalt"] = "ldw-youth-offer-need-gaps"
    fig.savefig(destination, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    destination.write_text(
        "".join(line.rstrip() + "\n" for line in destination.read_text(encoding="utf-8").splitlines()),
        encoding="utf-8",
    )


def build_outputs(source: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build and verify independently labelled D11b descriptive tables."""
    headline = model_tables.build_headline_outcome_table(source)
    qa.assert_headline_outcome_table(headline)
    qa.assert_population_accounting(source)

    exact = pathways.build_exact_pathways(source)
    qa.assert_exact_partition_accounting(exact)
    primary_cells = need.build_adverse_cells(exact)
    qa.assert_need_primary_panel(primary_cells, headline)

    primary_annual = need.add_group_burden_shares(primary_cells, "time_period")
    primary_periods = pd.concat(
        [need.pool_adverse_cells(primary_cells, period) for period in need.PERIOD_YEARS],
        ignore_index=True,
    )
    for period in need.PERIOD_YEARS:
        qa.assert_need_period_reconciliation(primary_cells, primary_periods, period)
    primary_pooled = need.add_group_burden_shares(primary_periods, "period")

    annual_gaps = need.calculate_fsm_sen_gaps(primary_annual, "time_period")
    pooled_gaps = need.calculate_fsm_sen_gaps(primary_pooled, "period")
    persistence = need.summarise_gap_persistence(annual_gaps)

    published = pathways.build_disadvantage_sustained(source)
    qa.assert_disadvantage_sustained_panel(published, exact)
    disadvantage_annual = need.build_disadvantage_adverse(published)
    disadvantage_pooled = pd.concat(
        [need.pool_disadvantage_adverse(disadvantage_annual, period)
         for period in need.PERIOD_YEARS], ignore_index=True,
    )
    disadvantage_pooled_gaps = need.calculate_disadvantage_gaps(disadvantage_pooled)
    if len(disadvantage_pooled_gaps) != 32 * len(need.PERIOD_YEARS):
        raise AssertionError("Incomplete pooled disadvantage borough comparisons")

    mainstream_exact = pathways.build_exact_pathways(
        source, population=pathways.MAINSTREAM_POPULATION,
        families=("Overall", "FSM", "SEN"),
    )
    qa.assert_selected_partition_accounting(mainstream_exact)
    mainstream = need.build_adverse_cells(mainstream_exact)
    mainstream_pooled = pd.concat(
        [need.pool_adverse_cells(mainstream, period) for period in need.PERIOD_YEARS],
        ignore_index=True,
    )
    mainstream_pooled_gaps = need.calculate_fsm_sen_gaps(mainstream_pooled, "period")

    ap_exact = pathways.build_exact_pathways(
        source, population=pathways.AP_POPULATION, families=("Overall",),
    )
    qa.assert_selected_partition_accounting(ap_exact)
    ap_all = need.build_adverse_cells(ap_exact)
    borough_codes = set(primary_cells["new_la_code"])
    ap_excluded = ap_all.loc[~ap_all["new_la_code"].isin(borough_codes)].copy()
    extras = set(ap_excluded[["time_period", "new_la_code", "cohort_count"]]
                 .itertuples(index=False, name=None))
    if extras != {("201718", "E09000001", 1), ("201819", "E09000001", 1)}:
        raise AssertionError("Unexpected exceptional AP authority observations")
    ap = ap_all.loc[ap_all["new_la_code"].isin(borough_codes)].copy()
    qa.assert_need_secondary_population(primary_cells, mainstream, ap)
    ap_london = need.summarise_london_adverse(ap, "time_period")

    return {
        "primary_annual_adverse.csv": primary_annual,
        "primary_pooled_adverse.csv": primary_pooled,
        "fsm_sen_annual_gaps.csv": annual_gaps,
        "fsm_sen_pooled_gaps.csv": pooled_gaps,
        "fsm_sen_persistence.csv": persistence,
        "disadvantage_annual_adverse_approx.csv": disadvantage_annual,
        "disadvantage_pooled_adverse_approx.csv": disadvantage_pooled,
        "mainstream_fsm_sen_pooled_gaps.csv": mainstream_pooled_gaps,
        "ap_london_annual.csv": ap_london,
    }


def main() -> None:
    source = load_london_la_slice(RAW)
    tables = build_outputs(source)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, frame in tables.items():
        frame.to_csv(OUTPUT / filename, index=False)
    plot_borough_gaps(tables["fsm_sen_pooled_gaps.csv"], FIGURE)

    # Reconstruct London comparisons from retained tables rather than export duplicates.
    london = need.summarise_london_adverse(tables["primary_pooled_adverse.csv"], "period")
    london = london.assign(new_la_code="LONDON", la_name="London")
    london_gaps = need.calculate_fsm_sen_gaps(london, "period")

    disadvantage_london = pd.concat(
        [need.pool_disadvantage_adverse(
            tables["disadvantage_annual_adverse_approx.csv"], period, london=True,
        ) for period in need.PERIOD_YEARS], ignore_index=True,
    )
    disadvantage_gaps = need.calculate_disadvantage_gaps(disadvantage_london)

    print("D11b complete: primary, subgroup, disclosure and AP population QA passed.")
    print(london_gaps[["period", "family", "gap_pp"]].to_string(index=False))
    print("London disadvantage gaps (approximate, pp):")
    print(disadvantage_gaps[["period", "gap_pp_approx"]].to_string(index=False))
    print(tables["fsm_sen_persistence.csv"]
          .groupby("family")[["positive_years", "zero_years", "negative_years"]]
          .sum().to_string())

    # Don't silently represent leftover files from an earlier 20-CSV run as new outputs.
    unlisted = sorted(path.name for path in OUTPUT.glob("*.csv")
                      if path.name not in tables)
    if unlisted:
        print(f"Existing CSVs not generated by this run in {OUTPUT}: {', '.join(unlisted)}")
    print(f"Nine tables: {OUTPUT}; Figure 9: {FIGURE}")


if __name__ == "__main__":
    main()
