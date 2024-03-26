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

pd.set_option("display.max_rows", 100)

# Set a date range for episode fetch
start_date = dt.date(2023, 1, 1)
end_date = dt.date(2023, 2, 1)


# HES data + patient demographics
engine = common.make_engine(database="abi")
raw_sus_data = common.get_data(engine, icb.sus_query, start_date, end_date)

episodes = from_icb.get_episodes(raw_sus_data)
codes = from_icb.get_clinical_codes(
    raw_sus_data, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
)

data = {"episodes": episodes, "codes": codes}

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_episodes = acs.index_episodes(data)

# Primary care patient information
engine = common.make_engine(database="modelling_sql_area")

primary_care_attributes = common.get_data(
    engine, icb.primary_care_attributes_query, patient_ids[:499]
)

# Primary care prescriptions
primary_care_prescriptions = common.get_data(
    engine, icb.primary_care_prescriptions_query, start_date, end_date
)

# Primary care measurements
primary_care_measurements = common.get_data(
    engine, icb.primary_care_measurements_query, start_date, end_date
)


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
