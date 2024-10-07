import argparse

def main():
    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser("get-csv")
    parser.add_argument(
        "-n",
        "--file-name",
        required=True,
        help="The root part of the data file name to load",
    )

    args = parser.parse_args()
    
    