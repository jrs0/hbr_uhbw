import argparse
from pandas import DataFrame
from pathlib import Path

description = """
Extract the DataFrame items from a pyhbr pickle as CSV or Parquet

Use this command to extract tables stored in a pyhbr pickle file
and save them as CSV or Parquet.

EXAMPLES

# In save_data\icb_hic_raw_fc439fc55ee_1728309069.pkl,
# Save just one item (picked interactively) as CSV
get-csv -f icb_hic.yaml -n raw

# In save_data/icb_hic_data_5157df47152_1728464409.pkl,
# save all DataFrames as Parquet files (-a means all,
# -p means save Parquet)
get-csv -f icb_hic.yaml -n data -pa

DETAIL

You only need to specify the "name" part of the file name.
For example, to read the pickle file:

    save_data/icb_hic_data_5157df47152_1728464409.pkl

which is in the format:

    {save_dir}/{analysis_name}_{name}_{commit}_{timestamp}.pkl

you only need to pass "-n data" (i.e. "-n {name}").

You will be prompted to choose a pickle file if multiple files
with the same name, which are shown in a table by commit and
timestamp.
"""


def save_dataframe(df: DataFrame, name: str, save_dir: str, parquet: bool):
    """Write a dataframe to either CSV or Parquet

    Args:
        df: The DataFrame to save
        name: The name of the DataFrame to save
        save_dir: The directory in which to save the files
        parquet: True for Parquet, False for CSV
    """
    if parquet:
        df_path = (Path(save_dir) / Path(name)).with_suffix(".parquet")
        df.to_parquet(df_path)
        print(f"Written Parquet to {df_path}")
    else:
        df_path = (Path(save_dir) / Path(name)).with_suffix(".csv")
        df.to_csv(df_path)
        print(f"Written CSV to {df_path}")


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    pass


def main():

    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser(
        "get-csv", description=description, formatter_class=CustomFormatter
    )
    parser.add_argument(
        "-f",
        "--config-file",
        required=True,
        help="Specify the config file with settings",
    )
    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="The name part of the data file name to load from save_dir",
    )
    parser.add_argument(
        "-p",
        "--parquet",
        help="Store the resulting dataframe in parquet format instead of CSV",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--all",
        help="Save all the DataFrames found in the item",
        action="store_true",
    )

    args = parser.parse_args()

    import yaml
    from pyhbr import common
    import pandas as pd

    # Read the configuration file
    with open(args.config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Failed to load config file: {exc}")
            exit(1)

    analysis_name = config["analysis_name"]
    save_dir = config["save_dir"]

    interactive = True
    data, data_path = common.load_item(
        f"{analysis_name}_{args.name}", interactive, save_dir
    )
    if data is None:
        return

    def get_all_dataframes(data) -> (list[str], list[pd.DataFrame]):
        """Recursively fetch all dataframes from a dictionary

        Returns:
            A tuple, where the first item is a list of DataFrame names
                and the second item is the list of DataFrames. The names
                list is formed by concatenating the keys in the dictionary
                with underscore as a separator.

        """
        name_list = []
        df_list = []

        # Convert a list into a dict with index keys
        if isinstance(data, list):
            data = {n: value for n, value in enumerate(data)}

        for key, value in data.items():
            if isinstance(value, pd.DataFrame):
                name_list.append(key)
                df_list.append(value)
            elif isinstance(value, dict) or isinstance(value, list):
                # Recursively descend into the next dictionary data
                sub_name_list, sub_df_list = get_all_dataframes(value)

                # Prepend the current key to the name list
                name_list += [f"{key}_{sub_name}" for sub_name in sub_name_list]

                # Append the dataframes
                df_list += sub_df_list

        return name_list, df_list

    name_list, df_list = get_all_dataframes(data)

    if args.all:
        # Save all the dataframes found
        for name, df in zip(name_list, df_list):
            save_dataframe(df, name, save_dir, args.parquet)

    else:
        # Save just one dataframe (user picks)

        print("\nFound the following DataFrame items in the loaded item")

        for n, name in enumerate(name_list):
            print(f" {n}: {name}")

        num_dataframes = len(name_list)
        while True:
            try:
                raw_choice = input(
                    f"Pick a DataFrame to write to save: [{0} - {num_dataframes-1}] (type q[uit]/exit, then Enter, to quit): "
                )
                if "exit" in raw_choice or "q" in raw_choice:
                    return
                choice = int(raw_choice)
            except Exception:
                print(f"{raw_choice} is not valid; try again.")
                continue
            if choice < 0 or choice >= num_dataframes:
                print(f"{choice} is not in range; try again.")
                continue
            break

        # Print a snapshot of the item
        df = df_list[choice]
        name = name_list[choice]
        print("Saving the following DataFrame:")
        print(df)

        # Save the dataframe
        save_dataframe(df, name, save_dir, args.parquet)
