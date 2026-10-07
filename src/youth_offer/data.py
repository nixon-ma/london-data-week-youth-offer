from pathlib import Path
import zipfile

import pandas as pd


RAW_CSV_MEMBER = "data/ees_ks4_202223_api.csv"

ANALYSIS_YEARS = {
    "201617",
    "201718",
    "201819",
    "201920",
    "202021",
    "202122",
    "202223",
}

RAW_COLUMNS = [
    "time_period",
    "geographic_level",
    "region_name",
    "new_la_code",
    "la_name",
    "establishment_type_group",
    "sex",
    "ethnicity_major",
    "ethnicity_minor",
    "disadvantage_status",
    "breakdown_topic",
    "breakdown",
    "version",
    "cohort_count",
    "destination_description",
    "pupil_count",
    "pupil_percent",
]


def filter_london_la_period(chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Keep London Local Authority rows from the frozen 2016/17–2022/23 period.
    """

    geo_mask = chunk["geographic_level"] == "Local authority"
    region_mask = chunk["region_name"] == "London"
    time_mask = chunk["time_period"].isin(ANALYSIS_YEARS)

    return chunk.loc[geo_mask & region_mask & time_mask].copy()


def load_london_la_slice(
    zip_path: Path,
    chunksize: int = 200_000,
) -> pd.DataFrame:
    """Read the large source incrementally and retain only the target LA slice."""

    filtered_chunks = []

    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(RAW_CSV_MEMBER) as csv_file:
            reader = pd.read_csv(
                csv_file,
                usecols=RAW_COLUMNS,
                dtype="string",
                chunksize=chunksize,
            )

            for chunk in reader:
                filtered = filter_london_la_period(chunk)

                if not filtered.empty:
                    filtered_chunks.append(filtered)

    return pd.concat(filtered_chunks, ignore_index=True)
