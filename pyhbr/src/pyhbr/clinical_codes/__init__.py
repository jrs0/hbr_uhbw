from importlib.resources import files
from serde.yaml import from_yaml

from dataclasses import dataclass
from serde import serde

@serde
@dataclass
class Index:
    """Index used to sort the code categories
    """
    index: str | tuple[str, str]

@serde
@dataclass
class Category:
    """Code/categories struct
    """
    name: str
    docs: str
    index: Index
    categories: list["Category"] | None
    exclude: set[str] | None

@serde
@dataclass
class ClinicalCodeTree:
    """Code definition file structure
    """
    categories: list[Category]
    groups: set[str]

def load_from_package(name: str) -> ClinicalCodeTree:
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
    return from_yaml(ClinicalCodeTree, contents)
    #return yaml.load(contents, Loader=yaml.CLoader)


