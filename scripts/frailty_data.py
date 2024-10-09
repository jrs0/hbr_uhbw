from pyhbr import common
import pandas as pd

data, data_path = common.load_item("icb_hic_data", interactive=True, save_dir="report/save_data")


features_index = data["features_index"]
management = data["info_management"]