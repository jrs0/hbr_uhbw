"""Common utilities for other modules.

A collection of routines used by the data source or analysis functions.
"""

from dataclasses import dataclass

import os
import sys
from pathlib import Path
from typing import Callable, Any
from time import time
import pickle
from pandas import Series
import numpy as np
import scipy

from sqlalchemy import create_engine, Engine, MetaData, Table, Select, Column
from sqlalchemy.exc import NoSuchTableError
from pandas import DataFrame, read_sql, to_datetime, read_pickle, concat
from git import Repo, InvalidGitRepositoryError


def make_engine(
    con_string: str = "mssql+pyodbc://dsn", database: str = "hic_cv_test"
) -> Engine:
    """Make a sqlalchemy engine

    This function is intended for use with Microsoft SQL
    Server. The preferred method to connect to the server
    on Windows is to use a Data Source Name (DSN). To use the
    default connection string argument, set up a data source
    name called "dsn" using the program "ODBC Data Sources".

    If you need to access multiple different databases on the
    same server, you will need different engines. Specify the
    database name while creating the engine (this will override
    a default database in the DSN, if there is one).

    Args:
        con_string: The sqlalchemy connection string.
        database: The database name to connect to.

    Returns:
        The sqlalchemy engine
    """
    connect_args = {"database": database}
    return create_engine(con_string, connect_args=connect_args)


class CheckedTable:
    """Wrapper for sqlalchemy table with checks for table/columns"""

    def __init__(self, table_name: str, engine: Engine, schema="dbo") -> None:
        """Get a CheckedTable by reading from the remote server

        This is a wrapper around the sqlalchemy Table for
        catching errors when accessing columns through the
        c attribute.

        Args:
            table_name: The name of the table whose metadata should be retrieved
            engine: The database connection

        Returns:
            The table data for use in SQL queries
        """
        self.name = table_name
        metadata_obj = MetaData(schema=schema)
        try:
            self.table = Table(self.name, metadata_obj, autoload_with=engine)
        except NoSuchTableError as e:
            raise RuntimeError(
                f"Could not find table '{e}' in database connection '{engine.url}'"
            ) from e

    def col(self, column_name: str) -> Column:
        """Get a column

        Args:
            column_name: The name of the column to fetch.

        Raises:
            RuntimeError: Thrown if the column does not exist
        """
        try:
            return self.table.c[column_name]
        except AttributeError as e:
            raise RuntimeError(
                f"Could not find column name '{column_name}' in table '{self.name}'"
            ) from e


def get_data(
    engine: Engine, query: Callable[[Engine, ...], Select], *args: ...
) -> DataFrame:
    """Convenience function to make a query and fetch data.

    Wraps a function like hic.demographics_query with a
    call to pd.read_data.

    Args:
        engine: The database connection
        query: A function returning a sqlalchemy Select statement
        *args: Positional arguments to be passed to query in addition
            to engine (which is passed first). Make sure they are passed
            in the same order expected by the query function.

    Returns:
        The pandas dataframe containing the SQL data
    """
    stmt = query(engine, *args)
    df = read_sql(stmt, engine)

    # Convert the column names to regular strings instead
    # of sqlalchemy.sql.elements.quoted_name. This avoids
    # an error down the line in sklearn, which cannot
    # process sqlalchemy column title tuples.
    df.columns = [str(col) for col in df.columns]

    return df


def get_data_by_patient(
    engine: Engine,
    query: Callable[[Engine, ...], Select],
    patient_ids: list[str],
    *args: ...,
) -> list[DataFrame]:
    """Fetch data using a query restricted by patient ID

    The patient_id list is chunked into 2000 long batches to fit
    within an SQL IN clause, and each chunk is run as a separate
    query. The results are assembled into a single DataFrame.

    Args:
        engine: The database connection
        query: A function returning a sqlalchemy Select statement. Must
            take a list[str] as an argument after engine.
        patient_ids: A list of patient IDs to restrict the query.
        *args: Further positional arguments that will be passed to the
            query function after the patient_ids positional argument.

    Returns:
        A list of dataframes, one corresponding to each chunk.
    """
    dataframes = []
    patient_id_chunks = chunks(patient_ids, 2000)
    num_chunks = len(patient_id_chunks)
    chunk_count = 1
    for chunk in patient_id_chunks:
        print(f"Fetching chunk {chunk_count}/{num_chunks}")
        dataframes.append(get_data(engine, query, chunk, *args))
        chunk_count += 1
    return dataframes


