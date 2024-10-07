import argparse

def main():
    
    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser("get-csv")
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

    args = parser.parse_args()
    
    import yaml
    from pyhbr import common
    import pandas as pd
    from pathlib import Path
    
    # Read the configuration file
    with open(args.config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Failed to load config file: {exc}")
            exit(1)
        
    analysis_name = config["analysis_name"]
    save_dir = config["save_dir"]
    
    interactive=True
    data, data_path = common.load_item(f"{analysis_name}_{args.name}", interactive, save_dir)
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
            data = { n: value for n, value in enumerate(data) }
        
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

    print("\nFound the following DataFrame items in the loaded item")

    for n, name in enumerate(name_list):
            print(f" {n}: {name}")
            
    num_dataframes = len(name_list)
    while True:
        try:
            raw_choice = input(
                f"Pick a DataFrame to write to csv: [{0} - {num_dataframes-1}] (type q[uit]/exit, then Enter, to quit): "
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
    
    # Write the item to CSV
    print("\nWriting the following DataFrame to CSV:\n")
    df = df_list[choice]
    print(df)
    df_path = (Path(save_dir) / Path(name_list[choice])).with_suffix(".csv")
    df.to_csv(df_path)
    print(f"\nWritten CSV to {df_path}")
    
    