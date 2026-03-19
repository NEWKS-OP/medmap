"""
Schema mapping configuration: source column names -> target SQL column names.
Detects file type by column signatures, not file names.
"""

# Column signatures to detect file type by content
# Each signature has 'required' and/or 'alt_required' sets, or a 'check' lambda
COLUMN_SIGNATURES = {
    "labs": {
        "required": {"case_id", "patient_id", "sodium_mmol_L"},
        "alt_required": {"case_id", "patient_id", "specimen_datetime"},
        "alt_required_2": {"CaseID", "PID", "Na"},
    },
    "icd10_ops": {
        "required": {"case_id", "primary_icd10_code", "ward"},
        "alt_required": {"CaseID", "PatientID", "ICD10_Haupt"},
    },
    "device_motion": {
        "required": {"patient_id", "timestamp", "movement_index_0_100", "fall_event_0_1"},
    },
    "device_1hz": {
        "required": {"patient_id", "timestamp", "accel_x_m_s2", "device_id"},
        "alt_required": {"PatientID", "DeviceID", "Timestamp", "AccelX"},
    },
    "medication": {
        "required": {"case_id", "patient_id", "medication_name", "record_type"},
        "alt_required": {"case_id", "patient_id", "medication_name", "event_type"},
        "alt_required_2": {"rec_type", "pat_id", "medikament"},
    },
    "nursing": {
        "required": {"case_id", "patient_id", "shift", "nursing_note_free_text"},
        "alt_required": {"case_id", "patient_id", "shift", "note_text"},
        "alt_required_2": {"CaseID", "PatientID", "Shift", "NursingNote"},
    },
    "epaAC_pivot": {
        "check": lambda cols: "SID" in cols and "SID_value" in cols and "FallID" in cols,
    },
    "epaAC_sap": {
        "check": lambda cols: any(
            c.startswith("EPA") or c == "MANDT" or c == "PATFAL" for c in cols
        ),
    },
    "epaAC_german": {
        "check": lambda cols: (
            "AufnDat" in cols
            or "Körpergröße" in cols
            or "Koerpergroesse" in cols
            or "EinschIDFall" in cols
        ),
    },
}

# Dirty -> Clean column name mappings (for normalizing dirty data to clean names)
DIRTY_LABS_RENAME = {
    "CaseID": "case_id",
    "PID": "patient_id",
    "Gender": "sex",
    "Age": "age_years",
    "SpecDT": "specimen_datetime",
    "Na": "sodium_mmol_L",
    "Na_flag": "sodium_flag",
    "Na_low": "sodium_ref_low",
    "Na_high": "sodium_ref_high",
    "K": "potassium_mmol_L",
    "K_flag": "potassium_flag",
    "K_low": "potassium_ref_low",
    "K_high": "potassium_ref_high",
    "Creat": "creatinine_mg_dL",
    "Creat_flag": "creatinine_flag",
    "Creat_low": "creatinine_ref_low",
    "Creat_high": "creatinine_ref_high",
    "eGFR": "egfr_mL_min_1_73m2",
    "eGFR_flag": "egfr_flag",
    "eGFR_low": "egfr_ref_low",
    "eGFR_high": "egfr_ref_high",
    "Gluc": "glucose_mg_dL",
    "Gluc_flag": "glucose_flag",
    "Gluc_low": "glucose_ref_low",
    "Gluc_high": "glucose_ref_high",
    "Hb": "hemoglobin_g_dL",
    "Hb_flag": "hb_flag",
    "Hb_low": "hb_ref_low",
    "Hb_high": "hb_ref_high",
    "WBC": "wbc_10e9_L",
    "WBC_flag": "wbc_flag",
    "WBC_low": "wbc_ref_low",
    "WBC_high": "wbc_ref_high",
    "PLT": "platelets_10e9_L",
    "PLT_flag": "platelets_flag",
    "PLT_low": "plt_ref_low",
    "PLT_high": "plt_ref_high",
    "CRP": "crp_mg_L",
    "CRP_flag": "crp_flag",
    "CRP_low": "crp_ref_low",
    "CRP_high": "crp_ref_high",
    "ALT": "alt_U_L",
    "ALT_flag": "alt_flag",
    "ALT_low": "alt_ref_low",
    "ALT_high": "alt_ref_high",
    "AST": "ast_U_L",
    "AST_flag": "ast_flag",
    "AST_low": "ast_ref_low",
    "AST_high": "ast_ref_high",
    "Bili": "bilirubin_mg_dL",
    "Bili_flag": "bilirubin_flag",
    "Bili_low": "bili_ref_low",
    "Bili_high": "bili_ref_high",
    "Alb": "albumin_g_dL",
    "Alb_flag": "albumin_flag",
    "Alb_low": "albumin_ref_low",
    "Alb_high": "albumin_ref_high",
    "INR": "inr",
    "INR_flag": "inr_flag",
    "INR_low": "inr_ref_low",
    "INR_high": "inr_ref_high",
    "Lact": "lactate_mmol_L",
    "Lact_flag": "lactate_flag",
    "Lact_low": "lactate_ref_low",
    "Lact_high": "lactate_ref_high",
}

