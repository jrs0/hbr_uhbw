from pyhbr import common
from pyhbr.analysis import describe

icb_basic_data = common.load_item("icb_basic_data")

describe.proportion_missingness(icb_basic_data["features_attributes"])

