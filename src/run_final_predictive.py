"""D9f predictive final gate.

Default invocation performs HISTORICAL-ONLY preflight, without scoring 2022/23.
Only an explicitly supplied --release-202223-predictive-evaluation flag
constructs the final targets, calculates metrics or exports scored results.

Examples from repository root:
  python src/run_final_predictive.py
  # ONLY AFTER EXPLICIT USER AUTHORISATION:
  python src/run_final_predictive.py --release-202223-predictive-evaluation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from youth_offer import data
from youth_offer.final_gate import (
    HISTORY_YEARS, LOCKED_TARGET_YEAR, build_historical_table,
    prepare_unscored_final_forecasts, score_released_final,
)


DEFAULT_ZIP = Path("data/raw/key-stage-4-destination-measures_2023-24.zip")


def run(*, raw_zip: Path, release_final: bool = False) -> dict:
    london_la = data.load_london_la_slice(raw_zip)

    # IMPORTANT: filter the raw data BEFORE deriving any headline outcomes.
    # No 2022/23 target is passed to the preflight table-building functions.
    historical_raw = london_la.loc[
        london_la["time_period"].isin(HISTORY_YEARS)
    ].copy()
    history = build_historical_table(historical_raw)
    forecasts, report = prepare_unscored_final_forecasts(history)
    output = Path("outputs/predictive_final_gate")
    output.mkdir(parents=True, exist_ok=True)
    (output / "historical_preflight.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print("Historical-only predictive preflight:")
    print(json.dumps(report, indent=2))

    if not release_final:
        print("Final 2022/23 predictive evaluation remains LOCKED; no final targets were scored.")
        return report

    # Explicit user release only: this is the FIRST point where 2022/23
    # target rows enter any outcome-construction or scoring function.
    released_raw = london_la.loc[
        london_la["time_period"].eq(LOCKED_TARGET_YEAR)
    ].copy()
    scored, metrics = score_released_final(forecasts, released_raw)
    scored.to_csv(output / "released_predictions_and_targets.csv", index=False)
    metrics.to_csv(output / "released_annual_metrics.csv", index=False)
    print("RELEASED 2022/23 predictive results:")
    print(metrics.to_string(index=False))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument(
        "--release-202223-predictive-evaluation",
        action="store_true",
        help="EXPLICIT HOLDOUT RELEASE: construct 2022/23 targets, score and export all four methods.",
    )
    args = parser.parse_args()
    run(raw_zip=args.raw_zip, release_final=args.release_202223_predictive_evaluation)


if __name__ == "__main__":
    main()
