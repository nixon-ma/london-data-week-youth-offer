
"""Visualisations for explanatory model diagnostics."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def plot_pearson_residuals(residual_table, output_path):
    """Plot Pearson residuals against fitted rates and cohort sizes."""

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)

    residuals = residual_table["pearson_residual"]

    # Plot 1: Residuals versus fitted adverse probability.
    axes[0].scatter(
        100 * residual_table["fitted_adverse_rate"],
        residuals,
        alpha=0.65,
        s=24,
    )
    axes[0].set_xlabel("Fitted adverse rate (%)")
    axes[0].set_ylabel("Pearson residual")
    axes[0].set_title("Residuals vs fitted rate")

    # Plot 2: Residuals versus cohort denominator.
    axes[1].scatter(
        residual_table["cohort_count"],
        residuals,
        alpha=0.65,
        s=24,
    )
    axes[1].set_xlabel("Cohort denominator")
    axes[1].set_title("Residuals vs cohort size")

    # Zero represents exact agreement with the fitted expectation.
    for ax in axes:
        ax.axhline(0, color="grey", linestyle="--", linewidth=1)

    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path


def plot_borough_year_residuals(residual_table, output_path):
    """Plot E4 Pearson residuals by borough and cohort year."""

    # Arrange boroughs alphabetically and cohorts chronologically.
    cohort_order = [
        "201617", "201718", "201819", "201920",
        "202021", "202122", "202223",
    ]

    heatmap_data = (
        residual_table.pivot(
            index="la_name",
            columns="time_period",
            values="pearson_residual",
        )
        .sort_index()
        .reindex(columns=cohort_order)
    )

    # Verify the complete borough-year panel.
    assert heatmap_data.shape == (32, 7)
    values = heatmap_data.to_numpy(dtype=float)
    assert np.isfinite(values).all()

    # Use a symmetric colour range centred at zero.
    colour_limit = max(1.0, np.max(np.abs(values)))

    fig, ax = plt.subplots(figsize=(10, 11))

    image = ax.imshow(
        values,
        cmap="RdBu_r",
        vmin=-colour_limit,
        vmax=colour_limit,
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(range(len(cohort_order)))
    ax.set_xticklabels([
        f"{year[:4]}/{year[4:]}" for year in cohort_order
    ])

    ax.set_yticks(range(len(heatmap_data.index)))
    ax.set_yticklabels(heatmap_data.index, fontsize=8)

    ax.set_xlabel("KS4 cohort year")
    ax.set_ylabel("London borough")
    ax.set_title("E4 Pearson residuals by borough and cohort")

    colourbar = fig.colorbar(image, ax=ax, shrink=0.8)
    colourbar.set_label("Pearson residual")

    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path
