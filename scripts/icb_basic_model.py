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

# Category columns should be one-hot encoded (in all these one-hot encoders,
# consider the effect of linear dependence among the columns due to the extra
# variable compared to dummy encoding -- the relevant parameter is called
# 'drop').
cat_columns = features.columns[
    (features.dtypes == "object") | (features.dtypes == "category")
]
cat_pipe = Pipeline(
    [
        (
            "one_hot_encode",
            OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=0.002),
        ),
    ]
)
cat_preprocess = [
    (
        "cat_preprocess",
        cat_pipe,
        cat_columns,
    )
]

# Flag columns (encoded using Int8, which supports NaN), should be one-hot
# encoded (considered separately from category in case I want to do something
# different with these).
flag_columns = features.columns[(features.dtypes == "Int8")]
flag_df = features.loc[:, flag_columns]  # Look at the columns
flag_pipe = Pipeline(
    [
        (
            "one_hot_encode",
            OneHotEncoder(handle_unknown="infrequent_if_exist"),
        ),
    ]
)
flag_preprocess = [
    (
        "flag_preprocess",
        flag_pipe,
        flag_columns,
    )
]


# Numerical columns -- impute missing values, remove low variance
# columns, and then centre and scale the rest.
float_columns = features.columns[(features.dtypes == "float")]
float_df = features.loc[:, float_columns]  # Look at the columns
float_pipe = Pipeline(
    [
        ("impute", SimpleImputer(missing_values=np.nan, strategy="mean")),
        ("low_variance", VarianceThreshold()),
        ("scaler", StandardScaler()),
    ]
)

float_preprocess = [
    (
        "float_preprocess",
        float_pipe,
        float_columns,
    )
]

preprocess = ColumnTransformer(
    cat_preprocess + float_preprocess + flag_preprocess,
    remainder="drop",
)

X_prep_fit = preprocess.fit(X_train)
X_prep = X_prep_fit.transform(X_train)

# Get the output feature names for the float columns. The only step that
# can change columns is the low_variance reducer.
float_output_features = X_prep_fit.named_transformers_["float_preprocess"][
    "low_variance"
].get_feature_names_out(float_columns)


# Get the output feature names for category columns (one-hot encoded)
cat_output_features = X_prep_fit.named_transformers_["cat_preprocess"][
    "one_hot_encode"
].get_feature_names_out()

# Get the output feature names for the flag columns (one-hot encoded)
flag_output_features = X_prep_fit.named_transformers_["flag_preprocess"][
    "one_hot_encode"
].get_feature_names_out()


# This is the map showing which column ranges in the output features 
# correspond to which column-transformer features lists. (map from
# strings to slices)
X_prep_fit.output_indices_

outcome_name = "bleeding_outcome"

model = RandomForestClassifier(
    n_estimators=100, max_depth=10, random_state=random_state
)

pipe = Pipeline([("preprocess", preprocess), ("model", model)])

fit = pipe.fit(X_train, y_train.loc[:, outcome_name])

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test.loc[:, outcome_name], probs[:, 1])
auc