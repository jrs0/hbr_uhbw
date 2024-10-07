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
    
    print("\nFound the following DataFrame items in the loaded item")
    name_list = []
    load_list = []
    count = 0
    for key, value in data.items():
        if isinstance(value, pd.DataFrame):
            print(f" {count}: {key}")
            name_list.append(key)
            load_list.append(value)
            count += 1
            
    num_dataframes = len(load_list)
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
    df = load_list[choice]
    print(df)
    df_path = (Path(save_dir) / Path(name_list[choice])).with_suffix(".csv")
    df.to_csv(df_path)
    print(f"\nWritten CSV to {df_path}")
    
    