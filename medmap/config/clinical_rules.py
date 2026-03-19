CLINICAL_RANGES = {
    "sodium_mmol_L": (100, 165),
    "potassium_mmol_L": (2.0, 7.5),
    "creatinine_mg_dL": (0.3, 15.0),
    "egfr_mL_min_1_73m2": (1, 120),
    "glucose_mg_dL": (20, 600),
    "hemoglobin_g_dL": (3, 25),
    "wbc_10e9_L": (0.1, 100),
    "platelets_10e9_L": (10, 1000),
    "crp_mg_L": (0, 500),
    "alt_U_L": (1, 5000),
    "ast_U_L": (1, 5000),
    "bilirubin_mg_dL": (0, 30),
    "albumin_g_dL": (1, 6),
    "inr": (0.5, 10),
    "lactate_mmol_L": (0.3, 20),
    "bmi": (10, 70),
    "impact_magnitude_g": (0, 50),
}

VALID_LAB_FLAGS = {"H", "L", "HH", "LL", ""}

MISSING_VALUE_TOKENS = {
    "null", "nan", "n/a", "na", "missing", "unknown", "keine",
    "none", "nil", "", " ",
}

ANOMALY_RULES = {
    "AKI_PROBABLE": {
        "conditions": {"creatinine_mg_dL": (">", 3.0), "egfr_mL_min_1_73m2": ("<", 20), "potassium_mmol_L": (">", 5.5)},
        "severity": "CRITICAL",
        "message": "Probable acute kidney injury: creatinine > 3.0, eGFR < 20, potassium > 5.5",
    },
    "SEPSIS_POSSIBLE": {
        "conditions": {"crp_mg_L": (">", 100), "lactate_mmol_L": (">", 2.0), "wbc_10e9_L": (">", 12)},
        "severity": "CRITICAL",
        "message": "Possible sepsis: CRP > 100, lactate > 2.0, WBC > 12",
    },
    "HIGH_FALL_RISK": {
        "conditions": {"fall_event_0_1": ("==", 1), "post_fall_immobility_minutes": (">", 15)},
        "severity": "HIGH",
        "message": "High fall risk: fall event detected with immobility > 15 minutes",
    },
    "DANGEROUS_MED_AKI": {
        "conditions": {"egfr_mL_min_1_73m2": ("<", 30)},
        "med_names": ["metformin", "nsar", "aminoglycoside", "ibuprofen", "diclofenac", "gentamicin"],
        "severity": "CRITICAL",
        "message": "Dangerous medication with impaired renal function (eGFR < 30)",
    },
    "MULTI_SOURCE_DETERIORATION": {
        "conditions": {"deterioration_flag": ("==", True)},
        "severity": "HIGH",
        "message": "Multi-source deterioration detected across nursing and motion data",
    },
    "ANTICOAG_INR_ABNORMAL": {
        "conditions": {},
        "med_names": ["warfarin", "phenprocoumon", "marcumar"],
        "inr_range": (2.0, 4.0),
        "severity": "HIGH",
        "message": "Anticoagulant therapy with abnormal INR (outside 2.0-4.0)",
    },
}
