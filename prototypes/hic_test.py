"""Simple testing script for HIC data processing
"""

import datetime as dt
from datetimeutil import relativedelta
import numpy as np

from pyhbr.common import make_engine, get_data
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr

import importlib
importlib.reload(arc_hbr)
importlib.reload(from_hic)

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



def arc_hbr_age(index_episodes: DataFrame, demographics: DataFrame) -> Series:
    """Calculate the age ARC-HBR criterion

    Does not take account of the varying length of a year, so
    the estimate of age from index start date and demographics is slightly
    wrong. This is not important, because (in the HIC date), the date of 
    birth could be out by 6 months (only birth year is specified).

    Args:
        index_episodes: Contains `episode_start` date and column `patient_id`,
            indexed by `episode_id`.
        demographics: Contains `year_of_birth` date and index `patient_id`.

    Returns:
        A series of values 0.5 (if age > 75 at index) or 0 otherwise, indexed
            by `episode_id`.
    """
    df = index_episodes.merge(demographics, how="left", on="patient_id")
    ns_in_year = 365 * 24 * 60 * 60 * 1e9
    age_at_index = (df["episode_start"] - df["year_of_birth"]).astype("int64") / ns_in_year
    return Series(np.where(age_at_index > 75, 0.5, 0), index=index_episodes.index)

## Age ARC HBR
arc_hbr_score["age"] = arc_hbr_age(index_episodes, demographics)

index_episode
demographics