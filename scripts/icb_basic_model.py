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


def plot_reclass_instability(
    ax: Axes,
    probs: DataFrame,
    y_test: Series,
    threshold: float,
    title: str = "Stability of risk classification",
):
    """Plot the probability of reclassification by predicted risk

    Args:
        ax: The axes on which to draw the plot
        probs: The matrix of probabilities from the model-under-test
            (first column) and the bootstrapped models (subsequent
            models).
        y_test: The true outcome corresponding to each row of the
            probs matrix. This is used to colour the points based on
            whether the outcome occurred on not.
        threshold: The risk level at which a patient is considered high risk
        title: The plot title.
    """

    # For the predictions of each model, categorise patients as
    # high risk or not based on the threshold.
    high_risk = probs > threshold

    # Find the subsets of patients who were flagged as high risk
    # by the original model.
    originally_low_risk = high_risk[~high_risk.iloc[:, 0]]
    originally_high_risk = high_risk[high_risk.iloc[:, 0]]

    # Count how many of the patients remained high risk or
    # low risk in the bootstrapped models.
    stayed_high_risk = originally_high_risk.iloc[:, 1:].sum(axis=1)
    stayed_low_risk = (~original_low_risk.iloc[:, 1:]).sum(axis=1)

    # Calculate the number of patients who changed category (category
    # unstable)
    num_resamples = probs.shape[1]
    stable_count = pd.concat([stayed_low_risk, stayed_high_risk])
    unstable_prob = (
        ((num_resamples - category_stable_total) / num_resamples)
        .rename("unstable_prob")
        .to_frame()
    )

    # Merge the original risk with the unstable count
    original_risk = probs.iloc[:, 0].rename("original_risk")
    df = (
        original_risk.to_frame()
        .merge(unstable_prob, on="spell_id", how="left")
        .merge(y_test.rename("outcome"), on="spell_id", how="left")
    )

    x = 100 * df["original_risk"]
    y = 100 * df["unstable_prob"]
    c = df["outcome"]
    colour_map = {False: "g", True: "r"}

    for outcome_to_plot, colour in colour_map.items():
        x_to_plot = [x for x, outcome in zip(x, c) if outcome == outcome_to_plot]
        y_to_plot = [y for y, outcome in zip(y, c) if outcome == outcome_to_plot]
        ax.scatter(x_to_plot, y_to_plot, c=colour, s=1, marker=".")

    # Plot the risk category threshold and label it
    ax.axline(
        [100 * threshold, 0],
        [100 * threshold, 1],
        c="r",
    )

    # Plot the 50% line for more-likely-than-not reclassification
    ax.axline([0, 50], [100, 50])

    # Get the lower axis limits
    min_risk = 100 * df["original_risk"].min()
    min_unstable_prob = 100 * df["unstable_prob"].min()

    # Plot boxes to show high and low risk groups
    # low_risk_rect = Rectangle((min_risk, min_unstable_prob), 100*threshold, 100, facecolor="g", alpha=0.3)
    # ax[1].add_patch(low_risk_rect)
    # high_risk_rect = Rectangle((100*threshold, min_unstable_prob), 100*(1 - threshold), 100, facecolor="r", alpha=0.3)
    # ax[1].add_patch(high_risk_rect)

    text_str = f"High-risk threshold ({100*threshold}%)"
    ax.text(
        100 * threshold,
        min_unstable_prob * 1.1,
        text_str,
        fontsize=9,
        rotation="vertical",
        color="r",
        horizontalalignment="center",
        verticalalignment="bottom",
        backgroundcolor="w",
    )

    # Calculate the number of patients who fall in each stability group.
    # Unstable means
    num_high_risk = (df["original_risk"] >= threshold).sum()
    num_low_risk = (df["original_risk"] < threshold).sum()

    num_unstable_given_low_risk = (
        (df["original_risk"] < threshold) & (df["unstable_prob"] >= 0.5)
    ).sum()
    num_unstable_given_high_risk = (
        (df["original_risk"] >= threshold) & (df["unstable_prob"] >= 0.5)
    ).sum()

    num_stable = (df["unstable_prob"] < 0.5).sum()
    num_unstable = (df["unstable_prob"] >= 0.5).sum()

    high_risk_and_unstable = (
        (df["original_risk"] >= threshold) & (df["unstable_prob"] > 0.5)
    ).sum()

    low_risk_and_stable = (
        (df["original_risk"] < threshold) & (df["unstable_prob"] < 0.5)
    ).sum()

    # Count the number of events in each risk group
    num_events_in_low_risk_group = df[df["original_risk"] < threshold]["outcome"].sum()
    num_events_in_high_risk_group = df[df["original_risk"] >= threshold]["outcome"].sum()

    ax.set_xlim(0.9 * min_risk, 110)
    ax.set_ylim(0.9 * min_unstable_prob, 110)

    text_str = f"{num_low_risk} predicted\nlow risk. {num_unstable_given_low_risk} have\n>50% chance\nreclass. as high\nrisk. {num_events_in_low_risk_group} events\noccurred."
    ax.text(
        0.05,
        0.95,
        text_str,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
    )

    text_str = f"{num_high_risk} predicted\nhigh risk. {num_unstable_given_high_risk} have\n>50% chance\nreclass. as low\nrisk. {num_events_in_high_risk_group} events\noccurred."
    ax.text(
        0.95,
        0.95,
        text_str,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        horizontalalignment="right"
    )

    # Set axis properties
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    ax.set_title(title)
    ax.set_xlabel("Risk prediction from model")
    ax.set_ylabel("Probability of risk reclassification by equivalent model")


