"""D11c: London-wide historical-change accounting from exact KS4 counts."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from youth_offer.data import load_london_la_slice  # noqa: E402
from youth_offer import historical_change, model_tables, need, pathways, qa  # noqa: E402

RAW = ROOT / "data/raw/key-stage-4-destination-measures_2023-24.zip"
OUTPUT = ROOT / "outputs/destination_need/historical_change_details.csv"


def main() -> None:
    source = load_london_la_slice(RAW)
    headline = model_tables.build_headline_outcome_table(source)
    qa.assert_headline_outcome_table(headline)
    qa.assert_population_accounting(source)

    exact = pathways.build_exact_pathways(source)
    qa.assert_exact_partition_accounting(exact)
    cells = need.build_adverse_cells(exact)
    qa.assert_need_primary_panel(cells, headline)

    summary, detail = historical_change.decompose_historical_change(cells, headline)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    detail.to_csv(OUTPUT, index=False, float_format="%.17g")

    print("D11c: exact subgroup/headline reconciliation and decomposition identities passed.")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:+.3f}"))
    print(f"Group-level counts and contributions: {OUTPUT}")


if __name__ == "__main__":
    main()