DIRTY_ICD10_RENAME = {
    "CaseID": "case_id",
    "PatientID": "patient_id",
    "Station": "ward",
    "Aufnahmedatum": "admission_date",
    "Entlassungsdatum": "discharge_date",
    "Verweildauer_Tage": "length_of_stay_days",
    "ICD10_Haupt": "primary_icd10_code",
    "ICD10_Haupt_Bezeichnung": "primary_icd10_description_en",
    "ICD10_Neben": "secondary_icd10_codes",
    "ICD10_Neben_Bezeichnung": "secondary_icd10_descriptions_en",
    "OPS_Code": "ops_codes",
    "OPS_Bezeichnung": "ops_descriptions_en",
}

DIRTY_1HZ_RENAME = {
    "PatientID": "patient_id",
    "DeviceID": "device_id",
    "Timestamp": "timestamp",
    "BedOccupied": "bed_occupied_0_1",
    "MovementScore": "movement_score_0_100",
    "AccelX": "accel_x_m_s2",
    "AccelY": "accel_y_m_s2",
    "AccelZ": "accel_z_m_s2",
    "AccelMag": "accel_magnitude_g",
    "PressZ1": "pressure_zone1_0_100",
    "PressZ2": "pressure_zone2_0_100",
    "PressZ3": "pressure_zone3_0_100",
    "PressZ4": "pressure_zone4_0_100",
    "BedExit": "bed_exit_event_0_1",
    "BedReturn": "bed_return_event_0_1",
    "FallEvent": "fall_event_0_1",
    "ImpactMag": "impact_magnitude_g",
    "EventID": "event_id",
}

DIRTY_MEDICATION_RENAME = {
    "rec_type": "record_type",
    "pat_id": "patient_id",
    "enc_id": "encounter_id",
    "station": "ward",
    "aufnahme_dt": "admission_datetime",
    "entlassung_dt": "discharge_datetime",
    "order_id": "order_id",
    "uuid": "order_uuid",
    "atc_code": "medication_code_atc",
    "medikament": "medication_name",
    "applikation": "route",
    "dosis": "dose",
    "einheit": "dose_unit",
    "haeufigkeit": "frequency",
    "start_dt": "order_start_datetime",
    "stop_dt": "order_stop_datetime",
    "bei_bedarf": "is_prn_0_1",
    "indikation": "indication",
    "verschreiber": "prescriber_role",
    "bestellung_status": "order_status",
    "gabe_dt": "administration_datetime",
    "gegebene_dosis": "administered_dose",
    "gabe_einheit": "administered_unit",
    "gabe_status": "administration_status",
    "notiz": "note",
}

