## Generate the report for icb_basic (HES + SWD data)
##
##

import shutil
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import argparse

# Provide the option to render the quarto
parser = argparse.ArgumentParser("icb_basic_report.py")
parser.add_argument("-r", "--render", help="Render the auto-generated quarto report", action="store_true")
parser.add_argument("-c", "--clean", help="Remove the build directory for this report", action="store_true")
args = parser.parse_args()

# Set up the 
environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template("report.qmd")

# All outputs will be created inside the build folder
# relative to the current working directory
build_dir = Path("build")
build_dir.mkdir(parents=True, exist_ok=True)

# Make a subdirectory for this report
report_dir = build_dir / Path("icb_basic_report")
report_dir.mkdir(parents=True, exist_ok=True)

# Optionally clean
if args.clean:
    shutil.rmtree(report_dir)

# Set the directory for storing images
image_source_dir = Path("../figures")
image_dest_dir = report_dir / Path("images")
image_dest_dir.mkdir(parents=True, exist_ok=True)

# List the models to be included
models = {
    "random_forest": {
        "text": "random forest",
        "title": "Random Forest",
        "abbr": "RF",
    },
    "logistic_regression": {
        "text": "logistic regression",
        "title": "Logistic Regression",
        "abbr": "LR"
    },
    "xgboost": {
        "text": "XGBoost",
        "title": "XGBoost",
        "abbr": "XGB"
    }    
}

# Copy images to the build folder
for name, model in models.items():
    roc_image = Path(f"roc_{name}.png")
    shutil.copy(image_source_dir / roc_image, image_dest_dir / roc_image)
    model["roc_curves_image"] = Path("images") / roc_image

# Copy static files to output folder
shutil.copy("../risk_management_file/ref.bib", report_dir / Path("ref.bib"))

variables = {
    "title": "Bleeding/Ischaemia Risk Models",
    "subtitle": "Trained using hospital episode statistics and primary care data",
    "author": "John Scott",
    "bib_file": "ref.bib",
    "models": models
}

# Render the report template and write it to the build directory
doc = template.render(variables)
(report_dir / Path("report.qmd")).write_text(doc)

# Optionally render the quarto
if args.render:
    subprocess.run(["quarto", "render", "report.qmd"], cwd=report_dir)