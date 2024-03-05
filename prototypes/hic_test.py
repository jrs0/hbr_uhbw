"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr

from pyhbr.data_source import hic

import importlib

importlib.reload(arc_hbr)
importlib.reload(from_hic)
importlib.reload(hic)

import pandas as pd

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

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_episodes = arc_hbr.index_episodes(episodes, codes)

# Add relevant information to the index_episodes
index_episodes["age"] = arc_hbr.calculate_age(index_episodes, demographics)
index_episodes["gender"] = arc_hbr.get_gender(index_episodes, demographics)
index_episodes["index_egfr"] = arc_hbr.get_lowest_index_lab_result(
    index_episodes, lab_results, "egfr"
)
index_episodes["index_hb"] = arc_hbr.get_lowest_index_lab_result(
    index_episodes, lab_results, "hb"
)
index_episodes["index_platelets"] = arc_hbr.get_lowest_index_lab_result(
    index_episodes, lab_results, "platelets"
)

# Add patient_id to the codes, and prepare to join to index episodes
codes_by_patient = codes.merge(
    episodes[["patient_id", "episode_start"]], how="left", on="episode_id"
).rename(
    columns={"episode_start": "other_episode_start", "episode_id": "other_episode_id"}
)

# Join index episodes to all codes
all_other_codes = (
    index_episodes[["patient_id", "episode_start"]]
    .reset_index()
    .merge(codes_by_patient, how="left", on="patient_id")
    .set_index(["episode_id", "other_episode_id", "type", "position"])
)


# Calculate the ARC HBR score
arc_hbr_score = pd.DataFrame()
arc_hbr_score["arc_hbr_age"] = arc_hbr.arc_hbr_age(index_episodes)
arc_hbr_score["arc_hbr_oac"] = arc_hbr.arc_hbr_oac(index_episodes, prescriptions)
arc_hbr_score["arc_hbr_ckd"] = arc_hbr.arc_hbr_ckd(index_episodes)
arc_hbr_score["arc_hbr_anaemia"] = arc_hbr.arc_hbr_anaemia(index_episodes)
arc_hbr_score["arc_hbr_tcp"] = arc_hbr.arc_hbr_tcp(index_episodes)
