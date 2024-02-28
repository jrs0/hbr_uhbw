"""Assessing model stability

Model stability of an internally-validated model
refers to how well models developed on a similar internal
population agree with each other. The methodology for
assessing model stability follows Riley and Collins, 2022
(https://arxiv.org/abs/2211.01061)

Assessing model stability is an end-to-end test of the entire
model development process. Riley and Collins do not refer to
a test/train split, but their method will be interpreted as
applying to the training set (with instability measures assessed
by applying models to the test set). As a result, the first step
in the process is to split the internal dataset into a training
set P0 and a test set T.

Assuming that a training set P0 is used to develop a model M0
using a model development  process D (involving steps such
cross-validation and hyperparameter tuning in the training set,
and validation of accuracy of model prediction in the test set),
the following steps are required to assess the stability of M0:

1. Bootstrap resample P0 with replacement M >= 200 times, creating
   M new datasets Pm that are all the same size as P0
2. Apply D to each Pm, to obtain M new models Mn which are all
   comparable with M0.
3. Collect together the predictions from all Mn and compare them
   to the predictions from M0 for each sample in the test set T.
4. From the data in 3, plot instability plots such as a scatter
   plot of M0 predictions on the x-axis and all the Mn predictions
   on the y-axis, for each sample of T. In addition, plot graphs
   of how all the model validation metrics vary as a function of
   the bootstrapped models Mn.

Implementation

A function is required that takes the original training set P0
and generates N bootstrapped resamples Pn that are the same size
as P.

A function is required that wraps the entire model
into one call, taking as input the bootstrapped resample Pn and
providing as output the bootstrapped model Mn. This function can
then be called M times to generate the bootstrapped models. This
function is not defined in this file (see the fit.py file)

An aggregating function will then take all the models Mn, the
model-under-test M0, and the test set T, and make predictions
using all the models for each sample in the test set. It should
return all these predictions (probabilities) in a 2D array, where
each row corresponds to a test-set sample, column 0 is the probability
from M0, and columns 1 through M are the probabilities from each Mn.

This 2D array may be used as the basis of instability plots. Paired
with information about the true outcomes y_test, this can also be used
to plot ROC-curve variability (i.e. plotting the ROC curve for all
model M0 and Mn on one graph). Any other accuracy metric of interest
can be calculated from this information (i.e. for step 4 above).
"""

import warnings
from dataclasses import dataclass

import numpy as np
from numpy.random import RandomState
from pandas import DataFrame, Series

from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.utils import resample

from matplotlib.axes import Axes

@dataclass
class Resamples:
    """Store a training set along with M resamples of it
    """
    X0: DataFrame
    y0: Series
    Xm: list[DataFrame]
    ym: list[Series]


def make_bootstrapped_resamples(X0: DataFrame, y0: Series, M: int, random_state: RandomState) -> Resamples:
    """Make M resamples of the training data
    
    Makes M bootstrapped resamples of a training set (X0,y0).
    M should be at least 200 (as per recommendation).

    Args:
        X0: The features in the training set to be resampled
        y0: The outcome in the training set to be resampled
        M: How many resamples to take
        random_state: Source of randomness for resampling

    Raises:
        ValueError: If the number of rows in X0 and y0 do not match

    Returns:
        An object containing the original training set and the resamples.
    """
    
    num_samples = X0.shape[0]
    if num_samples != len(y0):
        raise ValueError("Number of rows in X0_train and y0_train must match")
    if M < 200:
        warnings.warn("M should be at least 200; see Riley and Collins, 2022")

    Xm = []
    ym = []
    for _ in range(M):
        X, y = resample(X0, y0, random_state=random_state)
        Xm.append(X)
        ym.append(y)

    return Resamples(X0, y0, Xm, ym)

@dataclass
class FittedModel:
    """Stores a model fitted to a training set and resamples of the training set.
    """
    M0: Pipeline
    Mm: list[Pipeline]
    
    def flatten(self) -> list[Pipeline]:
        """Get a flat list of all the models

        Returns:
            The list of fitted models, with M0 at the front
        """
        return [self.M0] + self.Mm    
    

def fit_model(model: Pipeline, X0: DataFrame, y0: Series, M: int, random_state: RandomState) -> FittedModel:
    """Fit a model to a training set and resamples of the training set.
    
    Use the unfitted model pipeline returned by model_factory to:
    
    * Fit a model to the training set (X0, y0)
    * Fit a model to M resamples (Xm, ym) of the training set
    
    The model is an unfitted scikit-learn Pipeline. Note that if RandomState is used
    when specifying the model, then the models used to fit the resamples here will
    be _statstical clones_ (i.e. they might not necessarily produce the same result
    on the same data). clone() is called on model before fitting, so each fit gets a 
    new clean object.
    
    Args:
        model: An unfitted scikit-learn pipeline, which is used as the basis for
            all the fits. Each fit calls clone() on this object before fitting, to
            get a new model with clean parameters. The cloned fitted models are then
            stored in the returned fitted model.
        X0: The training set features
        y0: The training set outcome
        M (int): How many resamples to take from the training set (ideally >= 200)
        random_state: The source of randomness for model fitting

    Returns:
        An object containing the model fitted on (X0,y0) and all (Xm,ym)
    """
    
    # Develop a single model from the training set (X0_train, y0_train),
    # using any method (e.g. including cross validation and hyperparameter
    # tuning) using training set data. This is referred to as D in
    # stability.py.
    print("Fitting model-under-test")
    pipe = clone(model)
    M0 = pipe.fit(X0, y0)

    # Resample the training set to obtain the new datasets (Xm, ym)
    print(f"Creating {M} bootstrap resamples of training set")
    resamples = make_bootstrapped_resamples(X0, y0, M, random_state)
    
    # Develop all the bootstrap models to compare with the model-under-test M0
    print("Fitting bootstrapped models")
    Mm = []
    for m in range(M):
        pipe = clone(model)
        ym = resamples.ym[m]
        Xm = resamples.Xm[m]
        Mm.append(pipe.fit(Xm, ym))

    return FittedModel(M0, Mm)

