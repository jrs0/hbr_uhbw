"""Simple testing script for HIC data processing
"""

import datetime as dt
import numpy as np

from pyhbr.common import make_engine
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr

from pyhbr.data_source import hic

import importlib

importlib.reload(arc_hbr)
importlib.reload(from_hic)
importlib.reload(hic)

import pandas as pd
from pandas import DataFrame, Series

pd.set_option("display.max_rows", 50)

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

codes = from_hic.get_clinical_codes(
    engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
)  # slow
episodes = from_hic.get_episodes(engine, start_date, end_date)  # fast
prescriptions = from_hic.get_prescriptions(engine, episodes)  # fast
lab_results = from_hic.get_lab_results(engine, episodes)  # really slow

demographics = from_hic.get_demographics(engine)

if episodes.value_counts("episode_id").max() > 1:
    raise RuntimeError(
        "Found non-unique episode IDs; subsequent script will be invalid"
    )

index_episodes = arc_hbr.index_episodes(episodes, codes)

arc_hbr_score = pd.DataFrame()


def get_gender(index_episodes: DataFrame, demographics: DataFrame) -> Series:
    """Get gender from the demographics table for each index event

    Args:
        index_episodes: Indexed by `episode_id` and having column `patient_id`
        demographics: Having columns `patient_id` and `gender`.

    Returns:
        A series containing gender indexed by `episode_id`
    """
    return index_episodes.merge(demographics, how="left", on="patient_id")["gender"]


def calculate_age(index_episodes: DataFrame, demographics: DataFrame) -> Series:
    """Calculate the patient age at index

    The HIC data contains only year_of_birth, which is used here. In order
    to make an unbiased estimate of the age, birthday is assumed to be
    2nd july (halfway through the year).

    Args:
        index_episodes: Contains `episode_start` date and column `patient_id`,
            indexed by `episode_id`.
        demographics: Contains `year_of_birth` date and index `patient_id`.

    Returns:
        A series containing age, indexed by `episode_id`.
    """
    df = index_episodes.merge(demographics, how="left", on="patient_id")
    age_offset = np.where(
        (df["episode_start"].dt.month < 7) & (df["episode_start"].dt.day < 2), 1, 0
    )
    age_at_index = df["episode_start"].dt.year - df["year_of_birth"] - age_offset
    age_at_index.index = index_episodes.index
    return age_at_index


def arc_hbr_age(has_age: DataFrame) -> Series:
    """Calculate the age ARC-HBR criterion

    Calculate the age ARC HBR criterion (0.5 points if > 75 at index, 0 otherwise.

    Args:
        has_age: Dataframe indexed by episode_id which has a column `age`

    Returns:
        A series of values 0.5 (if age > 75 at index) or 0 otherwise, indexed
            by `episode_id`.
    """
    return Series(np.where(has_age["age"] > 75, 0.5, 0), index=has_age.index)


## Age ARC HBR
index_episodes["age"] = calculate_age(index_episodes, demographics)
arc_hbr_score["age"] = arc_hbr_age(index_episodes)

# Add gender to the index_episodes table
index_episodes["gender"] = get_gender(index_episodes, demographics)


def arc_hbr_oac(index_episodes: DataFrame, prescriptions: DataFrame) -> Series:
    """Calculate the oral-anticoagulant ARC HBR criterion

    1.0 point if an one of the OACs "warfarin", "apixaban",
    "rivaroxaban", "edoxaban", "dabigatran", is present on
    admission in the index episode.

    Note: The number of OAC medicines present on admission in the HIC
    data is zero in a small sample. Needs checking.

    Args:
        index_episodes: Index `episode_id` is used to narrow prescriptions.
        prescriptions: Contains `name` (of medicine0 and `on_admission` (bool).

    Returns:
        The OAC ARC score for each index event.
    """
    df = index_episodes.merge(prescriptions, how="left", on="episode_id")
    oac_list = ["warfarin", "apixaban", "rivaroxaban", "edoxaban", "dabigatran"]
    oac_criterion = (df["name"].isin(oac_list) & df["on_admission"]).astype("float")
    return Series(oac_criterion, index=index_episodes.index)


## OAC ARC HBR
arc_hbr_score["oac"] = arc_hbr_oac(index_episodes, prescriptions)


def get_lowest_index_lab_result(
    index_episodes: DataFrame, lab_results: DataFrame, test_name: str
) -> Series:
    """Get the lowest lab result associated to the index episode

    Getting the lowest value corresponds to the worst severity for
    measurements such as eGFR, Hb and platelet count.

    Args:
        index_episodes: Has an `episode_id` for filtering lab_results
        lab_results: Has a `test_name` column matching the `test_name` argument,
            and a `result` column for the numerical test result
        test_name: Which lab measurement to get.

    Returns:
        A series containing the minimum value of test_name in the index
            episode. Contains NaN if test_name was not recorded in the
            index episode.
    """
    df = index_episodes.merge(lab_results, how="left", on="episode_id")
    index_lab_result = df[df["test_name"] == test_name]

    # Pick the lowest result. For measurements such as platelet count,
    # eGFR, and Hb, lower is more severe.
    min_index_lab_result = index_lab_result.groupby("episode_id").min("result")

    # Some index episodes do not have an measurement, so join
    # to get all index episodes (NaN means no index measurement)
    min_result_or_nan = pd.merge(
        index_episodes, min_index_lab_result["result"], how="left", on="episode_id"
    )

    return min_result_or_nan["result"].rename(f"index_{test_name}")


def arc_hbr_ckd(has_index_egfr: DataFrame) -> Series:
    """Calculate the ARC HBR chronic kidney disease (CKD) criterion

    The ARC HBR CKD criterion is calculated based on the eGFR as
    follows:

    | eGFR                           | Score |
    |--------------------------------|-------|
    | eGFR < 30 mL/min               | 1.0   |
    | 30 mL/min \<= eGFR < 60 mL/min | 0.5   |
    | eGFR >= 60 mL/min              | 0.0   |

    If the eGFR is NaN, set score to zero (TODO: fall back to ICD-10
    codes in this case)

    Args:
        has_index_egfr: Dataframe having the column "index_egfr" (in units of mL/min)
            with the lowest eGFR measurement at index, or NaN which means no eGFR
            measurement was taken on the index episode.

    Returns:
        A series containing the CKD ARC criterion, based on the eGFR at
            index.
    """

    # Replace NaN values for now with 100 (meaning score 0.0)
    df = has_index_egfr["index_egfr"].fillna(90)

    # Using a high upper limit to catch any high eGFR values. In practice,
    # the highest value is 90 (which comes from the string ">90" in the database).
    return pd.cut(df, [0, 30, 60, 10000], right=False, labels=[1.0, 0.5, 0.0])


def arc_hbr_anaemia(has_index_hb: DataFrame, demographics: DataFrame) -> Series:
    """Calculate the ARC HBR anaemia (low Hb) criterion



    Args:
        has_index_hb: Dataframe having the column `index_hb` containing the
            lowest Hb measurement at the index event, or NaN if no Hb measurement
            was made.
        demographics:

    Returns:
        A series containing the HBR score for the index episode.
    """


## CKD ARC HBR
index_episodes["index_egfr"] = get_lowest_index_lab_result(
    index_episodes, lab_results, "egfr"
)
arc_hbr_score["ckd"] = arc_hbr_ckd(index_episodes)

## Anaemia ARC HBR
index_episodes["index_hb"] = get_lowest_index_lab_result(
    index_episodes, lab_results, "hb"
)
