"""Calculation of the ARC HBR score
"""

import numpy as np
from pandas import DataFrame, Series, cut
import seaborn as sns
from pyhbr.middle.from_hic import HicData
from pyhbr.clinical_codes import counting


def get_gender(index_episodes: DataFrame, demographics: DataFrame) -> Series:
    """Get gender from the demographics table for each index event

    Args:
        index_episodes: Indexed by `episode_id` and having column `patient_id`
        demographics: Having columns `patient_id` and `gender`.

    Returns:
        A series containing gender indexed by `episode_id`
    """
    gender = index_episodes.merge(demographics, how="left", on="patient_id")["gender"]
    gender.index = index_episodes.index
    return gender


def calculate_age(index_episodes: DataFrame, demographics: DataFrame) -> Series:
    """Calculate the patient age at index

    The HIC data contains only year_of_birth, which is used here. In order
    to make an unbiased estimate of the age, birthday is assumed to be
    2nd july (halfway through the year).

    Args:
        index_episodes: Contains `episode_start` date and column `patient_id`,
            indexed by `episode_id`.
        demographics: Contains `year_of_birth` date and index `patient_id`.

    Returns:
        A series containing age, indexed by `episode_id`.
    """
    df = index_episodes.merge(demographics, how="left", on="patient_id")
    age_offset = np.where(
        (df["episode_start"].dt.month < 7) & (df["episode_start"].dt.day < 2), 1, 0
    )
    age_at_index = df["episode_start"].dt.year - df["year_of_birth"] - age_offset
    age_at_index.index = index_episodes.index
    return age_at_index


def arc_hbr_age(has_age: DataFrame) -> Series:
    """Calculate the age ARC-HBR criterion

    Calculate the age ARC HBR criterion (0.5 points if > 75 at index, 0 otherwise.

    Args:
        has_age: Dataframe indexed by episode_id which has a column `age`

    Returns:
        A series of values 0.5 (if age > 75 at index) or 0 otherwise, indexed
            by `episode_id`.
    """
    return Series(np.where(has_age["age"] > 75, 0.5, 0), index=has_age.index)


def arc_hbr_oac(index_episodes: DataFrame, prescriptions: DataFrame) -> Series:
    """Calculate the oral-anticoagulant ARC HBR criterion

    1.0 point if an one of the OACs "warfarin", "apixaban",
    "rivaroxaban", "edoxaban", "dabigatran", is present
    in the index episode (meaning it was present on admission,
    or was prescribed in that episode).

    !!! note
        The on admission flag could be used to imply expected
        chronic/extended use, but this is not included as it filters
        out all OAC prescriptions in the HIC data.

    Args:
        index_episodes: Index `episode_id` is used to narrow prescriptions.
        prescriptions: Contains `name` (of medicine).

    Returns:
        The OAC ARC score for each index event.
    """
    df = index_episodes.merge(prescriptions, how="left", on="episode_id")
    oac_list = ["warfarin", "apixaban", "rivaroxaban", "edoxaban", "dabigatran"]
    oac_criterion = df["name"].isin(oac_list).astype("float")
    return Series(oac_criterion, index=index_episodes.index)


def arc_hbr_nsaid(index_episodes: DataFrame, prescriptions: DataFrame) -> Series:
    """Calculate the non-steroidal anti-inflamatory drug (NSAID) ARC HBR criterion

    1.0 point is added if an one of the following NSAIDs is present
    on admission:

    * Ibuprofen
    * Naproxen
    * Diclofenac
    * Celecoxib
    * Mefenamic acid
    * Etoricoxib
    * Indomethacin

    Args:
        index_episodes: Index `episode_id` is used to narrow prescriptions.
        prescriptions: Contains `name` (of medicine).

    Returns:
        The OAC ARC score for each index event.
    """
    df = index_episodes.merge(prescriptions, how="left", on="episode_id")
    nsaid_criterion = ((df["group"] == "nsaid") & (df["on_admission"] == True)).astype(
        "float"
    )
    return Series(nsaid_criterion, index=index_episodes.index)


