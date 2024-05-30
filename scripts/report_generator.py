## Generate the report for icb_basic (HES + SWD data)
##
##

import shutil
import subprocess
import argparse
import copy
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import yaml
from pyhbr import common

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

# Read the configuration file
with open(args.config_file) as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(f"Failed to load config file: {exc}")
        exit(1)

# Set up the Jinja2 templates
environment = Environment(loader=FileSystemLoader(config["templates_folder"]))
template = environment.get_template(config["report_template"])

# All outputs will be created inside the build folder
# relative to the current working directory
build_dir = Path(config["build_directory"])
build_dir.mkdir(parents=True, exist_ok=True)

# Make a subdirectory for this report
report_dir = build_dir / Path(config["report_subfolder"])
report_dir.mkdir(parents=True, exist_ok=True)

# Optionally clean the subfolder
if args.clean:
    shutil.rmtree(report_dir)

# Make the output folder for images in the build directory
image_dest_dir = report_dir / Path("images")
image_dest_dir.mkdir(parents=True, exist_ok=True)

# Get the path to saved data files
save_dir = Path(config["save_dir"])

# Copy the config and adjust to create Jinja2 variables
variables = copy.deepcopy(config)
variables["bib_file"] = "ref.bib"


def copy_most_recent_image(image_name: str) -> Path:
    """Find the most recent image with the given name and copy it to the build directory.

    NOTE: uses image_dest_dir from outer scope

    Args:
        image_name: The image base name

    Returns:
        The path of the image relative to the project build subfolder
            that can be referenced in the report.
    """
    image_path = common.pick_most_recent_saved_file(image_name, save_dir, "png")
    image_file_name = image_path.name
    shutil.copy(image_path, image_dest_dir / image_file_name)
    return Path("images") / image_file_name

# Copy the summary table into the report directory
summary_path = common.pick_most_recent_saved_file("icb_basic_summary", save_dir)
shutil.copy(summary_path, report_dir / summary_path.name)
variables["summary_table_file"] = summary_path.name

# Copy the most recent version of each figure into the
# build directory
for name, model in variables["models"].items():

    # ROC curves
    model["roc_curves_image"] = copy_most_recent_image(f"icb_basic_{name}_roc")

    plots = ["stability", "calibration"]
    outcomes = ["bleeding", "ischaemia"]
    for outcome in outcomes:
        for plot in plots:
            model[f"{plot}_{outcome}_image"] = copy_most_recent_image(
                f"icb_basic_{name}_{plot}_{outcome}"
            )

# Copy static files to output folder
shutil.copy(config["bib_file"], report_dir / Path("ref.bib"))

# Render the report template and write it to the build directory
doc = template.render(variables)
(report_dir / Path("report.qmd")).write_text(doc)

# Optionally render the quarto
if args.render:
    subprocess.run(["quarto", "render", "report.qmd"], cwd=report_dir)
