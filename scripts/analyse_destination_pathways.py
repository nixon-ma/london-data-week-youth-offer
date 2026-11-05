"""Analyse historical KS4 destination pathways from the frozen DfE release."""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from youth_offer.data import load_london_la_slice  # noqa: E402
from youth_offer import model_tables, qa, pathways  # noqa: E402

RAW = ROOT / "data/raw/key-stage-4-destination-measures_2023-24.zip"
OUTPUT = ROOT / "outputs/destination_pathways"
FIGURES = ROOT / "docs/figures"
YEARS = ("201617", "201718", "201819", "201920", "202021", "202122", "202223")
COLORS = ("#3074a4", "#11867d", "#e89c43")


def plot_sustained_pathways(london, destination):
    """Keep unequal pathway scales explicit rather than hiding small shares."""
    overall = london.loc[london.family.eq("Overall") & london.group.eq("All pupils")]

    fig, axes = plt.subplots(3, 1, figsize=(10.2, 8.2), sharex=True)
    items = [
        (pathways.EDUCATION, "Sustained education"),
        (pathways.EMPLOYMENT, "Sustained employment"),
        (pathways.APPRENTICESHIPS, "Sustained apprenticeships"),
    ]

    for ax, (category, label), color in zip(axes, items, COLORS):
        rows = overall.loc[overall.destination.eq(category)].set_index("time_period").reindex(YEARS)
        if rows.share_pct.isna().any():
            raise ValueError(f"Missing London pathway rates: {category}")

        y = rows.share_pct.to_numpy(dtype=float)
        ax.plot(np.arange(7), y, marker="o", lw=2.25, color=color)
        ax.set_ylabel(f"{label} (%)")
        ax.grid(axis="y", color="#e4e9ee")
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)

        if category == pathways.EDUCATION:
            ax.set_ylim(y.min() - .6, y.max() + .6)
            ax.text(.98, .86, "Truncated y-axis", transform=ax.transAxes,
                    ha="right", fontsize=9, color="#667588")
        else:
            ax.set_ylim(0, max(1, y.max() * 1.35))

        ax.annotate(f"{y[-1]:.2f}%", (6, y[-1]), xytext=(8, 2),
                    textcoords="offset points", color=color, fontsize=9)

    axes[-1].set_xticks(range(7), [f"{y[:4]}/{y[4:]}" for y in YEARS])
    axes[0].set_title("Sustained pathways after KS4: seven London cohorts", loc="left", pad=13)
    fig.text(.12, .013, "DfE 2023/24 release; mainstream + special, school-location LAs. Separate axes; education axis truncated.",
             fontsize=9, color="#667588")
    fig.tight_layout(rect=(0, .035, 1, 1), h_pad=1.6)

    destination.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["svg.hashsalt"] = "ldw-youth-offer-destination-pathways"
    fig.savefig(destination, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)

    # Remove nondeterministic whitespace to make local figure regeneration stable.
    destination.write_text(
        "".join(line.rstrip() + "\n" for line in destination.read_text(encoding="utf-8").splitlines()),
        encoding="utf-8",
    )


def main():
    source = load_london_la_slice(RAW)

    headline = model_tables.build_headline_outcome_table(source)
    qa.assert_headline_outcome_table(headline)

    exact = pathways.build_exact_pathways(source)
    qa.assert_exact_partition_accounting(exact)

    # The new five-way layer must reproduce the pre-existing frozen headline.
    overall = exact.loc[exact.family.eq("Overall")].pivot(
        index=["time_period", "new_la_code"], columns="destination", values="pupil_count"
    )
    check = headline.set_index(["time_period", "new_la_code"])
    frozen = check[model_tables.SUSTAINED].reindex(overall.index)
    if frozen.isna().any() or not (overall[pathways.EDUCATION] + overall[pathways.EMPLOYMENT]
            + overall[pathways.APPRENTICESHIPS]).eq(frozen).all():
        raise AssertionError("New sustained categories differ from frozen headline")
    for category in (pathways.NOT_RECORDED, pathways.ACTIVITY_NOT_CAPTURED):
        reference = check[category].reindex(overall.index)
        if reference.isna().any() or not overall[category].eq(reference).all():
            raise AssertionError(f"New pathway differs from frozen headline: {category}")

    n_boroughs = exact.loc[exact.family.eq("Overall")].groupby("time_period")["new_la_code"].nunique()
    if not (len(exact.loc[exact.family.eq("Overall")]) == 7 * 32 * 5
            and n_boroughs.eq(32).all() and set(n_boroughs.index) == set(YEARS)):
        raise AssertionError("Primary panel must contain seven complete 32-borough cohorts")

    london = pathways.summarise_london_pathways(exact)
    endpoint = pathways.endpoint_comparison(london)

    disadvantage = pathways.build_disadvantage_published(source)
    qa.assert_disadvantage_panel(disadvantage, exact)
    coverage = pathways.summarise_disadvantage_coverage(disadvantage)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    exact.to_csv(OUTPUT / "exact_pathways.csv", index=False)
    london.to_csv(OUTPUT / "london_pathways.csv", index=False)
    endpoint.to_csv(OUTPUT / "endpoint_pathways.csv", index=False)
    disadvantage.to_csv(OUTPUT / "disadvantage_published_pathways.csv", index=False)
    coverage.to_csv(OUTPUT / "disadvantage_coverage.csv", index=False)

    svg = FIGURES / "08_destination_pathways.svg"
    plot_sustained_pathways(london, svg)

    print("Destination-pathway and frozen-headline QA passed.")
    print(f"Exact groups: {len(exact) // 5}; London summary rows: {len(london)}")
    print("2022/23 overall pathway counts and shares:")
    print(london.loc[london.family.eq("Overall") & london.time_period.eq("202223"),
                     ["destination", "pupil_count", "share_pct"]].to_string(index=False))
    print(f"Output: {OUTPUT}; figure: {svg}")


if __name__ == "__main__":
    main()