def current_commit() -> str:
    """Get current commit.

    Returns:
        Get the first 12 characters of the current commit,
            using the first repository found above the current
            working directory. If the working directory is not
            in a git repository, return "nogit".
    """
    try:
        repo = Repo(search_parent_directories=True)
        sha = repo.head.object.hexsha[0:11]
        return sha
    except InvalidGitRepositoryError:
        return "nogit"


def current_timestamp() -> int:
    """Get the current timestamp.

    Returns:
        The current timestamp (since epoch) rounded
            to the nearest second.
    """
    return int(time())


def get_saved_files_by_name(name: str, save_dir: str, extension: str) -> DataFrame:
    """Get all saved data files matching name

    Get the list of files in the save_dir folder matching
    name. Return the result as a table of file path, commit
    hash, and saved date. The table is sorted by timestamp,
    with the most recent file first.

    Raises:
        RuntimeError: If save_dir does not exist, or there are files
            in save_dir within invalid file names (not in the format
            name_commit_timestamp.pkl).

    Args:
        name: The name of the saved file to load. This matches name in
            the filename name_commit_timestamp.pkl.
        save_dir: The directory to search for files.
        extension: What file extension to look for. Do not include the dot.

    Returns:
        A dataframe with columns `path`, `commit` and `created_data`.
    """

    # Check for missing datasets directory
    if not os.path.isdir(save_dir):
        raise RuntimeError(
            f"Missing folder '{save_dir}'. Check your working directory."
        )

    # Read all the .pkl files in the directory
    files = DataFrame({"path": os.listdir(save_dir)})

    # Identify the file name part. The horrible regex matches the
    # expression _[commit_hash]_[timestamp].pkl. It is important to
    # match this part, because "anything" can happen in the name part
    # (including underscores and letters and numbers), so splitting on
    # _ would not work. The name can then be removed.
    files["name"] = files["path"].str.replace(
        rf"_([0-9]|[a-zA-Z])*_\d*\.{extension}", "", regex=True
    )

    # Remove all the files whose name does not match, and drop
    # the name from the path
    files = files[files["name"] == name]
    if files.shape[0] == 0:
        raise ValueError(
            f"There is no file with the name '{name}' in the datasets directory"
        )
    files["commit_and_timestamp"] = files["path"].str.replace(name + "_", "")

    # Split the commit and timestamp up (note also the extension)
    try:
        files[["commit", "timestamp", "extension"]] = files[
            "commit_and_timestamp"
        ].str.split(r"_|\.", expand=True)
    except Exception as exc:
        raise RuntimeError(
            "Failed to parse files in the datasets folder. "
            "Ensure that all files have the correct format "
            "name_commit_timestamp.extension, and "
            "remove any files not matching this "
            "pattern. TODO handle this error properly, "
            "see save_datasets.py."
        ) from exc

    files["created_date"] = to_datetime(files["timestamp"].astype(int), unit="s")
    recent_first = files.sort_values(by="timestamp", ascending=False).reset_index()[
        ["path", "commit", "created_date"]
    ]
    return recent_first


def pick_saved_file_interactive(
    name: str, save_dir: str, extension: str = "pkl"
) -> str | None:
    """Select a file matching name interactively

    Print a list of the saved items in the save_dir folder, along
    with the date and time it was generated, and the commit hash,
    and let the user pick which item should be loaded interactively.
    The full filename of the resulting file is returned, which can
    then be read by the user.

    Args:
        name: The name of the saved file to list
        save_dir: The directory to search for files
        extension: What file extension to look for. Do not include the dot.

    Returns:
        The absolute path to the interactively selected file, or None
            if the interactive load was aborted.
    """

    recent_first = get_saved_files_by_name(name, save_dir, extension)
    print(recent_first)

    num_datasets = recent_first.shape[0]
    while True:
        try:
            raw_choice = input(
                f"Pick a dataset to load: [{0} - {num_datasets-1}] (type q[uit]/exit, then Enter, to quit): "
            )
            if "exit" in raw_choice or "q" in raw_choice:
                return None
            choice = int(raw_choice)
        except Exception:
            print(f"{raw_choice} is not valid; try again.")
            continue
        if choice < 0 or choice >= num_datasets:
            print(f"{choice} is not in range; try again.")
            continue
        break

    full_path = os.path.join(save_dir, recent_first.loc[choice, "path"])
    return full_path


