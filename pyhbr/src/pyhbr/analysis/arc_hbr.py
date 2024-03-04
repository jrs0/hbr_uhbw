"""Calculation of the ARC HBR score
"""

import pandas as pd


def index_episodes(episodes: pd.DataFrame, codes: pd.DataFrame) -> pd.DataFrame:
    """Get the index episodes for ACS/PCI patients

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
        episodes: All patient episodes. Must contain `episode_id`, `spell_id`
            and `episode_start`.
        codes: All diagnosis/procedure codes by episode. Must contain
            `episode_id`, `position` (indexed from 1 which is the primary
            code, >1 are secondary codes), and `group` (containing either `acs`
            or `pci`).

    Returns:
        The index episodes.
    """

    # Index episodes are defined by the contents of the first episode in the
    # spell (to capture to cause of admission to hospital).
    first_episodes = episodes.sort_values("episode_start").groupby("spell_id").head(1)

    # Join the diagnosis/procedure codes (inner join reduces to episodes which
    # have codes in any group, which is a superset of the index episodes)
    first_episodes_with_codes = pd.merge(
        first_episodes, codes, how="inner", on="episode_id"
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
    index_episodes = pd.DataFrame()
    index_episodes["acs_index"] = (
        matching_episodes["group"].eq("acs_bezin").groupby("episode_id").any()
    )
    index_episodes["pci_index"] = (
        matching_episodes["group"].eq("pci").groupby("episode_id").any()
    )

    # Join some useful information about the episode
    return index_episodes.merge(
        episodes[["patient_id", "episode_start"]], how="left", on="episode_id"
    )
