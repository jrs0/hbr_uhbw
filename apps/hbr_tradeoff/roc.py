import streamlit as st
import matplotlib.pyplot as plt
import utils

def show_roc_expander(accuracy: dict[str, float]):
    """Show what ROC curve would achieve the model accuracy input by the user
    
    Args:
        accuracy: The output dictionary from inputs.model_accuracy(), containing
            the true positive/negative rates for the outcomes
    
    """
    
    # Get the variables for convenience (should be renamed to match
    # dictionary keys).
    q_b_tpr = accuracy["tpr_b"]
    q_b_tnr = accuracy["tnr_b"]
    q_i_tpr = accuracy["tpr_i"]
    q_i_tnr = accuracy["tnr_i"]
    
    roc_expander = st.expander(
        "**What ROC Curve would achieve this accuracy?**", expanded=False
    )

    roc_container = roc_expander.container(border=True)
    roc_container.header("Required ROC Curves", divider=True)
    roc_container.write(
        "The ROC curve is a plot of true-positive rate on the y-axis against false-positive rate on the x-axis, for various thresholds that might be used to decide that a patient is high risk."
    )
    roc_container.write(
        "The accuracy specification above determines a single coordinate on this plot, which the ROC curve must pass though if the model is to have the required accuracy. Better models will require the ROC curve to pass through a point near the top-left corner."
    )
    roc_container.write(
        "The area under the ROC curve (AUC) is only relevant insofar as a ROC curve passing through a point near the top-left corner will likely have a high AUC."
    )
    roc_container.write(
        "Below, two hypothetical ROC curves are plotted (one for the bleeding model and one for the ischaemia model), which pass through the required points."
    )

    fig, ax = plt.subplots()

    # Plot baseline
    ax.plot([0.0, 100], [0.0, 100], "--")

    # Bleeding model ROC
    data = {"x": [0.0, 100 * (1 - q_b_tnr), 100.0], "y": [0.0, 100 * q_b_tpr, 100.0]}
    auc = utils.simple_auc(q_b_tpr, q_b_tnr)
    ax.plot(data["x"], data["y"], color="r", label=f"Bleeding model (AUC > {auc:.2f})")
    ax.fill_between(data["x"], data["y"], [0.0] * 3, color="r", alpha=0.05)

    # Ischaemia model ROC
    data = {"x": [0.0, 100 * (1 - q_i_tnr), 100.0], "y": [0.0, 100 * q_i_tpr, 100.0]}
    auc = utils.simple_auc(q_i_tpr, q_i_tnr)
    ax.plot(data["x"], data["y"], color="b", label=f"Ischaemia model (AUC > {auc:.2f})")
    ax.fill_between(data["x"], data["y"], [0.0] * 3, color="b", alpha=0.05)

    ax.set_xlabel("False-positive rate (%)")
    ax.set_ylabel("True-positive rate (%)")
    ax.set_title("Bleeding Model")
    ax.legend(loc="lower right")

    roc_container.pyplot(fig)
    roc_container.write(
        "The ROC AUC is calculated for the minimum convex shapes that pass through the required point. A more realistic ROC curve that passes through the point would likely have a slightly higher area, due to the extra curvature in the straight segments."
    )