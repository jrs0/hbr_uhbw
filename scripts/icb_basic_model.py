import numpy as np
from numpy.random import RandomState
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from pyhbr import common

# Load outcome and training data
icb_basic_data = common.load_item("icb_basic_data")

# For convenience
outcomes = icb_basic_data["outcomes"]
features_index = icb_basic_data["features_index"]  # bool-only
features_codes = icb_basic_data["features_codes"]  # float-only
features_prescriptions = icb_basic_data["features_prescriptions"]  # float-only
features_measurements = icb_basic_data["features_measurements"]  # float-only
features_attributes = icb_basic_data["features_attributes"]  # float, category, Int8

# Combine all the features
features = (
    features_index.merge(features_codes, how="left", on="spell_id")
    .merge(features_prescriptions, how="left", on="spell_id")
    .merge(features_measurements, how="left", on="spell_id")
    .merge(features_attributes, how="left", on="spell_id")
)

# This is an sqlalchemy problem -- some column names are
# sqlalchemy.sql.elements.quoted_name, which is nearly impossible
# to discover (because dtype is object and it prints as a string)
# Fix this upstream.
features.columns = [str(col) for col in features.columns]

# Convert to a binary outcome (rather than a count)
binary_outcome = outcomes > 0

# Create a random seed
random_state = RandomState(0)

# Create the train/test split
X_train, X_test, y_train, y_test = train_test_split(
    features, binary_outcome, test_size=0.25, random_state=random_state
)

# To one-hot encode
object_columns = features.columns[
    (features.dtypes == "object") | (features.dtypes == "category")
]
object_pipe = Pipeline([
    #("low_variance", VarianceThreshold()),
    ("one_hot_encode", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=0.01)),
])
one_hot_encoders = [
    (
        "object_preprocess",
        object_pipe,
        object_columns,
    )
]

# To center and scale
float_columns = features.columns[(features.dtypes == "float")]
float_pipe = Pipeline([
    ("low_variance", VarianceThreshold()),
    ("impute", SimpleImputer(missing_values=np.nan, strategy='mean')),
    ("scaler", StandardScaler())
])

scalers = [
    (
        "float_preprocess",
        float_pipe,
        float_columns,
    )
]

preprocess = ColumnTransformer(
    one_hot_encoders + scalers,
    remainder="drop",
)

model = RandomForestClassifier()

pipe = Pipeline([("preprocess", preprocess), ("model", model)])

fit = pipe.fit(X_train, y_train.iloc[:, 0])

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test.iloc[:, 0], probs[:, 1])