def min_index_result(
    test_name: str, index_episodes: DataFrame, lab_results: DataFrame
) -> Series:
    """Get the lowest lab result associated to the index episode

    Getting the lowest value corresponds to the worst severity for
    measurements such as eGFR, Hb and platelet count.

    Args:
        index_episodes: Has an `episode_id` for filtering lab_results
        lab_results: Has a `test_name` column matching the `test_name` argument,
            and a `result` column for the numerical test result
        test_name: Which lab measurement to get.

    Returns:
        A series containing the minimum value of test_name in the index
            episode. Contains NaN if test_name was not recorded in the
            index episode.
    """
    df = index_episodes.merge(lab_results, how="left", on="episode_id")
    index_lab_result = df[df["test_name"] == test_name]

    # Pick the lowest result. For measurements such as platelet count,
    # eGFR, and Hb, lower is more severe.
    min_index_lab_result = index_lab_result.groupby("episode_id").min("result")

    # Some index episodes do not have an measurement, so join
    # to get all index episodes (NaN means no index measurement)
    min_result_or_nan = index_episodes.merge(
        min_index_lab_result["result"], how="left", on="episode_id"
    )

    return min_result_or_nan["result"].rename(f"index_{test_name}")


def first_index_spell_result(
    test_name: str,
    index_episodes: DataFrame,
    lab_results: DataFrame,
    episodes: DataFrame,
) -> Series:
    """Get the (first) lab result associated to the index spell

    Compared to min_index_result, this function accounts for the
    possibility that a lab result was not associated with the first
    episode of the spell, and is therefore missed. The minimum value
    is not taken, because of the possibility that a value in a later
    episode is smaller due to some other cause.

    Args:
        index_episodes: Has an `episode_id` index.
        lab_results: Has a `test_name` column matching the `test_name` argument,
            and a `result` column for the numerical test result.
        episodes: Required to obtain the other episodes in the same spell as
            the index episode. Has a `spell_id` column and an `episode_id` index.
        test_name: Which lab measurement to get.

    Returns:
        A series containing the minimum value of test_name in the index
            episode. Contains NaN if test_name was not recorded in the
            index episode.
    """

    # Find the spells that contain the index episodes. This is
    # used to get a list of all episodes in the index spells.
    index_spells = index_episodes[[]].merge(
        episodes["spell_id"], how="left", on="episode_id"
    ).set_index("spell_id")
    all_spell_episodes = index_spells.merge(
        episodes.reset_index(), how="left", on="spell_id"
    )[["episode_id", "spell_id"]]

    # Get the lab tests specified by test_name for all the episodes
    # which occur in the index spell.
    df = all_spell_episodes.merge(lab_results, how="left", on="episode_id")
    index_lab_result = df[df["test_name"] == "hb"]

    # Pick the first result. For measurements such as platelet count,
    # eGFR, and Hb, lower is more severe.
    first_lab_result = index_lab_result.sort_values("sample_date").groupby("spell_id").head(1)

    # Some index episodes do not have an measurement, so join
    # to get all index episodes (NaN means no index measurement)
    first_result_or_nan = index_episodes.merge(
        first_lab_result[["result", "episode_id"]], how="left", on="episode_id"
    )

    return first_result_or_nan["result"].rename(f"index_{test_name}")


def arc_hbr_ckd(has_index_egfr: DataFrame) -> Series:
    """Calculate the ARC HBR chronic kidney disease (CKD) criterion

    The ARC HBR CKD criterion is calculated based on the eGFR as
    follows:

    | eGFR                           | Score |
    |--------------------------------|-------|
    | eGFR < 30 mL/min               | 1.0   |
    | 30 mL/min \<= eGFR < 60 mL/min | 0.5   |
    | eGFR >= 60 mL/min              | 0.0   |

    If the eGFR is NaN, set score to zero (TODO: fall back to ICD-10
    codes in this case)

    Args:
        has_index_egfr: Dataframe having the column `min_index_egfr` (in units of mL/min)
            with the lowest eGFR measurement at index, or NaN which means no eGFR
            measurement was taken on the index episode.

    Returns:
        A series containing the CKD ARC criterion, based on the eGFR at
            index.
    """

    # Replace NaN values for now with 100 (meaning score 0.0)
    df = has_index_egfr["min_index_egfr"].fillna(90)

    # Using a high upper limit to catch any high eGFR values. In practice,
    # the highest value is 90 (which comes from the string ">90" in the database).
    return cut(df, [0, 30, 60, 10000], right=False, labels=[1.0, 0.5, 0.0])


