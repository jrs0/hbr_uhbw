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
        Series: The OAC ARC score for each index event.
    """
    df = index_episodes.merge(prescriptions, how="left", on="episode_id")
    oac_list = ["warfarin", "apixaban", "rivaroxaban", "edoxaban", "dabigatran"]
    oac_criterion = (df["name"].isin(oac_list) & df["on_admission"]).astype("float")
    return Series(oac_criterion, index=index_episodes.index)

## OAC ARC HBR
arc_hbr_score["oac"] = arc_hbr_oac(index_episodes, prescriptions)



arc_hbr_score