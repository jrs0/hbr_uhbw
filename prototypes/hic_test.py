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

codes = from_hic.get_clinical_codes(engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml")
lab_results = from_hic.get_lab_results(engine)
prescriptions = from_hic.get_prescriptions(engine)
demographics = get_data(engine, hic.demographics_query)
episodes = get_data(engine, hic.episodes_query, start_date, end_date)

if episodes.value_counts("episode_id").max() > 1:
    raise RuntimeError(
        "Found non-unique episode IDs; " "subsequent script will be invalid"
    )

index_episodes = arc_hbr.index_episodes(episodes, codes)

codes

lab_results

episodes.sort_values(["patient_id", "spell_id", "episode_id"]).head(50)

# Before linking to episodes, add a prescription ID (just the index
# column). This is to remove duplicated prescriptions in the last step
# of linking, due ot overlapping episode time windows.
prescriptions.reset_index(inplace=True, names="prescription_id")

# Join together all prescriptions and episode information by patient. Use
# a left join on prescriptions (assumed narrowed to the prescriptions types
# of interest) to keep the result smaller.
with_episodes = pd.merge(prescriptions, episodes, how="left", on="patient_id")

# Thinking of each row as both an episode and a prescription, drop any
# rows where the prescription order date does not fall within the start
# and end of the episode (start date inclusive).
consistent_dates = (with_episodes["order_date"] >= with_episodes["episode_start"]) & (
    with_episodes["order_date"] < with_episodes["episode_end"]
)
overlapping_episodes = with_episodes[consistent_dates]

# Since some episodes overlap in time, some prescriptions will end up
# being associated with more than one episode. To remove these duplicate
deduplicated = (
    overlapping_episodes.sort_values("episode_start").groupby("prescription_id").head(1)
)

# Keep episode_id, drop other episodes/unnecessary columns
deduplicated.drop(columns=["prescription_id"]).drop(
    columns=[c for c in episodes.columns if c != "episode_id"]
).reset_index(drop=True)
