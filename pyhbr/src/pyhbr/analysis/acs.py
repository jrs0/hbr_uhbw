import datetime as dt
from pandas import DataFrame, Series
from pyhbr.clinical_codes import counting
from pyhbr.analysis import describe
from pyhbr.middle import from_hic  # Need to move the function
import pandas as pd


def get_index_spells(
    episodes: DataFrame,
    codes: DataFrame,
    acs_group: str,
    pci_group: str | None,
    stemi_group: str,
    nstemi_group: str,
) -> DataFrame:
    """Get the index spells for ACS/PCI patients

    Index spells are defined by the contents of the first episode of
    the spell (i.e. the cause of admission to hospital). Spells are
    considered an index event if either of the following hold:

    * The primary diagnosis of the first episode contains an
      ACS ICD-10 code. This is to ensure that only episodes where the
      main diagnosis of the episode is ACS are considered, and not
      cases where a secondary ACS is present that could refer to a
      historical event.
    * There is a PCI procedure in any primary or secondary position
      in the first episode of the spell. It is assumed that a procedure
      is only coded in secondary positions if it did occur in that
      episode.

    A prerequisite for spell to be an index spell is that it contains
    episodes present in both the episodes and codes tables. The episodes table
    contains start-time/spell information, and the codes table contains
    information about what diagnoses/procedures occurred in each episode.

    The table returned contains one row per index spell (and is indexed by
    spell id). It also contains other information about the index spell,
    which is derived from the first episode of the spell.

    Args:
        episodes: All patient episodes. Must contain `episode_id`, `spell_id`
            and `episode_start`, `age` and `gender`.
        codes: All diagnosis/procedure codes by episode. Must contain
            `episode_id`, `position` (indexed from 1 which is the primary
            code, >1 are secondary codes), and `group` (expected to contain
            the value of the acs_group and pci_group arguments).
        acs_group: The name of the ICD-10 code group used to define ACS.
        pci_group: The name of the OPCS-4 code group used to define PCI. Pass None
            to not use PCI as an inclusion criterion for index events. In this
            case, the pci_index column is omitted, and only ACS primary diagnoses
            are allowed.
        stemi_group: The name of the ICD-10 code group used to identify STEMI MI
        nstemi_group: The name of the ICD-10 code group used to identify NSTEMI MI

    Returns:
        A table of index spells and associated information about the
            first episode of the spell.
    """

    # Index spells are defined by the contents of the first episode in the
    # spell (to capture the cause of admission to hospital).
    first_episodes = episodes.sort_values("episode_start").groupby("spell_id").head(1)

    # In the codes dataframe, if one code is in multiple groups, it gets multiple
    # (one per code group). Concatenate the code groups to reduce to one row per
    # code, then use str.contains() later to identify code groups
    reduced_codes = codes.copy()
    non_group_cols = [c for c in codes.columns if c != "group"]
    reduced_codes["group"] = codes.groupby(non_group_cols)["group"].transform(
        lambda x: ",".join(x)
    )
    reduced_codes = reduced_codes.drop_duplicates()

    # Join the diagnosis/procedure codes. The inner join reduces to episodes which
    # have codes in any group, which is a superset of the index episodes -- if an
    # episode has no codes in any code group, it cannot be an index event.
    first_episodes_with_codes = first_episodes.merge(
        reduced_codes, how="inner", on="episode_id"
    )

    # ACS matches based on a primary diagnosis of ACS (this is to rule out
    # cases where patient history may contain ACS recorded as a secondary
    # diagnosis).
    acs_match = (first_episodes_with_codes["group"].str.contains(acs_group)) & (
        first_episodes_with_codes["position"] == 1
    )

    # A PCI match is allowed anywhere in the procedures list, but must still
    # be present in the first episode of the index spell.
    if pci_group is not None:
        pci_match = first_episodes_with_codes["group"].str.contains(pci_group)
    else:
        pci_match = False

    # Get all the episodes matching the ACS or PCI condition (multiple rows
    # per episode)
    matching_episodes = first_episodes_with_codes[acs_match | pci_match]
    matching_episodes.set_index("episode_id", drop=True, inplace=True)

    index_spells = DataFrame()

    # Reduce to one row per episode, and store a flag for whether the ACS
    # or PCI condition was present. If PCI is none, there is no need for these
    # columns because all rows are ACS index events
    if pci_group is not None:
        index_spells["pci_index"] = (
            matching_episodes["group"].str.contains(pci_group).groupby("episode_id").any()
        )
        index_spells["acs_index"] = (
            matching_episodes["group"].str.contains(acs_group).groupby("episode_id").any()
        )
        
    # The stemi/nstemi columns are always needed to distinguish the type of ACS. If 
    # both are false, the result is unstable angina
    index_spells["stemi_index"] = (
        matching_episodes["group"].str.contains(stemi_group).groupby("episode_id").any()
    )   
    index_spells["nstemi_index"] = (
        matching_episodes["group"]
        .str.contains(nstemi_group)
        .groupby("episode_id")
        .any()
    )

    # Join some useful information about the episode
    index_spells = (
        index_spells.merge(
            episodes[["patient_id", "episode_start", "spell_id", "age", "gender"]],
            how="left",
            on="episode_id",
        )
        .rename(columns={"episode_start": "spell_start"})
        .reset_index("episode_id")
        .set_index("spell_id")
    )

    # Convert the age column to a float. This should probably
    # be done upstream
    index_spells["age"] = index_spells["age"].astype(float)

    return index_spells


