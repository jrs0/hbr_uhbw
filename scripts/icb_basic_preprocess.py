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
primary_care_attributes["smoking"] = primary_care_attributes["smoking"].replace("(U|u)nknown", np.nan, regex=True)

# Reduce the index spells to those which have a valid row of
# patient attributes
index_spells = data["index_spells"]

swd_index_spells = acs.get_swd_index_spells(index_spells, primary_care_attributes)

# Get the patient index-spell attributes
index_attributes = acs.get_index_attributes(swd_index_spells, primary_care_attributes)

# Remove attribute columns that have too much missingness or where
# the column contains only one value after excluding NA
missingness = describe.proportion_missingness(index_attributes)
zero_variance = describe.zero_variance_columns(index_attributes)

x = missingness[missingness < 0.75]
y = zero_variance[~zero_variance]

to_keep = missingness[(missingness < 0.75) & ~zero_variance]


def contains_enough_variance(
    column: Series, missingness_threshold: float, common_value_threshold: float
) -> bool:
    """Decide if a column has enough variance to include as predictor
    
    Args:
        column: A column (which can have numeric or non-numeric type)
            to assess whether there is enough variance to use as a
            predictor in models.
        missingness_threshold: A column is excluded if there is more
            missingness (NA or None) than this value.
        common_value_threshold: A column is excluded if the most common
            value occupies more than this proportion of the rows (excluding
            missing values).

    Returns:
        True if enough variance, False otherwise
    """

    # Check if the column fails the missingness test
    if column.isna().sum() / len(column) > missingness_threshold:
        return False

    # Check if the column meets the common value test
    frequencies = column.value_counts()
    if frequencies.iloc[0] > common_value_threshold * frequencies.sum():
        return False
    
    # Else the column has low enough missingness and high enough variance
    return True

missingness_threshold = 0.5
common_value_threshold = 0.99
cols_to_keep = index_attributes.apply(
    lambda col: contains_enough_variance(
        col, missingness_threshold, common_value_threshold
    )
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
