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

    def is_leaf(self):
        """Check if the categories is a leaf node

        Returns:
            True if leaf node (i.e. clinical code), false otherwise
        """
        return self.categories is None

    def excludes(self, group: str) -> bool :
        """Check if this category excludes a code group

        Args:
            group: The string name of the group to check

        Returns:
            True if the group is excluded; False otherwise
        """
        if self.exclude is not None:
            return group in self.exclude
        else:
            return False
    
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

def get_codes_in_group(group: str, categories: list[Category]) -> list[str]:
    
    # Filter out the categories that exclude the group
    categories_left = [c for c in categories if]
    
    codes_in_group = []
    
    # Loop over the remaining categories. For all the leaf
    # categories, if there is no exclude for this group,
    # include it in the results. For non-leaf categories,
    # call this function again and append the resulting codes
    for category in categories_left:
        if category.is_leaf() and not category.excludes(group):
            # Make a custom code object here to store codes and docs
            codes_in_group.append(category.name)
        else:
            sub_categories = category.categories
            # Check it is non-empty (or refactor logic)
            new_codes = get_codes_in_group(group, sub_categories)
            codes_in_group.extend(new_codes)