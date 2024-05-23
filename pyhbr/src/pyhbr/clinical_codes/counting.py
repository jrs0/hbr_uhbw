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