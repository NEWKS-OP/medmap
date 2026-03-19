"""
Schema mapping configuration: source column names -> target SQL column names.
Detects file type by column signatures, not file names.
"""

# Column signatures to detect file type by content
COLUMN_SIGNATURES = {
    "labs": {
        "required": {"case_id", "patient_id", "sodium_mmol_L"},
        "alt_required": {"case_id", "patient_id", "specimen_datetime"},
    },
    "icd10_ops": {
        "required": {"case_id", "primary_icd10_code", "ward"},
    },
    "device_motion": {
        "required": {"patient_id", "timestamp", "movement_index_0_100", "fall_event_0_1"},
    },
    "device_1hz": {
        "required": {"patient_id", "timestamp", "accel_x_m_s2", "device_id"},
    },
    "medication": {
        "required": {"case_id", "patient_id", "medication_name", "record_type"},
        "alt_required": {"case_id", "patient_id", "medication_name", "event_type"},
    },
    "nursing": {
        "required": {"case_id", "patient_id", "shift", "nursing_note_free_text"},
        "alt_required": {"case_id", "patient_id", "shift", "note_text"},
    },
    "epaAC_sap": {
        "check": lambda cols: any(c.startswith("EPA") or c == "MANDT" or c == "PATFAL" for c in cols),
    },
    "epaAC_german": {
        "check": lambda cols: "AufnDat" in cols or "Körpergröße" in cols or "Koerpergroesse" in cols,
    },
}

# Source -> Target column mappings per table

LABS_MAPPING = {
    "case_id": "coCaseId",
    "specimen_datetime": "coSpecimen_datetime",
    "sodium_mmol_L": "coSodium_mmol_L",
    "sodium_flag": "coSodium_flag",
    "sodium_ref_low": "cosodium_ref_low",
    "sodium_ref_high": "cosodium_ref_high",
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
    "ward": "coWard",
    "admission_date": "coAdmission_date",
    "discharge_date": "coDischarge_date",
    "length_of_stay_days": "coLength_of_stay_days",
    "primary_icd10_code": "coPrimary_icd10_code",
    "primary_icd10_description_en": "coPrimary_icd10_description_en",
    "secondary_icd10_codes": "coSecondary_icd10_codes",
    "secondary_icd10_descriptions_en": "cpSecondary_icd10_descriptions_en",
    "ops_codes": "coOps_codes",
    "ops_descriptions_en": "ops_descriptions_en",
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
    "prescriber_role": "prescriber_role",
    "order_status": "order_status",
    "administration_datetime": "administration_datetime",
    "administered_dose": "administered_dose",
    "administered_unit": "administered_unit",
    "administration_status": "administration_status",
    "note": "note",
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
}

# PID prefix per source type
PID_PREFIXES = {
    "labs": "LAB",
    "device_motion": "MOT",
    "device_1hz": "MOT",
    "medication": "MED",
    "nursing": "NUR",
    "epaAC": "EPA",
    "icd10_ops": "ICD",
}


def detect_file_type(columns: list[str]) -> str:
    """Detect file type based on column names, not file name."""
    col_set = set(columns)
    col_lower = {c.lower() for c in columns}

    for sig_name, sig in COLUMN_SIGNATURES.items():
        if "check" in sig:
            if sig["check"](columns):
                return sig_name
        if "required" in sig:
            if sig["required"].issubset(col_set) or sig["required"].issubset(col_lower):
                return sig_name
        if "alt_required" in sig:
            if sig["alt_required"].issubset(col_set) or sig["alt_required"].issubset(col_lower):
                return sig_name

    return "unknown"
