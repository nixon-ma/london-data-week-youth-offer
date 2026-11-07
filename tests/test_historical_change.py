"""Synthetic identities and failure cases for D11c historical-change accounting."""

from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from youth_offer import historical_change as change  # noqa: E402


class HistoricalChangeTests(unittest.TestCase):
    YEARS = ("201617", "201718", "201819", "201920", "202021", "202122", "202223")
    PAIR = ((20, 4), (80, 8))
    ENDPOINT = {"forward": (("201617",), ("202223",))}

    @classmethod
    def panel(cls, years=None, boroughs=("A",)):
        values = {year: cls.PAIR for year in cls.YEARS}
        if years:
            values.update(years)
        cells, headline = [], []
        for year, pair in values.items():
            for borough in boroughs:
                n_total = sum(n for n, _ in pair)
                a_total = sum(a for _, a in pair)
                not_recorded = sum(a // 2 for _, a in pair)
                headline.append({
                    "time_period": year, "new_la_code": borough,
                    "cohort_count": n_total, "adverse_count": a_total,
                    change.NOT_RECORDED: not_recorded,
                    change.ACTIVITY_NOT_CAPTURED: a_total - not_recorded,
                })
                for family, groups in (("Overall", ("All pupils",)), *change.PARTITIONS.items()):
                    group_values = ((n_total, a_total),) if family == "Overall" else pair
                    for group, (n, a) in zip(groups, group_values):
                        group_not_recorded = not_recorded if family == "Overall" else a // 2
                        cells.append({
                            "time_period": year, "new_la_code": borough,
                            "family": family, "group": group,
                            "cohort_count": n,
                            "not_recorded_count": group_not_recorded,
                            "activity_not_captured_count": a - group_not_recorded,
                            "adverse_count": a,
                        })

        return pd.DataFrame(cells), pd.DataFrame(headline)

    def decompose(self, pair, comparisons=None):
        cells, headline = self.panel({"202223": pair})

        return change.decompose_historical_change(
            cells, headline, self.ENDPOINT if comparisons is None else comparisons
        )

    def test_composition_only(self):
        summary, detail = self.decompose(((40, 8), (60, 6)))
        self.assertEqual(len(summary), 2)
        self.assertEqual(len(detail), 4)
        for row in summary.itertuples():
            self.assertAlmostEqual(row.composition_pp, 2.0)
            self.assertAlmostEqual(row.within_group_pp, 0.0)
            self.assertAlmostEqual(row.observed_change_pp, 2.0)
        self.assertEqual(detail["start_cohort_count"].tolist(), [20, 80, 20, 80])
        self.assertEqual(detail["end_cohort_count"].tolist(), [40, 60, 40, 60])

    def test_within_rate_only(self):
        summary, _ = self.decompose(((20, 6), (80, 16)))
        for row in summary.itertuples():
            self.assertAlmostEqual(row.composition_pp, 0)
            self.assertAlmostEqual(row.within_group_pp, 10)
            self.assertAlmostEqual(row.observed_change_pp, 10)

    def test_simultaneous_changes_split_exactly(self):
        summary, detail = self.decompose(((40, 12), (60, 12)))
        for row in summary.itertuples():
            self.assertAlmostEqual(row.composition_pp, 2)
            self.assertAlmostEqual(row.within_group_pp, 10)
            self.assertAlmostEqual(row.observed_change_pp, 12)
        for family in change.PARTITIONS:
            group_rows = detail.loc[detail["partition"].eq(family)]
            self.assertAlmostEqual(group_rows["composition_pp"].sum(), 2)
            self.assertAlmostEqual(group_rows["within_group_pp"].sum(), 10)

    def test_offsetting_change_and_reverse_endpoints(self):
        cells, headline = self.panel({"202223": ((40, 4), (60, 0))})
        comparisons = {
            "forward": (("201617",), ("202223",)),
            "reverse": (("202223",), ("201617",)),
        }
        summary, _ = change.decompose_historical_change(cells, headline, comparisons)
        forward = summary.loc[summary["comparison"].eq("forward")].set_index("partition")
        reverse = summary.loc[summary["comparison"].eq("reverse")].set_index("partition")
        for family in change.PARTITIONS:
            self.assertAlmostEqual(forward.loc[family, "composition_pp"], 2)
            self.assertAlmostEqual(forward.loc[family, "within_group_pp"], -10)
            self.assertAlmostEqual(forward.loc[family, "observed_change_pp"], -8)
            for component in ("composition_pp", "within_group_pp", "observed_change_pp"):
                self.assertAlmostEqual(forward.loc[family, component],
                                       -reverse.loc[family, component])

    def test_zero_change(self):
        summary, detail = self.decompose(self.PAIR)
        self.assertTrue(summary[["composition_pp", "within_group_pp", "observed_change_pp"]]
                        .eq(0).all().all())
        self.assertTrue(detail[["composition_pp", "within_group_pp"]].eq(0).all().all())

    def test_pooled_counts_not_mean_annual_rates_or_borough_rates(self):
        values = {
            "201617": ((20, 4), (80, 8)),
            "201718": ((200, 20), (800, 40)),
            "201819": ((50, 15), (50, 10)),
            "202122": ((50, 10), (50, 5)),
            "202223": ((20, 6), (80, 8)),
        }
        cells, headline = self.panel(values, boroughs=("A", "B"))
        summary, detail = change.decompose_historical_change(cells, headline)
        self.assertEqual(len(summary), 6)
        self.assertEqual(len(detail), 12)
        primary = detail.loc[detail["comparison"].eq("Early pooled → recent pooled")]
        eligible = primary.loc[(primary["partition"].eq("FSM"))
                               & primary["group"].eq("FSM eligible")].iloc[0]
        self.assertEqual(eligible["start_cohort_count"], 2 * (20 + 200 + 50))
        self.assertEqual(eligible["start_adverse_count"], 2 * (4 + 20 + 15))
        self.assertEqual(eligible["end_cohort_count"], 2 * (50 + 20))
        self.assertEqual(eligible["end_adverse_count"], 2 * (10 + 6))
        self.assertAlmostEqual(eligible["start_adverse_rate_pct"], 100 * 39 / 270)
        self.assertAlmostEqual(eligible["end_adverse_rate_pct"], 100 * 16 / 70)
        for comparison, group in summary.groupby("comparison"):
            self.assertAlmostEqual(group["observed_change_pp"].iloc[0],
                                   group["observed_change_pp"].iloc[1])

    def test_borough_pupil_weighting_and_non_numeric_publication_percent(self):
        a_cells, a_headline = self.panel({"202223": ((40, 8), (60, 6))}, boroughs=("A",))
        b_cells, b_headline = self.panel({
            year: ((5, 1), (195, 39)) for year in self.YEARS
        }, boroughs=("B",))
        cells = pd.concat([a_cells, b_cells], ignore_index=True)
        cells["published_percent_token"] = "low"  # Not an exact count input.
        headline = pd.concat([a_headline, b_headline], ignore_index=True)
        summary, _ = change.decompose_historical_change(cells, headline, self.ENDPOINT)
        weighted_change = 100 * ((14 + 40) / 300 - (12 + 40) / 300)
        self.assertAlmostEqual(summary["observed_change_pp"].iloc[0], weighted_change)
        self.assertNotAlmostEqual(weighted_change, 1.0)  # Unweighted borough-rate change.

    def test_missing_and_duplicate_cells_rejected(self):
        cells, headline = self.panel()
        cases = (
            cells.iloc[:-1],
            pd.concat([cells, cells.iloc[[0]]], ignore_index=True),
            cells.loc[~cells["family"].eq("SEN")],
        )
        for invalid in cases:
            with self.subTest(rows=len(invalid)), self.assertRaisesRegex(
                ValueError, "Incomplete or duplicated"
            ):
                change.decompose_historical_change(invalid, headline)
        with self.assertRaisesRegex(ValueError, "headline borough/cohort keys"):
            change.decompose_historical_change(
                cells, pd.concat([headline, headline.iloc[[0]]], ignore_index=True)
            )

    def test_count_and_component_safeguards(self):
        cells, headline = self.panel()
        for column, value in (
            ("cohort_count", 0), ("adverse_count", "low"),
            ("adverse_count", 1.5), ("adverse_count", -1),
            ("not_recorded_count", None), ("activity_not_captured_count", 1000),
        ):
            bad = cells.copy()
            bad[column] = bad[column].astype("object")
            bad.loc[bad.index[0], column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                change.decompose_historical_change(bad, headline)
        for column in ("cohort_count", "adverse_count", change.NOT_RECORDED,
                       change.ACTIVITY_NOT_CAPTURED):
            bad = headline.copy()
            bad.loc[bad.index[0], column] += 1
            with self.subTest(headline_column=column), self.assertRaises(ValueError):
                change.decompose_historical_change(cells, bad)

    def test_partition_component_mismatch_and_disclosure_code(self):
        cells, headline = self.panel()
        bad = cells.copy()
        idx = bad.index[bad["group"].eq("FSM eligible")][0]
        bad.loc[idx, "not_recorded_count"] += 1
        bad.loc[idx, "activity_not_captured_count"] -= 1
        with self.assertRaisesRegex(ValueError, "partition disagrees with headline"):
            change.decompose_historical_change(bad, headline)
        bad = headline.copy()
        bad[change.NOT_RECORDED] = bad[change.NOT_RECORDED].astype("object")
        bad.loc[bad.index[0], change.NOT_RECORDED] = "c"
        with self.assertRaisesRegex(ValueError, "Non-numeric exact count"):
            change.decompose_historical_change(cells, bad)

    def test_invalid_comparison_windows_rejected(self):
        cells, headline = self.panel()
        for years in (("201617", "201617"), ("209999",), ("202223",)):
            with self.subTest(years=years), self.assertRaisesRegex(
                ValueError, "comparison periods"
            ):
                change.decompose_historical_change(cells, headline, {
                    "invalid": (years, ("202223",))
                })


if __name__ == "__main__":
    unittest.main()
