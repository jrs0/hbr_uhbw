"""Contains utilities for clinical code groups
"""

from __future__ import annotations
from importlib.resources import files

from dataclasses import dataclass
from serde import serde
from serde.yaml import from_yaml

# Note: this class is missing the @serde decorator 
# deliberately. It seems like there is an issue with
# the class being recursively defined and the use of
# the decorator. However, pyserde supports runtime
# serde of classes without the @serde annotation 
# (see https://github.com/yukinarit/pyserde/blob/
# main/docs/en/decorators.md#deserializing-class
# -without-serde), which works fine.
@dataclass
class Category:
    """Code/categories struct
    
    Attributes:
        name: The name of the category (e.g. I20) or clinical code (I20.1)
        docs: The description of the category or code
        index: Used to sort a list of Categories
        categories: For a category, the list of sub-categories contained.
            None for a code.
        exclude: Contains code groups which do not contain any members
            from this category or any of its sub-categories. 
        
    """
    name: str
    docs: str
    index: str | tuple[str, str]
    categories: list[Category] | None
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
    return yaml.load(contents, Loader=yaml.CLoader)


