import datetime as dt
from pandas import DataFrame
from pyhbr.clinical_codes import counting


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