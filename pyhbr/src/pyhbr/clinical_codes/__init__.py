"""Contains utilities for clinical code groups
"""

from __future__ import annotations
from importlib.resources import files as res_files

from dataclasses import dataclass
from serde import serde
from serde.yaml import from_yaml
import pandas as pd
from pandas import Series, DataFrame


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

    def excludes(self, group: str) -> bool:
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


def normalise_code(code: str) -> str:
    """Remove whitespace/dots, and convert to lower-case

    The format of clinical codes can vary across different data
    sources. A simple way to compare codes is to convert them into
    a common format and compare them as strings. The purpose of
    this function is to define the common format, which uses all
    lower-case letters, does not contain any dots, and does not
    include any leading/trailing whitespace.

    Comparing codes for equality does not immediately allow checking
    whether one code is a sub-category of another. It also ignores
    clinical code annotations such as dagger/asterisk.

    Examples:
        >>> normalise_code("  I21.0 ")
        'i210'

    Args:
        code: The raw code, e.g.

    Returns:
        The normalised form of the clinical code
    """
    return code.lower().strip().replace(".", "")


@dataclass
class ClinicalCode:
    """Store a clinical code together with its description.

    Attributes:
        name: The code itself, e.g. "I21.0"
        docs: The code description, e.g. "Acute
            transmural myocardial infarction of anterior wall"
    """

    name: str
    docs: str

    def normalise(self):
        """Return the name without whitespace/dots, as lowercase

        See the documentation for [normalize_code()][pyhbr.clinical_codes.normalise_code].

        Returns:
            The normalized form of this clinical code
        """
        return normalise_code(self.name)


def get_codes_in_group(group: str, categories: list[Category]) -> list[ClinicalCode]:
    """Helper function to get clinical codes in a group

    Args:
        group: The group to fetch
        categories: The list of categories to search for codes

    Returns:
        A list of clinical codes in the group
    """

    # Filter out the categories that exclude the group
    categories_left = [c for c in categories if not c.excludes(group)]

    codes_in_group = []

    # Loop over the remaining categories. For all the leaf
    # categories, if there is no exclude for this group,
    # include it in the results. For non-leaf categories,
    # call this function again and append the resulting codes
    for category in categories_left:
        if category.is_leaf() and not category.excludes(group):
            code = ClinicalCode(name=category.name, docs=category.docs)
            codes_in_group.append(code)
        else:
            sub_categories = category.categories
            # Check it is non-empty (or refactor logic)
            new_codes = get_codes_in_group(group, sub_categories)
            codes_in_group.extend(new_codes)

    return codes_in_group


@serde
@dataclass
class ClinicalCodeTree:
    """Code definition file structure"""

    categories: list[Category]
    groups: set[str]

    def codes_in_group(self, group: str) -> list[ClinicalCode]:
        """Get the clinical codes in a code group

        Args:
            group: The group to fetch

        Raises:
            ValueError: Raised if the requested group does not exist

        Returns:
            The list of code groups
        """
        if not group in self.groups:
            raise ValueError(f"'{group}' is not a valid code group ({self.groups})")

        return get_codes_in_group(group, self.categories)

def load_from_file(path: str) -> ClinicalCodeTree:
    """Load a clinical codes file relative to the working directory

    Args:
        path: The path to the codes file relative to the current
            working directory.

    Returns:
        The contents of the file
    """
    with open(path, "r") as file:
        contents = file.read()
        return from_yaml(ClinicalCodeTree, contents)
    

def load_from_package(name: str) -> ClinicalCodeTree:
    """Load a clinical codes file from the pyhbr package.

    The clinical codes are stored in yaml format, and this
    function returns a dictionary corresponding to the structure
    of the yaml file.

    Examples:
        >>> import pyhbr.clinical_codes as codes
        >>> tree = codes.load_from_package("icd10_test.yaml")
        >>> group = tree.codes_in_group("group_1")
        >>> [code.name for code in group]
        ['I20.0', 'I20.1', 'I20.8', 'I20.9']

    Args:
        name: The file name of the codes file to load

    Returns:
        The contents of the file.
    """
    contents = res_files("pyhbr.clinical_codes.files").joinpath(name).read_text()
    return from_yaml(ClinicalCodeTree, contents)


def codes_in_any_group(codes: ClinicalCodeTree) -> pd.DataFrame:
    """Get a DataFrame of all the codes in any group in a codes file

    Returns a table with the normalised code (lowercase/no whitespace/no
    dots) in column `code`, and the group containing the code in the
    column `group`.

    All codes which are in any group will be included.

    Codes will be duplicated if they appear in more than one group.

    Args:
        codes: The tree clinical codes (e.g. ICD-10 or OPCS-4, loaded
            from a file) to search for codes

    Returns:
        pd.DataFrame: All codes in any group in the codes file
    """
    dfs = []
    for g in codes.groups:
        clinical_codes = codes.codes_in_group(g)
        normalised_codes = [c.normalise() for c in clinical_codes]
        docs = [c.docs for c in clinical_codes]
        df = pd.DataFrame({"code": normalised_codes, "docs": docs, "group": g})
        dfs.append(df)

    return pd.concat(dfs).reset_index(drop=True)


def filter_to_groups(
    codes_table: pd.DataFrame, codes: ClinicalCodeTree
) -> pd.DataFrame:
    """Filter a table of raw clinical codes to only keep codes in groups

    Use this function to drop clinical codes which are not of interest,
    and convert all codes to normalised form (lowercase, no whitespace, no dot).

    This function is tested on the HIC dataset, but should be modifiable
    for use with any data source returning diagnoses and procedures as
    separate tables in long format. Consider modifying the columns of
    codes_table that are contained in the output.

    Args:
        codes_table: Either a diagnoses or procedures table. For this
            function to work, it needs:

            * A `code` column containing the clinical code.
            * An `episode_id` identifying which episode contains the code.
            * A `position` identifying the primary/secondary position of the
                code in the episode.

        codes: The clinical codes object (previously loaded from a file)
            containing code groups to use.

    Returns:
        A table containing the episode ID, the clinical code (normalised),
            the group containing the code, and the code position.

    """
    codes_with_groups = codes_in_any_group(codes)
    codes_table["code"] = codes_table["code"].apply(normalise_code)
    codes_table = pd.merge(codes_table, codes_with_groups, on="code", how="inner")
    codes_table = codes_table[["episode_id", "code", "docs", "group", "position"]]

    return codes_table


def get_code_groups(codes: Series, code_tree: ClinicalCodeTree) -> DataFrame:
    """Normalise a code column and assign codes to groups

    Args:
        codes: A column of (potentially non-normalised) clinical
            codes.
        code_tree: The clinical codes object (previously loaded from a file)
            containing code groups to use.

    Returns:
        A table where the first column ("code") is the normalised code
            obtained from the code column. The second column ("group")
            contains the group containing the code if the code is in

    """
    codes_with_groups = codes_in_any_group(code_tree)
    normalised_codes = codes.apply(normalise_code).rename("code")
    return normalised_codes.to_frame().merge(codes_with_groups, on="code", how="left")
