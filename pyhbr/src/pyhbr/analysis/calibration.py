"""Calibration plots

A calibration plot is a comparison of the proportion p
of events that occur in the subset of those with predicted
probability p'. Ideally, p = p' meaning that of the
cases predicted to occur with probability p', p of them
do occur. Calibration is presented as a plot of p against
'p'.

The stability of the calibration can be investigated, by
plotting p against p' for multiple bootstrapped models
(see stability.py).
"""

import numpy as np
from sklearn.calibration import calibration_curve
from pandas import DataFrame, Series
from matplotlib.axes import Axes
import matplotlib.ticker as mtick
from matplotlib.patches import Rectangle
from matplotlib import cm

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
        est_prev_variance = []
        actual_samples_per_bin = []
        num_events = []
        for b in bins:

            # Get the outcomes corresponding to the current
            # bin (group of equal predicted risk)
            equal_risk_group = y_test.loc[b.index]

            actual_samples_per_bin.append(len(b))
            num_events.append(equal_risk_group.sum())

            prevalence_ci = get_prevalence(equal_risk_group)
            est_prev_err.append((prevalence_ci["upper"] - prevalence_ci["lower"]) / 2)
            est_prev.append(prevalence_ci["prevalence"])
            est_prev_variance.append(prevalence_ci["variance"])

        # Add the data to the calibration list
        df = DataFrame(
            {
                "bin_center": bin_center,
                "bin_half_width": bin_half_width,
                "est_prev": est_prev,
                "est_prev_err": est_prev_err,
                "est_prev_variance": est_prev_variance,
                "samples_per_bin": actual_samples_per_bin,
                "num_events": num_events,
            }
        )
        calibration_dfs.append(df)

    return calibration_dfs

def get_calibration(probs: DataFrame, y_test: Series, n_bins: int) -> list[DataFrame]:
    """Calculate the calibration of the fitted models

    !!! warning
    
        This function is deprecated. Use the variable bin width calibration
        function instead.

    Get the calibration curves for all models (whose probability
    predictions for the positive class are columns of probs) based
    on the outcomes in y_test. Rows of y_test correspond to rows of
    probs. The result is a list of pairs, one for each model (column
    of probs). Each pair contains the vector of x- and y-coordinates
    of the calibration curve.

    Args:
        probs: The dataframe of probabilities predicted by the model.
            The first column is the model-under-test (fitted on the training
            data) and the other columns are from the fits on the training
            data resamples.
        y_test: The outcomes corresponding to the predicted probabilities.
        n_bins: The number of bins to group probability predictions into, for
            the purpose of averaging the observed frequency of outcome in the
            test set.

    Returns:
        A list of DataFrames containing the calibration curves. Each DataFrame
            contains the columns `predicted` and `observed`.

    """
    curves = []
    for column in probs.columns:
        prob_true, prob_pred = calibration_curve(y_test, probs[column], n_bins=n_bins)
        df = DataFrame({"predicted": prob_pred, "observed": prob_true})
        curves.append(df)
    return curves


def get_average_calibration_error(probs, y_test, n_bins):
    """
    This is the weighted average discrepancy between the predicted risk and the
    observed proportions on the calibration curve.

    See "https://towardsdatascience.com/expected-calibration-error-ece-a-step-
    by-step-visual-explanation-with-python-code-c3e9aa12937d" for a good
    explanation.

    The formula for estimated calibration error (ece) is:

       ece = Sum over bins [samples_in_bin / N] * | P_observed - P_pred |,

    where P_observed is the empirical proportion of positive samples in the
    bin, and P_pred is the predicted probability for that bin. The results are
    weighted by the number of samples in the bin (because some probabilities are
    predicted more frequently than others).

    The result is interpreted as an absolute error: i.e. a value of 0.1 means
    that the calibration is out on average by 10%. It may be better to modify the
    formula to compute an average relative error.

    Testing: not yet tested.
    """

    # There is one estimated calibration error for each model (the model under
    # test and all the bootstrap models). These will be averaged at the end
    estimated_calibration_errors = []

    # The total number of samples is the number of rows in the probs array. This
    # is used with the number of samples in the bins to weight the probability
    # error
    N = probs.shape[0]

    bin_edges = np.linspace(0, 1, n_bins + 1)
    for n in range(probs.shape[1]):

        prob_true, prob_pred = calibration_curve(y_test, probs[:, n], n_bins=n_bins)

        # For each prob_pred, need to count the number of samples in that lie in
        # the bin centered at prob_pred.
        bin_width = 1 / n_bins
        count_in_bins = []
        for prob in prob_pred:
            bin_start = prob - bin_width / 2
            bin_end = prob + bin_width / 2
            count = ((bin_start <= probs[:, n]) & (probs[:, n] < bin_end)).sum()
            count_in_bins.append(count)
        count_in_bins = np.array(count_in_bins)

        error = np.sum(count_in_bins * np.abs(prob_true - prob_pred)) / N
        estimated_calibration_errors.append(error)

    return np.mean(estimated_calibration_errors)