DIRTY_NURSING_RENAME = {
    "CaseID": "case_id",
    "PatientID": "patient_id",
    "Ward": "ward",
    "ReportDate": "report_date",
    "Shift": "shift",
    "NursingNote": "nursing_note_free_text",
}

# Source -> Target column mappings per table

LABS_MAPPING = {
    "case_id": "coCaseId",
    "patient_id": "coPatient_id",
    "sex": "coSex",
    "age_years": "coAge_years",
    "specimen_datetime": "coSpecimen_datetime",
    "sodium_mmol_L": "coSodium_mmol_L",
    "sodium_flag": "coSodium_flag",
    "sodium_ref_low": "coSodium_ref_low",
    "sodium_ref_high": "coSodium_ref_high",
    "potassium_mmol_L": "coPotassium_mmol_L",
    "potassium_flag": "coPotassium_flag",
    "potassium_ref_low": "coPotassium_ref_low",
    "potassium_ref_high": "coPotassium_ref_high",
    "creatinine_mg_dL": "coCreatinine_mg_dL",
    "creatinine_flag": "coCreatinine_flag",
    "creatinine_ref_low": "coCreatinine_ref_low",
    "creatinine_ref_high": "coCreatinine_ref_high",
    "egfr_mL_min_1_73m2": "coEgfr_mL_min_1_73m2",
    "egfr_flag": "coEgfr_flag",
    "egfr_ref_low": "coEgfr_ref_low",
    "egfr_ref_high": "coEgfr_ref_high",
    "glucose_mg_dL": "coGlucose_mg_dL",
    "glucose_flag": "coGlucose_flag",
    "glucose_ref_low": "coGlucose_ref_low",
    "glucose_ref_high": "coGlucose_ref_high",
    "hemoglobin_g_dL": "coHemoglobin_g_dL",
    "hb_flag": "coHb_flag",
    "hb_ref_low": "coHb_ref_low",
    "hb_ref_high": "coHb_ref_high",
    "wbc_10e9_L": "coWbc_10e9_L",
    "wbc_flag": "coWbc_flag",
    "wbc_ref_low": "coWbc_ref_low",
    "wbc_ref_high": "coWbc_ref_high",
    "platelets_10e9_L": "coPlatelets_10e9_L",
    "platelets_flag": "coPlatelets_flag",
    "plt_ref_low": "coPlt_ref_low",
    "plt_ref_high": "coPlt_ref_high",
    "crp_mg_L": "coCrp_mg_L",
    "crp_flag": "coCrp_flag",
    "crp_ref_low": "coCrp_ref_low",
    "crp_ref_high": "coCrp_ref_high",
    "alt_U_L": "coAlt_U_L",
    "alt_flag": "coAlt_flag",
    "alt_ref_low": "coAlt_ref_low",
    "alt_ref_high": "coAlt_ref_high",
    "ast_U_L": "coAst_U_L",
    "ast_flag": "coAst_flag",
    "ast_ref_low": "coAst_ref_low",
    "ast_ref_high": "coAst_ref_high",
    "bilirubin_mg_dL": "coBilirubin_mg_dL",
    "bilirubin_flag": "coBilirubin_flag",
    "bili_ref_low": "coBili_ref_low",
    "bili_ref_high": "coBili_ref_high",
    "albumin_g_dL": "coAlbumin_g_dL",
    "albumin_flag": "coAlbumin_flag",
    "albumin_ref_low": "coAlbumin_ref_low",
    "albumin_ref_high": "coAlbumin_ref_high",
    "inr": "coInr",
    "inr_flag": "coInr_flag",
    "inr_ref_low": "coInr_ref_low",
    "inr_ref_high": "coInr_ref_high",
    "lactate_mmol_L": "coLactate_mmol_L",
    "lactate_flag": "coLactate_flag",
    "lactate_ref_low": "coLactate_ref_low",
    "lactate_ref_high": "coLactate_ref_high",
}

