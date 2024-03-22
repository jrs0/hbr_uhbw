from pyhbr.middle.from_hic import HicData

def get_patient_history(patient_id: str, hic_data: HicData):
    """Get a list of all this patient's episode data

    Args:
        patient_id: Which patient to fetch
        hic_data: Contains `episodes` and `codes` tables

    Returns:
        A table indexed by spell_id, episode_id, type (of clinical code)
            and clinical code position.
    """
    df = hic_data.codes.merge(
        hic_data.episodes[["patient_id", "spell_id", "episode_start"]],
        how="left",
        on="episode_id",
    )
    this_patient = (
        df[df["patient_id"] == patient_id]
        .sort_values(["episode_start", "type","position"])
        .drop(columns="group")
        .set_index(["spell_id", "episode_id", "type", "position"])
    ).drop_duplicates()
    return this_patient