def predict_probabilities(fitted_model: FittedModel, X_test: DataFrame) -> DataFrame:
    """Predict outcome probabilities using the fitted models on the test set
    
    Aggregating function which finds the predicted probability
    from the model-under-test M0 and all the bootstrapped models
    Mn on each sample of the training set features X_test. The
    result is a 2D numpy array, where each row corresponds to
    a test-set sample, the first column is the predicted probabilities
    from M0, and the following N columns are the predictions from all
    the other Mn.

    Note: the numbers in the matrix are the probabilities of 1 in the
    test set y_test.
    
    Args:
        fitted_model: The model fitted on the training set and resamples
    
    Returns:
        An table of probabilities of the positive outcome in the class,
            where each column comes from a different model. Column zero 
            corresponds to the training set, and the other columns are
            from the resamples. The index for the DataFrame is the same
            as X_test
    """
    columns = []
    for m, M in enumerate(fitted_model.flatten()):
        print(f"Predicting test-set probabilities {m}")
        columns.append(M.predict_proba(X_test)[:, 1])

    raw_probs = np.column_stack(columns)

    df = DataFrame(raw_probs)
    df.columns = [f"prob_M{m}" for m in range(len(fitted_model.Mm) + 1)]
    df.index = X_test.index
    return df

def smape(A, F):
    terms = []
    for a, f in zip(A, F):
        if a == f == 0:
            terms.append(0)
        else:
            terms.append(2 * np.abs(f - a) / (np.abs(a) + np.abs(f)))
    return (100/len(A)) * np.sum(terms)

def get_average_instability(probs):
    """
    Instability is the extend to which the bootstrapped models
    give a different prediction from the model under test. The 
    average instability is an average of the SMAPE between
    the prediction of the model-under-test and the predictions of
    each of the other bootstrap models (i.e. pairing the model-under-test)
    with a single bootstrapped model gives one SMAPE value, and 
    these are averaged over all the bootstrap models).
    
    SMAPE is preferable to mean relative error, because the latter
    diverges when the prediction from the model-under-test is very small.
    It may however be better still to use the log of the accuracy ratio;
    see https://en.wikipedia.org/wiki/Symmetric_mean_absolute_percentage_error,
    since the probabilities are all positive (or maybe there is a better 
    thing for comparing probabilities specifically)
    
    Testing: not yet tested
    """
    num_rows = probs.shape[0]
    num_cols = probs.shape[1]
    
    smape_over_bootstraps = []
    
    # Loop over each boostrap model
    for j in range(1, num_cols):
        
        # Calculate SMAPE between bootstrap model j and
        # the model-under-test
        smape_over_bootstraps.append(smape(probs[:,0], probs[:,j]))

    return np.mean(smape_over_bootstraps)

def plot_instability(ax: Axes, probs: DataFrame, y_test: Series, title="Probability stability"):
    """
    This function plots a scatter graph of one point
    per value in the test set (row of probs), where the
    x-axis is the value of the model under test (the
    first column of probs), and the y-axis is every other
    probability predicted from the bootstrapped models Mn
    (the other columns of probs). The predictions from
    the model-under-test corresponds to the straight line
    at 45 degrees through the origin

    For a stable model M0, the scattered points should be
    close to the M0 line, indicating that the bootstrapped
    models Mn broadly agree with the predictions made by M0.

    Testing: not yet tested
    """

    num_rows = probs.shape[0]
    num_cols = probs.shape[1]
    x = []
    y = []
    c = []
    for i in range(num_rows):
        for j in range(1, num_cols):
            x.append(probs.iloc[i, 0])  # Model-under-test
            y.append(probs.iloc[i, j])  # Other bootstrapped models
            c.append(y_test[i]),  # What was the actual outcome

    colour_map = {0: "g", 1: "r"}

    for outcome_to_plot, colour in colour_map.items():
       x_to_plot = [x for x, outcome in zip(x, c) if outcome == outcome_to_plot]
       y_to_plot = [y for y, outcome in zip(y, c) if outcome == outcome_to_plot]
       ax.scatter(x_to_plot, y_to_plot, c=colour, s=1, marker=".")

    ax.axline([0, 0], [1, 1])

    # You can restrict the axes here if you want
    #ax.set_xlim(0, 0.1)
    #ax.set_ylim(0,0.1)

    ax.legend(
        [   
            "Did not occur (background)",
            "Event occurred (foreground)",
        ],
        markerscale=15
    )
    ax.set_title(title)
    ax.set_xlabel("Prediction from model-under-test")
    ax.set_ylabel("Bootstrap model predictions")
    