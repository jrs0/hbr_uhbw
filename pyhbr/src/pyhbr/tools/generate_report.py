"""Generate the report folder from a config file and model data
"""

import argparse


def main():

    # Provide the option to render the quarto
    parser = argparse.ArgumentParser("report_generator")
    parser.add_argument(
        "-f",
        "--config-file",
        required=True,
        help="Specify the config file describing the report",
    )
    parser.add_argument(
        "-r",
        "--render",
        help="Render the auto-generated quarto report",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--clean",
        help="Remove the build directory for this report",
        action="store_true",
    )
    args = parser.parse_args()

    # Import packages here to avoid delay on help menu
    import shutil
    import subprocess
    import copy
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    import yaml
    import pickle
    from pyhbr import common
    import pandas as pd
    import numpy as np
    from loguru import logger as log

    # Read the configuration file
    with open(args.config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Failed to load config file: {exc}")
            exit(1)

    # ------------------------------------------------------------------
    # Robust Feature Importance Extraction Helper
    # ------------------------------------------------------------------
    def extract_top_features_from_model_data(
        model_data, outcome=None, feature_config=None, top_n=3
    ) -> str:
        """Extract top N features directly from model_data dict structure."""
        if not isinstance(model_data, dict):
            return "N/A"

        fit_results = model_data.get("fit_results", {})
        feat_imp = fit_results.get("feature_importances")
        df_imp = None

        if isinstance(feat_imp, dict) and feat_imp:
            # Select target outcome dictionary
            if outcome and outcome in feat_imp:
                imp_dict = feat_imp[outcome]
            elif outcome is None and len(feat_imp) > 0:
                first_val = next(iter(feat_imp.values()))
                imp_dict = first_val if isinstance(first_val, dict) else feat_imp
            else:
                imp_dict = feat_imp

            if isinstance(imp_dict, dict) and imp_dict:
                names = None
                values = None

                # Locate feature name key
                for k, v in imp_dict.items():
                    k_str = str(k).lower()
                    if k_str in [
                        "names",
                        "name",
                        "features",
                        "feature",
                        "columns",
                        "column",
                    ]:
                        names = v
                        break

                # Locate feature importance/values key
                for k, v in imp_dict.items():
                    k_str = str(k).lower()
                    if k_str in [
                        "result",
                        "results",
                        "importances",
                        "importance",
                        "scores",
                        "values",
                        "val",
                    ]:
                        values = v
                        break

                # Unnest dictionary values if present (e.g. {'mean': [...], ...})
                if isinstance(values, dict):
                    for sub_k in [
                        "mean",
                        "median",
                        "importance",
                        "result",
                        "val",
                        "values",
                    ]:
                        if sub_k in values:
                            values = values[sub_k]
                            break
                    else:
                        values = next(iter(values.values()))

                if names is not None and values is not None:
                    try:
                        names_list = [str(n) for n in names]
                        val_arr = np.asarray(values)

                        # Handle object arrays or nested lists
                        if val_arr.dtype == object:
                            val_arr = np.array(
                                [
                                    np.nanmean(x)
                                    if hasattr(x, "__len__")
                                    else float(x)
                                    for x in val_arr
                                ]
                            )

                        # Aggregate multidimensional arrays (bootstraps/folds)
                        while val_arr.ndim > 1:
                            axis_match = [
                                i
                                for i, s in enumerate(val_arr.shape)
                                if s == len(names_list)
                            ]
                            if axis_match:
                                target_axis = axis_match[0]
                                axes_to_mean = tuple(
                                    i
                                    for i in range(val_arr.ndim)
                                    if i != target_axis
                                )
                                val_arr = np.nanmean(
                                    val_arr, axis=axes_to_mean
                                )
                            else:
                                val_arr = np.nanmean(val_arr, axis=0)

                        min_len = min(len(val_arr), len(names_list))
                        if min_len > 0:
                            df_imp = pd.DataFrame(
                                {
                                    "column": names_list[:min_len],
                                    "feature_importances": val_arr[:min_len],
                                }
                            )
                    except Exception:
                        df_imp = None

                # Fallback: key-value pairs where keys are feature names
                if df_imp is None or df_imp.empty:
                    kv_pairs = []
                    for k, v in imp_dict.items():
                        if str(k).lower() not in [
                            "names",
                            "name",
                            "result",
                            "results",
                            "features",
                            "importances",
                        ]:
                            try:
                                val_num = (
                                    np.nanmean(v)
                                    if hasattr(v, "__len__")
                                    else float(v)
                                )
                                kv_pairs.append((str(k), val_num))
                            except Exception:
                                pass
                    if kv_pairs:
                        df_imp = pd.DataFrame(
                            kv_pairs, columns=["column", "feature_importances"]
                        )

        # Fallback 2: Extract directly from FittedModel estimator object
        if (df_imp is None or df_imp.empty) and "fitted_models" in fit_results:
            try:
                fitted_container = fit_results["fitted_models"]
                fm = (
                    fitted_container.get(outcome)
                    if isinstance(fitted_container, dict)
                    else None
                )
                if fm is not None:
                    estimator = getattr(fm, "M0", None) or getattr(
                        fm, "Mm", None
                    )
                    if estimator is not None:
                        if hasattr(estimator, "named_steps"):
                            estimator = list(estimator.named_steps.values())[-1]
                        importances = getattr(
                            estimator,
                            "feature_importances_",
                            getattr(estimator, "coef_", None),
                        )
                        if importances is not None:
                            importances = np.asarray(importances)
                            if importances.ndim > 1:
                                importances = np.nanmean(importances, axis=0)
                            feature_names = getattr(
                                model_data.get("X_train"), "columns", None
                            )
                            if feature_names is None:
                                feature_names = [
                                    f"Feature_{i}"
                                    for i in range(len(importances))
                                ]
                            df_imp = pd.DataFrame(
                                {
                                    "column": list(feature_names),
                                    "feature_importances": importances,
                                }
                            )
            except Exception:
                pass

        if df_imp is None or df_imp.empty:
            return "N/A"

        # Coerce to numeric values
        df_imp["feature_importances"] = pd.to_numeric(
            df_imp["feature_importances"], errors="coerce"
        ).fillna(0)

        # Normalize relative magnitude (handles signed coefficients and tree importances)
        df_imp["abs_imp"] = df_imp["feature_importances"].abs()
        total_imp = df_imp["abs_imp"].sum()

        if total_imp > 0:
            df_imp["normalized_imp"] = df_imp["abs_imp"] / total_imp
        else:
            df_imp["normalized_imp"] = 0

        df_imp = df_imp.sort_values("normalized_imp", ascending=False)

        # Clean transformer prefixes (e.g., 'num__age' -> 'age')
        df_imp["clean_column"] = df_imp["column"].apply(
            lambda x: str(x).split("__")[-1]
        )

        # Map to human-readable names from config if available
        if feature_config:
            df_imp["readable_name"] = df_imp["clean_column"].apply(
                lambda x: feature_config.get(x, {}).get("text", x)
                if isinstance(feature_config.get(x), dict)
                else x
            )
        else:
            df_imp["readable_name"] = df_imp["clean_column"]

        top_df = df_imp.head(top_n)
        formatted_items = []
        for _, row in top_df.iterrows():
            feat_name = row["readable_name"]
            pct = row["normalized_imp"] * 100
            formatted_items.append(f"{feat_name} ({pct:.1f}%)")

        if len(formatted_items) > 1:
            return ", ".join(formatted_items[:-1]) + f", and {formatted_items[-1]}"
        return formatted_items[0] if formatted_items else "N/A"

    # Load the config file
    config = common.read_config_file(args.config_file)
    analysis_name = config["analysis_name"]
    save_dir = config["save_dir"]
    now = common.current_timestamp()

    # Set up the log file output
    log_file = (
        Path(save_dir) / Path(analysis_name + f"_generate_report_{now}")
    ).with_suffix(".log")
    log_format = "{time} {level} {message}"
    log_id = log.add(log_file, format=log_format)

    # Load data files
    data, raw_data, data_path = common.load_most_recent_data_files(
        analysis_name, save_dir
    )

    build_dir = Path(config["build_directory"])
    build_dir.mkdir(parents=True, exist_ok=True)

    report_dir = build_dir / Path(f"{analysis_name}_report")
    report_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        shutil.rmtree(report_dir)

    image_dest_dir = report_dir / Path("images")
    image_dest_dir.mkdir(parents=True, exist_ok=True)

    variables = copy.deepcopy(config)

    def copy_most_recent_image(image_name: str) -> Path:
        image_path = common.pick_most_recent_saved_file(image_name, save_dir, "png")
        image_file_name = image_path.name
        shutil.copy(image_path, image_dest_dir / image_file_name)
        return Path("images") / image_file_name

    def copy_most_recent_file(
        name: str, extension: str, save_dir: str, report_dir: Path, dest_dir: Path
    ) -> Path:
        src_path = common.pick_most_recent_saved_file(name, save_dir, extension)
        (report_dir / dest_dir).mkdir(parents=True, exist_ok=True)
        dest_path = report_dir / dest_dir / src_path.name
        shutil.copy(src_path, dest_path)
        return dest_dir / src_path.name

    summary_table, summary_table_path = common.load_item(
        f"{analysis_name}_summary", save_dir=save_dir
    )

    without_trade_off = summary_table[~summary_table["model_key"].eq("trade_off")]

    # ---------------------------------------------------------
    # BLEEDING
    # ---------------------------------------------------------
    outcome = "bleeding"
    df = without_trade_off[without_trade_off["outcome_key"].eq(outcome)]

    m_best = df[df["median_auc"].eq(df["median_auc"].max())]
    best_bleeding_key = m_best["model_key"].iloc[0]
    variables[f"best_{outcome}_model_auc"] = f"{m_best['median_auc'].iloc[0]:.2f}"
    variables[f"best_{outcome}_model_name"] = config["models"][best_bleeding_key][
        "text"
    ]

    best_b_data, _ = common.load_item(
        f"{analysis_name}_{best_bleeding_key}", save_dir=save_dir
    )
    variables[f"best_{outcome}_top_features"] = extract_top_features_from_model_data(
        best_b_data, outcome="bleeding", feature_config=config.get("features"), top_n=3
    )

    m_worst = df[df["median_auc"].eq(df["median_auc"].min())]
    variables[f"worst_{outcome}_model_auc"] = f"{m_worst['median_auc'].iloc[0]:.2f}"
    variables[f"worst_{outcome}_model_name"] = config["models"][
        m_worst["model_key"].iloc[0]
    ]["text"]

    # ---------------------------------------------------------
    # ISCHAEMIA
    # ---------------------------------------------------------
    outcome = "ischaemia"
    df = without_trade_off[without_trade_off["outcome_key"].eq(outcome)]

    m_best = df[df["median_auc"].eq(df["median_auc"].max())]
    best_ischaemia_key = m_best["model_key"].iloc[0]
    variables[f"best_{outcome}_model_auc"] = f"{m_best['median_auc'].iloc[0]:.2f}"
    variables[f"best_{outcome}_model_name"] = config["models"][best_ischaemia_key][
        "text"
    ]

    best_i_data, _ = common.load_item(
        f"{analysis_name}_{best_ischaemia_key}", save_dir=save_dir
    )
    variables[f"best_{outcome}_top_features"] = extract_top_features_from_model_data(
        best_i_data,
        outcome="ischaemia",
        feature_config=config.get("features"),
        top_n=3,
    )

    m_worst = df[df["median_auc"].eq(df["median_auc"].min())]
    variables[f"worst_{outcome}_model_auc"] = f"{m_worst['median_auc'].iloc[0]:.2f}"
    variables[f"worst_{outcome}_model_name"] = config["models"][
        m_worst["model_key"].iloc[0]
    ]["text"]

    variables["summary_table"] = summary_table.drop(
        columns=["model_key", "outcome_key", "median_auc"]
    ).to_markdown()

    variables["summary_table_file"] = copy_most_recent_file(
        f"{analysis_name}_summary", "pkl", save_dir, report_dir, Path("tables")
    )

    outcome_prevalences, outcome_prevalences_path = common.load_item(
        f"{analysis_name}_outcome_prevalences", save_dir=save_dir
    )

    variables["outcome_prevalences"] = outcome_prevalences.reset_index().to_markdown(
        index=False
    )

    features_df = pd.DataFrame.from_dict(config["features"], orient="index")
    features_df.rename(
        columns={
            "text": "Feature",
            "docs": "Description",
            "category": "Data Source",
        },
        inplace=True,
    )
    variables["features_table"] = features_df.to_markdown(index=False)

    variables["outcome_prevalences_file"] = copy_most_recent_file(
        f"{analysis_name}_outcome_prevalences",
        "pkl",
        save_dir,
        report_dir,
        Path("tables"),
    )

    variables["data_file"] = copy_most_recent_file(
        f"{analysis_name}_data", "pkl", save_dir, report_dir, Path("tables")
    )

    variables["index_start"] = raw_data["index_start"].strftime("%Y-%m-%d")
    variables["index_end"] = raw_data["index_end"].strftime("%Y-%m-%d")
    variables["num_index_spells"] = len(data["index_spells"])

    codes = raw_data["code_groups"]
    codes["group"] = codes["group"].map(variables["code_groups"])
    codes["code"] = codes["code"].str.upper()
    diagnosis_codes = (
        codes[codes["type"] == "diagnosis"][["code", "docs", "group"]]
        .rename(
            columns={
                "code": "ICD-10 Code",
                "docs": "Description",
                "group": "Code Group",
            }
        )
        .dropna()
    )
    variables["diagnosis_codes_table"] = diagnosis_codes.to_markdown(index=False)

    variables["bleeding_secondary_cutoff"] = (
        config["outcomes"]["bleeding"]["non_fatal"]["max_position"] - 1
    )
    variables["ischaemia_secondary_cutoff"] = (
        config["outcomes"]["ischaemia"]["non_fatal"]["max_position"] - 1
    )
    variables["num_features"] = len(features_df)

    variables["codes_hist_image"] = copy_most_recent_image(
        f"{analysis_name}_codes_hist"
    )
    variables["outcome_survival_image"] = copy_most_recent_image(
        f"{analysis_name}_survival"
    )
    variables["arc_survival_image"] = copy_most_recent_image(
        f"{analysis_name}_arc_survival"
    )

    # Process each model
    for name, model in variables["models"].items():

        model["file"] = copy_most_recent_file(
            f"{analysis_name}_{name}", "pkl", save_dir, report_dir, Path("models")
        )

        model_data, model_data_path = common.load_item(
            f"{analysis_name}_{name}", save_dir=save_dir
        )
        variables["test_proportion"] = model_data["config"]["test_proportion"]

        # Extract top features string for individual model
        model["top_features_text"] = extract_top_features_from_model_data(
            model_data, feature_config=config.get("features"), top_n=3
        )

        model["roc_curves_image"] = copy_most_recent_image(
            f"{analysis_name}_{name}_roc"
        )
        model["feature_importance_image"] = copy_most_recent_image(
            f"{analysis_name}_{name}_feature_importance"
        )
        model["trade_off_image"] = copy_most_recent_image(
            f"{analysis_name}_{name}_trade_off"
        )

        plots = ["stability", "calibration"]
        outcomes = ["bleeding", "ischaemia"]
        for outcome in outcomes:
            for plot in plots:
                model[f"{plot}_{outcome}_image"] = copy_most_recent_image(
                    f"{analysis_name}_{name}_{plot}_{outcome}"
                )

        bleeding_row = f"{model['abbr']}-B"
        ischaemia_row = f"{model['abbr']}-I"
        model["roc_auc_bleeding"] = summary_table.loc[bleeding_row, "ROC AUC"]
        model["roc_auc_ischaemia"] = summary_table.loc[ischaemia_row, "ROC AUC"]
        model["instability_bleeding"] = summary_table.loc[
            bleeding_row, "Spread of Instability"
        ]
        model["instability_ischaemia"] = summary_table.loc[
            ischaemia_row, "Spread of Instability"
        ]
        model["risk_uncertainty_bleeding"] = summary_table.loc[
            bleeding_row, "Estimated Risk Uncertainty"
        ]
        model["risk_uncertainty_ischaemia"] = summary_table.loc[
            ischaemia_row, "Estimated Risk Uncertainty"
        ]

    shutil.copy(config["bib_file"], report_dir / Path("ref.bib"))
    shutil.copy(config["citation_style"], report_dir / Path("style.csl"))
    shutil.copy(args.config_file, report_dir / Path("config.yaml"))

    environment = Environment(loader=FileSystemLoader(config["templates_folder"]))

    report_template = environment.get_template(config["report_template"])
    doc = report_template.render(variables)
    (report_dir / Path("report.qmd")).write_text(doc, encoding="utf-8")

    readme_template = environment.get_template("README.md")
    doc = readme_template.render(variables)
    (report_dir / Path("README.md")).write_text(doc, encoding="utf-8")

    if args.render:
        subprocess.run(["quarto", "render", "report.qmd"], cwd=report_dir)


if __name__ == "__main__":
    main()