def identify_fatal_outcome(
    index_spells: DataFrame,
    date_of_death: DataFrame,
    cause_of_death: DataFrame,
    outcome_group: str,
    max_position: int,
    max_after: dt.timedelta,
) -> Series:
    """Get fatal outcomes defined by a diagnosis code in a code group

    Args:
        index_spells: A table containing `spell_id` as Pandas index and a
            column `episode_id` for the first episode in the index spell.
        date_of_death: Contains a column date_of_death, with Pandas index
            `patient_id`
        cause_of_death: Contains columns `patient_id`, `code` (ICD-10) for
            cause of death, `position` of the code, and `group`.
        outcome_group: The name of the ICD-10 code group which defines the fatal
            outcome.
        max_position: The maximum primary/secondary cause of death that will be
            checked for the code group.
        max_after: The maximum follow-up period after the index for valid outcomes.

    Returns:
        A series of boolean containing whether a fatal outcome occurred in the follow-up
            period.
    """

    # Inner join to get a table of index patients with death records
    mortality_after_index = (
        index_spells.reset_index()
        .merge(date_of_death, on="patient_id", how="inner")
        .merge(cause_of_death, on="patient_id", how="inner")
    )
    mortality_after_index["survival_time"] = (
        mortality_after_index["date_of_death"] - mortality_after_index["spell_start"]
    )

    # Reduce to only the fatal outcomes that meet the time window and
    # code inclusion criteria
    df = mortality_after_index[
        (mortality_after_index["survival_time"] < max_after)
        & (mortality_after_index["position"] <= max_position)
        & (mortality_after_index["group"] == outcome_group)
    ]

    # Rename the id columns to be compatible with counting.count_code_groups
    # and select columns of interest
    return df.rename(columns={"spell_id": "index_spell_id"})[
        ["index_spell_id", "survival_time", "code", "position", "docs", "group"]
    ]


def get_survival_data(
    index_spells: DataFrame,
    fatal: DataFrame,
    non_fatal: DataFrame,
    max_after: dt.timedelta,
) -> DataFrame:
    """Get survival data from fatal and non-fatal outcomes

    Args:
        index_spells: The index spells, indexed by `spell_id`
        fatal: The table of fatal outcomes, containing a `survival_time` column
        non_fatal: The table of non-fatal outcomes, containing a `time_to_other_episode` column
        max_after: The right censor time. This is the maximum time for data contained in the
            fatal and non_fatal tables; any index spells with no events in either table
            will be right-censored with this time.

    Returns:
        The survival data containing both fatal and non-fatal events. The survival time is the
            `time_to_event` column, the `fatal` column contains a flag indicating whether the
            event was fatal, and the `right_censor` column indicates whether the survival time
            is censored. The `code` and `docs` column provide information about the type of
            event for non-censored data (NA otherwise).
    """
    # Get bleeding survival analysis data (for both fatal
    # and non-fatal bleeding). First, combine the fatal
    # and non-fatal data
    cols_to_keep = ["index_spell_id", "code", "docs", "time_to_event"]
    non_fatal_survival = non_fatal.rename(
        columns={"time_to_other_episode": "time_to_event"}
    )[cols_to_keep]
    non_fatal_survival["fatal"] = False
    fatal_survival = fatal.rename(columns={"survival_time": "time_to_event"})[
        cols_to_keep
    ]
    fatal_survival["fatal"] = True
    survival = pd.concat([fatal_survival, non_fatal_survival])

    # Take only the first event for each index spell
    first_event = (
        survival.sort_values("time_to_event")
        .groupby("index_spell_id")
        .head(1)
        .set_index("index_spell_id")
    )
    first_event["right_censor"] = False
    with pd.option_context("future.no_silent_downcasting", True):
        with_censor = (
            index_spells[[]]
            .merge(first_event, left_index=True, right_index=True, how="left")
            .fillna({"fatal": False, "time_to_event": max_after, "right_censor": True})
            .infer_objects(copy=False)
        )
    return with_censor


