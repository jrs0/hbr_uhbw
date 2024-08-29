import argparse
import numpy as np

def plot_permutation_importance(ax, feature_importances, config, model_name):
    result = feature_importances["result"]
    names = feature_importances["names"]
    perm_sorted_idx = result.importances_mean.argsort()

    # Map feature names based on config file (default to column name)
    real_names = np.array([config["features"].get(name, { "text": name })["text"] for name in names])

    ax.boxplot(
        result.importances[perm_sorted_idx][-10:,:].T,
        vert=False,
        labels=real_names[perm_sorted_idx][-10:],
    )
    ax.axvline(x=0, color="k", linestyle="--")
    
    ax.set_xlabel("Decrease in ROC AUC by permuting feature")
    ax.set_ylabel("Feature name")
    ax.set_title(f"For {model_name}")
    return ax

def main():

    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser("make-results")
    parser.add_argument(
        "-f",
        "--config-file",
        required=True,
        help="Specify the config file describing the model files that exist",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Specify which model to plot results. The model is plotted, and no results or summary table is saved",
    )
    args = parser.parse_args()

    from pathlib import Path
    import pandas as pd
    import matplotlib.pyplot as plt
    import scipy
    import yaml

    from pyhbr import common
    from pyhbr.analysis import roc
    from pyhbr.analysis import stability
    from pyhbr.analysis import calibration
    from pyhbr.analysis import describe
    from pyhbr.analysis import model

    import importlib

    importlib.reload(stability)
    importlib.reload(common)
    importlib.reload(roc)
    importlib.reload(describe)

    # Read the configuration file
    with open(args.config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Failed to load config file: {exc}")
            exit(1)

    # Set the aspect ratio for the figures to roughly 2:1,
    # because each plot is two graphs side-by-side
    figsize = (11, 5)

    # This is used to load a file, and is also used
    # as the prefix for all saved data files.
    analysis_name = config["analysis_name"]

    # Load one model or all models
    if args.model is not None:
        model_name = args.model

        if model_name not in config["models"]:
            print(
                f"Error: requested model {model_name} is not present in config file {args.config}"
            )
            exit(1)
            
        model_data, _ = common.load_item(f"{analysis_name}_{model_name}", save_dir=config["save_dir"])   
        models = { model_name: model_data }
        
    else:
        
        # Load all the models into memory
        models = {}
        for model in config["models"].keys():
            models[model], _ = common.load_item(f"{analysis_name}_{model}", save_dir=config["save_dir"])


    # Loop over all the models creating the output graphs
    for model_name, model_data in models.items():

        # These levels will define high risk for bleeding and ischaemia
        #
        # Various options are available for choosing this risk level:
        #
        # 1. Using established thresholds from the literature. For high
        #    bleeding risk, one such threshold is 4%, defined by the ARC
        #    HBR definition. (Need to find a similar concensus threshold
        #    for ischaemia risk.)
        # 2. Use the outcome prevalence in the training set. This would
        #    be an estimate of the observed average risk across the whole
        #    sample
        #
        # Currently option 2 is used below
        bleeding_threshold = model_data["y_test"]["bleeding"].mean()
        ischaemia_threshold = model_data["y_test"]["ischaemia"].mean()
        high_risk_thresholds = {
            "bleeding": bleeding_threshold,
            "ischaemia": ischaemia_threshold,
        }

        # Get the model
        fit_results = model_data["fit_results"]
        y_test = model_data["y_test"]
        
        model_abbr = config["models"][model_name]["abbr"]
        bleeding_abbr = config["outcomes"]["bleeding"]["abbr"]
        ischaemia_abbr = config["outcomes"]["ischaemia"]["abbr"]

        # Print the feature importances
        pd.set_option('display.max_rows', 500)
        print("Bleeding feature importance")
        print(fit_results["feature_importances"]["bleeding"])
        print("Ischaemia feature importance")
        print(fit_results["feature_importances"]["ischaemia"])
        
        # Make a plot of feature importances
        fig, ax = plt.subplots(1, 2, figsize=figsize)
        for n, outcome in enumerate(["bleeding", "ischaemia"]):
            outcome_abbr = config["outcomes"][outcome]["abbr"]
            model_name = f"{model_abbr}-{outcome_abbr}"
            plot_permutation_importance(ax[n], fit_results["feature_importances"][outcome], config, model_name)
           
        fig.suptitle("Top ten most important features by permutation importance")
        plt.tight_layout()
           
        if args.model is not None:
            # Plot only
            plt.show()
        else:
            plt.savefig(
                common.make_new_save_item_path(
                    f"{analysis_name}_{model_name}_feature_importance", config["save_dir"], "png"
                )
            )
        plt.close()

        # Plot the ROC curves for the models
        fig, ax = plt.subplots(1, 2, figsize=figsize)
        for n, outcome in enumerate(["bleeding", "ischaemia"]):
            title = f"{outcome.title()} ROC Curves"
            roc_curves = fit_results["roc_curves"][outcome]
            roc_aucs = fit_results["roc_aucs"][outcome]
            roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
        plt.suptitle(
            f"ROC Curves for Models {model_abbr}-{bleeding_abbr} and {model_abbr}-{ischaemia_abbr}"
        )
        plt.tight_layout()
        
        if args.model is not None:
            # Plot only
            plt.show()
        else:
            plt.savefig(
                common.make_new_save_item_path(
                    f"{analysis_name}_{model_name}_roc", config["save_dir"], "png"
                )
            )
        plt.close()

        for outcome in ["bleeding", "ischaemia"]:

            outcome_abbr = config["outcomes"][outcome]["abbr"]

            # Plot the stability
            fig, ax = plt.subplots(1, 2, figsize=figsize)
            probs = fit_results["probs"]
            stability.plot_stability_analysis(
                ax, outcome, probs, y_test, high_risk_thresholds
            )
            plt.suptitle(
                f"Stability of {outcome.title()} Model {model_abbr}-{outcome_abbr}"
            )
            plt.tight_layout()
            
            if args.model is not None:
                # Plot only
                plt.show()
            else:            
                plt.savefig(
                    common.make_new_save_item_path(
                        f"{analysis_name}_{model_name}_stability_{outcome}", config["save_dir"], "png"
                    )
                )
            plt.close() # to save memory

            # Plot the calibrations
            fig, ax = plt.subplots(1, 2, figsize=figsize)
            calibrations = fit_results["calibrations"]
            calibration.plot_calibration_curves(ax[0], calibrations[outcome])
            calibration.draw_calibration_confidence(ax[1], calibrations[outcome][0])
            plt.suptitle(
                f"Calibration of {outcome.title()} Model {model_abbr}-{outcome_abbr}"
            )
            plt.tight_layout()
            
            if args.model is not None:
                # Plot only
                plt.show()
            else:
                plt.savefig(
                    common.make_new_save_item_path(
                        f"{analysis_name}_{model_name}_calibration_{outcome}", config["save_dir"], "png"
                    )
                )
            plt.close() # to save memory

    # Only create the model summary table if not plotting a single model
    if args.model is None:

        # Get the table of model summary metrics
        summary = describe.get_summary_table(models, high_risk_thresholds, config)
        common.save_item(summary, f"{analysis_name}_summary", config["save_dir"])

        # Get the table of outcome prevalences
        data, data_path = common.load_item(f"{analysis_name}_data", save_dir=config["save_dir"])
        outcome_prevalences = describe.get_outcome_prevalence(data["outcomes"])
        common.save_item(outcome_prevalences, f"{analysis_name}_outcome_prevalences", save_dir=config["save_dir"])
