from importlib.resources import files
import yaml


def load_from_package(name: str) -> dict:
    """Load a clinical codes file from the pyhbr package.

    The clinical codes are stored in yaml format, and this
    function returns a dictionary corresponding to the structure
    of the yaml file.

    Args:
        name: The file name of the codes file to load

    Returns:
        The contents of the file.
    """
    contents = files("pyhbr.clinical_codes.files").joinpath(name).read_text()
    return yaml.load(contents, Loader=yaml.CLoader)
