"""Utilities for counting clinical codes satisfying conditions
"""

from pandas import DataFrame, Series
from datetime import timedelta

def get_all_other_codes(
    base_episodes: DataFrame, episodes: DataFrame, codes: DataFrame
) -> DataFrame:
    """For each patient, get clinical codes in other episodes before/after the base

    This makes a table of base episodes along with all other episodes for a patient.
    Two columns `base_episode_id` and `other_episode_id` identify the two episodes
    for each row (they may be equal), and other information is stored such as the
    time of the base episode, the time to the other episode, and clinical code information
    for the other episode.

    This table is used as the basis for all processing involving counting codes before
    and after an episode.

    Args:
        base_episodes: Contains `episode_id` as an index.
        episodes: Contains `episode_id` as an index, and `patient_id` and `episode_start` as columns
        codes: Contains `episode_id` and other code data as columns

    Returns:
        A table containing columns `base_episode_id`, `other_episode_id`,
            `base_episode_start`, `time_to_other_episode`, and code data columns
            for the other episode. Note that the base episode itself is included
            as an other episode.
    """

    # Remove everything but the index episode_id (in case base_episodes
    # already has the columns)
    df = base_episodes[[]]

    base_episode_info = df.merge(
        episodes[["patient_id", "episode_start"]], how="left", on="episode_id"
    ).rename(columns={"episode_start": "base_episode_start"})
    
    other_episodes = base_episode_info.reset_index(names="base_episode_id").merge(
        episodes[["episode_start", "patient_id"]].reset_index(names="other_episode_id"),
        how="left",
        on="patient_id",
    )

    other_episodes["time_to_other_episode"] = (
        other_episodes["episode_start"] - other_episodes["base_episode_start"]
    )

    with_codes = other_episodes.merge(
        codes, how="left", left_on="other_episode_id", right_on="episode_id"
    ).drop(columns=["patient_id", "episode_start", "episode_id"])

    return with_codes

def get_previous_year(
    all_other_codes: DataFrame, min_before: timedelta, max_before: timedelta
) -> DataFrame:
    """Get the episodes that occurred before the base episode

    Use the time_to_other_episode column to filter the all_other_codes
    table to just those that occurred between max_before and min_before
    the base episode.

    Both min_before and max_before are positive-valued.

    Args:
        all_other_codes: Table containing at least `time_to_other_episode`
        min_before: Other episodes will be included if they occurred at least min_before
            time before the base episode
        max_before: Other episodes will be included if they occurred at most max_before
            time before the base episode

    Returns:
        The episodes within the specified date range.
    """
    df = all_other_codes
    return df[
        (df["time_to_other_episode"] <= -min_before)
        & (df["time_to_other_episode"] >= -max_before)
    ]



def count_code_groups(
    index_episodes: DataFrame,
    other_episodes: DataFrame,
    code_groups: list[str],
    any_position: bool,
) -> Series:
    """Count occurrences of prior code group in the previous year

    Count the total occurrences of a codes in any of code_groups in
    the other episodes before the index episode specified in
    previous_year.

    Note that the index episode itself will not necessarily be
    excluded from the count (if other_episodes contains the index
    episode).

    Args:
        index_episodes: Any DataFrame with `episode_id` as index
        other_episodes: Table of other episodes (relative to the index).
            This can be narrowed to either the previous or subsequent
            year, or a different time frame. (In particular, exclude the
            index event if required.)
        code_groups: List of code group names containing clinical codes
            that will count towards the sum.
        any_position: If True, count any code in any diagnosis/procedure
            position. If False, only count a code if it is the primary
            diagnosis/procedure.

    TODO: add another argument for first_episode (bool), to narrow to
    first episode of spell. Needs spell_id in the all_other_codes table.

    Returns:
        A series containing the number of code group occurrences in the
            other_episodes table.
    """

    code_group_count = (
        other_episodes[
            (any_position | (other_episodes["position"] == 1))
            & (other_episodes["group"].isin(code_groups))
        ]
        .groupby("base_episode_id")
        .size()
        .rename("code_group_count")
    )

    return (
        index_episodes[[]]
        .merge(code_group_count, how="left", left_index=True, right_index=True)
        .fillna(0.0)
    )