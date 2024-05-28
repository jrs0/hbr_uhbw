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

# Provide the option to render the quarto
parser = argparse.ArgumentParser("report_generator")
parser.add_argument("-f", "--config-file", required=True, help="Specify the config file describing the report")
parser.add_argument("-r", "--render", help="Render the auto-generated quarto report", action="store_true")
parser.add_argument("-c", "--clean", help="Remove the build directory for this report", action="store_true")
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

# Set the directory for storing images
image_source_dir = Path(config["image_source_dir"])
image_dest_dir = report_dir / Path("images")
image_dest_dir.mkdir(parents=True, exist_ok=True)

# Copy the config and adjust to create Jinja2 variables
variables = copy.deepcopy(config)
variables["bib_file"] = "ref.bib"

# Copy images to the build folder. 
for name, model in variables["models"].items():
    
    # ROC curves
    roc_image = Path(f"roc_{name}.png")
    shutil.copy(image_source_dir / roc_image, image_dest_dir / roc_image)
    model["roc_curves_image"] = Path("images") / roc_image

# Copy static files to output folder
shutil.copy(config["bib_file"], report_dir / Path("ref.bib"))

# Render the report template and write it to the build directory
doc = template.render(variables)
(report_dir / Path("report.qmd")).write_text(doc)

# Optionally render the quarto
if args.render:
    subprocess.run(["quarto", "render", "report.qmd"], cwd=report_dir)