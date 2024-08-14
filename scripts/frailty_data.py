# This uses the icb_hic_data.py script but prepares the dataset suitable
# for looking into the effect of frailty on ischaemia outcomes. The 
# starting point for the dataset is the tmp data, which is roughly
# halfway down the icb_hic_data.py file. The main difference between
# that file and this one is the focus on survival times here (as 
# opposedto binary yes/no outcomes).


import importlib
import datetime as dt

import pandas as pd
from pyhbr import common, clinical_codes
from pyhbr.analysis import acs
from pyhbr.clinical_codes import counting
from pyhbr.data_source import icb, hic_icb, hic
from pyhbr.middle import from_icb, from_hic
from pyhbr.analysis import arc_hbr

importlib.reload(common)
importlib.reload(acs)
importlib.reload(from_icb)
importlib.reload(from_hic)
importlib.reload(icb)
importlib.reload(hic)
importlib.reload(hic_icb)
importlib.reload(clinical_codes)
importlib.reload(counting)

tmp, tmp_path = common.load_item("icb_hic_tmp")

# Extract some datasets for convenience
episodes = tmp["episodes"]
codes = tmp["codes"]
index_spells = tmp["index_spells"]
date_of_death = tmp["date_of_death"]
cause_of_death = tmp["cause_of_death"]
primary_care_attributes = tmp["primary_care_attributes"]
primary_care_prescriptions = tmp["primary_care_prescriptions"]
secondary_care_prescriptions = tmp["secondary_care_prescriptions"]
primary_care_measurements = tmp["primary_care_measurements"]
lab_results = tmp["lab_results"]

# Get features from the lab results
features_lab = arc_hbr.first_index_lab_result(index_spells, lab_results, episodes)