ICD10_MAPPING = {
    "case_id": "coCaseId",
    "patient_id": "coPatient_id",
    "ward": "coWard",
    "admission_date": "coAdmission_date",
    "discharge_date": "coDischarge_date",
    "length_of_stay_days": "coLength_of_stay_days",
    "primary_icd10_code": "coPrimary_icd10_code",
    "primary_icd10_description_en": "coPrimary_icd10_description_en",
    "secondary_icd10_codes": "coSecondary_icd10_codes",
    "secondary_icd10_descriptions_en": "coSecondary_icd10_descriptions_en",
    "ops_codes": "coOps_codes",
    "ops_descriptions_en": "coOps_descriptions_en",
}

DEVICE_MOTION_MAPPING = {
    "case_id": "coCaseId",
    "timestamp": "coTimestamp",
    "patient_id": "coPatient_id",
    "movement_index_0_100": "coMovement_index_0_100",
    "micro_movements_count": "coMicro_movements_count",
    "bed_exit_detected_0_1": "coBed_exit_detected_0_1",
    "fall_event_0_1": "coFall_event_0_1",
    "impact_magnitude_g": "coImpact_magnitude_g",
    "post_fall_immobility_minutes": "coPost_fall_immobility_minutes",
}

DEVICE_1HZ_MAPPING = {
    "case_id": "coCaseId",
    "timestamp": "coTimestamp",
    "patient_id": "coPatient_id",
    "device_id": "coDevice_id",
    "bed_occupied_0_1": "coBed_occupied_0_1",
    "movement_score_0_100": "coMovement_score_0_100",
    "accel_x_m_s2": "coAccel_x_m_s2",
    "accel_y_m_s2": "coAccel_y_m_s2",
    "accel_z_m_s2": "coAccel_z_m_s2",
    "accel_magnitude_g": "coAccel_magnitude_g",
    "pressure_zone1_0_100": "coPressure_zone1_0_100",
    "pressure_zone2_0_100": "coPressure_zone2_0_100",
    "pressure_zone3_0_100": "coPressure_zone3_0_100",
    "pressure_zone4_0_100": "coPressure_zone4_0_100",
    "bed_exit_event_0_1": "coBed_exit_event_0_1",
    "bed_return_event_0_1": "coBed_return_event_0_1",
    "fall_event_0_1": "coFall_event_0_1",
    "impact_magnitude_g": "coImpact_magnitude_g",
    "event_id": "coEvent_id",
}

MEDICATION_MAPPING = {
    "case_id": "coCaseId",
    "patient_id": "coPatient_id",
    "record_type": "coRecord_type",
    "encounter_id": "coEncounter_id",
    "ward": "coWard",
    "admission_datetime": "coAdmission_datetime",
    "discharge_datetime": "coDischarge_datetime",
    "order_id": "coOrder_id",
    "order_uuid": "coOrder_uuid",
    "medication_code_atc": "coMedication_code_atc",
    "medication_name": "coMedication_name",
    "route": "coRoute",
    "dose": "coDose",
    "dose_unit": "coDose_unit",
    "frequency": "coFrequency",
    "order_start_datetime": "coOrder_start_datetime",
    "order_stop_datetime": "coOrder_stop_datetime",
    "is_prn_0_1": "coIs_prn_0_1",
    "indication": "coIndication",
    "prescriber_role": "coPrescriber_role",
    "order_status": "coOrder_status",
    "administration_datetime": "coAdministration_datetime",
    "administered_dose": "coAdministered_dose",
    "administered_unit": "coAdministered_unit",
    "administration_status": "coAdministration_status",
    "note": "coNote",
}

NURSING_MAPPING = {
    "case_id": "coCaseId",
    "patient_id": "coPatient_id",
    "ward": "coWard",
    "report_date": "coReport_date",
    "shift": "coShift",
    "nursing_note_free_text": "coNursing_note_free_text",
    "note_text": "coNursing_note_free_text",
}