def pick_most_recent_saved_file(
    name: str, save_dir: str, extension: str = "pkl"
) -> Path:
    """Get the path to the most recent file matching name.

    Like pick_saved_file_interactive, but automatically selects the most
    recent file in save_data.

    Args:
        name: The name of the saved file to list
        save_dir: The directory to search for files
        extension: What file extension to look for. Do not include the dot.

    Returns:
        The relative path to the most recent matching file.
    """
    recent_first = get_saved_files_by_name(name, save_dir, extension)
    return Path(save_dir) / Path(recent_first.loc[0, "path"])


def requires_commit() -> bool:
    """Check whether changes need committing

    To make most effective use of the commit hash stored with a
    save_item call, the current branch should be clean (all changes
    committed). Call this function to check.

    Returns False if there is no git repository.

    Returns:
        True if the working directory is in a git repository that requires
            a commit; False otherwise.
    """
    try:
        repo = Repo(search_parent_directories=True)
        return repo.is_dirty(untracked_files=True)
    except InvalidGitRepositoryError:
        # No need to commit if not repository
        return False


def make_new_save_item_path(name: str, save_dir: str, extension: str) -> Path:
    """Make the path to save a new item to the save_dir

    The name will have the format name_{current_common}_{timestamp}.{extension}.

    Args:
        name: The base name for the new filename
        save_dir: The folder in which to place the item
        extension: The file extension (omit the dot)

    Returns:
        The relative path to the new object to be saved
    """

    # Make the file suffix out of the current git
    # commit hash and the current time
    filename = f"{name}_{current_commit()}_{current_timestamp()}.{extension}"
    return Path(save_dir) / Path(filename)


def save_item(
    item: Any,
    name: str,
    save_dir: str = "save_data/",
    enforce_clean_branch=True,
    prompt_commit=False,
) -> None:
    """Save an item to a pickle file

    Saves a python object (e.g. a pandas DataFrame) dataframe in the save_dir
    folder, using a filename that includes the current timestamp and the current
    commit hash. Use load_item to retrieve the file.

    !!! important
        Ensure that `save_data/` (or your chosen `save_dir`) is added to the
        .gitignore of your repository to ensure sensitive data is not committed.

    By storing the commit hash and timestamp, it is possible to identify when items
    were created and what code created them. To make most effective use of the
    commit hash, ensure that you commit, and do not make any further code edits,
    before running a script that calls save_item (otherwise the commit hash will
    not quite reflect the state of the running code).

    Args:
        item: The python object to save (e.g. pandas DataFrame)
        name: The name of the item. The filename will be created by adding
            a suffix for the current commit and the timestamp to show when the
            data was saved (format: `name_commit_timestamp.pkl`)
        save_dir: Where to save the data, relative to the current working directory.
            The directory will be created if it does not exist.
        enforce_clean_branch: If True, the function will raise an exception if an attempt
            is made to save an item when the repository has uncommitted changes.
        prompt_commit: if enforce_clean_branch is true, choose whether the prompt the
            user to commit on an unclean branch. This can help avoiding losing
            the results of a long-running script. Prefer to use false if the script
            is cheap to run.
    """

    if enforce_clean_branch:

        abort_msg = "Aborting save_item() because branch is not clean. Commit your changes before saving item to increase the chance of reproducing the item based on the filename commit hash."

        if prompt_commit:
            # If the branch is not clean, prompt the user to commit to avoid losing
            # long-running model results. Take care to only commit if the state of
            # the repository truly reflects what was run (i.e. if no changes were made
            # while the script was running).
            while requires_commit():
                print(abort_msg)
                print(
                    "You can commit now and then retry the save after committing."
                )
                retry_save = query_yes_no(
                    "Do you want to retry the save? Commit, then select yes, or choose no to abort the save."
                )

                if not retry_save:
                    print(f"Aborting save of {name}")
                    return
       
            # If we get out the loop without returning, then the branch
            # is not clean and the save can proceed.
            print("Branch now clean, proceeding to save")
        
        else:
            
            if requires_commit():
                # In this case, unconditionally throw an error
                raise RuntimeError(abort_msg)
        
    if not Path(save_dir).exists():
        print(f"Creating missing folder '{save_dir}' for storing item")
        Path(save_dir).mkdir(parents=True, exist_ok=True)

    path = make_new_save_item_path(name, save_dir, "pkl")
    with open(path, "wb") as file:
        print(f"Saving {str(path)}")
        pickle.dump(item, file)


