"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine, get_data
from pyhbr.middle import from_hic
from pyhbr.data_source import hic
from pyhbr.analysis import arc_hbr

import pandas as pd

pd.set_option("display.max_rows", 50)

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

codes = from_hic.get_clinical_codes(
    engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
)  # slow
episodes = get_data(engine, hic.episodes_query, start_date, end_date)  # fast
prescriptions = from_hic.get_prescriptions(engine, episodes)  # fast
lab_results = from_hic.get_lab_results(engine, episodes)  # really slow

demographics = get_data(engine, hic.demographics_query)

if episodes.value_counts("episode_id").max() > 1:
    raise RuntimeError(
        "Found non-unique episode IDs; subsequent script will be invalid"
    )

index_episodes = arc_hbr.index_episodes(episodes, codes)

# Not much reduction, because lab results are already narrowed to blood tests,
# which are performed routinely for ACS/PCI patients.
lab2 = reduce_patients(lab_results, index_episodes, episodes)

pres2 = reduce_patients(prescriptions, index_episodes, episodes)

def reduce_patients(table: pd.DataFrame, index_episodes: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    """Use the index episodes to narrow another table to only required patients.

    When assembling the data for the index group using other tables, there is no
    use for data about patients not listed in the index set. Removing this data
    can help speed up data processing.
    
    Args:
        table: A table containing `episode_id` that should be reduced
        index_episodes: Must contain `patient_id` and `episode_id`
        episodes: All episodes. Must contain `patient_id` and `episode_id`

    Returns:
        The reduced version of table.
    """

# Get the patient_id for all episodes
patient_episodes = episodes[["episode_id", "patient_id"]]

# This is the reduced list of patients to keep
patients_in_index = index_episodes[["patient_id"]].drop_duplicates()

# Add patient_id to the table to identify which rows to keep
with_patients = pd.merge(prescriptions, patient_episodes, how="left", on="episode_id")

# Join the table onto the patients to keep (inner join will drop patients not in index
# from the results, and also ignore index patients with no record in table)
reduced_table = pd.merge(patients_in_index, with_patients, how="inner", on="patient_id")

# Drop the patient_id column
return reduced_table.drop(columns=["patient_id"])