CASE_DATA_MAPPING = {
    "case_id": "coId",
    "patient_id": "coPatientId",
    "sex": "coGender",
    "gender": "coGender",
    "age_years": "coAgeYears",
    "primary_icd10_code": "coIcd",
    "admission_date": "coE2I223",
    "discharge_date": "coE2I228",
    "lastname": "coLastname",
    "firstname": "coFirstname",
    "date_of_birth": "coDateOfBirth",
    "type_of_stay": "coTypeOfStay",
    "drg_name": "coDrgName",
    "reclining_type": "coRecliningType",
    "state": "coState",
}

# epaAC German column names -> standard internal names
EPAC_GERMAN_MAPPING = {
    "FallID": "case_id",
    "PATFAL": "case_id",
    "PID": "patient_id",
    "PATFOE": "patient_id",
    "AufnDat": "admission_date",
    "PATADT": "admission_date",
    "Alter": "age_years",
    "Körpergröße": "height",
    "Koerpergroesse": "height",
    "Körpergewicht": "weight",
    "Koerpergewicht": "weight",
    "BMI": "bmi",
    "EinschIDFall": "case_id",
    "FallNr (STRING)": "fall_nr",
    "AufnZeit": "admission_time",
    "EntlassDat": "discharge_date",
    "EntlassZeit": "discharge_time",
    "EinschDat": "assessment_date",
    "EinschZeit": "assessment_time",
    "StatBez (STRING)": "ward",
    "InstrVers": "instrument_version",
}

# PID prefix per source type
PID_PREFIXES = {
    "labs": "LAB",
    "device_motion": "MOT",
    "device_1hz": "MOT",
    "medication": "MED",
    "nursing": "NUR",
    "epaAC": "EPA",
    "epaAC_sap": "EPA",
    "epaAC_german": "EPA",
    "epaAC_pivot": "EPA",
    "icd10_ops": "ICD",
}


# Clinic 2 abbreviated column renames
CLINIC2_LABS_RENAME = {
    "dat": "specimen_datetime", "cas": "case_id", "pat": "patient_id",
    "sex": "sex", "age": "age_years",
    "pov": "potassium_mmol_L", "pof": "potassium_flag",
    "pol": "potassium_ref_low", "poh": "potassium_ref_high",
    "hev": "hemoglobin_g_dL", "hef": "hb_flag",
    "hel": "hb_ref_low", "heh": "hb_ref_high",
    "wbv": "wbc_10e9_L", "wbf": "wbc_flag",
    "wbl": "wbc_ref_low", "wbh": "wbc_ref_high",
    "cpv": "crp_mg_L", "cpf": "crp_flag",
    "cpl": "crp_ref_low", "cph": "crp_ref_high",
    "asv": "ast_U_L", "asf": "ast_flag",
    "asl": "ast_ref_low", "ash": "ast_ref_high",
    "sov": "sodium_mmol_L", "sof": "sodium_flag",
    "sol": "sodium_ref_low", "soh": "sodium_ref_high",
    "egv": "egfr_mL_min_1_73m2", "egf": "egfr_flag",
    "egl": "egfr_ref_low", "egh": "egfr_ref_high",
    "alv": "alt_U_L", "alf": "alt_flag",
    "all": "alt_ref_low", "alh": "alt_ref_high",
    "biv": "bilirubin_mg_dL", "bif": "bilirubin_flag",
    "bil": "bili_ref_low", "bih": "bili_ref_high",
    "inv": "inr", "inf": "inr_flag",
    "inl": "inr_ref_low", "inh": "inr_ref_high",
    "lav": "lactate_mmol_L", "laf": "lactate_flag",
    "lal": "lactate_ref_low", "lah": "lactate_ref_high",
    "crv": "creatinine_mg_dL", "crf": "creatinine_flag",
    "crl": "creatinine_ref_low", "crh": "creatinine_ref_high",
    "glv": "glucose_mg_dL", "glf": "glucose_flag",
    "gll": "glucose_ref_low", "glh": "glucose_ref_high",
    "plv": "platelets_10e9_L", "plf": "platelets_flag",
    "pll": "plt_ref_low", "plh": "plt_ref_high",
    "abv": "albumin_g_dL", "abf": "albumin_flag",
    "abl": "albumin_ref_low", "abh": "albumin_ref_high",
}

