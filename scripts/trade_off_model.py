

from pyhbr import common
import pandas as pd
import numpy as np
from pandas import DataFrame, Series

data, data_path = common.load_item("icb_hic_data")

# For convenience
outcomes = data["outcomes"]

# Base the features dataframe on the outcomes index
features = outcomes[[]]

# Load all features -- these are the items in the data file that
# have a key that starts with "features_"
for key in data.keys():
    if "features_" in key:
        print(f"Joining {key} into features dataframe")
        features = features.merge(data[key], how="left", on="spell_id")


