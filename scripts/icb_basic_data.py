"""Fetch ICB data (HES + SWD data)
"""

import importlib
import datetime as dt

import pandas as pd
from pyhbr import common, clinical_codes
from pyhbr.analysis import acs
from pyhbr.clinical_codes import counting
from pyhbr.data_source import icb
from pyhbr.middle import from_icb

importlib.reload(common)
importlib.reload(acs)
importlib.reload(from_icb)
importlib.reload(icb)
importlib.reload(clinical_codes)
importlib.reload(counting)

pd.set_option("future.no_silent_downcasting", True)

# Set a date range for episode fetch
start_date = dt.date(2015, 1, 1)
end_date = dt.date(2023, 1, 1)

# Get the raw HES data
engine = common.make_engine(database="abi")
raw_sus_data = from_icb.get_raw_sus_data(engine, start_date, end_date)

# The full dataset is large, so using a save point
# to speed up script development
common.save_item(raw_sus_data, "raw_sus_data")

# HES data + patient demographics
episodes_and_codes = from_icb.get_episodes_and_codes(raw_sus_data)

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_spells = acs.get_index_spells(episodes_and_codes)

# Get the list of patients to narrow subsequent SQL queries
patient_ids = index_spells["patient_id"].unique()

# Fetch all the primary care data, narrowed by patient
engine = common.make_engine(database="modelling_sql_area")
primary_care_data = from_icb.get_primary_care_data(engine, patient_ids)

# Find latest date seen in all the datasets
latest_primary_care_attributes = primary_care_data["primary_care_attributes"][
    "attribute_period"
].max()
latest_primary_care_prescriptions = primary_care_data["primary_care_prescriptions"][
    "date"
].max()
latest_primary_care_measurements = primary_care_data["primary_care_measurements"][
    "date"
].max()
latest_sus_data = raw_sus_data["episode_start"].max()
common_latest = min(
    [
        latest_primary_care_attributes,
        latest_primary_care_prescriptions,
        latest_primary_care_measurements,
        latest_sus_data,
    ]
)

# Find earliest date seen in all the datasets
earliest_primary_care_attributes = primary_care_data["primary_care_attributes"][
    "attribute_period"
].min()
earliest_primary_care_prescriptions = primary_care_data["primary_care_prescriptions"][
    "date"
].min()
earliest_primary_care_measurements = primary_care_data["primary_care_measurements"][
    "date"
].min()
earliest_sus_data = raw_sus_data["episode_start"].min()
common_earliest = max(
    [
        earliest_primary_care_attributes,
        earliest_primary_care_prescriptions,
        earliest_primary_care_measurements,
        earliest_sus_data,
    ]
)

# Add a margin of one year on either side of the earliest/latest
# dates to ensure outcomes and features will be valid at the edges
index_start_date = common_earliest + dt.timedelta(days=365)
index_end_date = common_latest - dt.timedelta(days=365)

# Reduce the index spells to only those within the valid window
index_spells = index_spells[
    (index_spells["spell_start"] < index_end_date)
    & (index_spells["spell_start"] > index_start_date)
]

# Combine the data into a single dictionary. This dataset is
# the standard HES + SWD data available at the ICB (not including
# the HIC data). This is a temporary save point to make it simpler
# to debug the script (avoiding the long-running SQL queries above).
icb_basic_tmp = episodes_and_codes | primary_care_data

# Store metadata
icb_basic_tmp["start_date"] = start_date
icb_basic_tmp["end_date"] = end_date
icb_basic_tmp["index_start_date"] = index_start_date
icb_basic_tmp["index_end_date"] = index_end_date

# Store the index events that were used to subset
# the primary care data (based on the patient_ids in
# the index spells)
icb_basic_tmp["index_spells"] = index_spells

# Save point for the primary care data
common.save_item(icb_basic_tmp, "icb_basic_tmp")

# Load the data from file
icb_basic_tmp = common.load_item("icb_basic_tmp")

# Extract some datasets for convenience
index_spells = icb_basic_tmp["index_spells"]
primary_care_attributes = icb_basic_tmp["primary_care_attributes"]
primary_care_prescriptions = icb_basic_tmp["primary_care_prescriptions"]
primary_care_measurements = icb_basic_tmp["primary_care_measurements"]

# Preprocess the SWD columns
primary_care_attributes["smoking"] = from_icb.preprocess_smoking(
    primary_care_attributes["smoking"]
)
primary_care_attributes["ethnicity"] = from_icb.preprocess_ethnicity(
    primary_care_attributes["ethnicity"]
)

# Join the latest patient attributes to each index spell
index_spells_with_attribute_period = acs.get_index_attribute_periods(
    index_spells, primary_care_attributes
)

# Get the patient index-spell attributes (before reducing based on missingness/low-variance)
all_index_attributes = acs.get_index_attributes(
    index_spells_with_attribute_period, primary_care_attributes
)

# Remove attribute columns that have too much missingness or where
# the column is nearly constant (low variance)
features_attributes = acs.remove_features(
    all_index_attributes, max_missingness=0.75, const_threshold=0.95
)

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(index_spells, icb_basic_tmp)

# Get the bleeding and ischaemia outcomes
outcomes = acs.get_outcomes(index_spells, all_other_codes)
features_codes = acs.get_code_features(index_spells, all_other_codes)

# Get counts of relevant prescriptions in the year before the index
features_prescriptions = acs.prescriptions_before_index(
    index_spells, primary_care_prescriptions
)

# Only blood pressure and HbA1c go back to 2019 in the data -- not
# including the other measurements in order to keep the sample size up.
prior_blood_pressure = from_icb.blood_pressure(
    index_spells, primary_care_measurements
)
prior_hba1c = from_icb.hba1c(index_spells, primary_care_measurements)
features_measurements = prior_blood_pressure.merge(prior_hba1c, how="left", on="spell_id")

# Get basic index features (drop instead of keep in case new
# features are added)
features_index = index_spells.drop(columns=["episode_id", "patient_id", "spell_start"])

# Combine all tables (features and outcomes) into a single table
# for saving.
icb_basic_data = {
    "icb_basic_tmp": icb_basic_tmp,
    "outcomes": outcomes,
    "features_index": features_index,
    "features_codes": features_codes,
    "features_attributes": features_attributes,
    "features_prescriptions": features_prescriptions,
    "features_measurements": features_measurements,
}

common.save_item(icb_basic_data, "icb_basic_data")
