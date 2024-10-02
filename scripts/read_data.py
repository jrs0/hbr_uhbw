# This script shows how to read data saved in the save_dir
# interactively.

from pyhbr import common
import numpy as np

# Set the path to the save directory
save_dir = "run/save_data"

# Load a data file pickle (.pkl). Only specify
# the first part of the filename. By specifying
# interactive as True, you can pick which file
# is loaded (by timestamp). Otherwise, the most
# recent file will be loaded. The data_path
# contains the absolute path to the loaded data
interactive = True
data, data_path = common.load_item("icb_hic_data", interactive, save_dir)

# Use .keys() to see what items are inside the data
# (data is a dictionary)
data.keys()

# Access data files as follows
index_spells = data["index_spells"]

# The data file saved by fetch_data contains a "raw_data"
# key, which is a path to the raw data used to build the
# other tables in data. This is what is fetched in the
# SQL-query part of the fetch_data script. You can load
# it as follows:
raw_data = common.load_exact_item(data["raw_file"], save_dir)

# Items stored in raw_data
raw_data.keys()

