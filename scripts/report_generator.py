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


def copy_most_recent_file(
    name: str, extension: str, save_dir: str, report_dir: Path, dest_dir: Path
) -> Path:
    """Find the most recent file with the given name and copy it to the destination

    Args:
        name: The base name of the file to copy
        extension: The file extension of the file to copy
        save_dir: The directory in which to locate the file
            to copy
        report_dir: The path to the report output directory relative to
            the working directory
        dest_dir: The destination directory name in which to place the file
            relative to the report directory

    Returns:
        The path to the copied item, relative to the report directory.
            This can be used as a string in the report to locate the item.
    """
    src_path = common.pick_most_recent_saved_file(name, save_dir, extension)
    
    # Create the destination directory if it does not exist
    (report_dir / dest_dir).mkdir(parents=True, exist_ok=True)
    
    dest_path = report_dir / dest_dir / src_path.name
    shutil.copy(src_path, dest_path)
    return dest_dir / src_path.name


# Copy the summary table into the report directory
variables["summary_table_file"] = copy_most_recent_file(
    "icb_basic_summary", "pkl", save_dir, report_dir, Path("tables")
)

# Get the table of outcome prevalences
variables["outcome_prevalences_file"] = copy_most_recent_file(
    "icb_basic_outcome_prevalences", "pkl", save_dir, report_dir, Path("tables")
)

# For reference
variables["data_file"] = copy_most_recent_file(
    "icb_basic_data", "pkl", save_dir, report_dir, Path("tables")
)

# Load the data (this is the same file copied above)
data = common.load_item("icb_basic_data", save_dir=save_dir)
variables["index_start"] = data["icb_basic_tmp"]["index_start"]
variables["index_end"] = data["icb_basic_tmp"]["index_end_date"]
variables["num_index_spells"] = len(data["icb_basic_tmp"]["index_spells"])

# Copy the most recent version of each figure into the
# build directory
for name, model in variables["models"].items():

    # Copy the model file
    model["file"] = copy_most_recent_file(
        f"icb_basic_{name}", "pkl", save_dir, report_dir, Path("models")
    )
    
    # Save the test set proportion (every model is the same,
    # so overwriting is fine)
    model_data = common.load_item(f"icb_basic_{name}", save_dir=save_dir)
    variables["test_proportion"] = model_data["config"]["test_proportion"]

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
shutil.copy(config["citation_style"], report_dir / Path("style.csl"))

# Render the report template and write it to the build directory
doc = template.render(variables)
(report_dir / Path("report.qmd")).write_text(doc)

# Optionally render the quarto
if args.render:
    subprocess.run(["quarto", "render", "report.qmd"], cwd=report_dir)