def filter_by_code_groups(
    episode_codes: DataFrame,
    code_group: str,
    max_position: int,
    exclude_index_spell: bool,
) -> DataFrame:
    """Filter based on matching code conditions occurring in other episodes

    From any table derived from get_all_other_episodes (e.g. the
    output of get_time_window), identify clinical codes (and
    therefore episodes) which correspond to an outcome of interest.

    The input table has one row per clinical code, which is grouped
    into episodes and spells by other columns. The outcome only
    contains codes that define an episode or spell as an outcome.
    The result from this function can be used to analyse the make-up
    of outcomes.

    Args:
        episode_codes: Table of other episodes to filter.
            This can be narrowed to either the previous or subsequent
            year, or a different time frame. (In particular, exclude the
            index event if required.) The table must contain these
            columns:

            * `other_episode_id`: The ID of the other episode
                containing the code (relative to the index episode).
            * `other_spell_id`: The spell containing the other episode.
            * `group`: The name of the code group.
            * `type`: The code type, "diagnosis" or "procedure".
            * `position`: The position of the code (1 for primary, > 1
                for secondary).
            * `time_to_other_episode`: The time elapsed between the index
                episode start and the other episode start.

        code_group: The code group name used to identify outcomes
        max_position: The maximum clinical code position that will be allowed
            to define an outcome. Pass 1 to allow primary diagnosis only,
            2 to allow primary diagnosis and the first secondary diagnosis,
            etc.
        exclude_index_spell: Do not allow any code present in the index
            spell to define an outcome.

    Returns:
        A series containing the number of code group occurrences in the
            other_episodes table.
    """

    # Reduce to only the code groups of interest
    df = episode_codes[episode_codes["group"] == code_group]

    # Keep only necessary columns
    df = df[
        [
            "index_spell_id",
            "other_spell_id",
            "code",
            "docs",
            "position",
            "time_to_other_episode",
        ]
    ]

    # Optionally remove rows corresponding to the index spell
    if exclude_index_spell:
        df = df[~(df["other_spell_id"] == df["index_spell_id"])]

    # Only keep codes that match the position-based inclusion criterion
    df = df[df["position"] <= max_position]

    return df


def get_outcomes(
    index_spells: DataFrame,
    all_other_codes: DataFrame,
    date_of_death: DataFrame,
    cause_of_death: DataFrame,
    non_fatal_group: str,
    fatal_group: str,
) -> DataFrame:
    """Get non-fatal and fatal outcomes defined by code groups

    Args:
        index_spells: A table containing `spell_id` as Pandas index and a
            column `episode_id` for the first episode in the index spell.
        all_other_codes: A table of other episodes (and their clinical codes)
            relative to the index spell, output from counting.get_all_other_codes.
        date_of_death: Contains a column date_of_death, with Pandas index
            `patient_id`
        cause_of_death: Contains columns `patient_id`, `code` (ICD-10) for
            cause of death, `position` of the code, and `group`.
        non_fatal_group: The name of the ICD-10 group defining the non-fatal
            outcome (the primary diagnosis of subsequent episodes are checked
            for codes in this group)
        fatal_group: The name of the ICD-10 group defining the fatal outcome
            (the primary diagnosis in the cause-of-death is checked for codes
            in this group).

    Returns:
        A dataframe, indexed by `spell_id` (i.e. the index spell), with columns
            `all` (which counts the total fatal and non-fatal outcomes),
            and `fatal` (which just contains the fatal outcome)
    """

    # Follow-up time for fatal and non-fatal events
    max_after = dt.timedelta(days=365)

    # Properties of non-fatal events
    primary_only = True
    exclude_index_spell = False
    first_episode_only = False
    min_after = dt.timedelta(hours=48)

    # Work out fatal outcome
    fatal = get_fatal_outcome(
        index_spells, date_of_death, cause_of_death, fatal_group, max_after
    )

    # Get the episodes (and all their codes) in the follow-up window
    following_year = counting.get_time_window(all_other_codes, min_after, max_after)

    # Get non-fatal outcome
    outcome_episodes = filter_by_code_groups(
        following_year,
        [non_fatal_group],
        primary_only,
        exclude_index_spell,
        first_episode_only,
    )
    non_fatal = counting.count_code_groups(index_spells, outcome_episodes)

    return DataFrame({"all": non_fatal + fatal, "fatal": fatal})


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
    max_position = 999  # Allow any primary/secondary position
    exclude_index_spell = False
    max_before = dt.timedelta(days=365)
    min_before = dt.timedelta(days=30)

    # Get the episodes that occurred in the previous year (for clinical code features)
    previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)

    code_features = {}
    for group in code_groups:
        group_episodes = filter_by_code_groups(
            previous_year,
            group,
            max_position,
            exclude_index_spell,
        )
        code_features[group + "_before"] = counting.count_code_groups(
            index_spells, group_episodes
        )

    return DataFrame(code_features)