CLINIC2_DEVICE_RENAME = {
    "date": "timestamp", "id": "patient_id",
    "fall": "fall_event_0_1", "mag_impact": "impact_magnitude_g",
    "min_immob": "post_fall_immobility_minutes",
    "num_ex": "bed_exit_detected_0_1",
    "num_mov": "micro_movements_count",
    "idx_mov": "movement_index_0_100",
}

CLINIC2_1HZ_RENAME = {
    "id": "event_id", "id_pat": "patient_id", "id_dev": "device_id",
    "date": "timestamp",
    "accx": "accel_x_m_s2", "accy": "accel_y_m_s2",
    "accz": "accel_z_m_s2", "acc_mag": "accel_magnitude_g",
    "exit": "bed_exit_event_0_1", "return": "bed_return_event_0_1",
    "zone1_pa": "pressure_zone1_0_100", "zone2_pa": "pressure_zone2_0_100",
    "zone3_pa": "pressure_zone3_0_100", "zone4_pa": "pressure_zone4_0_100",
    "fall": "fall_event_0_1", "imp_mag": "impact_magnitude_g",
    "occ": "bed_occupied_0_1", "mov": "movement_score_0_100",
}

CLINIC2_ICD10_RENAME = {
    "DATE_AD": "admission_date", "ID_PAT": "patient_id",
    "ID_CAS": "case_id", "WARD": "ward",
    "D_M": "primary_icd10_code",
    "D_M_STR": "primary_icd10_description_en",
    "D_S": "secondary_icd10_codes",
    "D_S_STR": "secondary_icd10_descriptions_en",
    "PROC": "ops_codes", "PROC_STR": "ops_descriptions_en",
    "DATE_DIS": "discharge_date", "LOS": "length_of_stay_days",
}

CLINIC2_MEDICATION_RENAME = {
    "date_order1": "order_start_datetime",
    "date_order2": "order_stop_datetime",
    "ID_2": "patient_id", "ID_1": "encounter_id",
    "type": "record_type",
    "ID_order1": "order_id", "ID_order2": "order_uuid",
    "atc": "medication_code_atc", "name": "medication_name",
    "via": "route", "amount": "dose", "unit": "dose_unit",
    "freq": "frequency", "ward": "ward",
    "date_ad": "admission_datetime", "date_dis": "discharge_datetime",
    "prn": "is_prn_0_1", "indic": "indication",
    "role": "prescriber_role", "order_status": "order_status",
    "notes": "note",
}

CLINIC2_NURSING_RENAME = {
    "DAT": "report_date", "CAS": "case_id", "PAT": "patient_id",
    "WAR": "ward", "SHF": "shift", "TXT": "nursing_note_free_text",
}

# Positional headers for headerless files (clinic_3) and generic headers (clinic_4)
POSITIONAL_HEADERS = {
    "device_motion": [
        "timestamp", "patient_id", "fall_event_0_1",
        "movement_index_0_100", "bed_exit_detected_0_1",
        "micro_movements_count", "impact_magnitude_g",
        "post_fall_immobility_minutes",
    ],
    "device_1hz": [
        "patient_id", "device_id", "timestamp", "bed_occupied_0_1",
        "movement_score_0_100", "accel_x_m_s2", "accel_y_m_s2",
        "accel_z_m_s2", "accel_magnitude_g",
        "pressure_zone1_0_100", "pressure_zone2_0_100",
        "pressure_zone3_0_100", "pressure_zone4_0_100",
        "bed_exit_event_0_1", "bed_return_event_0_1",
        "fall_event_0_1", "impact_magnitude_g", "event_id",
    ],
    "icd10_ops": [
        "case_id", "patient_id", "ops_codes", "ops_descriptions_en",
        "primary_icd10_code", "primary_icd10_description_en",
        "secondary_icd10_codes", "secondary_icd10_descriptions_en",
        "admission_date", "discharge_date", "length_of_stay_days", "ward",
    ],
    "nursing": [
        "patient_id", "case_id", "report_date", "shift", "ward",
        "nursing_note_free_text",
    ],
}

