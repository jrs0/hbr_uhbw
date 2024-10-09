# Script

from pyhbr import common
import pandas as pd
import matplotlib.pyplot as plt

data, data_path = common.load_item(
    "icb_hic_data", interactive=True, save_dir="report/save_data"
)

features_index = data["features_index"]
management = data["info_management"]
score = data["info_index_scores"]["cambridge_score"]
attributes = data["features_attributes"]

df = features_index.merge(management, on="spell_id", how="left").merge(
    score, on="spell_id", how="left"
)

