"""Calculate the ARC HBR score for the HIC data
"""

import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd

from pyhbr import common, clinical_codes
from pyhbr.analysis import acs
from pyhbr.data_source import icb
from pyhbr.middle import from_icb

import importlib
importlib.reload(common)
importlib.reload(acs)
importlib.reload(from_icb)
importlib.reload(icb)
importlib.reload(clinical_codes)

# Set a date range for episode fetch
start_date = dt.date(2018, 1, 1)
end_date = dt.date(2023, 1, 1)

# HES data + patient demographics
engine = common.make_engine(database="abi")
episodes_and_demographics = from_icb.get_episodes_and_demographics(
    engine, start_date, end_date
)

# The full dataset is large, so using a save point
# to speed up script development
common.save_item(episodes_and_demographics, "episodes_and_demographics")

# Load from the save point
episodes_and_demographics = common.load_item("episodes_and_demographics")

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_spells = acs.get_index_spells(episodes_and_demographics)

# Get the list of patients to narrow subsequent SQL queries
patient_ids = index_spells["patient_id"].unique()

# Fetch all the primary care data, narrowed by patient
engine = common.make_engine(database="modelling_sql_area")
primary_care_data = from_icb.get_primary_care_data(engine, patient_ids)

# Combine the data into a single dictionary. This dataset is
# the standard HES + SWD data available at the ICB (not including
# the HIC data)
icb_basic_data = episodes_and_demographics | primary_care_data

# Store metadata
icb_basic_data["start_date"] = start_date
icb_basic_data["end_date"] = end_date

# Store the index events that were used to subset
# the primary care data (based on the patient_ids in 
# the index spells)
icb_basic_data["index_spells"] = index_spells

# Save point for the primary care data
common.save_item(icb_basic_data, "icb_basic_data")

# Load the data
icb_basic_data = common.load_item("icb_basic_data")


####### OLD


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

# Get the bleed episodes (for chart review) -- bleeding in any position
groups = following_year[following_year["group"].isin(bleeding_groups)].groupby(
    "base_episode_id"
)
for key, _ in groups:
    print(groups.get_group(key), "\n\n")

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
