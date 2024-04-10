import importlib

from numpy.random import RandomState
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from pyhbr import common

from pyhbr.analysis import model

importlib.reload(model)


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

# Make all the preprocessors for each group of columns
preprocessors = [
    model.make_category_preprocessor(X_train),
    model.make_flag_preprocessor(X_train),
    model.make_float_preprocessor(X_train),
]


def make_columns_transformer(
    preprocessors: list[Preprocessor | None],
) -> ColumnTransformer:

    # Remove None values from the list (occurs when no columns
    # of that type are present in the training data)
    not_none = [pre for pre in preprocessors if pre is not None]

    # Make the list of tuples in the format for ColumnTransformer
    tuples = [(pre.name, pre.pipe, pre.columns) for pre in not_none]

    return ColumnTransformer(tuples, remainder="drop")


# Combine the preprocessors together into a column transformer
# which performs the preprocessing on the groups of columns in
# parallel.
preprocess = make_columns_transformer(preprocessors)

# Select the outcome for modelling
outcome_name = "bleeding_outcome"

# Create a model to be trained on the preprocessed training set
model = RandomForestClassifier(
    n_estimators=100, max_depth=10, random_state=random_state
)

pipe = Pipeline([("preprocess", preprocess), ("model", model)])

fit = pipe.fit(X_train, y_train.loc[:, outcome_name])

def get_num_feature_columns(fit: Pipeline) -> int:
    """Get the total number of feature columns
    Args:
        fit: The fitted pipeline, containing a "preprocess"
            step.

    Returns:
        The total number of columns in the features, after
            preprocessing.
    """
    
    # Get the map from column transformers to the slices
    # that they occupy in the training data
    preprocess = fit["preprocess"]
    column_slices = preprocess.output_indices_

    total = 0
    for s in column_slices.values():
        total += s.stop - s.start
        
    return total

def get_preprocessed_column_map(
    fit: Pipeline, preprocessors: list[Preprocessor]
) -> dict[str, str]:

    # Get the fitted ColumnTransformer from the fitted pipeline
    preprocess = fit["preprocess"]

    # Map from preprocess name to the relevant step that changes
    # column names. This must be kept consistent with the
    # make_*_preprocessor functions
    relevant_step = {
        "category": "one_hot_encoder",
        "float": "low_variance",
        "flag": "one_hot_encode",
    }

    # Get the map showing which column transformers (preprocessors)
    # are responsible which which slices of columns in the output
    # training dataframe
    column_slices = preprocess.output_indices_

    # Make an empty list of the right length to store all the columns
    column_names = get_num_feature_columns(fit) * [None]

    for pre in preprocessors:
        name = pre.name
        step_name = relevant_step[name]

        # Get the step which transforms column names
        step = preprocess.named_transformers_[pre.name][step_name]

        # A special case is required for the low_variance columns
        # which need original list of columns passing in
        if name == "float":
            columns = step.get_feature_names_out(pre.columns)
        else:
            columns = step.get_feature_names_out()

        # Get the properties of the slice where this set of
        # columns sits
        start = column_slices[name].start
        stop = column_slices[name].stop
        length = stop - start

        # Check the length of the slice matches the output
        # columns length
        if len(columns) != length:
            raise RuntimeError(
                "Length of output columns slice did not match the length of the column names list"
            )
            
        # Insert the list of colum names by slice
        column_names[column_slices[name]] = columns

    return column_names

get_preprocessed_column_map(fit, preprocessors)

preprocess = fit["preprocess"]
preprocess.output_indices_

get_preprocessed_column_map(fit, preprocessors)


probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test.loc[:, outcome_name], probs[:, 1])
auc


################# DRAFT


X_prep_fit = col_transformer.fit(X_train)
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
