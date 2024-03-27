"""Convert the ICB data to ACS/bleeding/ischaemia datasets
"""

import importlib
import datetime as dt
from pyhbr import common
from pyhbr.clinical_codes import counting
from pyhbr.analysis import describe
from pyhbr.analysis import acs

importlib.reload(counting)
importlib.reload(acs)
importlib.reload(describe)

data = common.load_item("icb_basic_data")

index_spells = data["index_spells"]

# Fix this upstream (should not contain duplicates) -- just link
# it to spell_id (i.e. the index), and that will pick out what was
# recorded in the index spell.
demographics = data["demographics"].reset_index()

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(index_spells, data)

# Get the bleeding and ischaemia outcomes
outcomes = acs.get_outcomes(index_spells, all_other_codes)
code_features = acs.get_code_features(index_spells, all_other_codes)

# Join the attributes onto the index spells by patient, and then
# only keep attributes that are before the index event, but within
# the attribute_valid_window
#
# The attribute_period column of an attributes row indicates that
# the attribute was valid at the end of the interval
# (attribute_period, attribute_period + 1month). It is important
# that no attribute is used in modelling that could have occurred
# after the index event, meaning that attribute_period + 1 < idx_date
# must hold for any attribute used as a predictor. On the other hand,
# data substantially before the index event should not be used. The
# valid window is controlled by imposing
#
# (idx_date - attribute_period) < attribute_valid_window
#
# Ensure that attribute_valid_window is slightly larger than a multiple
# of months to ensure that a full month is captured.
#

# Define a window before the index event where SWD attributes will be considered valid.
# 41 days is used to ensure that a full month is definitely captured. Consider
# using 31*n + 10 to allow attributes up to n months before the index event to be used
# (the most recent attributes will still be preferred).
attribute_valid_window = dt.timedelta(days=41)

primary_care_attributes = data["primary_care_attributes"]

index_spells.reset_index().merge(
    primary_care_attributes[["patient_id", "attribute_period"]],
    how="left",
    on="patient_id",
).dtypes

""".groupby("spell_id").apply(
    lambda g: g[
        ((g["attribute_period"] + dt.timedelta(days=31)) < g["spell_start"])
        & ((g["spell_start"] - g["attribute_period"]) < attribute_valid_window)
    ]
)
"""

# Combine all tables (features and outcomes) into a single table
# for saving.
training_data = (
    index_spells[["acs_index", "pci_index"]]
    .merge(outcomes, how="left", on="spell_id")
    .merge(code_features, how="left", on="spell_id")
)


rate_summaries = describe.get_column_rates(training_data)