# Plot the stability of predicted probabilities
fig, ax = plt.subplots(1, 2)
stability.plot_instability(
    ax[0],
    bleeding_probs,
    y_test.loc[:, "bleeding_outcome"],
    "Stability of repeat risk prediction",
)
plot_reclass_instability(ax[1], bleeding_probs, y_test.loc[:, "bleeding_outcome"], 0.04)
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
        for b in bins:

            # Get the outcomes corresponding to the current
            # bin (group of equal predicted risk)
            equal_risk_group = y_test.loc[b.index]

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
            }
        )
        calibration_dfs.append(df)

    return calibration_dfs


# Plot the calibration curves
fig, ax = plt.subplots(1, 1)
calibration.plot_calibration_curves(ax, bleeding_calibration_curves, "red", "testtt")
calibration.plot_calibration_curves(ax, ischaemia_calibration_curves, "blue", "test")
plt.show()

calibrations = get_variable_width_calibration(
    bleeding_probs, y_test.loc[:, "bleeding_outcome"], 5
)

# Plot an example calibration curve
c = calibrations[0]

from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import matplotlib.ticker as mtick


# Function to plot error boxes
def make_error_boxes(ax, x, y, xerr, yerr, colour="r", alpha=0.3):
    """Plot error boxes and error bars around points

    Args:
        ax: The axis on which to plot the error boxes.
        x: The x-centers of the boxes to plot.
        y: The y-centers of the boxes to plot.
        xerr: The half width of the box in the x direction.
        yerr: The half width of the box in the y direction.
        colour:  The colour of the box.
        alpha: The transparency of the box.
    """

    ax.errorbar(
        x=x,
        y=y,
        xerr=xerr,
        yerr=yerr,
        fmt="None",
    )

    # Create list for all the error patches
    errorboxes = []

    # Loop over data points; create box from errors at each point
    for xc, yc, xe, ye in zip(x, y, xerr, yerr):
        rect = Rectangle((xc - xe, yc - ye), 2 * xe, 2 * ye)
        errorboxes.append(rect)

    # Create patch collection with specified colour/alpha
    pc = PatchCollection(errorboxes, facecolor=colour, alpha=alpha)

    # Add collection to axes
    ax.add_collection(pc)


c = calibrations[3]

# Create figure and axes
fig, ax = plt.subplots(1)
make_error_boxes(
    ax, c["bin_center"], c["est_prev"], c["bin_half_width"], c["est_prev_err"]
)
# ax.set_xscale("log")
# ax.set_yscale("log")
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_ylabel("Estimated risk in risk group")
ax.set_xlabel("Model-predicted risks")
plt.title("Calibration of equal-sized equal-predicted-risk groups")

# Get the minimum and maximum for the x range
min_x = (c["bin_center"]).min()
max_x = (c["bin_center"]).max()

# Generate a dense straight line (smooth curve on log scale)
coords = np.geomspace(min_x, max_x, num=50)

ax.set_xlim([0, 0.04])
ax.set_ylim([0, 0.04])

ax.plot(coords, coords, c="k")

ax.set_aspect("equal")

# plt.tight_layout()~
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