def plot_calibration_curves(
    ax: Axes,
    curves: list[DataFrame],
    title="Stability of Calibration",
):
    """Plot calibration curves for the model under test and resampled models

    Args:
        ax: The axes on which to plot the calibration curves
        curves: A list of DataFrames containing the calibration curve data
        title: Title to add to the plot.
    """
    mut_curve = curves[0]  # model-under-test
    ax.plot(
        100 * mut_curve["bin_center"],
        100 * mut_curve["est_prev"],
        label="Model-under-test",
        c="r",
    )
    for curve in curves[1:]:
        ax.plot(
            100*curve["bin_center"],
            100*curve["est_prev"],
            label="Resample",
            c="b",
            linewidth=0.3,
            alpha=0.4,
        )

    # Get the minimum and maximum for the x range
    min_x = 100 * (curves[0]["bin_center"]).min()
    max_x = 100 * (curves[0]["bin_center"]).max()

    # Generate a dense straight line (smooth curve on log scale)
    coords = np.geomspace(min_x, max_x, num=50)
    ax.plot(coords, coords, c="k")

    ax.legend(["Model-under-test", "Bootstrapped models"])

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("Estimated Prevalence")
    ax.set_xlabel("Model-Estimated Risks")
    ax.set_title(title)


def plot_prediction_distribution(ax, probs, n_bins):
    """
    Plot the distribution of predicted probabilities over the models as
    a bar chart, with error bars showing the standard deviation of each
    model height. All model predictions (columns of probs) are given equal
    weight in the average; column 0 (the model under test) is not singled
    out in any way.

    The function plots vertical error bars that are one standard deviation
    up and down (so 2*sd in total)
    """
    bin_edges = np.linspace(0, 1, n_bins + 1)
    freqs = []
    for j in range(probs.shape[1]):
        f, _ = np.histogram(probs[:, j], bins=bin_edges)
        freqs.append(f)
    means = np.mean(freqs, axis=0)
    sds = np.std(freqs, axis=0)

    bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2

    # Compute the bin width to leave a gap between bars
    # of 20%
    bin_width = 0.80 / n_bins

    ax.bar(bin_centers, height=means, width=bin_width, yerr=2 * sds)
    # ax.set_title("Distribution of predicted probabilities")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Count")


def get_prevalence(y_test: Series):
    """Estimate the prevalence in a set of outcomes

    To calculate model calibration, patients are grouped
    together into similar-risk groups. The prevalence of
    the outcome in each group is then compared to the
    predicted risk.

    The true risk of the outcome within each group is not
    known, but it is known what outcome occurred.

    One possible assumption is that the patients in each
    group all have the same risk, p. In this case, the
    outcomes from the group follow a Bernoulli
    distribution. The population parameter p (where the
    popopulation is all patients receiving risk predictions
    in this group) can be estimated simply using
    $\hat{p} = N_\\text{outcome}/N_\\text{group_size}$.
    Using a simple approach to calculate the confidence
    interval on this estimate, assuming a large enough
    sample size for normally distributed estimate of the
    mean, gives a CI of:

    $$
    \hat{p} \pm 1.96\sqrt{\\frac{\hat{p}(1-\hat{p})}{N_\\text{group_size}}}
    $$

    (See [this answer](https://stats.stackexchange.com/a/156807)
    for details.)

    However, the assumption of uniform risk within the
    models groups-of-equal-risk-prediction may not be valid,
    because it assumes that the model is predicting
    reasonably accurate risks, and the model is the item
    under test.

    One argument is that, if the estimated prevalence matches
    the risk of the group closely, then this may give evidence
    that the models predicted risks are accurate -- the alternative
    would be that the real risks follow a different distribution, whose
    mean happens (coincidentally) to coincide with the predicted
    risk. Such a conclusion may be possible if the confidence
    interval for the estimated prevalence is narrow, and agrees
    with the predicted risk closely.

    Without further assumptions, there is nothing further that
    can be said about the distribution of patient risks within
    each group. As a result, good calibration is a necessary,
    but not sufficient, condition for accurate risk
    predictions in the model .

    Args:
        y_test: The (binary) outcomes in a single risk group.
            The values are True/False (boolean)

    Returns:
        A map containing the key "prevalence", for the estimated
            mean of the Bernoulli distribution, and "lower"
            and "upper" for the estimated confidence interval,
            assuming all patients in the risk group are drawn
            from a single Bernoulii distribution. The "variance"
            is the estimate of the sample variance of the estimated
            prevalence, and can be used to form an average of
            the accuracy uncertainties in each bin.

            Note that the assumption of a Bernoulli distribution
            is not necessarily accurate.
    """
    n_group_size = len(y_test)
    p_hat = np.mean(y_test)
    variance = (p_hat * (1 - p_hat)) / n_group_size # square of standard error of Bernoulli
    half_width = 1.96 * np.sqrt(variance) # Estimate of 95% confidence interval
    return {
        "prevalence": p_hat,
        "lower": p_hat - half_width,
        "upper": p_hat + half_width,
        "variance": variance
    }

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
    ax.set_ylabel("Estimated Prevalence")
    ax.set_xlabel("Model-Estimated Risks")
    ax.set_title("Accuracy of Risk Estimates")

    # Get the minimum and maximum for the x range
    min_x = 100 * (c["bin_center"]).min()
    max_x = 100 * (c["bin_center"]).max()

    # Generate a dense straight line (smooth curve on log scale)
    coords = np.geomspace(min_x, max_x, num=50)

    ax.plot(coords, coords, c="k")

    #ax.set_aspect("equal")