def load_item(
    name: str, interactive: bool = False, save_dir: str = "save_data"
) -> (Any, Path):
    """Load a previously saved item (pickle) from file

    Use this function to load a file that was previously saved using
    save_item(). By default, the latest version of the item will be returned
    (the one with the most recent timestamp).

    None is returned if an interactive load is cancelled by the user.

    To load an item that is an object from a library (e.g. a pandas DataFrame),
    the library must be installed (otherwise you will get a ModuleNotFound
    exception). However, you do not have to import the library before calling this
    function.

    Args:
        name: The name of the item to load
        interactive: If True, let the user pick which item version to load interactively.
            If False, non-interactively load the most recent item (i.e. with the most
            recent timestamp). The commit hash is not considered when loading the item.
        save_fir: Which folder to load the item from.

    Returns:
        A tuple, with the python object loaded from file as first element and the
            Path to the item as the second element, or None if the user cancelled
            an interactive load.

    """
    if interactive:
        item_path = pick_saved_file_interactive(name, save_dir, "pkl")
    else:
        item_path = pick_most_recent_saved_file(name, save_dir, "pkl")

    if item_path is None:
        print("Aborted (interactive) load item")
        return None

    print(f"Loading {item_path}")

    # Load a generic pickle. Note that if this is a pandas dataframe,
    # pandas must be installed (otherwise you will get module not found).
    # The same goes for a pickle storing an object from any other library.
    with open(item_path, "rb") as file:
        return pickle.load(file), item_path


def chunks(patient_ids: list[str], n: int) -> list[list[str]]:
    """Divide a list of patient ids into n-sized chunks

    The last chunk may be shorter.

    Args:
        patient_ids: The List of IDs to chunk
        n: The chunk size.

    Returns:
        A list containing chunks (list) of patient IDs
    """
    return [patient_ids[i : i + n] for i in range(0, len(patient_ids), n)]


def mean_confidence_interval(
    data: Series, confidence: float = 0.95
) -> dict[str, float]:
    """Compute the confidence interval around the mean

    Args:
        data: A series of numerical values to compute the confidence interval.
        confidence: The confidence interval to compute.

    Returns:
        A map containing the keys "mean", "lower", and "upper". The latter
            keys contain the confidence interval limits.
    """
    a = 1.0 * np.array(data)
    n = len(a)
    mean = np.mean(a)
    standard_error = scipy.stats.sem(a)

    # Check this
    half_width = standard_error * scipy.stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return {
        "mean": mean,
        "confidence": confidence,
        "lower": mean - half_width,
        "upper": mean + half_width,
    }


def median_to_string(instability: DataFrame, unit="%") -> str:
    """Convert the median-quartile DataFrame to a String

    Args:
        instability: Table containing three rows, indexed by
            0.5 (median), 0.25 (lower quartile) and 0.75
            (upper quartile).
        unit: What units to add to the values in the string.

    Returns:
        A string containing the median, and the lower and upper
            quartiles.
    """
    return f"{instability.loc[0.5]:.2f}{unit} Q [{instability.loc[0.025]:.2f}{unit}, {instability.loc[0.975]:.2f}{unit}]"


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    From https://stackoverflow.com/a/3041990.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")
