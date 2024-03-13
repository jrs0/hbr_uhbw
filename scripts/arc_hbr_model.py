from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from numpy.random import RandomState
from sklearn.metrics import roc_auc_score
from pyhbr import common
import pandas as pd

data = common.load_item("arc_hbr_data", True)

features = data["features"]
arc_hbr_score = data["arc_hbr_score"]
bleeding_outcome = data["bleeding_outcome"]

random_state = RandomState(0)

# Granular features
X1 = features.drop(columns=["gender"]).dropna() # To avoid one-hot encoding for now

# ARC Score
X2 = arc_hbr_score.loc[X1.index]

# Combine
X = pd.concat([X1, X2], axis=1)

# Binary bleeding outcome
y = bleeding_outcome.loc[X.index] > 0

X_train, X_test, y_train, y_test = train_test_split(X1, y, test_size = 0.25, random_state=random_state)


model = RandomForestClassifier()

fit = model.fit(X_train, y_train)

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test, probs[:,1])