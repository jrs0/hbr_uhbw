"""Utilities for counting clinical codes satisfying conditions
"""

from pandas import DataFrame, Series
from datetime import timedelta


def get_all_other_codes(
    index_spells: DataFrame, episodes: DataFrame, codes: DataFrame
) -> DataFrame:
    """For each patient, get clinical codes in other episodes before/after the index

    This makes a table of index episodes (which is the first episode of the index spell)
    along with all other episodes for a patient. Two columns `index_episode_id` and
    `other_episode_id` identify the two episodes for each row (they may be equal), and
    other information is stored such as the time of the base episode, the time to the
    other episode, and clinical code information for the other episode.

    This table is used as the basis for all processing involving counting codes before
    and after an episode.

    !!! note
        Episodes will not be included in the result if they do not have any clinical
            codes that are in any code group.

    Args:
        index_spells: Contains `episode_id` as an index.
        episodes: Contains `episode_id` as an index, and `patient_id` and `episode_start` as columns
        codes: Contains `episode_id` and other code data as columns

    Returns:
        A table containing columns `index_episode_id`, `other_episode_id`,
            `index_episode_start`, `time_to_other_episode`, and code data columns
            for the other episode. Note that the base episode itself is included
            as an other episode.
    """

    # Remove everything but the index episode_id (in case base_episodes
    # already has the columns)
    df = index_spells.reset_index(names="spell_id").set_index("episode_id")[
        ["spell_id"]
    ]

    index_episode_info = df.merge(
        episodes[["patient_id", "episode_start"]], how="left", on="episode_id"
    ).rename(
        columns={"episode_start": "index_episode_start", "spell_id": "index_spell_id"}
    )

    other_episodes = (
        index_episode_info.reset_index(names="index_episode_id")
        .merge(
            episodes[["episode_start", "patient_id", "spell_id"]].reset_index(
                names="other_episode_id"
            ),
            how="left",
            on="patient_id",
        )
        .rename(columns={"spell_id": "other_spell_id"})
    )

    other_episodes["time_to_other_episode"] = (
        other_episodes["episode_start"] - other_episodes["index_episode_start"]
    )

    # Use an inner join to filter out other episodes that have no associated codes
    # in any group.
    with_codes = other_episodes.merge(
        codes, how="inner", left_on="other_episode_id", right_on="episode_id"
    ).drop(columns=["patient_id", "episode_start", "episode_id"])

    return with_codes


def get_time_window(
    time_diff_table: DataFrame,
    window_start: timedelta,
    window_end: timedelta,
    time_diff_column: str = "time_to_other_episode",
) -> DataFrame:
    """Get events that occurred in a time window with respect to a base event

    Use the time_diff_column column to filter the time_diff_table to just those
    that occurred between window_start and window_end with respect to the base. 
    For example, rows can represent an index episode paired with other episodes,
    with the time_diff_column representing the time to the other episode.

    The arguments window_start and window_end control the minimum and maximum 
    values for the time difference. Use positive values for a window after the 
    base event, and use negative values for a window before the base event.

    Events on the boundary of the window are included.

    Note that the base event itself will be included as a row if window_start
    is negative and window_end is positive.

    Args:
        time_diff_table: Table containing at least the `time_diff_column`
        window_start: The smallest value of `time_diff_column` that will be included
            in the returned table. Can be negative, meaning events before the base
            event will be included.
        window_end: The largest value of `time_diff_column` that will be included in
            the returned table. Can be negative, meaning events after the base
            will be included.
        time_diff_column: The name of the column containing the time difference,
            which is positive for an event occurring after the base event.

    Returns:
        The rows within the specific time window
    """
    df = time_diff_table
    return df[
        (df[time_diff_column] <= window_end) & (df[time_diff_column] >= window_start)
    ]


def filter_by_code_groups(
    episodes: DataFrame,
    code_groups: list[str],
    primary_only: bool,
    exclude_index_spell: bool,
    first_episode_only: bool,
) -> DataFrame:
    """Filter based on matching code conditions occurring in other episodes

    From any table derived from get_all_other_episodes (e.g. the
    output of get_time_window), filter to only the other episodes
    which contain codes matching particular conditions.

    This function is intended to be used in conjunction with

    Args:
        episodes: Table of other episodes to filter.
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

        code_groups: List of code group names containing clinical codes
            that will remain in the result.
        primary_only: If False, count any code in any diagnosis/procedure
            position. If True, only count a code if it is the primary
            diagnosis/procedure.
        exclude_index_spell: Do not include any code in the count if it
            is from an episode in the index spell.
        first_episode_only: Only count codes if they come from the first
            episode of a spell.

    Returns:
        A series containing the number of code group occurrences in the
            other_episodes table.
    """

    # Reduce to only the code groups of interest
    df = episodes
    df = df[df["group"].isin(code_groups)]

    # Duplicated rows correspond to codes in multiple
    # code groups. A code is duplicated like this if it
    # has the same type (diagnosis/procedure) and position as
    # another code in the same other episode.
    df = df.drop_duplicates(["other_episode_id", "type", "position"])

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

    # Optionally retain only the first episode in each other spell.
    # BUG: there is an issue here if the other_episode_start has only
    # day granularity, and the first and second episodes begin on the
    # same day.
    if first_episode_only:
        df = df.sort_values("time_to_other_episode").groupby("other_spell_id").head(1)

    # Optionally exclude secondary diagnoses/procedures
    if primary_only:
        df = df[df["position"] == 1]

    return df


def count_code_groups(index_spells: DataFrame, filtered_episodes: DataFrame) -> Series:
    """Count the number of matching codes relative to index episodes

    This function counts the rows for each index spell ID in the output of
    filter_by_code_groups, and adds 0 for any index spell ID without
    any matching rows in filtered_episodes.

    The intent is to count the number of codes (one per row) that matched
    filter conditions in other episodes with respect to the index spell.

    Args:
        index_spells: The index spells, which provides the list of
            spell IDs of interest. The output will be NA for any spell
            ID that does not have any matching rows in filtered_episodes.
        filtered_episodes: The output from filter_by_code_groups,
            which produces a table where each row represents a matching
            code.

    Returns:
        How many codes (rows) occurred for each index spell
    """
    df = (
        filtered_episodes.groupby("index_spell_id")
        .size()
        .rename("count")
        .to_frame()
        .reset_index(names="spell_id")
        .set_index("spell_id")
    )
    return index_spells[[]].merge(df, how="left", on="spell_id").fillna(0)["count"]

def count_events(index_spells: DataFrame, events: DataFrame, event_name: str) -> DataFrame:
    """Count the occurrences (rows) of an event given in long format.
    
    The input table (events) contains instances of events, one per row,
    where the event_name contains the name of a string column labelling the
    events. The table also contains a `spell_id` column, which may be 
    associated with multiple rows.
    
    The function pivots the events so that there is one row per spell,
    each event has its own column, and the table contains the total number
    of each event associated with the spell.

    The index_spells table is required because some index spells may have
    no events. These index spells will have a row of zeros in the output.

    Args:
        index_spells: Must have Pandas index `spell_id`
        events: Contains a `spell_id` column and an event_name
            column.

    Returns:
        A table of the counts for each event (one event per column), with
            Pandas index `spell_id`.
    """

    # Pivot the prescriptions into one column per medicine type,
    # and prefix the name with "prior_" (e.g. "prior_oac").
    nonzero_counts = (
        events.groupby("spell_id")[event_name]
        .value_counts()
        .unstack(fill_value=0)
    )
    all_counts = (
        index_spells[[]].merge(nonzero_counts, how="left", on="spell_id").fillna(0)
    )
    return all_counts