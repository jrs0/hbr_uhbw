# PyHBR Design

This section describes the design of PyHBR and how the code is structured.

## Data Sources and Analysis

The package contains routines for performing data analysis and fitting models. The source data for this analysis are tables stored in Microsoft SQL Server.

In order to make the models reusable, the analysis/model code expects the tables in a particular format, which is documented for each analysis/model script. The code for analysis is in the `pyhbr.analysis` module.

The database query and data fetch is performed by separate code, which is expected to be modified to port this package to a new data source. These data collection scripts are stored in the `pyhbr.data_source` module.

A middle preprocessing layer `pyhbr.middle` is used to converted raw data from the data sources into the form expected by analysis. This helps keep the raw data sources clean (there is no need for extensive transformations in the SQL layer).

### SQL Queries

The approach taken to prepare SQL statements is to use SQLAlchemy to prepare a query, and then pass it to Pandas [read_sql](https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html) for execution. The advantage of using SQLAlchemy statements instead of raw strings in `read_sql` is the ability to construct statements using a declarative syntax (including binding parameters), and increased opportunity for error checking (which may be useful for porting the scripts to new databases).

An example of how SQL statements are built is shown below:

```python
from sqlalchemy import select
from pyhbr.common import make_engine, CheckedTable
import pandas as pd
import datetime as dt

# All interactions with the database (including building queries,
# which queries the server to check columns) needs an sqlalchemy 
# engine
engine = make_engine()

# The CheckedTable is a simple wrapper around sqlalchemy.Table,
# for the purpose of checking for missing columns. It replaces
# sqlalchemy syntax table.c.column_name with table.col("column_name")
table = CheckedTable("cv1_episodes", engine)

# The SQL statement is built up using the sqlalchemy select function.
# The declarative syntax reduces the chance of errors typing a raw
# SQL string. This line will throw an error if any of the columns are
# wrong.
stmt = select(
    table.col("subject").label("patient_id"),
    table.col("episode_identifier").label("episode_id"),
    table.col("spell_identifier").label("spell_id"),
    table.col("episode_start_time").label("episode_start"),
    table.col("episode_end_time").label("episode_end"),
).where(
    table.col("episode_start_time") >= dt.date(2000, 1, 1),
    table.col("episode_end_time") <= dt.date(2005, 1, 1)
)

# The SQL query can be printed for inspection if required,
# or for using directly in a SQL script
print(stmt)

# Otherwise, execute the query using pandas to get a dataframe
df = pd.read_sql(stmt, engine)
```

See the `pyhbr.data_source` module for more examples of functions that return the `stmt` variable for different tables.

The following are some tips for building statements using the `CheckedTable` object:

* `CheckedTable` contains the SQLAlchemy `Table` as the `table` member. This means you can use `select(table.table)` to initially fetch all the columns (useful for seeing what the table contains)
* If you need to rename a column (using `AS` in SQL), use `label`; e.g. `select(table.col("old_name").label("new_name"))`.
* Sometimes (particularly with ID columns which are typed incorrectly), it is useful to be able to cast to a different type. You can do this using `select(table.col("col_to_cast").cast(String))`. The list of generic types is provided [here](https://docs.sqlalchemy.org/en/20/core/type_basics.html#generic-camelcase-types); import the one you need using a line like `from sqlalchemy import String`.

### Middle Layer

To account for differences in data sources and the analysis, the module `pyhbr.middle` contains modules like `from_hic` which contain function that return transformed versions of the data sources more suitable for analysis.

The outputs from this layer are documented here so that it is possible to take a new data source and write a new module in `pyhbr.middle` which exposes the new data source for analysis. These tables are grouped together into classes and (where the table name is used as the attribute name) used as the argument to analysis functions. Analysis functions may not use all the columns of each table, but when a column is present it should have the name and meaning given below.

All tables are Pandas DataFrames.

#### Episodes

Most analysis is performed in terms of episodes, which correspond to individual consultant interactions within a hospital visit (called a spell). Episode information is stored in a table called `episodes`, which has the following columns:

* `episode_id` (`str`, Pandas index): uniquely identifies the episode.
* `patient_id` (`str`): the unique identifier for the patient.
* `spell_id` (`str`): identifies the spell containing the episode.
* `episode_start` (`datetime.date`): the episode start time.

!!! note
    Consider filtering the episodes table based on a date range of interest when it is fetched from the data source. This will speed up subsequent processing.

#### Codes

Episodes contain clinical code data, which lists the diagnoses made and the procedures performed in an episode. This is stored in a table called `codes`, with the following columns:

* `episode_id` (`str`): which episode contains this clinical code.
* `code` (`str`): the clinical code, all lowercase with no whitespace or dot, e.g. `i212`
* `position` (`int`): the position of the code in the episode. 1 means the primary position (e.g. for a primary diagnosis), and >1 means a secondary code. Often episodes contain 5-10 clinical codes, and the maximum number depends on the data source.
* `type` (`category`): either "diagnosis" (for ICD-10 diagnosis codes) or "procedure" (for OPCS-4 codes)
* `group` (`str`): which group contains this clinical code.

The Pandas index is a unique integer (note that `episode_id` is not unique, since a single episode can contain many codes).

!!! note

    This table only contains codes that are in a code group (i.e. the function making `codes` should filter out codes not in any group; the `group` column is not NaN). If all codes are required, make a code group "all" which contains every code. Note that codes occupy multiple rows in the `codes` table if they are in more than one group (take care when counting rows). In these cases, a duplicate code is identified by having the same `code`, `position` and `type` values, but a different group.

#### Demographics

Demographic information is stored in a table called `demographics`, which has the following columns:

* `patient_id` (`str`, Pandas index): the unique patient identifier
* `gender` (`category`): One of "male", "female", or "unknown". 

#### Laboratory Tests

Write me please

#### Prescriptions

Write me please

## Data/Model/Analysis Save Points

To support saving intermediate results of calculations, `pyhbr.common` includes two functions `save_item` and `load_item`, which save a Python object to a directory (by default `save_data/` in your working directory).

The scripts in [hbr_uhbw](https://github.com/jrs0/hbr_uhbw) use these functions to create these checkpoints:

* **Data**: After fetching data from databases or data sources and converting it into the raw format suitable for modelling or analysis. These files have `_data` in the file name. This data is then loaded again for modelling or analysis
* **Model**: After training models using the data stored in the `_data` files. These files have `_model` in the file name. This data is loaded for analysis.
* **Analysis**: After performing analysis using the `_data` or `_model` files. These files have `_analysis` in the file name. This data can be loaded and used to generate reports/outputs.

Splitting up the scripts in this way makes them easier to develop, because each of the three parts above can take quite long to run.

Multiple objects can be saved under one file by including them in a dictionary. It is up to the script to determine the format of the items being saved and loaded.

!!! warning

    By default, `save_item` puts the saved files into a directory called `save_data/` relative to your current working directory. Ensure that this is added to the .gitignore if the files contain sensitive data, to avoid committing them to your repository.

#### Saving Data

In addition to saving the item, `pyhbr.common.save_item` also includes in the file name:

* The commit hash of the git repository at the time `save_item` is called. This is intended to make it easier to reproduce the state of the repository that generated the file. By default, `save_item` requires you to commit any changes before saving a file. (The cleanest/most reproducible thing to do is commit changes, and then run a script non-interactively from the top.) If you are not using a git repository, then "nogit" is used in place of the commit hash.
* The timestamp when `save_item` was called, which is more granular than the commit hash (or useful in case you do not have a git repository).

!!! note
    You can save multiple items with the same name, because the file names will use different timestamps. By default, `load_item` will load the most recently saved file with a given name.

The `save_item` function is shown below. The simplest way to call it is `save_item(df, "my_df")`, which will save the DataFrame `df` to the directory `save_data/` using the name "my_df".

??? note "Use this function to save a Python object (e.g. a DataFrame)"

    ::: pyhbr.common.save_item
        options:
            # If the root heading is shown, then a TOC entry will be
            # present too. Set a very high heading level to hide it.
            heading_level: 100
            show_root_heading: true
            show_root_full_path: false
            show_symbol_type_heading: true
            show_root_toc_entry: false

#### Loading Data

To load a previously saved item, using `pyhbr.common.load_item`. It can be called most simply using `load_item("my_df")`, assuming you previously saved an object in the default directory (`save_data`) with the name "my_df". By default, the most recent item is loaded, but using `load_item("my_df", True)` will let you pick which file you want to load.

The function `load_item` is shown below:

??? note "Use this function to load a previously saved Python object"

    ::: pyhbr.common.load_item
        options:
            # If the root heading is shown, then a TOC entry will be
            # present too. Set a very high heading level to hide it.
            heading_level: 100
            show_root_heading: true
            show_root_full_path: false
            show_symbol_type_heading: true
            show_root_toc_entry: false


## Clinical Codes

PyHBR has functions for creating and using lists of ICD-10 and OPCS-4 codes. A prototype version of the graphical program to create the code lists was written in Tauri [here](https://github.com/jrs0/hbr_models). However, it is simpler and more portable to have the codes editor bundled in this python package, and written in python.

Users should be able to do the following things with the codes editor GUI:

* Open the GUI program, and select a blank ICD-10 or OPCS-4 codes tree to begin creating code groups.
* Create new code groups starting from the blank template.
* Search for strings within the ICD-10/OPCS-4 descriptions to make creation of groups easier.
* Save the resulting codes file to a working directory.
* Open and edit a previously saved codes file from a working directory.

Once the groups have been defined, the user should be able to perform the following actions with the code groups files:

* Import codes files from the package (i.e. predefined code groups).
* Import codes files (containing custom groups) from a working directory.
* Extract the code groups, and show which codes are in which groups.
* Use the code groups in analysis (i.e. get a Pandas DataFrame showing which codes are in which groups)

Multiple code groups are stored in a single file, which means that only two codes files are necessary: `icd10-yaml` and `opcs4.yaml`. There is no limit to the number of code groups.

Previously implemented functionality to check whether a clinical code is valid will not be implemented here, because sufficiently performant code cannot be written in pure python (and this package is intended to contain only pure Python to maximise portability).

Instead, all codes are converted to a standard "normal form" where upper-case letters are replaced with lower-case, and dots/whitespace is removed. Codes can then be compared, and most codes will match under this condition. (Codes that will not match include those with suffixes, such as dagger or asterix, or codes that contain further qualifying suffixes that are not present in the codes tree.).

### Counting Codes

Diagnosis and procedure codes can be grouped together and used as features for building models. One way to do this is to count the codes in a particular time window (for example, one year before an index event), and use that as a predictor for subsequent outcomes.

This sections describes how raw episode data is converted into this counted form in PyHBR.

#### Getting Clinical Code Data

Hospital episodes contain multiple diagnosis and procedure codes. The starting point for counting codes is using the `pyhbr.middle.*.get_clinical_codes` function, which returns a data frame with the following columns:

* `episode_id`: Which episode the code was in
* `code`: The name of the clinical code in normal form (lowercase, no whitespace/dots), e.g. "n183"
* `group`: The group containing the code. The table only contains codes that are defined in a code group, which is based on the codes files from the previous section
* `position`: The priority of the clinical code, where 1 means the primary diagnosis/procedure, and > 1 means a secondary code.
* `type`: Either "diagnosis" or "procedure" depending on the type of code.

This table does not use `episode_id` as the index because a single episode ID often has many rows.

An example of this function in `pyhbr.middle.from_hic` is:

??? note "Example function which fetches clinical codes"

    ::: pyhbr.middle.from_hic.get_clinical_codes
        options:
            # If the root heading is shown, then a TOC entry will be
            # present too. Set a very high heading level to hide it.
            heading_level: 100
            show_root_heading: true
            show_root_full_path: false
            show_symbol_type_heading: true
            show_root_toc_entry: false

#### Codes in Other Episodes Relative to a Base Episode

To count up codes that occur in a time window before or after a particular base episode, it is necessary to join together each base episode with all the other episodes for the same patient.

To do this, three tables are needed:

* `base_episodes`: A table of the base episodes of interest, containing `episode_id` as an index.
* `episodes`: A table of episode information (all episodes), which is indexed by `episode_id` and contains `patient_id` and `episode_start` as columns.
* `codes`: The table of diagnosis/procedure codes from the previous section, containing a column `episode_id` and other code data columns.

A function which combines these into a table containing all codes for other episodes relative to a base episode is `pyhbr.clinical_codes.counting.get_all_other_codes`:

??? note "Function that gets data from other episodes relative to a base episode"

    ::: pyhbr.clinical_codes.counting.get_all_other_codes
        options:
            # If the root heading is shown, then a TOC entry will be
            # present too. Set a very high heading level to hide it.
            heading_level: 100
            show_root_heading: true
            show_root_full_path: false
            show_symbol_type_heading: true
            show_root_toc_entry: false

#### Counting Codes Group Occurrences 

In any table that has ``

