"""Common utilities for other modules.

A collection of routines used by the data source or analysis functions.
"""

import os
from typing import Callable, Any
from time import time
import pickle

from sqlalchemy import create_engine, Engine, MetaData, Table, Select, Column
from sqlalchemy.exc import NoSuchTableError
from pandas import DataFrame, read_sql, to_datetime, read_pickle
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

    def __init__(self, table_name: str, engine: Engine) -> None:
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
        metadata_obj = MetaData()
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
    return read_sql(stmt, engine)

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

def get_saved_files_by_name(name: str, save_dir: str) -> DataFrame:
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
        r"_([0-9]|[a-zA-Z])*_\d*\.pkl", "", regex=True
    )

    # Remove all the files whose name does not match, and drop
    # the name from the path
    files = files[files["name"] == name]
    if files.shape[0] == 0:
        raise ValueError(
            f"There is not dataset with the name '{name}' in the datasets directory"
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
            "name_commit_timestamp.(rds|pkl), and "
            "remove any files not matching this "
            "pattern. TODO handle this error properly, "
            "see save_datasets.py."
        ) from exc

    files["created_date"] = to_datetime(files["timestamp"].astype(int), unit="s")
    recent_first = files.sort_values(by="timestamp", ascending=False).reset_index()[
        ["path", "commit", "created_date"]
    ]
    return recent_first

def pick_saved_file_interactive(name: str, save_dir: str) -> str | None:
    """Select a file matching name interactively
    
    Print a list of the saved items in the save_dir folder, along
    with the date and time it was generated, and the commit hash,
    and let the user pick which item should be loaded interactively.
    The full filename of the resulting file is returned, which can
    then be read by the user.
    
    Args:
        name: The name of the saved file to list
        save_dir: The directory to search for files
        
    Returns:
        The absolute path to the interactively selected file, or None
            if the interactive load was aborted.
    """

    recent_first = get_saved_files_by_name(name, save_dir)
    print(recent_first)

    num_datasets = recent_first.shape[0]
    while True:
        try:
            raw_choice = input(f"Pick a dataset to load: [{0} - {num_datasets-1}] (type q[uit]/exit, then Enter, to quit): ")
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

def pick_most_recent_saved_file(name: str, save_dir: str) -> str:
    """Get the path to the most recent file matching name.
    
    Like pick_saved_file_interactive, but automatically selects the most
    recent file in save_data.

    Args:
        name: The name of the saved file to list
        save_dir: The directory to search for files
        
    Returns:
        The absolute path to the most recent matching file.
    """
    recent_first = get_saved_files_by_name(name, save_dir)
    full_path = os.path.join(save_dir, recent_first.loc[0, "path"])
    return full_path

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

def save_item(item: Any, name: str, save_dir: str = "save_data/", enforce_clean_branch=True) -> None:
    """Save an item to a pickle file

    Saves a python object (e.g. a pandas DataFrame) dataframe in the save_dir
    folder, using a filename that includes the current timestamp and the current 
    commit hash. Use load_item to retrieve the file.
    
    By storing the commit hash and timestamp, it is possible to identify when items
    were created and what code created them. To make most effective use of the
    commit hash, ensure that you commit, and do not make any further code edits,
    before running a script that calls save_item (otherwise the commit hash will
    not quite reflect the state of the running code).

    Args:
        item: The python object to saave (e.g. pandas DataFrame)
        name: The name of the item. The filename will be created by adding
            a suffix for the current commit and the timestamp to show when the
            data was saved (format: `name_commit_timestamp.pkl`)
        save_dir: Where to save the data, relative to the current working directory.
            The directory will be created if it does not exist.
        enforce_clean_branch: If True, the function will raise an exception if an attempt
            is made to save an item when the repository has uncommitted changes.
    """

    if enforce_clean_branch and requires_commit():
        raise RuntimeError("Aborting save_item() because branch is not clean. Commit changes and try again.")

    if not os.path.isdir(save_dir):
        print(f"Creating missing folder '{save_dir}' for storing item")
        os.mkdir(save_dir)

    # Make the file suffix out of the current git
    # commit hash and the current time
    filename = f"{name}_{current_commit()}_{current_timestamp()}.pkl"
    path = os.path.join(save_dir, filename)

    with open(path, "wb") as file:
        pickle.dump(item, file)

def load_item(name: str, interactive: bool = False, save_dir: str = "save_data") -> Any:
    """Load a previously saved item from file
    
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
        The python object loaded from file, or None for an interactive load that
            is cancelled by the user.

    """
    if interactive:
        item_path = pick_saved_file_interactive(name, save_dir)
    else:
        item_path = pick_most_recent_saved_file(name, save_dir)

    if item_path is None:
        print("Aborted (interactive) load item")
        return

    print(f"Loading {item_path}")
    
    # Load a generic pickle. Note that if this is a pandas dataframe,
    # pandas must be installed (otherwise you will get module not found).
    # The same goes for a pickle storing an object from any other library.
    with open(item_path, "rb") as file:
        return pickle.load(file)