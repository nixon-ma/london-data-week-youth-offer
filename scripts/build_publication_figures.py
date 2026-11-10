"""Generate six headline figures and one supplementary publication figure from frozen London Youth Offer evidence.

Run from the repository root after the existing explanatory/development pipeline
and the authorised 2022/23 final predictive release have exported their CSVs.
This module draws figures only: it does not fit, tune or score models.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from youth_offer import data, model_tables  # noqa: E402

YEARS = ("201617", "201718", "201819", "201920", "202021", "202122", "202223")
YEAR_LABELS = [f"{y[:4]}/{y[4:]}" for y in YEARS]
NAVY = "#19283e"
BLUE = "#3074a4"
TEAL = "#11867d"
ORANGE = "#e89c43"
GREY = "#667588"
FAINT = "#e4e9ee"


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 14, "axes.labelsize": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.labelcolor": NAVY, "text.color": NAVY,
        "xtick.color": GREY, "ytick.color": GREY,
        "svg.fonttype": "none", "svg.hashsalt": "ldw-youth-offer-publication",
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })


def save(fig, directory: Path, stem: str):
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / f"{stem}.svg"
    fig.savefig(output, format="svg", bbox_inches="tight",
                metadata={"Date": None, "Creator": "London Data Week Youth Offer rebuild"})
    # Matplotlib sometimes adds trailing spaces inside multiline SVG paths.
    # Remove them for a clean git patch; SVG path data are whitespace-tolerant.
    output.write_text("".join(line.rstrip() + "\n" for line in output.read_text(encoding="utf-8").splitlines()), encoding="utf-8")
    plt.close(fig)


def require_columns(df, required, source):
    absent = set(required).difference(df.columns)
    if absent:
        raise ValueError(f"{source}: missing columns {sorted(absent)}")


def headline_data(london):
    h = model_tables.build_headline_outcome_table(london)
    expected = {(y, b) for y in YEARS for b in h.new_la_code.unique()}
    if (len(h) != 224 or h.new_la_code.nunique() != 32
            or set(zip(h.time_period, h.new_la_code)) != expected):
        raise ValueError("Expected exactly 32 boroughs in each of seven cohorts")
    if not (h[model_tables.SUSTAINED] + h[model_tables.NOT_RECORDED]
            + h[model_tables.ACTIVITY_NOT_CAPTURED]).eq(h.cohort_count).all():
        raise ValueError("Headline pupil counts do not reconcile")
    return h


def fig_trend(h, out):
    cols = [model_tables.NOT_RECORDED, model_tables.ACTIVITY_NOT_CAPTURED, "cohort_count", "adverse_count"]
    totals = h.groupby("time_period")[cols].sum().reindex(YEARS)
    rates = (100 * totals[[model_tables.NOT_RECORDED, model_tables.ACTIVITY_NOT_CAPTURED]].div(totals.cohort_count, axis=0)).astype(float)
    assert np.isfinite(rates.to_numpy()).all()
    fig, ax = plt.subplots(figsize=(10.4, 4.8))
    x = np.arange(7)
    ax.stackplot(x, rates.iloc[:, 0], rates.iloc[:, 1], colors=[BLUE, ORANGE], alpha=.92,
                 labels=["Not recorded as sustained", "Activity not captured"])
    overall = rates.sum(axis=1)
    ax.plot(x, overall, color=NAVY, lw=2, marker="o", markersize=4)
    for j in (0, 4, 6):
        ax.annotate(f"{overall.iloc[j]:.2f}%", (x[j], overall.iloc[j]),
                    xytext=(0, 10), textcoords="offset points", ha="center", fontweight="bold")
    ax.set_title("London's recorded destination gap widened after 2020/21", loc="left", pad=14)
    ax.set_ylabel("Share of KS4 cohort (%)")
    ax.set_xticks(x, YEAR_LABELS)
    ax.set_ylim(0, max(7.8, float(overall.max()) + .65))
    ax.grid(axis="y", color=FAINT)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.text(1, -0.21, f"2022/23: {int(totals.iloc[-1].adverse_count):,} pupils; 32 school-location boroughs",
            transform=ax.transAxes, ha="right", fontsize=9, color=GREY)
    fig.tight_layout()
    save(fig, out, "01_london_trend")


def fig_borough(h, out):
    latest = h.loc[h.time_period.eq("202223")].copy()
    latest["rate_pct"] = (100 * latest.adverse_rate).astype(float)
    latest["adverse_count"] = latest.adverse_count.astype(float)
    fig, ax = plt.subplots(figsize=(9.4, 5.7))
    ax.scatter(latest.rate_pct, latest.adverse_count, s=54, color=TEAL, alpha=.85,
               edgecolor="white", linewidth=.8, zorder=3)
    names = {"Newham", "Islington", latest.loc[latest.rate_pct.idxmax(), "la_name"],
             latest.loc[latest.adverse_count.idxmax(), "la_name"]}
    for _, r in latest.loc[latest.la_name.isin(names)].iterrows():
        ax.annotate(r.la_name, (r.rate_pct, r.adverse_count), xytext=(6, 7),
                    textcoords="offset points", fontsize=9, color=NAVY)
    ax.set_title("High rates and high pupil counts tell different stories", loc="left", pad=14)
    ax.set_xlabel("Outside recorded sustained destinations (%), 2022/23")
    ax.set_ylabel("Pupils outside recorded sustained destinations (count)")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(color=FAINT)
    ax.set_axisbelow(True)
    ax.text(1, -0.16, "Each point represents one of the 32 school-location London boroughs",
            transform=ax.transAxes, ha="right", fontsize=9, color=GREY)
    fig.tight_layout()
    save(fig, out, "02_borough_rates_counts")


def subgroup_rates(london):
    """2022/23 LA-aggregated groups; disadvantage uses published rates, not rounded pupil counts."""
    d = london.loc[
        london.time_period.eq("202223")
        & london.establishment_type_group.eq(model_tables.PRIMARY_POPULATION)
        & london.destination_description.eq(model_tables.SUSTAINED)
        & london.ethnicity_major.eq("Total") & london.ethnicity_minor.eq("Total")
    ].copy()
    groups = [
        ("Disadvantage", "disadvantage_status", ["Disadvantaged", "Not known to be disadvantaged"],
         {"sex": "Total", "breakdown_topic": "Total", "breakdown": "Total"}),
        ("FSM status", "breakdown", ["FSM eligible", "Not known to be FSM eligible"],
         {"sex": "Total", "disadvantage_status": "Total", "breakdown_topic": "FSM status"}),
        ("Identified SEN", "breakdown", ["Identified SEN", "No identified SEN"],
         {"sex": "Total", "disadvantage_status": "Total", "breakdown_topic": "SEN provision"}),
        ("Sex", "sex", ["Male", "Female"],
         {"disadvantage_status": "Total", "breakdown_topic": "Total", "breakdown": "Total"}),
    ]
    out = []
    for fam, col, names, filters in groups:
        cur = d
        for key, value in filters.items():
            cur = cur.loc[cur[key].eq(value)]
        cur = cur.loc[cur[col].isin(names)].copy()
        if len(cur) != 64 or not cur.groupby(col).size().eq(32).all():
            raise ValueError(f"{fam}: expected two complete 32-borough groups")
        for name in names:
            rows = cur.loc[cur[col].eq(name)]
            denom = pd.to_numeric(rows.cohort_count, errors="raise").to_numpy(dtype=float)
            if fam == "Disadvantage":
                # Counts are separately disclosure-rounded: use each published sustained
                # percentage and *approximate* published cohort weights (not exact rates).
                sustained_pct = pd.to_numeric(rows.pupil_percent, errors="raise").to_numpy(dtype=float)
                adverse_pct = 100 - np.average(sustained_pct, weights=denom)
            else:
                sustained = pd.to_numeric(rows.pupil_count, errors="raise").to_numpy(dtype=float)
                adverse_pct = 100 * (denom.sum() - sustained.sum()) / denom.sum()
            out.append((fam, name, float(adverse_pct)))
    return pd.DataFrame(out, columns=["family", "group", "rate_pct"])


def fig_subgroups(london, out):
    tab = subgroup_rates(london)
    fig, ax = plt.subplots(figsize=(10.2, 5.25))
    family_order = ["Disadvantage", "FSM status", "Identified SEN", "Sex"]
    right_labels = ["Disadvantaged", "FSM eligible", "Identified SEN", "Male"]
    left_labels = ["Other", "Other", "No identified SEN", "Female"]
    for j, family in enumerate(family_order):
        rows = tab.loc[tab.family.eq(family)]
        a = float(rows.loc[rows.group.eq(right_labels[j]), "rate_pct"].iloc[0])
        b = float(rows.loc[~rows.group.eq(right_labels[j]), "rate_pct"].iloc[0])
        y = len(family_order) - 1 - j
        ax.plot([a, b], [y, y], color=FAINT, lw=6, solid_capstyle="round", zorder=1)
        ax.scatter([a], [y], color=ORANGE, s=93, zorder=3)
        ax.scatter([b], [y], color=BLUE, s=93, zorder=3)
        ax.annotate(f"{a:.1f}%", (a, y), xytext=(0, 10), textcoords="offset points", ha="center", fontsize=9)
        ax.annotate(f"{b:.1f}%", (b, y), xytext=(0, -18), textcoords="offset points", ha="center", fontsize=9)
        ax.text(max(a, b) + .55, y, f"gap {a-b:.1f} pp", va="center", color=GREY, fontsize=9)
    ax.set_yticks(range(4), family_order[::-1])
    ax.set_xlim(0, 15)
    ax.set_ylim(-.5, 3.55)
    ax.set_xlabel("Outside recorded sustained destinations (%), 2022/23")
    ax.set_title("Socioeconomic disadvantage and SEN show substantial disparities", loc="left", pad=17)
    ax.plot([], [], "o", color=ORANGE, label="Disadvantaged / FSM / SEN / male")
    ax.plot([], [], "o", color=BLUE, label="Comparison group")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.grid(axis="x", color=FAINT)
    ax.set_axisbelow(True)
    fig.text(.12, .014,
             "Blue points, top to bottom: not known disadvantaged; not known FSM eligible; no identified SEN; female.\n"
             "Denominator: each group's own KS4 cohort across 32 London school-location boroughs.\n"
             "Disadvantage approximate (rounded percentages and cohort counts); FSM overlaps disadvantage.",
             fontsize=8.4, color=GREY, va="bottom", linespacing=1.3)
    fig.tight_layout(rect=(0, .14, 1, 1))
    save(fig, out, "03_subgroup_disparities")


def read_export(path, cols):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Generate the existing frozen outputs before plotting.")
    df = pd.read_csv(path, dtype={"estimate_key": str, "estimand": str, "method": str,
                                     "check": str, "case": str})
    require_columns(df, cols, path)
    return df


def fig_explanatory(d9e, out):
    points = read_export(d9e / "d9e_point_estimates.csv", ["estimate_key", "estimate"])
    cis = read_export(d9e / "d9e_bootstrap_intervals.csv", ["estimate_key", "lower_95", "upper_95"])
    robust = read_export(d9e / "d9e_robustness.csv", ["check", "case", "estimand", "status", "sensitivity_on_retained"])
    if points.estimate_key.duplicated().any() or cis.estimate_key.duplicated().any():
        raise ValueError("D9e estimand keys must be unique")
    tab = points.merge(cis, on="estimate_key", validate="one_to_one").set_index("estimate_key")
    keys = ["baseline_pp:202021", "baseline_pp:202223", "adjacent_pp:202223"]
    labels = ["2020/21 vs 2016/17", "2022/23 vs 2016/17", "2022/23 vs 2021/22"]
    subset = tab.loc[keys]
    x = subset.estimate.to_numpy(dtype=float)
    low = subset.lower_95.to_numpy(dtype=float)
    high = subset.upper_95.to_numpy(dtype=float)
    if not (np.isfinite([*x, *low, *high]).all() and np.all(low <= x) and np.all(x <= high)):
        raise ValueError("Invalid D9e bootstrap intervals")
    r = robust.loc[robust.check.eq("linear_cohort_trend") & robust.case.eq("all")
                   & robust.estimand.eq("baseline_pp:202223") & robust.status.eq("comparable")]
    if len(r) != 1:
        raise ValueError("Expected exactly one comparable linear-trend endpoint sensitivity")
    trend = float(r.sensitivity_on_retained.iloc[0])
    fig, ax = plt.subplots(figsize=(10.1, 5.2))
    ys = np.array([3, 2, 1])
    ax.errorbar(x, ys, xerr=[x-low, high-x], fmt="o", markersize=8, lw=2.4,
                capsize=4, color=TEAL, ecolor=TEAL, zorder=4)
    ax.scatter([trend], [0], marker="D", s=78, color=ORANGE, zorder=4)
    ax.axvline(0, color=GREY, ls="--", lw=1.1)
    ax.set_yticks([3, 2, 1, 0], [*labels, "Linear-trend alternative: endpoint"])
    ax.set_xlabel("Adjusted E4 change in adverse probability (percentage points)")
    ax.set_title("A recent rise is visible, but the endpoint depends on time specification", loc="left", pad=16)
    ax.set_xlim(-1.55, 1.55)
    for xi, yi in zip(x, ys):
        ax.annotate(f"{xi:+.3f} pp", (xi, yi), xytext=(4, 9), textcoords="offset points", fontsize=9)
    ax.annotate(f"{trend:+.3f} pp (no interval)", (trend, 0), xytext=(6, 9),
                textcoords="offset points", color=NAVY, fontsize=9)
    ax.set_ylim(-.55, 3.6)
    ax.grid(axis="x", color=FAINT)
    ax.set_axisbelow(True)
    fig.text(.12, .02, "E4: equally weighted reference profiles; 95% whole-borough bootstrap intervals. Trend is a different specification, not a bootstrap interval.",
             fontsize=8.1, color=GREY)
    fig.tight_layout(rect=(0, .05, 1, 1))
    save(fig, out, "04_explanatory_uncertainty")



def load_explanatory_fit_mae(d9e):
    """Read the pipeline's E1–E4 in-sample errors for Figure 6."""
    metrics = read_export(d9e.parent / "e1_e4_fit_metrics.csv",
                          ["model", "mae_pp", "rmse_pp"])
    models = ["E1", "E2", "E3", "E4"]
    if len(metrics) != 4 or set(metrics.model) != set(models):
        raise ValueError("Expected exactly one in-sample fit-metrics row per E1–E4 model")
    values = metrics.set_index("model").loc[models, ["mae_pp", "rmse_pp"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid E1–E4 in-sample fit metrics")
    return values[:, 0]


def fig_explanatory_structure(d9e, out):
    """Audited in-sample fit beside D9e's conditional composition associations."""
    points = read_export(d9e / "d9e_point_estimates.csv", ["estimate_key", "estimate"])
    intervals = read_export(d9e / "d9e_bootstrap_intervals.csv",
                            ["estimate_key", "lower_95", "upper_95"])
    if points.estimate_key.duplicated().any() or intervals.estimate_key.duplicated().any():
        raise ValueError("Composition estimand and interval keys must be unique")
    joined = points.merge(intervals, on="estimate_key", validate="one_to_one").set_index("estimate_key")
    composition = [
        ("FSM share +2 pp", "composition_pp:fsm_share"),
        ("Identified SEN share +2 pp", "composition_pp:identified_sen_share"),
        ("Special-school share +0.25 pp", "composition_pp:special_school_share"),
    ]
    rows = joined.loc[[k for _, k in composition]]
    estimates = rows.estimate.to_numpy(dtype=float)
    lower = rows.lower_95.to_numpy(dtype=float)
    upper = rows.upper_95.to_numpy(dtype=float)
    if not (np.isfinite([*estimates, *lower, *upper]).all()
            and np.all(lower <= estimates) and np.all(estimates <= upper)):
        raise ValueError("Invalid composition bootstrap intervals")
    fit = load_explanatory_fit_mae(d9e)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.5),
                                   gridspec_kw={"width_ratios": [1, 1.15]})
    names = ["E1  Year only", "E2  Borough only",
             "E3  Borough + year", "E4  + composition"]
    yy = np.arange(4)
    ax1.barh(yy, fit, height=.6, color=[BLUE, BLUE, TEAL, TEAL])
    for y, value in zip(yy, fit):
        ax1.text(value + .012, y, f"{value:.4f}", va="center", fontsize=10)
    ax1.set_yticks(yy, names)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 1.16)
    ax1.set_xlabel("In-sample MAE (pp; lower is better)")
    ax1.set_title("A  |  Structure and fit", loc="left", pad=12, fontweight="bold")
    ax1.grid(axis="x", color=FAINT)
    ax1.set_axisbelow(True)

    ycomp = np.arange(3)
    ax2.errorbar(estimates, ycomp, xerr=[estimates-lower, upper-estimates],
                 fmt="o", color=TEAL, ecolor=TEAL, capsize=4, lw=2.2,
                 markersize=7, zorder=3)
    ax2.axvline(0, color=GREY, linestyle="--", lw=1.1)
    ax2.set_yticks(ycomp, [x[0] for x in composition])
    ax2.invert_yaxis()
    ax2.set_xlim(min(-.21, float(lower.min())-.03),
                 max(.21, float(upper.max())+.03))
    ax2.set_xlabel("Modelled probability difference (pp)")
    ax2.set_title("B  |  Conditional E4 associations", loc="left", pad=12, fontweight="bold")
    for y, value in zip(ycomp, estimates):
        ax2.annotate(f"{value:+.3f}", (value, y), xytext=(3, 9),
                     textcoords="offset points", ha="left", fontsize=9)
    ax2.grid(axis="x", color=FAINT)
    ax2.set_axisbelow(True)
    fig.suptitle("Borough/year structure drives the largest in-sample fit gains",
                 x=.055, y=.995, ha="left", fontsize=15, fontweight="bold", color=NAVY)
    fig.text(.055, .015,
             "A: DATA_AUDIT.md §23.5 (224 in-sample borough-years).  B: D9e whole-borough bootstrap; equal-profile contrasts, not pupil effects or causal effects.",
             fontsize=8.4, color=GREY)
    fig.tight_layout(rect=(.01, .05, 1, .93), w_pad=3.0)
    save(fig, out, "06_explanatory_structure")


