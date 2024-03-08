"""Calculate the ARC HBR score for the HIC data
"""

import datetime as dt
import matplotlib.pyplot as plt

from pyhbr.common import make_engine
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr
from pyhbr.clinical_codes import counting
from pyhbr.data_source import hic

import importlib

importlib.reload(arc_hbr)
importlib.reload(from_hic)
importlib.reload(hic)
importlib.reload(counting)

import pandas as pd

pd.set_option("display.max_rows", 100)

# Set a date range for episode fetch
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

# Fetch data
engine = make_engine()
hic_data = from_hic.HicData(engine, start_date, end_date)

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_episodes = arc_hbr.index_episodes(hic_data)

# Get other episodes relative to the index episode (for counting code
# groups before/after the index)
all_other_codes = counting.get_all_other_codes(index_episodes, hic_data)

# Get the episodes that occurred in the previous year (for clinical code features)
max_before = dt.timedelta(days=365)
min_before = dt.timedelta(days=30)
previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)

# Get the episodes that occurred in the following year (for clinical code outcomes)
min_after = dt.timedelta(hours=72)  # Exclude periprocedural events
max_after = dt.timedelta(days=365)
following_year = counting.get_time_window(all_other_codes, min_after, max_after)

# Calculate more granular features as an intermediate step for calculating the
# ARC HBR score
features = arc_hbr.get_features(index_episodes, previous_year, hic_data)

# Calculate the ARC HBR score from the more granular features.
arc_hbr_score = arc_hbr.get_arc_hbr_score(features, hic_data)

# Get the bleeding outcome
bleeding_groups = ["bleeding_al_ani"]
bleeding_outcome = counting.count_code_groups(
    index_episodes, following_year, bleeding_groups, True
)

arc_hbr.plot_index_measurement_distribution(features)
plt.show()

# ======= QUICK MODEL =======

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from numpy.random import RandomState
from sklearn.metrics import roc_auc_score

random_state = RandomState(0)

# Granular features
X1 = features.drop(columns=["gender"]).dropna() # To avoid one-hot encoding for now

# ARC Score
X2 = arc_hbr_score.loc[X1.index]

# Combine
X = pd.concat([X1, X2], axis=1)

# Binary bleeding outcome
y = bleeding_outcome.loc[X.index] > 0

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.25, random_state=random_state)


model = RandomForestClassifier()

fit = model.fit(X_train, y_train)

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test, probs[:,1])