"""Accounting and disclosure checks for destination-pathway tables."""

from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from youth_offer import pathways, qa  # noqa: E402
from youth_offer.model_tables import PRIMARY_POPULATION  # noqa: E402


class PathwaysTests(unittest.TestCase):
    @staticmethod
    def source():
        """One borough with mutually consistent exact-count subgroup slices."""
        categories = pathways.DESTINATIONS
        counts = {
            "Overall": {"All pupils": [70, 10, 5, 10, 5]},
            "FSM": {"FSM eligible": [25, 3, 2, 6, 4],
                    "Not known to be FSM eligible": [45, 7, 3, 4, 1]},
            "SEN": {"Identified SEN": [12, 2, 1, 3, 2],
                    "No identified SEN": [58, 8, 4, 7, 3]},
            "SEN detail": {"SEN support": [7, 1, 1, 2, 1],
                           "SEN with EHC plan or statement": [5, 1, 0, 1, 1]},
            "Sex": {"Female": [35, 4, 3, 5, 3],
                    "Male": [35, 6, 2, 5, 2]},
            "Ethnicity": {"Asian / Asian British": [20, 1, 1, 1, 1],
                          "Black / African / Caribbean / Black British": [10, 1, 0, 1, 0],
                          "Mixed / Multiple ethnic groups": [5, 1, 1, 1, 0],
                          "Other ethnic group": [5, 0, 1, 1, 0],
                          "Unknown": [1, 0, 0, 0, 0],
                          "White": [29, 7, 2, 6, 4]},
        }

        records = []
        for family, groups in counts.items():
            for group, values in groups.items():
                cohort = sum(values)
                for category, count in zip(categories, values):
                    row = dict(time_period="201617", geographic_level="Local authority",
                               region_name="London", new_la_code="E00000001",
                               la_name="Example", establishment_type_group=PRIMARY_POPULATION,
                               sex="Total", ethnicity_major="Total", ethnicity_minor="Total",
                               disadvantage_status="Total", breakdown_topic="Total",
                               breakdown="Total", cohort_count=str(cohort),
                               destination_description=category, pupil_count=str(count),
                               pupil_percent=f"{100 * count / cohort:.1f}")
                    if family == "FSM":
                        row.update(breakdown_topic="FSM status", breakdown=group)
                    elif family in ("SEN", "SEN detail"):
                        row.update(breakdown_topic="SEN provision", breakdown=group)
                    elif family == "Sex":
                        row.update(sex=group)
                    elif family == "Ethnicity":
                        row.update(ethnicity_major=group)
                    records.append(row)

        return pd.DataFrame(records)

    def test_exact_pathways_summarise_using_one_denominator(self):
        source = self.source()
        result = pathways.build_exact_pathways(source)

        self.assertEqual(len(result.loc[result.family.eq("Overall")]), 5)
        qa.assert_exact_partition_accounting(result)

        london = pathways.summarise_london_pathways(result)
        education = london.loc[
            london.family.eq("Overall") & london.destination.eq(pathways.EDUCATION)
        ].iloc[0]

        self.assertEqual(int(education.pupil_count), 70)
        self.assertEqual(int(education.cohort_count), 100)
        self.assertAlmostEqual(float(education.share_pct), 70.0)

    def test_string_typed_source_has_complete_family_coverage(self):
        source = self.source()
        # The production loader reads raw CSV fields as pandas StringDtype.
        source = source.astype({column: "string" for column in source.columns})
        exact = pathways.build_exact_pathways(source)

        self.assertEqual(len(exact.loc[exact.family.eq("Overall")]), 5)
        qa.assert_exact_partition_accounting(exact)

    def test_london_share_is_pupil_weighted(self):
        # Two unequal cohorts: the pupil-weighted share is not the mean
        # of the two borough rates (90% and 10%).
        records = []
        for code, cohort, education in [("A", 10, 9), ("B", 100, 10)]:
            for destination, n in zip(pathways.DESTINATIONS,
                                      [education, 0, 0, cohort - education, 0]):
                records.append(dict(time_period="201617", new_la_code=code,
                                    family="Overall", group="All pupils",
                                    destination=destination, pupil_count=n,
                                    cohort_count=cohort))
        london = pathways.summarise_london_pathways(pd.DataFrame(records))

        result = london.loc[london.destination.eq(pathways.EDUCATION)].iloc[0]

        self.assertAlmostEqual(float(result.share_pct), 100 * 19 / 110)

    def test_partition_check_catches_inconsistent_sex_categories(self):
        source = self.source()
        changed = source.loc[
            source.sex.eq("Male")
            & source.destination_description.isin([pathways.EDUCATION, pathways.NOT_RECORDED])
        ]
        indices = changed.set_index("destination_description").index
        self.assertEqual(set(indices), {pathways.EDUCATION, pathways.NOT_RECORDED})
        a = changed.loc[changed.destination_description.eq(pathways.EDUCATION)].index[0]
        b = changed.loc[changed.destination_description.eq(pathways.NOT_RECORDED)].index[0]
        source.loc[a, ["pupil_count", "pupil_percent"]] = ["34", "68.0"]
        source.loc[b, ["pupil_count", "pupil_percent"]] = ["6", "12.0"]

        pathways_table = pathways.build_exact_pathways(source)
        with self.assertRaisesRegex(AssertionError, "Sex destination partition"):
            qa.assert_exact_partition_accounting(pathways_table)

    def test_missing_subgroup_borough_is_rejected(self):
        source = self.source()
        source = source.loc[~source.sex.eq("Female")].copy()

        with self.assertRaisesRegex(ValueError, "Incomplete borough/cohort subgroup coverage"):
            pathways.build_exact_pathways(source)

    def test_suppressed_disadvantage_is_not_zero(self):
        records = []
        for group in pathways.DISADVANTAGE_GROUPS:
            for category in pathways.DESTINATIONS:
                p = "c" if category == pathways.APPRENTICESHIPS else "1.0"
                records.append(dict(
                    time_period="202223", new_la_code="E00000001", la_name="Example",
                    establishment_type_group=PRIMARY_POPULATION, sex="Total",
                    ethnicity_major="Total", ethnicity_minor="Total",
                    disadvantage_status=group, breakdown_topic="Total", breakdown="Total",
                    cohort_count="100", destination_description=category,
                    pupil_count="c" if p == "c" else "5", pupil_percent=p,
                ))

        published = pathways.build_disadvantage_published(pd.DataFrame(records))
        suppressed = published.loc[published.destination.eq(pathways.APPRENTICESHIPS)]

        self.assertTrue(suppressed.reported_share_pct.isna().all())
        self.assertTrue(suppressed.percent_status.eq("suppressed_c").all())

        coverage = pathways.summarise_disadvantage_coverage(published)
        self.assertTrue(coverage.london_share_pct_approx_only_if_complete.isna().all())

    def test_complete_disadvantage_panel_passes_with_string_fields(self):
        exact = pathways.build_exact_pathways(self.source())
        records = []
        for group in pathways.DISADVANTAGE_GROUPS:
            for category in pathways.DESTINATIONS:
                records.append(dict(
                    time_period="201617", new_la_code="E00000001", group=group,
                    destination=category,
                ))
        published = pd.DataFrame(records).astype("string")

        qa.assert_disadvantage_panel(published, exact)

    def test_missing_disadvantage_group_is_rejected(self):
        exact = pathways.build_exact_pathways(self.source())
        records = []
        for category in pathways.DESTINATIONS:
            records.append(dict(
                time_period="201617", new_la_code="E00000001", la_name="Example",
                establishment_type_group=PRIMARY_POPULATION, sex="Total",
                ethnicity_major="Total", ethnicity_minor="Total",
                disadvantage_status="Disadvantaged", breakdown_topic="Total",
                breakdown="Total", cohort_count="100",
                destination_description=category, pupil_count="5", pupil_percent="5.0",
            ))
        published = pathways.build_disadvantage_published(pd.DataFrame(records))

        with self.assertRaisesRegex(ValueError, "Incomplete disadvantage borough/cohort coverage"):
            qa.assert_disadvantage_panel(published, exact)

    def test_five_way_accounting_catches_mismatched_group(self):
        source = self.source()
        bad = source.loc[source.destination_description.eq(pathways.NOT_RECORDED)].index[0]
        source.loc[bad, "pupil_count"] = "11"
        source.loc[bad, "pupil_percent"] = "11.0"

        with self.assertRaisesRegex(ValueError, "Five-way cohort accounting failed"):
            pathways.build_exact_pathways(source)


if __name__ == "__main__":
    unittest.main()
