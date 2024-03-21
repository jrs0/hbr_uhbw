"""Calculate the ARC HBR score for the HIC data
"""

import datetime as dt
import matplotlib.pyplot as plt

from pyhbr import common
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr
from pyhbr.analysis import acs
from pyhbr.clinical_codes import counting
from pyhbr.data_source import hic

import importlib

importlib.reload(common)
importlib.reload(arc_hbr)
importlib.reload(from_hic)
importlib.reload(hic)
importlib.reload(counting)
importlib.reload(acs)

import pandas as pd

pd.set_option("display.max_rows", 100)

# Set a date range for episode fetch
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

# Fetch data
engine = common.make_engine()
hic_data = from_hic.HicData(engine, start_date, end_date)

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_episodes = acs.index_episodes(hic_data)

# Get other episodes relative to the index episode (for counting code
# groups before/after the index)
all_other_codes = counting.get_all_other_codes(index_episodes, hic_data)

# Get the episodes that occurred in the previous year (for clinical code features)
max_before = dt.timedelta(days=365)
min_before = dt.timedelta(days=30)
previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)

# Get the episodes that occurred in the following year (for clinical code outcomes)
min_after = dt.timedelta(hours=72)  # Exclude periprocedural events
max_after = dt.timedelta(days=365)
following_year = counting.get_time_window(all_other_codes, min_after, max_after)

# Calculate more granular features as an intermediate step for calculating the
# ARC HBR score. Choose a function to extract the a value for the laboratory
# measurements at index.
features = arc_hbr.get_features(
    index_episodes, previous_year, hic_data, arc_hbr.first_index_spell_result
)

# Calculate the ARC HBR score from the more granular features.
arc_hbr_score = arc_hbr.get_arc_hbr_score(features, hic_data)

# Get the bleeding outcome
bleeding_groups = ["bleeding_al_ani"]
bleeding_outcome = counting.count_code_groups(
    index_episodes, following_year, bleeding_groups, True
)

# Get all the episodes in the index spell (not just the index
# episode), and then get a map from spell_id back to to the index
# episode_id
all_spell_episodes = arc_hbr.all_index_spell_episodes(index_episodes, hic_data.episodes)
spell_id_to_index_episode = index_episodes.merge(
    all_spell_episodes, how="left", on="episode_id"
)[["spell_id", "episode_id"]]

# Get all the prescriptions that happened in the index spell, and keep
# track of which index episode is linked to the spell
df = all_spell_episodes.merge(hic_data.prescriptions, how="left", on="episode_id")

# Find which index spells have an OAC prescription anywhere
oac_list = ["warfarin", "apixaban", "rivaroxaban", "edoxaban", "dabigatran"]
df["oac"] = df["name"].isin(oac_list)
index_spells_with_oac = pd.DataFrame(df.groupby("spell_id")["oac"].any())
oac_criterion = index_spells_with_oac.merge(
    spell_id_to_index_episode, how="left", on="spell_id"
).set_index("episode_id")["oac"]


arc_hbr.plot_index_measurement_distribution(features)
plt.show()

arc_hbr.plot_arc_score_distribution(arc_hbr_score)
plt.show()

arc_hbr.plot_prescriptions_distribution(hic_data)
plt.show()

# Package the data up for saving
data = {
    "hic_data": hic_data,
    "index_episodes": index_episodes,
    "features": features,
    "arc_hbr_score": arc_hbr_score,
    "bleeding_outcome": bleeding_outcome,
}

common.save_item(data, "arc_hbr_data")
