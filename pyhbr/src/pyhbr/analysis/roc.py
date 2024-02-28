"""ROC Curves

The file calculates the ROC curves of the bootstrapped
models (for assessing ROC curve stability; see stability.py).
"""

import numpy as np
from sklearn.metrics import roc_curve, roc_auc_score
from pandas import DataFrame, Series


def get_roc_curves(probs: DataFrame, y_test: Series) -> list[DataFrame]:
    """Get the ROC curves for the fitted models
    
    Get the ROC curves for all models (whose probability
    predictions for the positive class are columns of probs) based
    on the outcomes in y_test. Rows of y_test correspond to rows of
    probs. The result is a list of pairs, one for each model (column
    of probs). Each pair contains the vector of x- and y-coordinates
    of the ROC curve.
    
    Args:
        probs: The probabilities predicted by all the fitted models.
            The first column is the model-under-test (the training set),
            and the other columns are resamples of the training set.
        y_test: The outcome data corresponding to each row of probs.
        
    Returns:
        A list of DataFrames, each of which contains one ROC curve,
            corresponding to the columns in probs. The columns of the
            DataFrames are `fpr` (false positive rate) and `tpr` (true
            positive rate)
    """
    curves = []
    for n in range(probs.shape[1]):
        fpr, tpr, _ = roc_curve(y_test, probs.iloc[:, n])
        curves.append((fpr, tpr))
    return curves

@dataclass
class AucData:
    model_under_test_auc: float
    resample_auc: list[float]
    
    def mean_resample_auc(self) -> float:
        """Get the mean of the resampled AUCs
        """
        return np.mean(self.resample_auc)
    
    def std_dev_resample_auc(self) -> float:
        """Get the standard deviation of the resampled AUCs
        """
        return np.mean(self.resample_auc)

def get_auc(probs: DataFrame, y_test: Series) -> AucData:
    """Get the area under the ROC curves for the fitted models
    
    Compute area under the ROC curve (AUC) for the model-under-test
    (the first column of probs), and the other bootstrapped models
    (other columns of probs).

    """
    model_under_test_auc = roc_auc_score(y_test, probs.iloc[:,0]) # Model-under test
    resample_auc = []
    for column in probs:
        resample_auc.append(roc_auc_score(y_test, probs[column]))
    return AucData(model_under_test_auc, resample_auc)

def plot_roc_curves(ax, curves, auc, title = "ROC-stability Curves"):
    """Plot ROC curves of the model-under-test and resampled models
    
    Plot the set of bootstrapped ROC curves (an instability plot),
    using the data in curves (a list of curves to plot). Assume that the
    first curve is the model-under-test (which is coloured differently).

    The auc argument is an array where the first element is the AUC of the
    model under test, and the second element is the mean AUC of the
    bootstrapped models, and the third element is the standard deviation
    of the AUC of the bootstrapped models (these latter two measure
    stability). This argument is the output from get_bootstrapped_auc.
    """
    mut_curve = curves[0]  # model-under-test
    ax.plot(mut_curve[0], mut_curve[1], color="r")
    for curve in curves[1:]:
        ax.plot(curve[0], curve[1], color="b", linewidth=0.3, alpha=0.4)
    ax.axline([0, 0], [1, 1], color="k", linestyle="--")
    ax.legend(
        [
            f"Model (AUC = {auc[0]:.2f})",
            f"Bootstrapped models",
        ]
    )
    ax.set_title(title)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
