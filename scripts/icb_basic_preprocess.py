"""Convert the ICB data to ACS/bleeding/ischaemia datasets
"""

from pyhbr import common

data = common.load_item("icb_basic_data")

common.save_item(data, "icb_basic_data")

data["primary_care_prescriptions"]