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

data = common.load_item("icb_basic_data")

index_spells = data["index_spells"]

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(index_spells, data)

# Get the bleeding and ischaemia outcomes
outcomes = acs.get_outcomes(index_spells, all_other_codes)

summaries = {
    "bleeding_outcome_rate": describe.proportion_nonzero(outcomes["bleeding_outcome"]),
    "ischaemia_outcome_rate": describe.proportion_nonzero(outcomes["ischaemia_outcome"]),
}

# Predictors derived from clinical code groups use clinical coding data from 365
# days before the index to 30 days before the index (this excludes episodes where
# no coding data would be available, because the coding process itself takes
# approximately one month).

max_before = dt.timedelta(days=365)
min_before = dt.timedelta(days=30)

# Get the episodes that occurred in the previous year (for clinical code features)

previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)