def link_attribute_period_to_index(
    index_spells: DataFrame, primary_care_attributes: DataFrame
) -> DataFrame:
    """Link primary care attributes to index spells by attribute date

    The date column of an attributes row indicates that
    the attribute was valid at the end of the interval
    (date, date + 1month). It is important
    that no attribute is used in modelling that could have occurred
    after the index event, meaning that date + 1month < spell_start
    must hold for any attribute used as a predictor. On the other hand,
    data substantially before the index event should not be used. The
    valid window is controlled by imposing:

        date < spell_start - attribute_valid_window

    Args:
        index_spells: The index spell table, containing a `spell_start`
            column and `patient_id`
        primary_care_attributes: The patient attributes table, containing
            `date` and `patient_id`

    Returns:
        The index_spells table with a `date` column added to link the
            attributes (along with `patient_id`). This may be NaT if 
            there is no valid attribute for this index event.
    """

    # Define a window before the index event where SWD attributes will be considered valid.
    # 41 days is used to ensure that a full month is definitely captured. This
    # ensures that attribute data that is fairly recent is used as predictors.
    attribute_valid_window = dt.timedelta(days=60)

    # Add all the patient's attributes onto each index spell
    df = index_spells.reset_index().merge(
        primary_care_attributes[["patient_id", "date"]],
        how="left",
        on="patient_id",
    )

    # Only keep attributes that are from strictly before the index spell
    # (note date represents the start of the month that attributes
    # apply to)
    attr_before_index = df[(df["date"] + dt.timedelta(days=31)) < df["spell_start"]]

    # Keep only the most recent attribute before the index spell
    most_recent = attr_before_index.sort_values("date").groupby("spell_id").tail(1)

    # Exclude attributes that occurred outside the attribute_value_window before the index
    swd_index_spells = most_recent[
        most_recent["date"] > (most_recent["spell_start"] - attribute_valid_window)
    ]

    return index_spells.merge(
        swd_index_spells[["spell_id", "date"]].set_index("spell_id"),
        how="left",
        on="spell_id",
    )


def get_index_attributes(
    swd_index_spells: DataFrame, primary_care_attributes: DataFrame
) -> DataFrame:
    """Link the primary care patient data to the index spells

    Args:
        swd_index_spells: Index_spells linked to a a recent, valid
            patient attributes row. Contains the columns `patient_id` and
            `date` for linking, and has Pandas index `spell_id`.
        primary_care_attributes: The full attributes table.

    Returns:
        The table of index-spell patient attributes, indexed by `spell_id`.
    """

    return (
        (
            swd_index_spells[["patient_id", "date"]]
            .reset_index()
            .merge(
                primary_care_attributes,
                how="left",
                on=["patient_id", "date"],
            )
        )
        .set_index("spell_id")
        .drop(columns=["patient_id", "date"])
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


def get_secondary_care_prescriptions_features(
    prescriptions: DataFrame, index_spells: DataFrame, episodes: DataFrame
) -> DataFrame:
    """Get dummy feature columns for OAC and NSAID medications on admission

    Args:
        prescriptions: The table of secondary care prescriptions, containing
            a `group` column and `spell_id`.
        index_spells: The index spells, which must be indexed by `spell_id`
        episodes: The episodes table containing `admission` and `discharge`,
            for linking prescriptions to spells.
    """

    # Get all the data required
    df = (
        index_spells.reset_index("spell_id")
        .merge(prescriptions, on="patient_id", how="left")
        .merge(episodes[["admission", "discharge"]], on="episode_id", how="left")
    )

    # Keep only prescriptions ordered between admission and discharge
    # marked as present on admission
    within_spell = (df["order_date"] >= df["admission"]) & (
        df["order_date"] <= df["discharge"]
    )

    # Filter and create dummy variables for on-admission medication
    dummies = (
        pd.get_dummies(
            df[within_spell & df["on_admission"]].set_index("spell_id")["group"]
        )
        .groupby("spell_id")
        .max()
        .astype(int)
    )

    # Join back onto index events and set missing entries to zero
    return index_spells[[]].merge(dummies, how="left", on="spell_id").fillna(0)
