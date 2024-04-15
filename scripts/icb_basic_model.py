import importlib

import scipy
from numpy.random import RandomState
from sklearn.model_selection import train_test_split

from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from pyhbr import common

from pyhbr.analysis import model
from pyhbr.analysis import stability
from pyhbr.analysis import roc
from pyhbr.analysis import calibration
from pyhbr import common

import matplotlib.pyplot as plt

importlib.reload(model)
importlib.reload(calibration)
importlib.reload(common)
importlib.reload(stability)


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

# Combine the preprocessors together into a column transformer
# which performs the preprocessing on the groups of columns in
# parallel.
preprocess = model.make_columns_transformer(preprocessors)

# Select the outcome for modelling
outcome_name = "bleeding_outcome"

# Create a model to be trained on the preprocessed training set
mod = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state)

pipe = Pipeline([("preprocess", preprocess), ("model", mod)])

# Fit the bleeding and ischaemia models on the training set
# and bootstrap resamples of the training set (to assess stability)
fitted_bleeding_model = stability.fit_model(
    pipe, X_train, y_train.loc[:, "bleeding_outcome"], 10, random_state
)
fitted_ischaemia_model = stability.fit_model(
    pipe, X_train, y_train.loc[:, "ischaemia_outcome"], 10, random_state
)

# Get the predicted probabilities associated with all the resamples of
# the bleeding and ischaemia models
bleeding_probs = stability.predict_probabilities(fitted_bleeding_model, X_test)
ischaemia_probs = stability.predict_probabilities(fitted_ischaemia_model, X_test)


# Plot the stability of predicted probabilities
outcome_name = "bleeding_outcome"
fig, ax = plt.subplots(1, 2)
stability.plot_instability(
    ax[0],
    bleeding_probs,
    y_test.loc[:, outcome_name],
    "Stability of repeat risk prediction",
)
stability.plot_reclass_instability(
    ax[1], bleeding_probs, y_test.loc[:, outcome_name], 0.04
)
plt.tight_layout()
plt.show()

# Calculate the ROC curves for the models
bleeding_roc_curves = roc.get_roc_curves(
    bleeding_probs, y_test.loc[:, "bleeding_outcome"]
)
ischaemia_roc_curves = roc.get_roc_curves(
    ischaemia_probs, y_test.loc[:, "ischaemia_outcome"]
)
bleeding_auc = roc.get_auc(bleeding_probs, y_test.loc[:, "bleeding_outcome"])
ischaemia_auc = roc.get_auc(ischaemia_probs, y_test.loc[:, "ischaemia_outcome"])

# Plot the ROC curves for the models
fig, ax = plt.subplots(1, 2)
roc.plot_roc_curves(ax[0], bleeding_roc_curves, bleeding_auc, "Bleeding ROC Curves")
roc.plot_roc_curves(ax[1], ischaemia_roc_curves, ischaemia_auc, "Ischaemia ROC Curves")
plt.show()

# Get the calibration of the models
bleeding_calibration_curves = calibration.get_calibration(
    bleeding_probs, y_test.loc[:, "bleeding_outcome"], 15
)
ischaemia_calibration_curves = calibration.get_calibration(
    ischaemia_probs, y_test.loc[:, "ischaemia_outcome"], 15
)


