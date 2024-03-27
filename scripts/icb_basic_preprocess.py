"""Convert the ICB data to ACS/bleeding/ischaemia datasets
"""

import importlib
import datetime as dt
from pyhbr import common
from pyhbr.clinical_codes import counting

importlib.reload(counting)

data = common.load_item("icb_basic_data")

index_spells = data["index_spells"]

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(index_spells, data)

# Get the episodes that occurred in the previous year (for clinical code features)
max_before = dt.timedelta(days=365)
min_before = dt.timedelta(days=30)
previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)


counting.count_code_groups(index_spells, previous_year, ["bleeding_adaptt"], False)