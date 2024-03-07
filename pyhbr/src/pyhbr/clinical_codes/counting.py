"""Utilities for counting clinical codes satisfying conditions
"""

from pandas import DataFrame

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