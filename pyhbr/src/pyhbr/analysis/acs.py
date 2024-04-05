import datetime as dt
from pandas import DataFrame
from pyhbr.clinical_codes import counting
from pyhbr.analysis import describe
from pyhbr.middle import from_hic  # Need to move the function


def get_index_spells(data: dict[str, DataFrame]) -> DataFrame:
    """Get the index spells for ACS/PCI patients

    Index spells are defined by the contents of the first episode of
    the spell (i.e. the cause of admission to hospital). Spells are
    considered an index event if either of the following hold:

    * The primary diagnosis of the first episode contains an
      ACS ICD-10 code.
    * There is a PCI procedure in any primary or secondary position
      in the first episode of the spell.

    A prerequisite for spell to be an index spell is that it contains
    episodes present in both the episodes and codes tables. The episodes table
    contains start-time/spell information, and the codes table contains
    information about what diagnoses/procedures occurred in each episode.

    The table returned contains one row per index spell (and is indexed by
    spell id). It also contains other information about the index spell,
    which is derived from the first episode of the spell.

    If you need to modify this function, note that the group names used to
    identify ACS/PCI groups are called `acs` and `pci` (present in the
    codes table). Also note that the position column in the codes table
    is indexed from 1.

    Args:
        data: A dictionary containing at least these keys:
            * episodes: All patient episodes. Must contain `episode_id`, `spell_id`
                and `episode_start`.
            * codes: All diagnosis/procedure codes by episode. Must contain
                `episode_id`, `position` (indexed from 1 which is the primary
                code, >1 are secondary codes), and `group` (containing either `acs`
                or `pci`).

    Returns:
        A table of index spells and associated information about the
            first episode of the spell.
    """
    # Index spells are defined by the contents of the first episode in the
    # spell (to capture to cause of admission to hospital).
    first_episodes = (
        data["episodes"].sort_values("episode_start").groupby("spell_id").head(1)
    )

    # Join the diagnosis/procedure codes (inner join reduces to episodes which
    # have codes in any group, which is a superset of the index episodes)
    first_episodes_with_codes = first_episodes.merge(
        data["codes"], how="inner", on="episode_id"
    )

    # ACS matches based on a primary diagnosis of ACS (this is to rule out
    # cases where patient history may contain ACS recorded as a secondary
    # diagnosis).
    acs_match = (first_episodes_with_codes["group"] == "acs_bezin") & (
        first_episodes_with_codes["position"] == 1
    )

    # A PCI match is allowed anywhere in the procedures list, but must still
    # be present in the first episode of the index spell.
    pci_match = first_episodes_with_codes["group"] == "pci"

    # Get all the episodes matching the ACS or PCI condition (multiple rows
    # per episode)
    matching_episodes = first_episodes_with_codes[acs_match | pci_match]
    matching_episodes.set_index("episode_id", drop=True, inplace=True)

    # Reduce to one row per episode, and store a flag for whether the ACS
    # or PCI condition was present
    index_spells = DataFrame()
    index_spells["acs_index"] = (
        matching_episodes["group"].eq("acs_bezin").groupby("episode_id").any()
    )
    index_spells["pci_index"] = (
        matching_episodes["group"].eq("pci").groupby("episode_id").any()
    )

    # Join some useful information about the episode
    return (
        index_spells.merge(
            data["episodes"][["patient_id", "episode_start", "spell_id"]],
            how="left",
            on="episode_id",
        )
        .rename(columns={"episode_start": "spell_start"})
        .reset_index("episode_id")
        .set_index("spell_id")
    )


