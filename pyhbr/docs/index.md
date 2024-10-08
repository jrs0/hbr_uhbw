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

### `fetch-data`

The two purposes of this script are to fetch the data from the database, and process it into index events and features. The first time it is run, use:

```bash
# The -q flag runs the queries. The raw data are saved into the save_data
fetch-data -f icb_hic.yaml -q
```

The script will log to a file `icb_hic_fetch_data_sql_{timestamp}.log` for the SQL-query part, and log to `icb_hic_fetch_data_process_{timestamp}.log` for the index, features, etc.

The raw data (fetched from the SQL queries) is saved to a file `icb_hic_raw_{commit}_{timestamp}.pkl`

Passing `-q` will not stop the script processing the data into index events and features. This part is logged to the file `icb_hic_fetch_data_process_{timestamp}.log`. The main data output from the script is saved to the file `icb_hic_data_{commit}_{timestamp}.pkl`. 

On subsequent runs, to speed things up, you can run `fetch-data -f icb_hic.yaml` (without `-q`). This will load the latest raw data from the `save_data` folder instead of getting it from the SQL server.

!!! note "Extract CSV files from data"

    You can get CSV file versions of the DataFrames saved by `fetch-data` using the `get-csv` script (run `get-csv -h` for help). For example, to get tables from the `icb_hic_data_{commit}_{timestamp}.pkl` files, run `get-csv -f icb_hic.yaml -n data`. The `-n data` argument is important, and specifies what file you want to load. You only need to specify the `name` part of the file. To get this, strip off the `analysis_name` from the front (`icb_hic_` in this case, see `icb_hic.yaml`), and the commit/timestamp information (`_{commit}_{timestamp}.pkl`) from the end.
    
    If you have multiple files with different timestamps (e.g. because you ran `fetch-data` multiple times), you will be prompted interactively for which file you want to load.

    The `get-csv` script can be used to access DataFrames from any data file containing a dictionary mapping strings to DataFrames (this is most files).

The tables contained in the output data from the `fetch-data` script are:

* `index_spells`: The list of index ACS/PCI spells .
* `code_groups`: The table of diagnosis/procedure code groups defined by the `icd10.yaml` and `opcs4.yaml` files.
* `codes`: Which diagnosis/procedure codes occurred in patient episodes.
* `episodes`: Patient episodes, including age on admission and gender.
* `outcomes`: Bleeding/ischaemia fatal and non-fatal outcomes within one year (boolean).
* `non_fatal_bleeding`/`fatal_bleeding`/`non_fatal_ischaemia`/`fatal_ischaemia`: Details of the outcomes.
* `bleeding_survival`/`ischaemia_survival`: Data about when the outcomes occurred within one year
* `features_index`/`features_codes`/`features_attributes`/`features_prescriptions`/`features_measurements`/`features_secondary_prescriptions`/`features_lab`: Features derived from each dataset.
* `arc_hbr_score`: The ARC HBR score for each patient, including components.

### `plot-describe`

This script is run after the `fetch-data` script as follows:

```bash
# Plots are saved in the save_data folder
plot-describe -f icb_hic.yaml
```

A log of this script is saved to `icb_hic_plot_decsribe_{timestamp}.log`. To view the plots instead of saving them, add the `-p` flag to the line above. Each plot will be draw one after the other -- to move onto the next plot, mouse-over the plot and press `q`.

### `run-model`

The list of models to run are described under the `models` key in the `icb_hic.yaml` file. Although it is possible to run all the models at once, it is easier and quicker to run them one-at-a-time by passing the `-m` argument as follows:

```bash
run-model -f icb_hic.yaml -m logistic_regression
```

Each run of the script saves results in the `save_data` directory. The script writes to a log called `icb_hic_run_model_{timestamp}.log`. 

The model results are saved to a file called `icb_hic_{model_name}_{commit}_{timestamp}.pkl`, which stores the training and test sets (features and outcomes), and the model predictions.

Before fitting the models, the training set is resampled to create a number of bootstrap datasets (the number is configured in `icb_hic.yaml`). The model is fitted on each of these bootstrap models to assess model stability. The probabilities for bleeding and ischaemia predicted by each bootstrap model is accessible in CSV format by running:

```bash
get_csv -f icb_hic.yaml -n logistic_regression
```

The relevant DataFrames have names like `fit_results_probs_{outcome_name}`, and have one column for each bootstrap model. The first column (`prob_M0`) is the primary model, and is fitted using the original training set (not a resample of it).

The calibration and ROC curves are also available as CSV files; these are indexed by the bootstrap model (0 for the primary model, >0 for bootstraps).

### `make_results`

This script takes the output from the fitted model and plots the graphs. You can run it as follows, on a per-model basis:

```bash
# Plot the results for logistic_regression interactively
make-results -f icb_hic.yaml -m logistic_regression
```

Passing the `-m` parameter means the plots are shown interactively (cancel by pressing `q`), and not saved. It is useful to be able to switch between `run-model` and `make-results` to test the models, without having to wait for all models to run.

To save the model plots, remove the `-m` parameter. This will cause the script to loop through all the models in the `icb_hic.yaml` file, plot all the figures, and save them all in the `save_data` directory. It is necessary to have run all the models first before doing this (otherwise errors will occur due to missing model files).

### `generate-report`

This script generates the source code for a Quarto report in the `build` folder. To generate and also render the report, run:

```bash
# Use -r to render the report
generate-report -f icb_hic.yaml -r
```

To make the script faster, omit the `-r` to skip the render step. This will produce just the source code for the report, which is easier to use while modifying the report.

The report text is generated using the files inside the `template` folder. These are Jinja2 templates, which contain markup like `{{ variable }}` to replace part of the text with a variable. You can edit these files to change the text of the report.

All files used by the report are copied from the `save_data` folder to the `build` folder, so that the Quarto report is self-contained. There is no Python code inside the Quarto report, meaning it can be rendered using just Quarto without needing Python to be installed.

The rationale for generating report source code is to allow flexibility in editing the document without needing to rerun Python code. In addition, figures are referred to by file name, which contains the timestamp and commit hash when the file was generated.