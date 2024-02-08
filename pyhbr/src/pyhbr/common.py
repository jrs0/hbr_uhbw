"""Common utilities for other modules.

A collection of routines used by the data source or analysis functions.
"""

from sqlalchemy import create_engine, Engine, MetaData, Table, Select, Column
from sqlalchemy.exc import NoSuchTableError
from pandas import DataFrame
from typing import Callable


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
    def __init__(self, table_name: str, engine: Engine) -> None:
        """Get a CheckedTable by reading from the remote server

        This is a wrapper around the sqlalchemy Table for
        catching errors when accessing columns through the
        c attribute.

        Args:
            table: The name of the table whose metadata should be retrieved
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
            )

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
            )


def get_data(
    engine: Engine, query: Callable[[Engine, ...], Select], *args
) -> DataFrame:
    """Convenience function to make a query and fetch data

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
    return pd.read_sql(stmt, engine)
