"""Fetch raw data from the database and save it to a file
"""

import argparse


def main():

    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser("fetch-data")
    parser.add_argument(
        "-f",
        "--config-file",
        required=True,
        help="Specify the config file with settings",
    )
    parser.add_argument(
        "-s",
        "--stage",
        choices = ["fetch-sus", "fetch-others", "process"],
        default = "process",
        help="Stages happen in order (as shown), but script can be started from a later stage. Default is 'process' (using already-fetched data).",
    )
    args = parser.parse_args()
    
    import datetime as dt
    from dateutil import parser

    import pandas as pd
    from pyhbr import common, clinical_codes
    from pyhbr.analysis import acs
    from pyhbr.clinical_codes import counting
    from pyhbr.data_source import icb, hic_icb, hic
    from pyhbr.middle import from_icb, from_hic
    from pyhbr.analysis import arc_hbr
    import yaml
    
    # Read the configuration file
    with open(args.config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Failed to load config file: {exc}")
            exit(1)
        
    # Check if the user has started from the SUS fetch
    # step. If so, run the SQL query to fetch the SUS
    # data (this takes a long time), and save the result
    # to a file. 
    if args.stage == "fetch-sus":
        
        print("Fetching SUS data")
        
        # Set a date range for episode fetch. The primary
        # care data start in Oct 2019. Use an end date
        # in the future to ensure all recent data is fetched.
        # Index spell data is limited based on the min/max
        # dates seen in all the datasets below.
        start_date = parser.parse(config["start_date"])
        end_date = parser.parse(config["end_date"])

        # Get the raw HES data (this takes a long time ~ 20 minutes, up to 2 hours
        # at UHBW).
        abi_engine = common.make_engine(database="abi")
        raw_sus_data = from_icb.get_raw_sus_data(abi_engine, start_date, end_date)

        # Note that the SUS data is limited to in-area patients only, so that
        # the patients are present in the primary care attributes table (see
        # the notes on valid commissioner code in icb.py). This restriction
        # can be lifted if the primary care data is not used in the analysis.

        # The full dataset is large, so using a save point
        # to speed up script development
        common.save_item(raw_sus_data, "raw_sus_data", save_dir=config["save_dir"])

    # Load the raw SUS data (previously saved)
    raw_sus_data, raw_sus_data_path = common.load_item("raw_sus_data", save_dir=config["save_dir"])

    # This is the base name of the raw data file containing the SQL
    # query results (with minimal processing)
    raw_name = f"{config['analysis_name']}_raw"

    # If the user has requested a SUS data fetch or a fetch of
    # all the other tables (SWD, etc.), run the corresponding SQL
    # queries and save the results
    if args.stage == "fetch-sus" or args.stage == "fetch-others":

        # Fetch the list of episodes from the HIC table -- this will
        # speed up subsequent queries
        msa_engine = common.make_engine(database="modelling_sql_area")
        hic_episodes = common.get_data(msa_engine, hic_icb.episode_id_query)
        hic_patient_ids = hic_episodes.patient_id.unique()

        # Reduce the sus data to only the patients in the HIC data
        reduced_sus_data = raw_sus_data[raw_sus_data["patient_id"].isin(hic_patient_ids)]

        # Read the code groups and reduce to a table. The remainder of the code
        # uses the code groups dataframe, which you can either get from the code
        # files (as is done here) or create them manually
        diagnosis_codes = clinical_codes.load_from_package(config["icd10_codes_file"])
        procedure_codes = clinical_codes.load_from_package(config["opcs4_codes_file"])
        code_groups = clinical_codes.get_code_groups(diagnosis_codes, procedure_codes)

        # HES data + patient demographics
        episodes, codes = from_icb.get_episodes_and_codes(reduced_sus_data, code_groups)

        # Get the index episodes (primary ACS or PCI anywhere in first episode)
        # Modify the code groups used to define the index event here.
        index_spells = acs.get_index_spells(
            episodes,
            codes,
            config["acs_index_code_group"],
            config["pci_index_code_group"],
            config["stemi_index_code_group"],
            config["nstemi_index_code_group"],
        )

        # Get the list of patients to narrow subsequent SQL queries
        patient_ids = index_spells["patient_id"].unique()

        # Get date of death and cause of death from registry data
        date_of_death, cause_of_death = from_icb.get_mortality(
            abi_engine, start_date, end_date, code_groups
        )
        
        # score seg query
        dfs = common.get_data_by_patient(
            msa_engine, icb.score_seg_query, patient_ids,
        )
        score_seg = pd.concat(dfs).reset_index(drop=True)

        # Primary care prescriptions (very slow)
        dfs = common.get_data_by_patient(
            msa_engine, icb.primary_care_prescriptions_query, patient_ids, config["gp_opt_outs"]
        )
        primary_care_prescriptions = pd.concat(dfs).reset_index(drop=True)

        # Primary care measurements (slow)
        dfs = common.get_data_by_patient(
            msa_engine, icb.primary_care_measurements_query, patient_ids, config["gp_opt_outs"]
        )
        primary_care_measurements = pd.concat(dfs).reset_index(drop=True)

        # Primary care attributes (slow)
        dfs = common.get_data_by_patient(
            msa_engine, icb.primary_care_attributes_query, patient_ids, config["gp_opt_outs"]
        )
        with_flag_columns = [from_icb.process_flag_columns(df) for df in dfs]
        primary_care_attributes = pd.concat(with_flag_columns).reset_index(drop=True)

        # Find the most recent date that was seen in all the datasets. Note
        # that the date in the primary care attributes covers the month
        # beginning from that date.
        common_end = min(
            [
                primary_care_attributes["date"].max() + dt.timedelta(days=31),
                primary_care_prescriptions["date"].max(),
                primary_care_measurements["date"].max(),
                raw_sus_data["episode_start"].max(),
            ]
        )

        # Find earliest date seen in all the datasets.
        common_start = max(
            [
                primary_care_attributes["date"].min(),
                primary_care_prescriptions["date"].min(),
                primary_care_measurements["date"].min(),
                raw_sus_data["episode_start"].min(),
            ]
        )

        # Add a margin of one year on either side of the earliest/latest
        # dates to ensure outcomes and features will be valid at the edges
        index_start = common_start + dt.timedelta(days=365)
        index_end = common_end - dt.timedelta(days=365)

        # Reduce the index spells to only those within the valid window
        index_spells = index_spells[
            (index_spells["spell_start"] < index_end)
            & (index_spells["spell_start"] > index_start)
        ]

        # Fetch the raw lab results data
        lab_results = from_icb.get_unlinked_lab_results(msa_engine)  # really slow

        # Fetch raw secondary-care prescriptions data
        secondary_care_prescriptions = from_hic.get_unlinked_prescriptions(
            msa_engine, "HIC_Pharmacy"
        )  # fast

        # Combine the datasets for saving
        raw = {
            # Datasets
            "index_spells": index_spells,
            "episodes": episodes,
            "code_groups": code_groups,
            "codes": codes,
            "date_of_death": date_of_death,
            "cause_of_death": cause_of_death,
            "primary_care_attributes": primary_care_attributes,
            "primary_care_measurements": primary_care_measurements,
            "primary_care_prescriptions": primary_care_prescriptions,
            "score_seg": score_seg,
            "secondary_care_prescriptions": secondary_care_prescriptions,
            "lab_results": lab_results,
            # Metadata
            "start_date": start_date,
            "end_date": end_date,
            "common_start": common_start,
            "common_end": common_end,
            "index_start": index_start,
            "index_end_date": index_end,
            # Other items
            "raw_sus_data_file": raw_sus_data_path.name,
        }

        # Save point for the intermediate data
        common.save_item(raw, raw_name, save_dir=config["save_dir"])
        
    print("Starting processing")

    # Load the data from file
    raw, raw_path = common.load_item(raw_name, save_dir=config["save_dir"])

    # Extract some datasets for convenience
    episodes = raw["episodes"]
    codes = raw["codes"]
    index_spells = raw["index_spells"]
    date_of_death = raw["date_of_death"]
    cause_of_death = raw["cause_of_death"]
    primary_care_attributes = raw["primary_care_attributes"]
    primary_care_prescriptions = raw["primary_care_prescriptions"]
    secondary_care_prescriptions = raw["secondary_care_prescriptions"]
    primary_care_measurements = raw["primary_care_measurements"]
    lab_results = raw["lab_results"]
    score_seg = raw["score_seg"]

    # Get features from the lab results
    features_lab = arc_hbr.first_index_lab_result(index_spells, lab_results, episodes)

    # Process the prescriptions into features
    features_secondary_prescriptions = acs.get_secondary_care_prescriptions_features(
        secondary_care_prescriptions, index_spells, episodes
    )

    # Preprocess the SWD columns
    primary_care_attributes["smoking"] = from_icb.preprocess_smoking(
        primary_care_attributes["smoking"]
    )
    primary_care_attributes["ethnicity"] = from_icb.preprocess_ethnicity(
        primary_care_attributes["ethnicity"]
    )

    # Join the attribute date to the index spells for linking
    index_spells_attributes_link = acs.link_attribute_period_to_index(
        index_spells, primary_care_attributes
    )

    # Get the patient index-spell attributes (before reducing based on missingness/low-variance)
    all_index_attributes = acs.get_index_attributes(
        index_spells_attributes_link, primary_care_attributes
    )

    # Remove attribute columns that have too much missingness or where
    # the column is nearly constant (low variance)
    features_attributes = acs.remove_features(
        all_index_attributes,
        max_missingness=config["attributes_max_missingness"],
        const_threshold=config["attributes_const_threshold"],
    )

    # Do the same process to link the seg scores to the index
    # events.
    index_spells_scores_link = acs.link_attribute_period_to_index(
        index_spells, score_seg
    )

    # Get the scores (not used as features, for descriptive purposes)
    info_index_scores = acs.get_index_attributes(
        index_spells_attributes_link, score_seg
    )

    # Get other episodes relative to the index episode (for counting code
    # groups before/after the index).
    all_other_codes = counting.get_all_other_codes(index_spells, episodes, codes)

    # Choose a window for identifying management
    min_after = dt.timedelta(hours=0)
    max_after = dt.timedelta(days=7)
    pci_group = "all_pci_pathak"
    cabg_group = "cabg_bortolussi"
    info_management = acs.get_management(
        index_spells, all_other_codes, min_after, max_after, pci_group, cabg_group
    )
    print("Breakdown of management:")
    print(info_management.value_counts())

    # Get follow-up window for defining non-fatal outcomes
    min_after = dt.timedelta(hours=48)
    max_after = dt.timedelta(days=365)
    following_year = counting.get_time_window(all_other_codes, min_after, max_after)

    # The bleeding outcome is defined by the ADAPTT trial bleeding code group,
    # which matches BARC 2-5 bleeding events. Ischaemia outcomes are defined using
    # a three-point MACE specifically targetting ischaemic outcomes (i.e. only
    # ischaemic stroke is included, rather than haemorrhagic stroke which is sometimes
    # included in MACE definitions).

    # Get the non-fatal bleeding outcomes
    # Excluding the index spells appears to have very
    # little effect on the prevalence, so the index spell
    # is excluded to be consistent with ischaemia outcome
    # definition. Increasing maximum code position increases
    # the bleeding rate, but 1 is chosen to restrict to cases
    # where bleeding code is not historical/minor.
    max_position = config["outcomes"]["bleeding"]["non_fatal"]["max_position"]
    exclude_index_spell = True
    non_fatal_bleeding_group = config["outcomes"]["bleeding"]["non_fatal"]["group"]
    non_fatal_bleeding = acs.filter_by_code_groups(
        following_year,
        non_fatal_bleeding_group,
        max_position,
        exclude_index_spell,
    )

    # Get fatal bleeding outcomes. Maximum code
    # position increases count, but is restricted
    # to one to focus on bleeding-caused deaths.
    # Bleeding codes typically show up in the primary
    # or first secondary
    max_position =  config["outcomes"]["bleeding"]["fatal"]["max_position"]
    fatal_bleeding_group = config["outcomes"]["bleeding"]["fatal"]["group"]
    fatal_bleeding = acs.identify_fatal_outcome(
        index_spells,
        date_of_death,
        cause_of_death,
        fatal_bleeding_group,
        max_position,
        max_after,
    )

    # Get the non-fatal ischaemia outcomes. Allowing
    # outcomes from the index spell considerably
    # increases the ischaemia rate to about 25%, which
    # seems to high to be reasonable. This could be
    # due to (e.g.) a majority of ACS patients having two
    # acute episodes to treat the index event. Excluding
    # the index event brings the prevalence down to around 6%,
    # more in line with published research. Allowing
    # secondary codes somewhat increases the number of outcomes.
    max_position = config["outcomes"]["ischaemia"]["non_fatal"]["max_position"]
    exclude_index_spell = True
    non_fatal_ischaemia_group = config["outcomes"]["ischaemia"]["non_fatal"]["group"]
    non_fatal_ischaemia = acs.filter_by_code_groups(
        following_year,
        non_fatal_ischaemia_group,
        max_position,
        exclude_index_spell,
    )

    # This is how to look at patients with a particular spell
    # df = codes.merge(episodes, on="episode_id", how="left")
    # spell = df[df["spell_id"] == "1613481717937990639"].drop_duplicates(
    #     ["episode_id", "code", "type", "position"]
    # )
    # spell.sort_values(["episode_start", "type", "position"])

    # Get the fatal ischaemia outcomes. 
    fatal_ischaemia_group = config["outcomes"]["ischaemia"]["fatal"]["group"]
    max_position = config["outcomes"]["ischaemia"]["fatal"]["max_position"]
    fatal_ischaemia = acs.identify_fatal_outcome(
        index_spells,
        date_of_death,
        cause_of_death,
        fatal_ischaemia_group,
        max_position,
        max_after,
    )

    # Count the non-fatal bleeding/ischaemia outcomes
    outcomes = pd.DataFrame()
    outcomes["non_fatal_bleeding"] = counting.count_code_groups(
        index_spells, non_fatal_bleeding
    )
    outcomes["non_fatal_ischaemia"] = counting.count_code_groups(
        index_spells, non_fatal_ischaemia
    )
    outcomes["fatal_bleeding"] = counting.count_code_groups(index_spells, fatal_bleeding)
    outcomes["fatal_ischaemia"] = counting.count_code_groups(index_spells, fatal_ischaemia)

    # Get the survival time and right censoring data for bleeding and ischaemia (combines
    # both fatal/non-fatal outcomes with a flag to distinguish which is which)
    bleeding_survival = acs.get_survival_data(index_spells, fatal_bleeding, non_fatal_bleeding, max_after)
    ischaemia_survival = acs.get_survival_data(index_spells, fatal_ischaemia, non_fatal_ischaemia, max_after)

    # Reduce the outcomes to boolean, and make aggregate
    # (fatal/non-fatal) columns
    bool_outcomes = outcomes > 0
    bool_outcomes["bleeding"] = (
        bool_outcomes["fatal_bleeding"] | bool_outcomes["non_fatal_bleeding"]
    )
    bool_outcomes["ischaemia"] = (
        bool_outcomes["fatal_ischaemia"] | bool_outcomes["non_fatal_ischaemia"]
    )

    # Quick check on prevalences
    100 * bool_outcomes.sum() / len(bool_outcomes)

    features_codes = acs.get_code_features(index_spells, all_other_codes)

    # Remove the CV death code group (generalise this to remove
    # arbitrary code groups using the config file)
    to_drop = [
        "cv_death_ohm_before",
        "hussain_ami_stroke_before",  # Duplicates other AMI/stroke group
        "ami_stroke_ohm_before",  # AMI and stroke are included separately
    ]
    features_codes = features_codes.drop(columns=to_drop)

    # Get counts of relevant prescriptions in the year before the index
    features_prescriptions = acs.prescriptions_before_index(
        index_spells, primary_care_prescriptions
    )

    # Only blood pressure and HbA1c go back to 2019 in the data -- not
    # including the other measurements in order to keep the sample size up.
    prior_blood_pressure = from_icb.blood_pressure(index_spells, primary_care_measurements)
    prior_hba1c = from_icb.hba1c(index_spells, primary_care_measurements)
    features_measurements = prior_blood_pressure.merge(
        prior_hba1c, how="left", on="spell_id"
    )

    # Get hic index features (drop instead of keep in case new
    # features are added)
    features_index = index_spells.drop(columns=["episode_id", "patient_id", "spell_start"])

    # Create the ARC HBR score
    arc_hbr_score = pd.DataFrame(index=features_index.index)
    arc_hbr_score["arc_hbr_age"] = arc_hbr.arc_hbr_age(features_index)
    arc_hbr_score["arc_hbr_oac"] = arc_hbr.arc_hbr_medicine(
        index_spells,
        episodes,
        secondary_care_prescriptions,
        "oac",
        1.0,
    )
    arc_hbr_score["arc_hbr_oac"].sum()
    arc_hbr_score["arc_hbr_nsaid"] = arc_hbr.arc_hbr_medicine(
        index_spells,
        episodes,
        secondary_care_prescriptions,
        "nsaid",
        1.0,
    )
    arc_hbr_score["arc_hbr_nsaid"].sum()
    arc_hbr_score["arc_hbr_ckd"] = arc_hbr.arc_hbr_ckd(features_lab)
    arc_hbr_score["arc_hbr_anaemia"] = arc_hbr.arc_hbr_anaemia(
        features_index.merge(features_lab, how="left", on="spell_id")
    )
    arc_hbr_score["arc_hbr_tcp"] = arc_hbr.arc_hbr_tcp(features_lab)
    arc_hbr_score["arc_hbr_prior_bleeding"] = arc_hbr.arc_hbr_prior_bleeding(features_codes)
    arc_hbr_score["arc_hbr_cirrhosis_portal_hyp"] = arc_hbr.arc_hbr_cirrhosis_ptl_hyp(
        features_codes
    )
    arc_hbr_score["arc_hbr_stroke_ich"] = arc_hbr.arc_hbr_ischaemic_stroke_ich(features_codes)
    arc_hbr_score["arc_hbr_cancer"] = arc_hbr.arc_hbr_cancer(features_codes)
    arc_hbr_score["total_score"] = arc_hbr_score.sum(axis=1)

    #arc_hbr.plot_arc_score_distribution(arc_hbr_score)
    #plt.tight_layout()
    #plt.show()

    # Combine all tables (features and outcomes) into a single table
    # for saving.
    data = {
        "raw_file": raw_path.name,
        # Outcomes
        "outcomes": bool_outcomes,
        "non_fatal_bleeding": non_fatal_bleeding,
        "fatal_bleeding": fatal_bleeding,
        "non_fatal_ischaemia": non_fatal_ischaemia,
        "fatal_ischaemia": fatal_ischaemia,
        "bleeding_survival": bleeding_survival,
        "ischaemia_survival": ischaemia_survival,
        # HES data
        "features_index": features_index,
        "features_codes": features_codes,
        # SWD data
        "features_attributes": features_attributes,
        "features_prescriptions": features_prescriptions,
        "features_measurements": features_measurements,
        # HIC (UHBW) data
        "features_secondary_prescriptions": features_secondary_prescriptions,
        "features_lab": features_lab,
        # Info (for descriptive purposes)
        "info_index_scores": info_index_scores,
        # ARC HBR score
        "arc_hbr_score": arc_hbr_score
    }


    common.save_item(data, f"{config['analysis_name']}_data", save_dir=config["save_dir"], prompt_commit=True)