def index_episodes(data: dict[str, DataFrame]) -> DataFrame:
    """Get the index episodes for ACS/PCI patients

    !!! warning
        This function is deprecated. Use get_index_spells() instead.
        Defining index events and subsequent outcomes at an episode
        level is not a good idea, because several episodes in the
        same spell (whose clinical codes may be duplicates of the
        same clinical event) will cause double-counting.

    Index episodes are defined by the contents of the first episode of
    the spell (i.e. the cause of admission to hospital). Episodes are
    considered an index event if:

    * The primary diagnosis contains an ACS ICD-10 code; or
    * There is a PCI procedure in any primary or secondary position

    A prerequisite for an episode to be an index episode is that it
    is present in both the episodes and codes table. The episodes table
    contains start-time/spell information, and the codes table contains
    information about what diagnoses/procedures occurred in the episode.

    The table returned contains only the episodes that match, along
    with all the information about that episode present in the episodes
    and codes tables.

    If you need to modify this function, note that the group names used to
    identify ACS/PCI groups are called `acs` and `pci` (present in the
    codes table). Also note that the position column in the codes table
    is indexed from 1.

    Args:
        data: A dictionary containing at least these keys:
            * episodes: All patient episodes. Must contain `episode_id`, `spell_id`
                and `episode_start`.
            * codes: All diagnosis/procedure codes by episode. Must contain
                `episode_id`, `position` (indexed from 1 which is the primary
                code, >1 are secondary codes), and `group` (containing either `acs`
                or `pci`).

    Returns:
        The index episodes.
    """

    # Index episodes are defined by the contents of the first episode in the
    # spell (to capture to cause of admission to hospital).
    first_episodes = (
        data["episodes"].sort_values("episode_start").groupby("spell_id").head(1)
    )

    # Join the diagnosis/procedure codes (inner join reduces to episodes which
    # have codes in any group, which is a superset of the index episodes)
    first_episodes_with_codes = first_episodes.merge(
        data["codes"], how="inner", on="episode_id"
    )

    # ACS matches based on a primary diagnosis of ACS (this is to rule out
    # cases where patient history may contain ACS recorded as a secondary
    # diagnosis).
    acs_match = (first_episodes_with_codes["group"] == "acs_bezin") & (
        first_episodes_with_codes["position"] == 1
    )

    # A PCI match is allowed anywhere in the procedures list, but must still
    # be present in the index episode
    pci_match = first_episodes_with_codes["group"] == "pci"

    # Get all the episodes matching the ACS or PCI condition (multiple rows
    # per episode)
    matching_episodes = first_episodes_with_codes[acs_match | pci_match]

    matching_episodes.set_index("episode_id", drop=True, inplace=True)

    # Reduce to one row per episode, and store a flag for whether the ACS
    # or PCI condition was present
    index_episodes = DataFrame()
    index_episodes["acs_index"] = (
        matching_episodes["group"].eq("acs_bezin").groupby("episode_id").any()
    )
    index_episodes["pci_index"] = (
        matching_episodes["group"].eq("pci").groupby("episode_id").any()
    )

    # Join some useful information about the episode
    return index_episodes.merge(
        data["episodes"][["patient_id", "episode_start"]], how="left", on="episode_id"
    )


