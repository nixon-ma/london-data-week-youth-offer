"""Focused checks for exact adverse-count and pooled-rate calculations."""

from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from youth_offer import need, pathways, qa  # noqa: E402


class NeedTests(unittest.TestCase):
    def test_adverse_cells_count_cohort_denominator_once(self):
        records = []
        categories = pathways.DESTINATIONS
        groups = {
            ("Overall", "All pupils"): (7, 1, 0, 1, 1),
            ("FSM", "FSM eligible"): (3, 0, 0, 1, 1),
            ("FSM", "Not known to be FSM eligible"): (4, 1, 0, 0, 0),
        }
        for (family, group), values in groups.items():
            for destination, count in zip(categories, values):
                records.append({
                    "time_period": "202223", "new_la_code": "A", "la_name": "Example",
                    "family": family, "group": group, "destination": destination,
                    "pupil_count": count, "cohort_count": sum(values),
                })

        cells = need.build_adverse_cells(pd.DataFrame(records))
        overall = cells.loc[cells.family.eq("Overall")].iloc[0]
        self.assertEqual(len(cells), 3)
        self.assertEqual(overall.not_recorded_count, 1)
        self.assertEqual(overall.activity_not_captured_count, 1)
        self.assertEqual(overall.adverse_count, 2)
        self.assertEqual(overall.cohort_count, 10)
        self.assertAlmostEqual(overall.adverse_rate_pct, 20.0)
        self.assertAlmostEqual(overall.one_pupil_pp, 10.0)

    @staticmethod
    def annual_cells():
        # Eligible group: 4/10 (40%) and 6/90 (6.67%).
        # Non-eligible group: 1/20 (5%) and 3/30 (10%).
        records = []
        for year, group, n, a in [
            ("202122", "FSM eligible", 10, 4),
            ("202223", "FSM eligible", 90, 6),
            ("202122", "Not known to be FSM eligible", 20, 1),
            ("202223", "Not known to be FSM eligible", 30, 3),
        ]:
            records.append({
                "time_period": year, "new_la_code": "A", "la_name": "Example",
                "family": "FSM", "group": group,
                "not_recorded_count": a - 1, "activity_not_captured_count": 1,
                "adverse_count": a, "cohort_count": n,
                "adverse_rate_pct": 100 * a / n, "one_pupil_pp": 100 / n,
            })
        return pd.DataFrame(records)

    def test_two_year_pool_weights_pupil_counts_not_annual_rates(self):
        pooled = need.pool_adverse_cells(
            self.annual_cells(), "2021/22–2022/23"
        ).set_index("group")
        eligible = pooled.loc["FSM eligible"]
        other = pooled.loc["Not known to be FSM eligible"]

        self.assertEqual(eligible.adverse_count, 10)
        self.assertEqual(eligible.cohort_count, 100)
        self.assertAlmostEqual(eligible.adverse_rate_pct, 10.0)
        self.assertAlmostEqual(eligible.one_pupil_pp, 1.0)
        self.assertAlmostEqual(other.adverse_rate_pct, 8.0)
        self.assertEqual(eligible.period, "2021/22–2022/23")

    def test_latest_period_uses_only_202223(self):
        pooled = need.pool_adverse_cells(self.annual_cells(), "2022/23")
        eligible = pooled.set_index("group").loc["FSM eligible"]

        self.assertEqual(eligible.adverse_count, 6)
        self.assertEqual(eligible.cohort_count, 90)
        self.assertAlmostEqual(eligible.adverse_rate_pct, 100 * 6 / 90)
        self.assertEqual(eligible.period, "2022/23")

    def test_pool_rejects_missing_or_duplicate_cells_and_unknown_period(self):
        cells = self.annual_cells()
        with self.assertRaises(KeyError):
            need.pool_adverse_cells(cells, "invalid")
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.pool_adverse_cells(cells.iloc[:-1], "2021/22–2022/23")
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.pool_adverse_cells(
                pd.concat([cells, cells.iloc[[0]]]), "2021/22–2022/23"
            )


    @staticmethod
    def gap_cells():
        """Two boroughs with positive, negative and exactly tied group gaps."""
        records = []
        for borough, family, groups in [
            ("A", "FSM", [("FSM eligible", 1, 4),
                          ("Not known to be FSM eligible", 1, 8)]),
            ("A", "SEN", [("Identified SEN", 0, 3),
                          ("No identified SEN", 2, 9)]),
            ("B", "FSM", [("FSM eligible", 1, 3),
                          ("Not known to be FSM eligible", 2, 6)]),
            ("B", "SEN", [("Identified SEN", 2, 3),
                          ("No identified SEN", 1, 6)]),
        ]:
            for group, adverse, cohort in groups:
                records.append({
                    "time_period": "202223", "new_la_code": borough,
                    "la_name": f"Example {borough}", "family": family,
                    "group": group, "adverse_count": adverse,
                    "cohort_count": cohort,
                })
        return pd.DataFrame(records)

    def test_annual_gaps_have_exact_positive_zero_negative_signs(self):
        gaps = need.calculate_fsm_sen_gaps(self.gap_cells(), "time_period")
        by_key = gaps.set_index(["new_la_code", "family"])

        self.assertEqual(len(gaps), 4)
        self.assertAlmostEqual(by_key.loc[("A", "FSM"), "gap_pp"], 12.5)
        self.assertEqual(int(by_key.loc[("A", "FSM"), "gap_sign"]), 1)
        self.assertEqual(int(by_key.loc[("A", "SEN"), "gap_sign"]), -1)
        self.assertEqual(int(by_key.loc[("B", "FSM"), "gap_sign"]), 0)
        self.assertAlmostEqual(by_key.loc[("B", "FSM"), "gap_pp"], 0)
        self.assertAlmostEqual(by_key.loc[("B", "SEN"), "gap_pp"], 50.0)

    def test_gaps_accept_explicit_pooled_period_column(self):
        pooled = self.gap_cells().rename(columns={"time_period": "period"})
        pooled["period"] = "2021/22–2022/23"

        gaps = need.calculate_fsm_sen_gaps(pooled, "period")

        self.assertEqual(set(gaps["period"]), {"2021/22–2022/23"})
        self.assertEqual(len(gaps), 4)

    def test_gaps_reject_missing_or_duplicated_groups(self):
        cells = self.gap_cells()
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.calculate_fsm_sen_gaps(cells.iloc[:-1], "time_period")
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.calculate_fsm_sen_gaps(
                pd.concat([cells, cells.iloc[[0]]]), "time_period"
            )


    @staticmethod
    def persistence_gaps():
        """Two boroughs with complete seven-year FSM/SEN histories."""
        patterns = {
            ("A", "FSM"): [1, 1, 1, 1, 1, 1, 1],
            ("A", "SEN"): [1, 1, 1, 0, 0, -1, -1],
            ("B", "FSM"): [0, 0, 0, 0, 0, 0, 0],
            ("B", "SEN"): [-1, -1, -1, -1, -1, -1, -1],
        }
        records = []
        for (borough, family), signs in patterns.items():
            for i, (year, sign) in enumerate(zip(need.PERSISTENCE_YEARS, signs)):
                focus_n = 10 + i
                comparison_n = 2 * focus_n
                focus_a, comparison_a = {
                    1: (2, 2), 0: (1, 2), -1: (0, 1),
                }[sign]
                gap_pp = 100 * (focus_a / focus_n - comparison_a / comparison_n)
                records.append({
                    "time_period": year, "new_la_code": borough,
                    "la_name": f"Example {borough}", "family": family,
                    "gap_pp": gap_pp, "gap_sign": sign,
                    "focus_cohort_count": focus_n,
                    "comparison_cohort_count": comparison_n,
                })
        return pd.DataFrame(records)

    def test_persistence_counts_positive_zero_negative_years(self):
        annual = self.persistence_gaps()
        summary = need.summarise_gap_persistence(annual)
        groups = summary.set_index(["new_la_code", "family"])

        self.assertEqual(len(summary), 4)
        expected_signs = {
            ("A", "FSM"): (7, 0, 0),
            ("A", "SEN"): (3, 2, 2),
            ("B", "FSM"): (0, 7, 0),
            ("B", "SEN"): (0, 0, 7),
        }
        for key, counts in expected_signs.items():
            row = groups.loc[key]
            self.assertEqual(
                (int(row["positive_years"]), int(row["zero_years"]),
                 int(row["negative_years"])),
                counts,
            )
            self.assertEqual(sum(counts), 7)
            self.assertEqual(int(row["min_focus_cohort_count"]), 10)
            self.assertEqual(int(row["min_comparison_cohort_count"]), 20)

        self.assertGreater(groups.loc[("A", "SEN"), "max_gap_pp"], 0)
        self.assertLess(groups.loc[("A", "SEN"), "min_gap_pp"], 0)
        self.assertEqual(groups.loc[("B", "FSM"), "min_gap_pp"], 0)

    def test_persistence_rejects_incomplete_and_duplicated_histories(self):
        annual = self.persistence_gaps()
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.summarise_gap_persistence(annual.iloc[:-1])
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.summarise_gap_persistence(pd.concat([annual, annual.iloc[[0]]]))
        without_sen = annual.loc[~(annual.new_la_code.eq("A") & annual.family.eq("SEN"))]
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.summarise_gap_persistence(without_sen)

    def test_persistence_rejects_invalid_signs_and_denominators(self):
        annual = self.persistence_gaps()
        invalid = annual.copy()
        invalid.loc[invalid.index[0], "gap_sign"] = 2
        with self.assertRaisesRegex(ValueError, "Gap signs"):
            need.summarise_gap_persistence(invalid)
        invalid = annual.copy()
        invalid.loc[invalid.index[0], "focus_cohort_count"] = 0
        with self.assertRaisesRegex(ValueError, "Non-positive"):
            need.summarise_gap_persistence(invalid)
        invalid = annual.copy()
        invalid.loc[invalid.index[0], "gap_pp"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Missing annual gap"):
            need.summarise_gap_persistence(invalid)


    def test_burden_share_uses_complete_partition_not_overlapping_families(self):
        records = [
            ("Overall", "All pupils", 5, 100),
            ("FSM", "FSM eligible", 1, 10),
            ("FSM", "Not known to be FSM eligible", 4, 90),
            ("SEN", "Identified SEN", 2, 20),
            ("SEN", "No identified SEN", 3, 80),
            ("SEN detail", "SEN support", 1, 10),
        ]
        cells = pd.DataFrame([
            dict(time_period="202223", new_la_code="A", la_name="Example",
                 family=family, group=group, adverse_count=a, cohort_count=n)
            for family, group, a, n in records
        ])
        result = need.add_group_burden_shares(cells, "time_period")
        by_group = result.set_index(["family", "group"])
        self.assertAlmostEqual(by_group.loc[("FSM", "FSM eligible"), "share_of_adverse_pct"], 20)
        self.assertAlmostEqual(by_group.loc[("SEN", "Identified SEN"), "share_of_adverse_pct"], 40)
        self.assertTrue(pd.isna(by_group.loc[("Overall", "All pupils"), "share_of_adverse_pct"]))
        self.assertTrue(pd.isna(by_group.loc[("SEN detail", "SEN support"), "share_of_adverse_pct"]))

        bad = cells.copy()
        bad.loc[bad["group"].eq("FSM eligible"), "adverse_count"] = 2
        with self.assertRaisesRegex(ValueError, "partition does not reconcile"):
            need.add_group_burden_shares(bad, "time_period")

    def test_zero_adverse_total_has_undefined_burden_share(self):
        cells = pd.DataFrame([
            dict(time_period="202223", new_la_code="A", la_name="Example",
                 family=family, group=group, adverse_count=0, cohort_count=n)
            for family, group, n in [
                ("Overall", "All pupils", 10),
                ("FSM", "FSM eligible", 4),
                ("FSM", "Not known to be FSM eligible", 6),
            ]
        ])
        result = need.add_group_burden_shares(cells, "time_period")
        self.assertTrue(result["share_of_adverse_pct"].isna().all())

    def test_london_rates_are_pupil_weighted(self):
        cells = pd.DataFrame([
            dict(time_period="202223", new_la_code=borough, family="Overall",
                 group="All pupils", cohort_count=n, adverse_count=a,
                 not_recorded_count=a, activity_not_captured_count=0)
            for borough, a, n in [("A", 5, 10), ("B", 9, 90)]
        ])
        london = need.summarise_london_adverse(cells, "time_period").iloc[0]
        self.assertEqual(london["adverse_count"], 14)
        self.assertEqual(london["cohort_count"], 100)
        self.assertAlmostEqual(london["adverse_rate_pct"], 14)

    @staticmethod
    def disadvantage_cells():
        records = []
        for year, borough, group, weight, sustained in [
            ("202122", "A", "Disadvantaged", 10, 80.0),
            ("202223", "A", "Disadvantaged", 90, 90.0),
            ("202122", "A", "Not known to be disadvantaged", 20, 95.0),
            ("202223", "A", "Not known to be disadvantaged", 80, 95.0),
            ("202122", "B", "Disadvantaged", 10, 70.0),
            ("202223", "B", "Disadvantaged", 20, 80.0),
            ("202122", "B", "Not known to be disadvantaged", 30, 95.0),
            ("202223", "B", "Not known to be disadvantaged", 40, 95.0),
        ]:
            records.append(dict(time_period=year, new_la_code=borough,
                la_name=f"Example {borough}", group=group,
                cohort_count_disclosure_rounded=weight,
                sustained_pct_published=sustained))
        return pd.DataFrame(records)

    def test_disadvantage_pool_uses_rounded_weights_and_never_creates_exact_counts(self):
        annual = need.build_disadvantage_adverse(self.disadvantage_cells())
        self.assertNotIn("adverse_count", annual.columns)
        pooled = need.pool_disadvantage_adverse(annual, "2021/22–2022/23")
        row = pooled.set_index(["new_la_code", "group"]).loc[("A", "Disadvantaged")]
        self.assertAlmostEqual(row["adverse_rate_pct_approx"], 11.0)
        self.assertEqual(row["rounded_cohort_weight_sum"], 100)
        self.assertNotIn("adverse_count", pooled.columns)
        london = need.pool_disadvantage_adverse(annual, "2021/22–2022/23", london=True)
        london_row = london.set_index("group").loc["Disadvantaged"]
        self.assertAlmostEqual(london_row["adverse_rate_pct_approx"], (1100 + 700) / 130)

    def test_disadvantage_rejects_incomplete_or_suppressed_percentages(self):
        annual = need.build_disadvantage_adverse(self.disadvantage_cells())
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.pool_disadvantage_adverse(annual.iloc[:-1], "2021/22–2022/23")
        with self.assertRaisesRegex(ValueError, "Incomplete or duplicated"):
            need.pool_disadvantage_adverse(
                pd.concat([annual, annual.iloc[[0]]]), "2021/22–2022/23")
        suppressed = self.disadvantage_cells()
        suppressed.loc[0, "sustained_pct_published"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Invalid published"):
            need.build_disadvantage_adverse(suppressed)


    def test_disadvantage_approximate_gap_keeps_rounded_cohort_weights(self):
        annual = need.build_disadvantage_adverse(self.disadvantage_cells())
        pooled = need.pool_disadvantage_adverse(annual, "2021/22–2022/23")
        paired = need.calculate_disadvantage_gaps(pooled)
        a = paired.set_index("new_la_code").loc["A"]
        self.assertAlmostEqual(a["gap_pp_approx"], 6.0)
        self.assertEqual(a["disadvantaged_rounded_cohort_weight"], 100)
        self.assertNotIn("adverse_count", paired.columns)

        missing = pooled.loc[~(
            pooled["new_la_code"].eq("B")
            & pooled["group"].eq("Not known to be disadvantaged")
        )]
        with self.assertRaisesRegex(ValueError, "Incomplete disadvantage"):
            need.calculate_disadvantage_gaps(missing)


    def test_period_qa_detects_inconsistent_pooled_counts(self):
        annual = self.annual_cells()
        pooled = need.pool_adverse_cells(annual, "2021/22–2022/23")
        qa.assert_need_period_reconciliation(annual, pooled, "2021/22–2022/23")
        bad = pooled.copy()
        bad.loc[0, "cohort_count"] += 1
        with self.assertRaisesRegex(AssertionError, "pooled cohort_count mismatch"):
            qa.assert_need_period_reconciliation(annual, bad, "2021/22–2022/23")

    def test_ap_and_mainstream_population_qa_rejects_extra_authority(self):
        def overall(n):
            return pd.DataFrame([
                dict(time_period="202223", new_la_code="A", la_name="Example",
                     family="Overall", cohort_count=n)
            ])

        primary = overall(100)
        mainstream = overall(90)
        ap = overall(10)
        qa.assert_need_secondary_population(primary, mainstream, ap)
        extra = pd.concat([ap, pd.DataFrame([
            dict(time_period="201718", new_la_code="CITY", la_name="City",
                 family="Overall", cohort_count=1)
        ])], ignore_index=True)
        with self.assertRaisesRegex(AssertionError, "AP panel"):
            qa.assert_need_secondary_population(primary, mainstream, extra)


if __name__ == "__main__":
    unittest.main()
