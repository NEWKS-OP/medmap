"""Schema Detective agent: analyzes columns and proposes mappings.

Examines unknown columns from source data and proposes target schema mappings
with a confidence score. Uses pattern matching on column names and data content.
"""

import logging
import re
from typing import Optional

from pipeline.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Known column name patterns -> (target_column, confidence)
KNOWN_PATTERNS: dict[str, tuple[str, float]] = {
    r"weight|gewicht|poids|koerpergewicht": ("coWeight", 0.95),
    r"height|groesse|taille|koerpergroesse": ("coHeight", 0.95),
    r"egfr|glomerular|filtration": ("coEgfr_mL_min_1_73m2", 0.97),
    r"creatinine|kreatinin": ("coCreatinine_mg_dL", 0.97),
    r"sodium|natrium|na_mmol": ("coSodium_mmol_L", 0.96),
    r"potassium|kalium|k_mmol": ("coPotassium_mmol_L", 0.96),
    r"glucose|glukose|blutzucker": ("coGlucose_mg_dL", 0.95),
    r"hemoglobin|haemoglobin|hb_g": ("coHemoglobin_g_dL", 0.96),
    r"wbc|leuko|white_blood": ("coWbc_10e9_L", 0.95),
    r"platelets|thrombo|plt": ("coPlatelets_10e9_L", 0.95),
    r"crp|c_reactive": ("coCrp_mg_L", 0.96),
    r"alt_u|alt_value|sgpt|alanine": ("coAlt_U_L", 0.94),
    r"ast_u|ast_value|sgot|aspartate": ("coAst_U_L", 0.94),
    r"bilirubin|bili": ("coBilirubin_mg_dL", 0.95),
    r"albumin|alb_g": ("coAlbumin_g_dL", 0.95),
    r"inr|prothrombin": ("coInr", 0.96),
    r"lactate|laktat": ("coLactate_mmol_L", 0.96),
    r"bmi|body_mass": ("coBmi", 0.98),
    r"gender|sex|geschlecht": ("coGender", 0.99),
    r"case_id|fallid|caseid|fall_id": ("coCaseId", 0.99),
    r"patient_id|pid|patientid|pat_id": ("coPatientId", 0.99),
    r"ward|station|abteilung": ("coWard", 0.97),
    r"admission|aufnahme|einweisung": ("coAdmission_date", 0.90),
    r"discharge|entlass": ("coDischarge_date", 0.90),
    r"icd.*10|diagnos|hauptdiagnose": ("coPrimary_icd10_code", 0.95),
    r"medication|medikament|drug_name": ("coMedication_name", 0.96),
    r"dose|dosis": ("coDose", 0.93),
    r"frequency|frequenz|haeufigkeit": ("coFrequency", 0.92),
    r"route|applikation": ("coRoute", 0.93),
    r"shift|schicht": ("coShift", 0.97),
    r"nursing.*note|pflegebericht|note_text": ("coNursing_note_free_text", 0.96),
    r"report_date|berichtsdatum": ("coReport_date", 0.95),
    r"fall_event|sturz": ("coFall_event_0_1", 0.97),
    r"bed_exit|bettausstieg": ("coBed_exit_detected_0_1", 0.96),
    r"movement.*index|bewegungsindex": ("coMovement_index_0_100", 0.95),
    r"impact.*magnitude|aufprall": ("coImpact_magnitude_g", 0.94),
    r"immobility|immobilität": ("coPost_fall_immobility_minutes", 0.93),
    r"timestamp|zeitstempel": ("coTimestamp", 0.90),
    r"specimen.*date|probendatum": ("coSpecimen_datetime", 0.93),
    r"date_of_birth|geburtsdatum|dob": ("coDateOfBirth", 0.98),
    r"age|alter": ("coAgeYears", 0.95),
    r"firstname|vorname": ("coFirstname", 0.97),
    r"lastname|nachname|familienname": ("coLastname", 0.97),
}

# Compile patterns once
_COMPILED_PATTERNS = [
    (re.compile(pat, re.IGNORECASE), target, conf)
    for pat, (target, conf) in KNOWN_PATTERNS.items()
]