def get_outcomes(index_spells: DataFrame, all_other_codes: DataFrame) -> DataFrame:
    """Get bleeding and ischaemia outcomes

    The bleeding outcome is defined by the ADAPTT trial bleeding code group,
    which matches BARC 2-5 bleeding events. Subsequent events occurring more than
    3 days (to attempt to exclude periprocedural events) and less than 365 days are
    included. Outcomes are allowed to occur in any episode of any spell (including
    the index spell), but must occur in the primary position (to avoid matching
    historical/duplicate coding within a spell).

    TODO: the ischaemia outcome definition

    Args:
        index_spells: A table containing `spell_id` as Pandas index and a
            column `episode_id` for the first episode in the index spell.
        all_other_codes: A table of other episodes (and their clinical codes)
            relative to the index spell, output from counting.get_all_other_codes.

    Returns:
        A table with two columns `bleeding_outcome` and `ischaemia_outcome`, which
            count the number of subsequent events in the other episodes after
            the index.
    """

    bleeding_groups = ["bleeding_adaptt"]
    ischaemia_groups = ["hussain_ami_stroke"]
    primary_only = True
    exclude_index_spell = False
    first_episode_only = False
    min_after = dt.timedelta(days=3)
    max_after = dt.timedelta(days=365)

    # Get the episodes (and all their codes) in the follow-up window
    following_year = counting.get_time_window(all_other_codes, min_after, max_after)

    # Count bleeding outcomes
    bleeding_episodes = counting.filter_by_code_groups(
        following_year,
        bleeding_groups,
        primary_only,
        exclude_index_spell,
        first_episode_only,
    )
    bleeding_outcome = counting.count_code_groups(index_spells, bleeding_episodes)

    # Count ischaemia outcomes
    ischaemia_episodes = counting.filter_by_code_groups(
        following_year,
        ischaemia_groups,
        primary_only,
        exclude_index_spell,
        first_episode_only,
    )
    ischaemia_outcome = counting.count_code_groups(index_spells, ischaemia_episodes)

    return DataFrame(
        {"bleeding_outcome": bleeding_outcome, "ischaemia_outcome": ischaemia_outcome}
    )


def get_code_features(index_spells: DataFrame, all_other_codes: DataFrame) -> DataFrame:
    """Get counts of previous clinical codes in code groups before the index.

    Predictors derived from clinical code groups use clinical coding data from 365
    days before the index to 30 days before the index (this excludes episodes where
    no coding data would be available, because the coding process itself takes
    approximately one month).

    All groups included anywhere in the `group` column of all_other_codes are
    included, and each one becomes a new column with "_before" appended.

    Args:
        index_spells: A table containing `spell_id` as Pandas index and a
            column `episode_id` for the first episode in the index spell.
        all_other_codes: A table of other episodes (and their clinical codes)
            relative to the index spell, output from counting.get_all_other_codes.

    Returns:
        A table with one column per code group, counting the number of codes
            in that group that appeared in the year before the index.
    """
    code_groups = all_other_codes["group"].unique()
    primary_only = False
    exclude_index_spell = False
    first_episode_only = False
    max_before = dt.timedelta(days=365)
    min_before = dt.timedelta(days=30)

    # Get the episodes that occurred in the previous year (for clinical code features)
    previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)

    code_features = {}
    for group in code_groups:
        group_episodes = counting.filter_by_code_groups(
            previous_year,
            [group],
            primary_only,
            exclude_index_spell,
            first_episode_only,
        )
        code_features[group + "_before"] = counting.count_code_groups(
            index_spells, group_episodes
        )

    return DataFrame(code_features)


def get_index_attribute_periods(
    index_spells: DataFrame, primary_care_attributes: DataFrame
) -> DataFrame:
    """Link primary care attributes to index spells by attribute date

    The attribute_period column of an attributes row indicates that
    the attribute was valid at the end of the interval
    (attribute_period, attribute_period + 1month). It is important
    that no attribute is used in modelling that could have occurred
    after the index event, meaning that attribute_period + 1month < spell_start
    must hold for any attribute used as a predictor. On the other hand,
    data substantially before the index event should not be used. The
    valid window is controlled by imposing:

        attribute_period < spell_start - attribute_valid_window

    Args:
        index_spells: The index spell table, containing a `spell_start`
            column and `patient_id`
        primary_care_attributes: The patient attributes table, containing
            `attribute_period` and `patient_id`

    Returns:
        A filtered version of index_spells containing only index spells
            with a valid set of patient attributes. The `attribute_period`
            column is added to link the attributes (along with `patient_id`).
    """

    # Define a window before the index event where SWD attributes will be considered valid.
    # 41 days is used to ensure that a full month is definitely captured. This
    # ensures that attribute data that is fairly recent is used as predictors.
    attribute_valid_window = dt.timedelta(days=60)

    # Add all the patient's attributes onto each index spell
    df = index_spells.reset_index().merge(
        primary_care_attributes[["patient_id", "attribute_period"]],
        how="left",
        on="patient_id",
    )

    # Only keep attributes that are from strictly before the index spell
    # (note attribute_period represents the start of the month that attributes
    # apply to)
    attr_before_index = df[
        (df["attribute_period"] + dt.timedelta(days=31)) < df["spell_start"]
    ]

    # Keep only the most recent attribute before the index spell
    most_recent = (
        attr_before_index.sort_values("attribute_period").groupby("spell_id").tail(1)
    )

    # Exclude attributes that occurred outside the attribute_value_window before the index
    swd_index_spells = most_recent[
        most_recent["attribute_period"]
        > (most_recent["spell_start"] - attribute_valid_window)
    ]

    return index_spells.merge(
        swd_index_spells[["spell_id", "attribute_period"]].set_index("spell_id"),
        how="left",
        on="spell_id",
    )