def get_variable_width_calibration(
    probs: DataFrame, y_test: Series, n_bins: int
) -> list[DataFrame]:
    """Get variable-bin-width calibration curves

    Model predictions are arranged in ascending order, and then risk ranges
    are selected so that an equal number of predictions falls in each group.
    This means bin widths will be more granular at points where many patients
    are predicted the same risk. The risk bins are shown on the x-axis of
    calibration plots.

    In each bin, the proportion of patient with an event are calculated. This
    value, which is a function of each bin, is plotted on the y-axis of the
    calibration plot, and is a measure of the prevalence of the outcome in
    each bin. In a well calibrated model, this prevalence should match the
    mean risk prediction in the bin (the bin center).

    Note that a well-calibrated model is not a sufficient condition for
    correctness of risk predictions. One way that the prevalence of the
    bin can match the bin risk is for all true risks to roughly match
    the bin risk P. However, other ways are possible, for example, a
    proportion P of patients in the bin could have 100% risk, and the
    other have zero risk.


    Args:
        probs: Each column is the predictions from one of the resampled
            models. The first column corresponds to the model-under-test.
        y: Contains the observed outcomes.
        n_bins: The number of (variable-width) bins to include.

    Returns:
        A list of dataframes, one for each calibration curve. The
            "bin_center" column contains the central bin width;
            the "bin_half_width" column contains the half-width
            of each equal-risk group. The "est_prev" column contains
            the mean number of events in that bin;
            and the "est_prev_err" contains the half-width of the 95%
            confidence interval (symmetrical above and below bin_prev).
    """

    # Make the list that will contain the output calibration information
    calibration_dfs = []

    n_cols = probs.shape[1]
    for n in range(n_cols):

        # Get the probabilities predicted by one of the resampled
        # models (stored as a column in probs)
        col = probs.iloc[:, n].sort_values()

        # Bin the predictions into variable-width risk
        # ranges with equal numbers in each bin
        n_bins = 5
        samples_per_bin = int(np.ceil(len(col) / n_bins))
        bins = []
        for start in range(0, len(col), samples_per_bin):
            end = start + samples_per_bin
            bins.append(col[start:end])

        # Get the bin centres and bin widths
        bin_center = []
        bin_half_width = []
        for b in bins:
            upper = b.max()
            lower = b.min()
            bin_center.append((upper + lower) / 2)
            bin_half_width.append((upper - lower) / 2)

        # Get the event prevalence in the bin
        # Get the confidence intervals for each bin
        est_prev = []
        est_prev_err = []
        actual_samples_per_bin = []
        num_events = []
        for b in bins:

            # Get the outcomes corresponding to the current
            # bin (group of equal predicted risk)
            equal_risk_group = y_test.loc[b.index]

            actual_samples_per_bin.append(len(b))
            num_events.append(equal_risk_group.sum())

            prevalence_ci = calibration.get_prevalence(equal_risk_group)
            est_prev_err.append((prevalence_ci["upper"] - prevalence_ci["lower"]) / 2)
            est_prev.append(prevalence_ci["prevalence"])

        # Add the data to the calibration list
        df = DataFrame(
            {
                "bin_center": bin_center,
                "bin_half_width": bin_half_width,
                "est_prev": est_prev,
                "est_prev_err": est_prev_err,
                "samples_per_bin": actual_samples_per_bin,
                "num_events": num_events,
            }
        )
        calibration_dfs.append(df)

    return calibration_dfs


calibrations = get_variable_width_calibration(
    bleeding_probs, y_test.loc[:, "bleeding_outcome"], 5
)

# Plot an example calibration curve
c = calibrations[0]

from matplotlib.patches import Rectangle, Patch
from matplotlib.collections import PatchCollection
import matplotlib.ticker as mtick
from matplotlib import cm


# Function to plot error boxes
def make_error_boxes(ax: Axes, calibration: DataFrame):
    """Plot error boxes and error bars around points

    Args:
        ax: The axis on which to plot the error boxes.
        calibration: Dataframe containing one row per
            bin, showing how the predicted risk compares
            to the estimated prevalence.
    """

    alpha = 0.3

    c = calibration
    for n in range(len(c)):
        num_events = c.loc[n, "num_events"]
        samples_in_bin = c.loc[n, "samples_per_bin"]
        
        est_prev = 100 * c.loc[n, "est_prev"]
        est_prev_err = 100 * c.loc[n, "est_prev_err"]
        risk = 100 * c.loc[n, "bin_center"]
        bin_half_width = 100 * c.loc[n, "bin_half_width"]

        margin = 1.0
        x = risk - margin * bin_half_width
        y = est_prev - margin * est_prev_err
        width = 2 * margin * bin_half_width
        height = 2 * margin * est_prev_err

        rect = Rectangle(
            (x, y), width, height,
            label=f"Risk {risk:.2f}%, {num_events}/{samples_in_bin} events",
            alpha=alpha,
            facecolor=cm.jet(n/len(c))
        )
        ax.add_patch(rect)

    ax.errorbar(
        x=100 * c["bin_center"],
        y=100 * c["est_prev"],
        xerr=100 * c["bin_half_width"],
        yerr=100 * c["est_prev_err"],
        fmt="None",
    )
    
    ax.legend()

def draw_calibration_confidence(ax: Axes, calibration: DataFrame):
    """Draw a single model's calibration curve with confidence intervals

    Args:
        ax: The axes on which to draw the plot
        calibration: The model's calibration data
    """
    c = calibration

    make_error_boxes(ax, c)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("Estimated prevalence")
    ax.set_xlabel("Model-predicted risks")
    plt.title("Calibration of equal-sized similarly-predicted-risk groups")

    # Get the minimum and maximum for the x range
    min_x = 100 * (c["bin_center"]).min()
    max_x = 100 * (c["bin_center"]).max()

    # Generate a dense straight line (smooth curve on log scale)
    coords = np.geomspace(min_x, max_x, num=50)

    ax.plot(coords, coords, c="k")

    #ax.set_aspect("equal")

c = calibrations[3]

# Create figure and axes
fig, ax = plt.subplots(1, 2)
calibration.plot_calibration_curves(ax[0], calibrations)
draw_calibration_confidence(ax[1], calibrations[0]) 
plt.tight_layout()
plt.show()


# View the features that go directly into the model. This dataframe
# has the column that the model sees (after the preprocessing steps).
F_train = model.get_features(fit, X_train)

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test.loc[:, outcome_name], probs[:, 1])
auc

sns.displot(probs.iloc[2, :])
plt.show()


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