def arc_hbr_anaemia(has_index_hb_and_gender: DataFrame) -> Series:
    """Calculate the ARC HBR anaemia (low Hb) criterion

    Calculates anaemia based on the worst (lowest) index Hb measurement
    and gender currently. Should be modified to take most recent Hb value
    or clinical code.

    Args:
        has_index_hb_and_gender: Dataframe having the column `min_index_hb` containing the
            lowest Hb measurement (g/dL) at the index event, or NaN if no Hb measurement
            was made. Also contains `gender` (categorical with categories "male",
            "female", and "unknown").

    Returns:
        A series containing the HBR score for the index episode.
    """

    df = has_index_hb_and_gender

    # Evaluated in order
    arc_score_conditions = [
        df["min_index_hb"] < 11.0,  # Major for any gender
        df["min_index_hb"] < 11.9,  # Minor for any gender
        (df["min_index_hb"] < 12.9) & (df["gender"] == "male"),  # Minor for male
        df["min_index_hb"] >= 12.9,  # None for any gender
    ]
    arc_scores = [1.0, 0.5, 0.5, 0.0]

    # Default is used to fill missing Hb score with 0.0 for now. TODO: replace with
    # fall-back to recent Hb, or codes.
    return Series(
        np.select(arc_score_conditions, arc_scores, default=0.0),
        index=df.index,
    )


def arc_hbr_tcp(has_index_platelets: DataFrame) -> Series:
    """Calculate the ARC HBR thrombocytopenia (low platelet count) criterion

    The score is 1.0 if platelet count < 100e9/L, otherwise it is 0.0.

    Args:
        has_index_platelets: Has column `min_index_platelets`, which is the worst-case
            platelet count measurement seen in the index episode.

    Returns:
        Series containing the ARC score
    """
    return Series(
        np.where(has_index_platelets["min_index_platelets"] < 100, 1.0, 0),
        index=has_index_platelets.index,
    )


def arc_hbr_prior_bleeding(has_prior_bleeding: DataFrame) -> Series:
    """Calculate the prior bleeding/transfusion ARC HBR criterion

    This function takes a dataframe with a column prior_bleeding_12
    with a count of the prior bleeding events in the previous year.

    TODO: Input needs a separate column for bleeding in 6 months and
    bleeding in a year, so distinguish 0.5 from 1. Also need to add
    transfusion.

    Args:
        has_prior_bleeding: Has a column `prior_bleeding_12` with a count
            of the number of bleeds occurring one year before the index.
            Has `episode_id` as the index.

    Returns:
        The ARC HBR bleeding/transfusion criterion (0.0, 0.5, or 1.0)
    """
    return Series(
        np.where(has_prior_bleeding["prior_bleeding_12"] > 0, 0.5, 0),
        index=has_prior_bleeding.index,
    )


def arc_hbr_cancer(has_prior_cancer: DataFrame) -> Series:
    """Calculate the cancer ARC HBR criterion

    This function takes a dataframe with a column prior_cancer
    with a count of the cancer diagnoses in the previous year.

    Args:
        has_prior_cancer: Has a column `prior_cancer` with a count
            of the number of cancer diagnoses occurring in the
            year before the index event.

    Returns:
        The ARC HBR cancer criterion (0.0, 1.0)
    """
    return Series(
        np.where(has_prior_cancer["prior_cancer"] > 0, 1.0, 0),
        index=has_prior_cancer.index,
    )