# Clinic 3 labs has different column order: specimen_datetime, patient_id, case_id, age, sex, then labs
CLINIC3_LABS_HEADERS = [
    "specimen_datetime", "patient_id", "case_id", "age_years", "sex",
    "potassium_mmol_L", "potassium_flag", "potassium_ref_low", "potassium_ref_high",
    "hemoglobin_g_dL", "hb_flag", "hb_ref_low", "hb_ref_high",
    "wbc_10e9_L", "wbc_flag", "wbc_ref_low", "wbc_ref_high",
    "crp_mg_L", "crp_flag", "crp_ref_low", "crp_ref_high",
    "ast_U_L", "ast_flag", "ast_ref_low", "ast_ref_high",
    "sodium_mmol_L", "sodium_flag", "sodium_ref_low", "sodium_ref_high",
    "egfr_mL_min_1_73m2", "egfr_flag", "egfr_ref_low", "egfr_ref_high",
    "alt_U_L", "alt_flag", "alt_ref_low", "alt_ref_high",
    "bilirubin_mg_dL", "bilirubin_flag", "bili_ref_low", "bili_ref_high",
    "inr", "inr_flag", "inr_ref_low", "inr_ref_high",
    "lactate_mmol_L", "lactate_flag", "lactate_ref_low", "lactate_ref_high",
    "creatinine_mg_dL", "creatinine_flag", "creatinine_ref_low", "creatinine_ref_high",
    "glucose_mg_dL", "glucose_flag", "glucose_ref_low", "glucose_ref_high",
    "platelets_10e9_L", "platelets_flag", "plt_ref_low", "plt_ref_high",
    "albumin_g_dL", "albumin_flag", "albumin_ref_low", "albumin_ref_high",
]

# Clinic 3 medication (25 cols, no headers)
CLINIC3_MEDICATION_HEADERS = [
    "order_id", "order_uuid", "record_type", "patient_id", "encounter_id",
    "ward", "admission_datetime", "discharge_datetime",
    "medication_code_atc", "medication_name", "dose", "dose_unit",
    "frequency", "route", "order_start_datetime", "order_stop_datetime",
    "order_status", "administration_datetime", "administered_dose",
    "administered_unit", "administration_status", "is_prn_0_1",
    "indication", "prescriber_role", "note",
]

# Clinic 4 labs: patient_id, specimen_datetime, case_id, then lab values, last 2 are age and sex
CLINIC4_LABS_HEADERS = [
    "patient_id", "specimen_datetime", "case_id",
    "creatinine_mg_dL", "creatinine_flag", "creatinine_ref_low", "creatinine_ref_high",
    "sodium_mmol_L", "sodium_flag", "sodium_ref_low", "sodium_ref_high",
    "potassium_mmol_L", "potassium_flag", "potassium_ref_low", "potassium_ref_high",
    "glucose_mg_dL", "glucose_flag", "glucose_ref_low", "glucose_ref_high",
    "hemoglobin_g_dL", "hb_flag", "hb_ref_low", "hb_ref_high",
    "wbc_10e9_L", "wbc_flag", "wbc_ref_low", "wbc_ref_high",
    "crp_mg_L", "crp_flag", "crp_ref_low", "crp_ref_high",
    "alt_U_L", "alt_flag", "alt_ref_low", "alt_ref_high",
    "ast_U_L", "ast_flag", "ast_ref_low", "ast_ref_high",
    "egfr_mL_min_1_73m2", "egfr_flag", "egfr_ref_low", "egfr_ref_high",
    "bilirubin_mg_dL", "bilirubin_flag", "bili_ref_low", "bili_ref_high",
    "platelets_10e9_L", "platelets_flag", "plt_ref_low", "plt_ref_high",
    "lactate_mmol_L", "lactate_flag", "lactate_ref_low", "lactate_ref_high",
    "inr", "inr_flag", "inr_ref_low", "inr_ref_high",
    "albumin_g_dL", "albumin_flag", "albumin_ref_low", "albumin_ref_high",
    "age_years", "sex",
]