def fig_borough_heatmap(headline, out):
    """Show seven-year observed adverse rates without introducing borough estimates."""
    panel = headline.pivot(index="la_name", columns="time_period", values="adverse_rate")
    if panel.shape != (32, 7) or set(panel.columns) != set(YEARS):
        raise ValueError("Expected 32 boroughs and exactly seven distinct cohorts")
    panel = panel.loc[:, YEARS].astype(float) * 100
    if not (np.isfinite(panel.to_numpy()).all() and panel.ge(0).all().all()
            and panel.le(100).all().all()):
        raise ValueError("Invalid borough rates")
    panel = panel.loc[panel.mean(axis=1).sort_values(ascending=False).index]
    increasing = int((panel["202223"] > panel["202122"]).sum())
    rank_corr = float(panel["201617"].rank().corr(panel["202223"].rank()))
    vmax = max(10., float(np.ceil(panel.to_numpy().max() * 2) / 2))
    fig, ax = plt.subplots(figsize=(11.1, 10.0))
    heat = ax.imshow(panel.to_numpy(), cmap="YlGnBu", vmin=0, vmax=vmax,
                     aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(7), YEAR_LABELS)
    ax.set_yticks(np.arange(len(panel)), panel.index, fontsize=8.4)
    ax.set_xlabel("KS4 cohort")
    ax.set_title("Borough gaps persist, but most boroughs worsened in 2022/23",
                 loc="left", pad=18, fontsize=14)
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(heat, ax=ax, fraction=.033, pad=.035)
    bar.set_label("Outside recorded sustained destinations (% of cohort)")
    fig.text(.15, .03,
             f"Rows sorted by mean adverse rate across all seven cohorts  |  "
             f"{increasing}/32 boroughs increased in 2022/23  |  "
             f"2016/17–2022/23 rank correlation {rank_corr:.2f}",
             color=GREY, fontsize=9)
    fig.text(.15, .012,
             "School/institution LA, not pupils' residence; descriptive rates, not NEET or council performance.",
             color=GREY, fontsize=8.5)
    fig.tight_layout(rect=(0, .05, 1, .99))
    save(fig, out, "07_borough_rate_heatmap")

