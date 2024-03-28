"""Convert the ICB data to ACS/bleeding/ischaemia datasets
"""

import importlib
import datetime as dt
import numpy as np
from pyhbr import common
from pyhbr.clinical_codes import counting
from pyhbr.analysis import describe
from pyhbr.analysis import acs

importlib.reload(counting)
importlib.reload(acs)
importlib.reload(describe)

data = common.load_item("icb_basic_data")

primary_care_attributes = data["primary_care_attributes"]

# Do this in the data fetch
primary_care_attributes["smoking"] = primary_care_attributes["smoking"].replace(
    "(U|u)nknown", np.nan, regex=True
)

# Reduce the index spells to those which have a valid row of
# patient attributes
index_spells = data["index_spells"]

swd_index_spells = acs.get_swd_index_spells(index_spells, primary_care_attributes)

# Get the patient index-spell attributes
index_attributes = acs.get_index_attributes(swd_index_spells, primary_care_attributes)

# Remove attribute columns that have too much missingness or where
# the column is nearly constant (low variance)
reduced_index_attributes = acs.remove_features(
    index_attributes, max_missingness=0.75, const_threshold=0.95
)

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(swd_index_spells, data)

# Get the bleeding and ischaemia outcomes
outcomes = acs.get_outcomes(swd_index_spells, all_other_codes)
code_features = acs.get_code_features(swd_index_spells, all_other_codes)

# Combine all tables (features and outcomes) into a single table
# for saving.
training_data = (
    index_spells[["acs_index", "pci_index"]]
    .merge(outcomes, how="left", on="spell_id")
    .merge(code_features, how="left", on="spell_id")
)


rate_summaries = describe.get_column_rates(training_data)