def arc_hbr_cirrhosis_ptl_hyp(has_prior_cirrhosis: DataFrame) -> Series:
    """Calculate the liver cirrhosis with portal hypertension ARC HBR criterion

    This function takes a dataframe with two columns prior_cirrhosis
    and prior_portal_hyp, which count the number of diagnosis of
    liver cirrhosis and portal hypertension seen in the previous
    year.

    Args:
        has_prior_cirrhosis: Has columns `prior_cirrhosis` and
            `prior_portal_hyp`.

    Returns:
        The ARC HBR criterion (0.0, 1.0)
    """
    cirrhosis = has_prior_cirrhosis["prior_cirrhosis"] > 0
    portal_hyp = has_prior_cirrhosis["prior_portal_hyp"] > 0

    return Series(
        np.where(cirrhosis & portal_hyp, 1.0, 0),
        index=has_prior_cirrhosis.index,
    )


def arc_hbr_ischaemic_stroke_ich(has_prior_ischaemic_stroke: DataFrame) -> Series:
    """Calculate the ischaemic stroke/intracranial haemorrhage ARC HBR criterion

    This function takes a dataframe with two columns prior_bavm_ich
    and prior_portal_hyp, which count the number of diagnosis of
    liver cirrhosis and portal hypertension seen in the previous
    year.

    If bAVM/ICH is present, 1.0 is added to the score. Else, if
    ischaemic stroke is present, add 0.5. Otherwise add 0.

    Args:
        has_prior_ischaemic_stroke: Has a column `prior_ischaemic_stroke` containing
            the number of any-severity ischaemic strokes in the previous
            year, and a column `prior_bavm_ich` containing a count of
            any diagnosis of brain arteriovenous malformation or
            intracranial haemorrhage.


    Returns:
        The ARC HBR criterion (0.0, 1.0)
    """
    ischaemic_stroke = has_prior_ischaemic_stroke["prior_ischaemic_stroke"] > 0
    bavm_ich = has_prior_ischaemic_stroke["prior_bavm_ich"] > 0

    score_one = np.where(bavm_ich, 1, 0)
    score_half = np.where(ischaemic_stroke, 0.5, 0)
    score_zero = np.zeros(len(has_prior_ischaemic_stroke))

    return Series(
        np.maximum(score_one, score_half, score_zero),
        index=has_prior_ischaemic_stroke.index,
    )


def get_features(
    index_episodes: DataFrame, previous_year: DataFrame, data: HicData
) -> DataFrame:
    """Index/prior history features for calculating ARC HBR

    Make table of general features (more granular than the ARC-HBR criteria,
    from which the ARC score will be computed)

    Args:
        index_episodes: Contains `acs_index` and `pci_index` columns (indexed
            by `episode_id`)
        previous_year: Contains the all_other_codes table narrowed to the previous
            year (for the purposes of counting code groups).
        data (HicData): Contains DataFrame attributes `demographics` and
            `lab_results`.

    Returns:
        The table of features (used for calculating the ARC HBR score).
    """

    cirrhosis_groups = ["cirrhosis"]
    portal_hyp_groups = ["portal_hypertension"]
    bleeding_groups = ["bleeding_al_ani"]
    cancer_groups = ["cancer"]
    bavm_ich_groups = ["bavm", "ich"]
    ischaemic_stroke_groups = ["ischaemic_stroke"]
    feature_data = {
        "age": calculate_age(index_episodes, data.demographics),
        "gender": get_gender(index_episodes, data.demographics),
        "min_index_egfr": min_index_result("egfr", index_episodes, data.lab_results),
        "min_index_hb": min_index_result("hb", index_episodes, data.lab_results),
        "min_index_platelets": min_index_result(
            "platelets", index_episodes, data.lab_results
        ),
        # Only use primary position, as proxy for "requiring hospitalisation".
        # Note: logic will need to account for "first episode" when multiple
        # episodes are used.
        "prior_bleeding_12": counting.count_code_groups(
            index_episodes, previous_year, bleeding_groups, False
        ),
        "prior_cirrhosis": counting.count_code_groups(
            index_episodes, previous_year, cirrhosis_groups, True
        ),
        "prior_portal_hyp": counting.count_code_groups(
            index_episodes, previous_year, portal_hyp_groups, True
        ),
        "prior_bavm_ich": counting.count_code_groups(
            index_episodes, previous_year, bavm_ich_groups, True
        ),
        "prior_ischaemic_stroke": counting.count_code_groups(
            index_episodes, previous_year, ischaemic_stroke_groups, True
        ),
        # TODO: transfusion
        "prior_cancer": counting.count_code_groups(
            index_episodes, previous_year, cancer_groups, True
        ),
        # TODO: add cancer therapy
    }
    features = DataFrame(feature_data)
    features[["acs_index", "pci_index"]] = index_episodes[["acs_index", "pci_index"]]
    return features


