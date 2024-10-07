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
    print(data.keys())