# Clinic 4 ICD10 (10 cols)
CLINIC4_ICD10_HEADERS = [
    "patient_id", "case_id", "admission_date", "discharge_date",
    "length_of_stay_days", "primary_icd10_code",
    "primary_icd10_description_en", "ops_codes", "ops_descriptions_en",
    "ward",
]

# Clinic 4 medication (24 cols)
CLINIC4_MEDICATION_HEADERS = [
    "patient_id", "medication_code_atc", "medication_name",
    "order_start_datetime", "order_stop_datetime",
    "is_prn_0_1", "indication", "route", "dose", "dose_unit",
    "frequency", "administered_dose", "administered_unit",
    "administration_status", "administration_datetime",
    "prescriber_role", "order_status", "record_type",
    "order_id", "order_uuid", "encounter_id",
    "admission_datetime", "discharge_datetime", "note",
]

# Clinic 4 device (8 cols)
CLINIC4_DEVICE_HEADERS = [
    "patient_id", "timestamp", "bed_exit_detected_0_1",
    "fall_event_0_1", "movement_index_0_100",
    "micro_movements_count", "impact_magnitude_g",
    "post_fall_immobility_minutes",
]

# Clinic 4 device_1hz (14 cols — fewer than standard 18)
CLINIC4_1HZ_HEADERS = [
    "fall_event_0_1", "timestamp", "device_id", "patient_id",
    "bed_exit_event_0_1", "bed_return_event_0_1",
    "bed_occupied_0_1", "impact_magnitude_g",
    "pressure_zone1_0_100", "pressure_zone2_0_100",
    "pressure_zone3_0_100", "pressure_zone4_0_100",
    "movement_score_0_100", "accel_magnitude_g",
]


def infer_type_from_filename(filename):
    """Infer file type from filename pattern (fallback when column detection fails)."""
    fname = filename.lower()
    if "labs" in fname:
        return "labs"
    if "icd" in fname or "icd_ops" in fname:
        return "icd10_ops"
    if "1hz" in fname or "device_1hz" in fname or "device_raw" in fname:
        return "device_1hz"
    if "device" in fname or "motion" in fname:
        return "device_motion"
    if "medication" in fname or "medic" in fname:
        return "medication"
    if "nursing" in fname:
        return "nursing"
    if "epac" in fname or "epaac" in fname:
        return "epaAC_german"
    return "unknown"


def detect_file_type(columns):
    """Detect file type based on column names, not file name."""
    col_set = set(columns)

    # Check epaAC_pivot first (most specific)
    sig = COLUMN_SIGNATURES["epaAC_pivot"]
    if sig["check"](col_set):
        return "epaAC_pivot"

    # Check epaAC_german before epaAC_sap (german is more specific)
    sig = COLUMN_SIGNATURES["epaAC_german"]
    if sig["check"](col_set):
        return "epaAC_german"

    sig = COLUMN_SIGNATURES["epaAC_sap"]
    if sig["check"](columns):
        return "epaAC_sap"

    # Check all other signatures
    for sig_name in ["labs", "icd10_ops", "device_motion", "device_1hz",
                     "medication", "nursing"]:
        sig = COLUMN_SIGNATURES[sig_name]
        if "required" in sig:
            if sig["required"].issubset(col_set):
                return sig_name
        if "alt_required" in sig:
            if sig["alt_required"].issubset(col_set):
                return sig_name
        if "alt_required_2" in sig:
            if sig["alt_required_2"].issubset(col_set):
                return sig_name

    return "unknown"
