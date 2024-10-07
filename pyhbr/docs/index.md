# Welcome to the PyHBR Docs

This python package contains tools relating to estimating the risk of bleeding/ischaemia risk in cardiology patients. The main content of the package is a set of scripts for generating a report containing models of bleeding and ischaemia risk.

## Obtaining the code

The code for the python package `pyhbr` is available at [this GitHub repository](https://github.com/jrs0/hbr_uhbw), and the repository also contains the folder required for generating the report (not part of the Python package). The folder containing the report template is called `report`.

After setting up a python environment (on Windows, install Python [here](from https://www.python.org/downloads/) -- you do not need admin rights), you can download `pyhbr` either from Pip using `pip install pyhbr`, or from the git repository directly if you want to make changes to the package. In that case, read the instructions in the [README](https://github.com/jrs0/hbr_uhbw/tree/main/pyhbr).

To test that `pyhbr` is installed, open a console (i.e. a terminal, not an interactive Python prompt), and run `fetch-data -h`. If this produces a help message (instead of something like `command not found`) then `pyhbr` is installed correctly.

A separate program is used to create files of ICD-10 and OPCS-4 code groups (with names like `icd10.yaml` and `opcs4.yaml`). This program is contained in a [GitHub repository](https://github.com/jrs0/hbr_models) under the `codes_editor` folder, and the program is available to download from the [releases](https://github.com/jrs0/hbr_models/releases/tag/codes-editor-v0.1.0) page.

## Running the code

The models are run using five scripts: 

* `fetch-data`, which fetches tables from the database and extracts index events, outcomes, and features.
* `plot-describe`, which creates descriptive plots of the data (including features and outcomes).
* `run-model`, which fits a primary model for bleeding and ischaemia and other bootstrap models for stability.
* `make-results`, which takes the fitted models and creates plots of model fit, stability and calibration
* `generate-report`, which creates a Quarto report in source code form containing the figures and results generated from the other scripts. If you have Quarto installed, this script can also render the report into PDF and Word format.

All scripts take a flag `-h` for help, which shows other flags, and all scripts require a YAML config file passed using `-f`. In the `report` folder, this file is called `icb_hic.yaml` and contains all the settings required to generate the models/report.

All data and results are saved into a folder referred to as `save_dir`, which is set to `save_data`. All datasets, models, figures and other results will be stored in this folder, which should be gitignored. Items are saved with a timestamp and a git commit if the scripts are run from inside a git repository.
