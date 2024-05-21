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

# Set a date range for episode fetch. The primary
# care data start in Oct 2019. Use an end date
# in the future to ensure all data is fetched.
# Index spell data is limited based on the min/max
# dates seen in all the datasets below.
start_date = dt.date(2019, 1, 1)
end_date = dt.date(2025, 1, 1)

# Get the raw HES data (this takes a long time ~ 20 minutes)
engine = common.make_engine(database="abi")
raw_sus_data = from_icb.get_raw_sus_data(engine, start_date, end_date)

# Note that the SUS data is limited to in-area patients only, so that
# the patients are present in the primary care attributes table (see
# the notes on valid commissioner code in icb.py). This restriction
# can be lifted if the primary care data is not used in the analysis.

# The full dataset is large, so using a save point
# to speed up script development
common.save_item(raw_sus_data, "raw_sus_data")
raw_sus_data = common.load_item("raw_sus_data")

# HES data + patient demographics
episodes_and_codes = from_icb.get_episodes_and_codes(raw_sus_data)

# Get the index episodes (primary ACS or PCI anywhere in first episode)xs
# Modify the code groups used to define the index event here.
index_spells = acs.get_index_spells(episodes_and_codes, "acs_bezin", "all_pci_pathak")

# Get the list of patients to narrow subsequent SQL queries
patient_ids = index_spells["patient_id"].unique()

# Get date of death and cause of death from registry data
mortality = from_icb.get_mortality(engine, start_date, end_date)

# Fetch all the primary care data, narrowed by patient
engine = common.make_engine(database="modelling_sql_area")

# Primary care prescriptions
dfs = common.get_data_by_patient(
    engine, icb.primary_care_prescriptions_query, patient_ids
)
primary_care_prescriptions = pd.concat(dfs).reset_index(drop=True)

# Primary care measurements
dfs = common.get_data_by_patient(
    engine, icb.primary_care_measurements_query, patient_ids
)
primary_care_measurements = pd.concat(dfs).reset_index(drop=True)

# Primary care attributes
dfs = common.get_data_by_patient(engine, icb.primary_care_attributes_query, patient_ids)
with_flag_columns = [from_icb.process_flag_columns(df) for df in dfs]
primary_care_attributes = pd.concat(with_flag_columns).reset_index(drop=True)

# Find the most recent date that was seen in all the datasets. Note
# that the date in the primary care attributes covers the month
# beginning from that date.
common_end = min(
    [
        primary_care_attributes["date"].max() + dt.timedelta(days=31),
        primary_care_prescriptions["date"].max(),
        primary_care_measurements["date"].max(),
        raw_sus_data["episode_start"].max(),
    ]
)

# Find earliest date seen in all the datasets.
common_start = max(
    [
        primary_care_attributes["date"].min(),
        primary_care_prescriptions["date"].min(),
        primary_care_measurements["date"].min(),
        raw_sus_data["episode_start"].min(),
    ]
)

# Add a margin of one year on either side of the earliest/latest
# dates to ensure outcomes and features will be valid at the edges
index_start = common_start + dt.timedelta(days=365)
index_end = common_end - dt.timedelta(days=365)

# Reduce the index spells to only those within the valid window
index_spells = index_spells[
    (index_spells["spell_start"] < index_end)
    & (index_spells["spell_start"] > index_start)
]

# Combine the datasets for saving
icb_basic_tmp = {
    # Datasets
    "index_spells": index_spells,
    "episodes": episodes_and_codes["episodes"],
    "codes": episodes_and_codes["codes"],
    "date_of_death": mortality["date_of_death"],
    "cause_of_death": mortality["cause_of_death"],
    "primary_care_attributes": primary_care_attributes,
    "primary_care_measurements": primary_care_measurements,
    "primary_care_prescriptions": primary_care_prescriptions,
    # Metadata
    "start_date": start_date,
    "end_date": end_date,
    "common_start": common_start,
    "common_end": common_end,
    "index_start": index_start,
    "index_end_date": index_end,
}

# Save point for the intermediate data
common.save_item(icb_basic_tmp, "icb_basic_tmp")

# Load the data from file
icb_basic_tmp = common.load_item("icb_basic_tmp")

# Extract some datasets for convenience
index_spells = icb_basic_tmp["index_spells"]
date_of_death = icb_basic_tmp["date_of_death"]
cause_of_death = icb_basic_tmp["cause_of_death"]
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

# Join the attribute date to the index spells for linking
index_spells_with_link = acs.get_index_attribute_link(
    index_spells, primary_care_attributes
)

# Get the patient index-spell attributes (before reducing based on missingness/low-variance)
all_index_attributes = acs.get_index_attributes(
    index_spells_with_link, primary_care_attributes
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
outcomes = acs.get_outcomes(
    index_spells, all_other_codes, date_of_death, cause_of_death
)

features_codes = acs.get_code_features(index_spells, all_other_codes)

# Get counts of relevant prescriptions in the year before the index
features_prescriptions = acs.prescriptions_before_index(
    index_spells, primary_care_prescriptions
)

# Only blood pressure and HbA1c go back to 2019 in the data -- not
# including the other measurements in order to keep the sample size up.
prior_blood_pressure = from_icb.blood_pressure(index_spells, primary_care_measurements)
prior_hba1c = from_icb.hba1c(index_spells, primary_care_measurements)
features_measurements = prior_blood_pressure.merge(
    prior_hba1c, how="left", on="spell_id"
)

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