def confidence_badge(confidence: float) -> str:
    """Map confidence score to a badge label."""
    if confidence >= 0.90:
        return "AUTO"
    if confidence >= 0.70:
        return "CHECK"
    return "REVIEW"


def detect_column_mapping(column_name: str, sample_values: list = None) -> dict:
    """Analyze a single column and propose a target mapping.

    Returns dict with: source_column, target_column, confidence, badge, reasoning.
    """
    col_lower = column_name.lower().strip()

    # Try pattern matching
    for pattern, target, conf in _COMPILED_PATTERNS:
        if pattern.search(col_lower):
            return {
                "source_column": column_name,
                "target_column": target,
                "confidence": conf,
                "badge": confidence_badge(conf),
                "reasoning": f"Column name '{column_name}' matches pattern for {target}",
            }

    # Try data-based heuristics if sample values provided
    if sample_values:
        inferred = _infer_from_values(column_name, sample_values)
        if inferred:
            return inferred

    # Unknown column
    return {
        "source_column": column_name,
        "target_column": None,
        "confidence": 0.0,
        "badge": "REVIEW",
        "reasoning": f"No pattern match for '{column_name}'",
    }


def _infer_from_values(column_name: str, values: list) -> Optional[dict]:
    """Infer column type from sample values."""
    non_null = [v for v in values if v is not None and str(v).strip()]
    if not non_null:
        return None

    sample = [str(v) for v in non_null[:50]]

    # Check if all values are M/F -> gender
    unique = {s.upper() for s in sample}
    if unique <= {"M", "F", "MALE", "FEMALE", "MÄNNLICH", "WEIBLICH"}:
        return {
            "source_column": column_name,
            "target_column": "coGender",
            "confidence": 0.85,
            "badge": "CHECK",
            "reasoning": f"Values {unique} suggest gender column",
        }

    # Check if all values are Early/Late/Night -> shift
    if unique <= {"EARLY", "LATE", "NIGHT", "FRÜHSCHICHT", "SPÄTSCHICHT", "NACHTSCHICHT",
                  "EARLY SHIFT", "LATE SHIFT", "NIGHT SHIFT"}:
        return {
            "source_column": column_name,
            "target_column": "coShift",
            "confidence": 0.88,
            "badge": "CHECK",
            "reasoning": f"Values {unique} suggest shift column",
        }

    # Check if all numeric 0-1 -> binary flag
    try:
        nums = [float(s) for s in sample]
        if all(n in (0, 1, 0.0, 1.0) for n in nums):
            return {
                "source_column": column_name,
                "target_column": None,
                "confidence": 0.60,
                "badge": "REVIEW",
                "reasoning": "Binary 0/1 column — could be a flag field",
            }
    except (ValueError, TypeError):
        pass

    return None


class SchemaDetectiveAgent(BaseAgent):
    """Agent that analyzes all source columns and proposes schema mappings."""

    def __init__(self):
        super().__init__("SchemaDetective")

    def run(self, context: dict) -> AgentResult:
        """Analyze all columns in context dataframes.

        Reads context["dataframes"], writes context["column_mappings"].
        """
        dataframes = context.get("dataframes", {})
        if not dataframes:
            return self._fail("No dataframes in context")

        mappings = []
        total_cols = 0
        auto_count = 0
        review_count = 0

        for fname, df in dataframes.items():
            if df is None or df.empty:
                continue
            for col in df.columns:
                total_cols += 1
                sample = df[col].dropna().head(20).tolist()
                mapping = detect_column_mapping(col, sample)
                mapping["source_file"] = fname
                mappings.append(mapping)

                if mapping["badge"] == "AUTO":
                    auto_count += 1
                elif mapping["badge"] == "REVIEW":
                    review_count += 1

        context["column_mappings"] = mappings

        self.logger.info(
            "Schema Detective: %d columns, %d auto-mapped, %d need review",
            total_cols, auto_count, review_count,
        )

        return self._ok(
            data=mappings,
            total_columns=total_cols,
            auto_mapped=auto_count,
            needs_review=review_count,
            check_count=total_cols - auto_count - review_count,
        )
