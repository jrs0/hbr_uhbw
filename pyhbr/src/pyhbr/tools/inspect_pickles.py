"""Detailed inspection script to reveal the structure of model pickle files
and locate feature importances and feature names.
"""

import argparse
import pickle
from pathlib import Path
import numpy as np
import pandas as pd


def inspect_object(obj, name="obj", indent=0):
    """Print class info and key properties of an object."""
    prefix = " " * indent
    obj_type = f"{type(obj).__module__}.{type(obj).__qualname__}"
    print(f"{prefix}📌 {name}: {obj_type}")

    # If it's a pandas DataFrame or Series
    if isinstance(obj, (pd.DataFrame, pd.Series)):
        print(f"{prefix}   Shape: {obj.shape}")
        print(f"{prefix}   Columns/Index sample: {list(obj.columns if isinstance(obj, pd.DataFrame) else obj.index)[:5]}")
        print(f"{prefix}   Head:\n{obj.head(2)}")
        return

    # If it's a list or tuple
    if isinstance(obj, (list, tuple)):
        print(f"{prefix}   Length: {len(obj)}")
        for idx, item in enumerate(obj[:2]):  # Inspect first 2 items
            inspect_object(item, f"{name}[{idx}]", indent + 3)
        if len(obj) > 2:
            print(f"{prefix}   ... ({len(obj) - 2} more items)")
        return

    # If it's a dictionary
    if isinstance(obj, dict):
        print(f"{prefix}   Keys ({len(obj)}): {list(obj.keys())}")
        for k, v in obj.items():
            if k in ["fit_results", "fitted_models", "feature_importances", "model", "config"]:
                inspect_object(v, f"{name}['{k}']", indent + 3)
            else:
                print(f"{prefix}   ['{k}']: {type(v).__module__}.{type(v).__qualname__}")
        return

    # Check specific attributes on estimator / pipeline objects
    interesting_attrs = [
        "best_estimator_",
        "estimator",
        "model",
        "pipeline",
        "fitted_model",
        "clf",
        "named_steps",
        "steps",
        "feature_importances_",
        "coef_",
        "get_feature_names_out",
        "feature_names_in_",
    ]

    found = [a for a in interesting_attrs if hasattr(obj, a)]
    if found:
        print(f"{prefix}   Attributes found: {found}")

    # Inspect pipeline steps if present
    if hasattr(obj, "named_steps"):
        print(f"{prefix}   Pipeline Steps: {list(obj.named_steps.keys())}")
        for step_name, step_obj in obj.named_steps.items():
            inspect_object(step_obj, f"{name}.named_steps['{step_name}']", indent + 3)

    # Inspect underlying estimator inside SearchCV / wrappers
    for attr in ["best_estimator_", "model", "estimator", "pipeline", "clf"]:
        if hasattr(obj, attr) and getattr(obj, attr) is not obj and getattr(obj, attr) is not None:
            child = getattr(obj, attr)
            inspect_object(child, f"{name}.{attr}", indent + 3)

    # Report feature importance data if directly present
    if hasattr(obj, "feature_importances_"):
        imp = getattr(obj, "feature_importances_")
        print(f"{prefix}   ⭐ `feature_importances_` found! Shape: {np.shape(imp)}, Sample: {np.array(imp)[:3]}")

    if hasattr(obj, "coef_"):
        coef = getattr(obj, "coef_")
        print(f"{prefix}   ⭐ `coef_` found! Shape: {np.shape(coef)}, Sample: {np.array(coef)[:3]}")

    if hasattr(obj, "get_feature_names_out"):
        try:
            names = obj.get_feature_names_out()
            print(f"{prefix}   ⭐ `get_feature_names_out()` produced {len(names)} names (e.g. {names[:3]})")
        except Exception as e:
            print(f"{prefix}   ⚠️ `get_feature_names_out()` failed with error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Inspect model pickle file structures")
    parser.add_argument("-f", "--file", required=True, help="Path to a model .pkl file")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        return

    print("=" * 80)
    print(f"INSPECTING: {file_path}")
    print("=" * 80)

    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)
    except Exception as e:
        print(f"Failed to load pickle file: {e}")
        return

    inspect_object(data, name="model_data")

    print("\n" * 2)
    print("=" * 80)
    print("DIRECT ATTRIBUTE DIAGNOSTIC SUMMARY")
    print("=" * 80)

    # Output exact python code hints for reading this file structure
    if isinstance(data, dict):
        fit_results = data.get("fit_results", {})
        fitted_models = fit_results.get("fitted_models") or data.get("fitted_models")

        print(f"- Top-level dictionary keys: {list(data.keys())}")
        if isinstance(fit_results, dict):
            print(f"- fit_results keys: {list(fit_results.keys())}")

        if fitted_models is not None:
            print(f"- fitted_models container type: {type(fitted_models)}")
            if isinstance(fitted_models, (list, tuple)) and len(fitted_models) > 0:
                first = fitted_models[0]
                print(f"- Class of fitted_models[0]: {type(first)}")
                print(f"- Attributes on fitted_models[0]: {[a for a in dir(first) if not a.startswith('_')]}")
            elif isinstance(fitted_models, dict):
                print(f"- Keys in fitted_models dict: {list(fitted_models.keys())}")
                for k, v in fitted_models.items():
                    print(f"  - Key '{k}': {type(v)}")
                    print(f"    Attributes: {[a for a in dir(v) if not a.startswith('_')]}")


if __name__ == "__main__":
    main()
