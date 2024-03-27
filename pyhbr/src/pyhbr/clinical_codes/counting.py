"""Utilities for counting clinical codes satisfying conditions
"""

from pandas import DataFrame, Series
from datetime import timedelta


def get_all_other_codes(
    index_spells: DataFrame, data: dict[str, DataFrame]
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
        data: A dictionary containing two DataFrame values:
            * "episodes": Contains `episode_id` as an index, and `patient_id` and `episode_start` as columns
            * "codes": Contains `episode_id` and other code data as columns

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
        data["episodes"][["patient_id", "episode_start"]], how="left", on="episode_id"
    ).rename(
        columns={"episode_start": "index_episode_start", "spell_id": "index_spell_id"}
    )

    other_episodes = (
        index_episode_info.reset_index(names="index_episode_id")
        .merge(
            data["episodes"][["episode_start", "patient_id", "spell_id"]].reset_index(
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
        data["codes"], how="inner", left_on="other_episode_id", right_on="episode_id"
    ).drop(columns=["patient_id", "episode_start", "episode_id"])

    return with_codes


def get_time_window(
    all_other_codes: DataFrame, window_start: timedelta, window_end: timedelta
) -> DataFrame:
    """Get the episodes that occurred in a time window with respect to the base episode

    Use the time_to_other_episode column to filter the all_other_codes
    table to just those that occurred between window_start and window_end
    with respect to the the base episode.

    The arguments window_start and window_end are time differences between the other
    episode and the base episode. Use positive values for a window after the base,
    and use negative values for a window before the base.

    Episodes on the boundary of the window are included.

    Note that the base episode itself will be included as a row if window_start
    is negative and window_end is positive (i.e. the window includes episodes before
    and after the base).

    Args:
        all_other_codes: Table containing at least `time_to_other_episode`
        window_start: The smallest value of time_to_other_episode that will be included
            in the returned table. Can be negative, meaning episode before the base
            will be included.

        window_end: The largest value of time_to_other_episode that will be included in
            the returned table. Can be negative, meaning only episodes before the base
            will be included.

    Returns:
        The episodes within the specified window range.
    """
    df = all_other_codes
    return df[
        (df["time_to_other_episode"] <= window_end)
        & (df["time_to_other_episode"] >= window_start)
    ]


def count_code_groups(
    index_spells: DataFrame,
    other_episodes: DataFrame,
    code_groups: list[str],
    any_position: bool,
    exclude_index_spell: bool,
    first_episode_only: bool,
) -> Series:
    """Count occurrences of a code group in a set of other episodes

    Count the total occurrences of the codes in any of a list of
    code groups in the other episodes relative to the index spells.

    Note that the index episode itself will not necessarily be
    excluded from the count (if other_episodes contains the index
    episode, and exclude_index_spell is False).

    Args:
        index_episodes: Any DataFrame with `spell_id` as Pandas index and
            containing an `episode_id` column.
        other_episodes: Table of other episodes (relative to the index).
            This can be narrowed to either the previous or subsequent
            year, or a different time frame. (In particular, exclude the
            index event if required.)
        code_groups: List of code group names containing clinical codes
            that will count towards the sum.
        any_position: If True, count any code in any diagnosis/procedure
            position. If False, only count a code if it is the primary
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
    df = other_episodes
    df = df[df["group"].isin(code_groups)]

    # Duplicated rows correspond to codes in multiple
    # code groups. A code is duplicated if it has the
    # same type (diagnosis/procedure) and position as
    # another code in the same other episode.
    df = df.drop_duplicates(["other_episode_id", "type", "position"])

    # Keep only necessary columns
    df = df[["index_spell_id", "other_spell_id", "position", "time_to_other_episode"]]

    # Optionally remove rows corresponding to the index spell
    if exclude_index_spell:
        df = df[~(df["other_spell_id"] == df["index_spell_id"])]

    # Optionally retain only the first episode in each other spell.
    # BUG: there is an issue here if the other_episode_start has only
    # day granularity, and the first and second episodes begin on the
    # same day.
    if first_episode_only:
        df = df.groupby("other_spell_id").sort_values("time_to_other_episode").head(1)

    # Optionally exclude secondary diagnoses/procedures
    if not any_position:
        df = df[df["position"] == 1]

    # Rows now correspond to codes that can be counted relative to the index spell
    code_group_count = df.groupby("index_spell_id").size().rename("code_group_count")

    return (
        index_spells[[]]
        .merge(code_group_count, how="left", left_index=True, right_index=True)
        .fillna(0.0)["code_group_count"]
    )
