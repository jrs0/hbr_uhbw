"""Fetch ICB data (HES + SWD data)
"""

import importlib
import datetime as dt

from pyhbr import common, clinical_codes
from pyhbr.analysis import acs
from pyhbr.data_source import icb
from pyhbr.middle import from_icb

importlib.reload(common)
importlib.reload(acs)
importlib.reload(from_icb)
importlib.reload(icb)
importlib.reload(clinical_codes)

# Set a date range for episode fetch
start_date = dt.date(2022, 10, 1)
end_date = dt.date(2023, 1, 1)

# Get the raw HES data
engine = common.make_engine(database="abi")
raw_sus_data = from_icb.get_raw_sus_data(engine, start_date, end_date)

# The full dataset is large, so using a save point
# to speed up script development
common.save_item(raw_sus_data, "raw_sus_data")

# HES data + patient demographics
episodes_and_codes = from_icb.get_episodes_and_codes(raw_sus_data)



# Load from the save point
episodes = common.load_item("episodes_and_codes")

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_spells = acs.get_index_spells(episodes)

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