def get_index_attributes(
    swd_index_spells: DataFrame, primary_care_attributes: DataFrame
) -> DataFrame:
    """Link the primary care patient data to the index spells

    Args:
        swd_index_spells: Reduced index_spells which all have a recent, valid
            patient attributes row. Contains the columns `patient_id` and
            `attribute_period` for linking, and has Pandas index `spell_id`.
        primary_care_attributes: The full attributes table.

    Returns:
        The table of index-spell patient attributes, indexed by `spell_id`.
    """

    return (
        (
            swd_index_spells[["patient_id", "attribute_period"]]
            .reset_index()
            .merge(
                primary_care_attributes,
                how="left",
                on=["patient_id", "attribute_period"],
            )
        )
        .set_index("spell_id")
        .drop(columns=["patient_id", "attribute_period"])
    )


def remove_features(
    index_attributes: DataFrame, max_missingness, const_threshold
) -> DataFrame:
    """Reduce to just the columns meeting minimum missingness and variability criteria.

    Args:
        index_attributes: The table of primary care attributes for the index spells
        max_missingness: The maximum allowed missingness in a column before a column
            is removed as a feature.
        const_threshold: The maximum allowed constant-value proportion (NA + most
            common non-NA value) before a column is removed as a feature

    Returns:
        A table containing the features that remain, which contain sufficient
            non-missing values and sufficient variance.
    """
    missingness = describe.proportion_missingness(index_attributes)
    nearly_constant = describe.nearly_constant(index_attributes, const_threshold)
    to_keep = (missingness < max_missingness) & ~nearly_constant
    return index_attributes.loc[:, to_keep]


def prescriptions_before_index(
    swd_index_spells: DataFrame, primary_care_prescriptions: DataFrame
) -> DataFrame:
    """Get the number of primary care prescriptions before each index spell

    Args:
        index_spells: Must have Pandas index `spell_id`
        primary_care_prescriptions: Must contain a `name` column
            that contains a string containing the medicine name
            somewhere (any case), a `date` column with the
            prescription date, and a `patient_id` column.

    Returns:
        A table indexed by `spell_id` that contains one column
            for each prescription type, prefexed with "prior_"
    """

    df = primary_care_prescriptions

    # Filter for relevant prescriptions
    df = from_hic.filter_by_medicine(df)

    # Drop rows where the prescription date is not known
    df = df[~df["date"].isna()]

    # Join the prescriptions to the index spells
    df = (
        swd_index_spells[["spell_start", "patient_id"]]
        .reset_index()
        .merge(df, how="left", on="patient_id")
    )
    df["time_to_index_spell"] = df["spell_start"] - df["date"]

    # Only keep prescriptions occurring in the year before the index event
    min_before = dt.timedelta(days=0)
    max_before = dt.timedelta(days=365)
    events_before_index = counting.get_time_window(
        df, -max_before, -min_before, "time_to_index_spell"
    )

    # Pivot each row (each prescription) to one column per
    # prescription group.
    all_counts = counting.count_events(
        swd_index_spells, events_before_index, "group"
    ).add_prefix("prior_")

    return all_counts
