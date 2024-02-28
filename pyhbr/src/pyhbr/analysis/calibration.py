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


def get_calibration(probs: DataFrame, y_test: Series, n_bins: int) -> list[DataFrame]:
    """Calculate the calibration of the fitted models
    
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
            bin_start = prob - bin_width/2
            bin_end = prob + bin_width/2
            count = ((bin_start <= probs[:, n]) & (probs[:, n] < bin_end)).sum()
            count_in_bins.append(count)
        count_in_bins = np.array(count_in_bins)
                
        error = np.sum(count_in_bins * np.abs(prob_true - prob_pred)) / N
        estimated_calibration_errors.append(error)
        
    return np.mean(estimated_calibration_errors)


def plot_calibration_curves(ax: Axes, curves: list[DataFrame], title = "Calibration-stability curves"):
    """Plot calibration curves for the model under test and resampled models
    
    Args:
        ax: The axes on which to plot the calibration curves
        curves: A list of DataFrames containing `predicted` and `observed`
            columns. The first DataFrame corresponds to the model under test
        title: Title to add to the plot.
    """
    mut_curve = curves[0]  # model-under-test
    ax.plot(mut_curve["predicted"], mut_curve["observed"])
    for curve in curves[1:]:
        ax.plot(curve["predicted"], curve["observed"], color="b", linewidth=0.3, alpha=0.4)
    ax.axline([0, 0], [1, 1], color="k", linestyle="--")
    ax.legend(["Model-under-test", "Bootstrapped models"])
    ax.set_title(title)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")


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
    bin_width = 0.80/n_bins

    ax.bar(bin_centers, height=means, width=bin_width, yerr=2 * sds)
    #ax.set_title("Distribution of predicted probabilities")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Count")