def fig_predictive(development_dir, final_dir, out):
    dev = read_export(development_dir / "summary_metrics.csv", ["method", "mae_pp"])
    final = read_export(final_dir / "released_annual_metrics.csv", ["method", "mae_pp", "target_year"])
    if len(dev) != 4 or len(final) != 4 or set(dev.method) != {"B1", "B2", "B3", "M1"} or set(final.method) != {"B1", "B2", "B3", "M1"}:
        raise ValueError("Expected exactly four frozen methods in both evaluations")
    if set(final.target_year.astype(str)) != {"202223"}:
        raise ValueError("Final benchmark must refer exclusively to 2022/23")
    methods = ["B1", "B2", "B3", "M1"]
    x = np.arange(len(methods))
    d = dev.set_index("method").loc[methods, "mae_pp"].to_numpy(dtype=float)
    f = final.set_index("method").loc[methods, "mae_pp"].to_numpy(dtype=float)
    if not np.isfinite([*d, *f]).all():
        raise ValueError("Non-finite predictive errors")
    fig, ax = plt.subplots(figsize=(9.8, 5.15))
    w = .34
    b1 = ax.bar(x-w/2, d, w, color=BLUE, label="Development mean (2018/19–2021/22)")
    b2 = ax.bar(x+w/2, f, w, color=TEAL, label="Final cohort (2022/23)")
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()+.035,
                    f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, ["B1\nBorough\npersistence", "B2\nLondon\npersistence",
                      "B3\nLondon +\nborough offset", "M1\nMedian\nregression"])
    ax.set_ylabel("Mean absolute error (percentage points; lower is better)")
    ax.set_title("A simple borough-offset benchmark outperformed the learned model", loc="left", pad=16)
    ax.set_ylim(0, max(d.max(), f.max()) * 1.23)
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", color=FAINT)
    ax.set_axisbelow(True)
    fig.text(.12, .015, "Development: four target cohorts, equally weighted by year. Final: one 2022/23 cohort, 32 boroughs; retrospective benchmark only.",
             fontsize=8.4, color=GREY)
    fig.tight_layout(rect=(0, .04, 1, 1))
    save(fig, out, "05_predictive_benchmarks")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-zip", type=Path, default=ROOT / "data/raw/key-stage-4-destination-measures_2023-24.zip")
    parser.add_argument("--d9e-dir", type=Path, default=ROOT / "outputs/explanatory/d9e")
    parser.add_argument("--development-dir", type=Path, default=ROOT / "outputs/development")
    parser.add_argument("--final-dir", type=Path, default=ROOT / "outputs/predictive_final_gate")
    parser.add_argument("--out", type=Path, default=ROOT / "docs/figures")
    args = parser.parse_args(argv)
    style()
    london = data.load_london_la_slice(args.raw_zip)
    h = headline_data(london)
    fig_trend(h, args.out)
    fig_borough(h, args.out)
    fig_borough_heatmap(h, args.out)
    fig_subgroups(london, args.out)
    fig_explanatory(args.d9e_dir, args.out)
    fig_explanatory_structure(args.d9e_dir, args.out)
    fig_predictive(args.development_dir, args.final_dir, args.out)
    print(f"Saved six headline and one supplementary SVG figures to {args.out}")


if __name__ == "__main__":
    main()