def get_arc_hbr_score(features: DataFrame, data: HicData) -> DataFrame:
    """Calculate the ARC HBR score

    The `features` table has one row per index event, and must have the
    following data:

    * `episode_id` as Pandas index.
    * `age` column for age at index.
    * `gender` column for patient gender (category with values "male", "female"
        or "unknown")
    * `min_index_egfr` column containing the minimum eGFR measurement at
        the index episode, in mL/min
    * `min_index_hb` column containing the minimum Hb measurement at the
        index episode, in g/dL.
    * `min_index_platelets` column containing the minimum platelet count
        measurement at the index episode, in units 100e9/L.
    * `prior_bleeding_12` column containing the total number of qualifying
        prior bleeding events that occurred in the previous 12 months before
        the index event.
    * `prior_cancer` column containing the total number of cancer diagnosis
        codes seen in the previous 12 months before the index event.

    The data.prescriptions table must be indexed by `episode_id`, and needs a `name`
    column (str, for medicine name), and an `on_admission` column (bool) for
    whether the medicine was present on hospital admission.

    Args:
        features: Table of index-episode data for calculating the ARC HBR score
        prescriptions: A class containing a DataFrame attribute prescriptions.

    Returns:
        A table with one column per ARC HBR criterion, containing the score (0.0,
            0.5, or 1.0)
    """

    # Calculate the ARC HBR score
    arc_score_data = {
        "arc_hbr_age": arc_hbr_age(features),
        "arc_hbr_oac": arc_hbr_oac(features, data.prescriptions),
        "arc_hbr_ckd": arc_hbr_ckd(features),
        "arc_hbr_anaemia": arc_hbr_anaemia(features),
        "arc_hbr_tcp": arc_hbr_tcp(features),
        "arc_hbr_prior_bleeding": arc_hbr_prior_bleeding(features),
        "arc_hbr_cirrhosis_portal_hyp": arc_hbr_cirrhosis_ptl_hyp(features),
        "arc_hbr_ischaemic_stroke_ich": arc_hbr_ischaemic_stroke_ich(features),
        "arc_hbr_cancer": arc_hbr_cancer(features),
        "arc_hbr_nsaid": arc_hbr_nsaid(features, data.prescriptions),
    }
    return DataFrame(arc_score_data)


def plot_index_measurement_distribution(features: DataFrame):
    """Plot a histogram of measurement results at the index

    Args:
        index_episodes: Must contain `min_index_hb`, `min_index_egfr`,
        and `min_index_platelets`. The index_hb column is multiplied
        by 10 to get units g/L.
    """

    # Make a plot showing the three lab results as histograms
    df = features.copy()
    df["min_index_hb"] = 10 * df["min_index_hb"]  # Convert from g/dL to g/L
    df = (
        df.filter(regex="^min_index")
        .rename(
            columns={
                "min_index_egfr": "eGFR (mL/min)",
                "min_index_hb": "Hb (g/L)",
                "min_index_platelets": "Plt (x10^9/L)",
            }
        )
        .melt(value_name="Lowest test result at index episode", var_name="Test")
    )
    g = sns.displot(
        df,
        x="Lowest test result at index episode",
        hue="Test",
    )
    g.figure.subplots_adjust(top=0.95)
    g.ax.set_title("Distribution of Laboratory Test Results in ACS/PCI index events")
