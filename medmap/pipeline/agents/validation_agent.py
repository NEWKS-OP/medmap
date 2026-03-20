"""Validation Agent: challenges Schema Detective decisions.

Verifies that proposed column mappings are consistent with actual data values,
types, and cross-column coherence. Acts as a second opinion on detective's work.
"""

import logging
import re
from typing import Optional

import pandas as pd

from pipeline.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Expected data characteristics for target columns
COLUMN_VALIDATORS = {
    "coGender": {
        "valid_values": {"M", "F", "m", "f", "Male", "Female"},
        "max_unique": 10,
        "type": "categorical",
    },
    "coShift": {
        "valid_values": {"Early", "Late", "Night", "Early shift", "Late shift", "Night shift",
                         "Frühschicht", "Spätschicht", "Nachtschicht"},
        "max_unique": 15,
        "type": "categorical",
    },
    "coAgeYears": {
        "numeric_range": (0, 120),
        "type": "numeric",
    },
    "coCaseId": {
        "type": "id",
        "min_unique_ratio": 0.01,  # At least 1% unique values
    },
    "coPatientId": {
        "type": "id",
        "min_unique_ratio": 0.01,
    },
    "coSodium_mmol_L": {"numeric_range": (80, 180), "type": "numeric"},
    "coPotassium_mmol_L": {"numeric_range": (1.5, 8.0), "type": "numeric"},
    "coCreatinine_mg_dL": {"numeric_range": (0.1, 20.0), "type": "numeric"},
    "coEgfr_mL_min_1_73m2": {"numeric_range": (1, 150), "type": "numeric"},
    "coGlucose_mg_dL": {"numeric_range": (10, 700), "type": "numeric"},
    "coHemoglobin_g_dL": {"numeric_range": (2, 25), "type": "numeric"},
    "coWbc_10e9_L": {"numeric_range": (0.05, 100), "type": "numeric"},
    "coCrp_mg_L": {"numeric_range": (0, 500), "type": "numeric"},
    "coInr": {"numeric_range": (0.3, 12), "type": "numeric"},
    "coLactate_mmol_L": {"numeric_range": (0.1, 25), "type": "numeric"},
    "coBmi": {"numeric_range": (10, 80), "type": "numeric"},
    "coFall_event_0_1": {"valid_values": {"0", "1", 0, 1}, "type": "binary"},
    "coBed_exit_detected_0_1": {"valid_values": {"0", "1", 0, 1}, "type": "binary"},
    "coMovement_index_0_100": {"numeric_range": (0, 100), "type": "numeric"},
}


def validate_mapping(mapping: dict, df: pd.DataFrame) -> dict:
    """Validate a single column mapping against actual data.

    Returns the mapping enriched with validation_result and adjusted confidence.
    """
    source_col = mapping.get("source_column")
    target_col = mapping.get("target_column")
    original_confidence = mapping.get("confidence", 0)

    result = {
        **mapping,
        "validation_result": "PASS",
        "validation_notes": [],
        "adjusted_confidence": original_confidence,
    }

    if not target_col or source_col not in df.columns:
        result["validation_result"] = "SKIP"
        return result

    validator = COLUMN_VALIDATORS.get(target_col)
    if not validator:
        # No specific validator — trust the detective
        result["validation_result"] = "PASS"
        return result

    col_data = df[source_col].dropna()
    if col_data.empty:
        result["validation_result"] = "WARN"
        result["validation_notes"].append("Column is entirely null/empty")
        result["adjusted_confidence"] = original_confidence * 0.5
        return result

    notes = []
    penalty = 0.0

    col_type = validator.get("type")

    if col_type == "categorical":
        valid_vals = validator.get("valid_values", set())
        if valid_vals:
            actual = set(str(v).strip() for v in col_data.unique())
            invalid = actual - {str(v) for v in valid_vals}
            if invalid:
                overlap = len(actual - invalid) / max(len(actual), 1)
                if overlap < 0.5:
                    notes.append(f"Most values don't match expected: {list(invalid)[:5]}")
                    penalty += 0.3
                else:
                    notes.append(f"Some unexpected values: {list(invalid)[:3]}")
                    penalty += 0.1

        max_unique = validator.get("max_unique")
        if max_unique and col_data.nunique() > max_unique:
            notes.append(f"Too many unique values ({col_data.nunique()}) for categorical")
            penalty += 0.15

    elif col_type == "numeric":
        num_range = validator.get("numeric_range")
        if num_range:
            try:
                numeric_vals = pd.to_numeric(col_data, errors="coerce").dropna()
                if not numeric_vals.empty:
                    low, high = num_range
                    out_of_range = ((numeric_vals < low) | (numeric_vals > high)).sum()
                    ratio = out_of_range / len(numeric_vals)
                    if ratio > 0.5:
                        notes.append(f"{ratio:.0%} values outside expected range [{low}, {high}]")
                        penalty += 0.3
                    elif ratio > 0.1:
                        notes.append(f"{ratio:.0%} values outside range [{low}, {high}]")
                        penalty += 0.1
                else:
                    notes.append("No numeric values found — expected numeric column")
                    penalty += 0.25
            except Exception:
                notes.append("Failed to parse as numeric")
                penalty += 0.2

    elif col_type == "binary":
        valid_vals = validator.get("valid_values", set())
        actual = set(col_data.unique())
        str_actual = {str(v).strip() for v in actual}
        if not str_actual <= {str(v) for v in valid_vals}:
            notes.append(f"Non-binary values found: {list(actual)[:5]}")
            penalty += 0.25

    elif col_type == "id":
        min_ratio = validator.get("min_unique_ratio", 0.01)
        unique_ratio = col_data.nunique() / max(len(col_data), 1)
        if unique_ratio < min_ratio:
            notes.append(f"Very low cardinality ({unique_ratio:.2%}) for ID column")
            penalty += 0.15

    # Apply penalty
    result["adjusted_confidence"] = max(0, original_confidence - penalty)
    result["validation_notes"] = notes

    if penalty >= 0.3:
        result["validation_result"] = "FAIL"
        result["badge"] = "REVIEW"
    elif penalty > 0:
        result["validation_result"] = "WARN"
    else:
        result["validation_result"] = "PASS"

    return result


class ValidationAgent(BaseAgent):
    """Agent that validates Schema Detective's proposed mappings."""

    def __init__(self):
        super().__init__("ValidationAgent")

    def run(self, context: dict) -> AgentResult:
        """Validate all column mappings from the detective.

        Reads context["column_mappings"] and context["dataframes"].
        Updates mappings in-place with validation results.
        """
        mappings = context.get("column_mappings", [])
        dataframes = context.get("dataframes", {})

        if not mappings:
            return self._fail("No column mappings to validate")

        validated = []
        pass_count = 0
        warn_count = 0
        fail_count = 0

        for mapping in mappings:
            source_file = mapping.get("source_file", "")
            df = dataframes.get(source_file)
            if df is None or df.empty:
                validated.append(mapping)
                continue

            result = validate_mapping(mapping, df)
            validated.append(result)

            vr = result.get("validation_result", "SKIP")
            if vr == "PASS":
                pass_count += 1
            elif vr == "WARN":
                warn_count += 1
            elif vr == "FAIL":
                fail_count += 1

        context["column_mappings"] = validated

        self.logger.info(
            "Validation Agent: %d pass, %d warn, %d fail",
            pass_count, warn_count, fail_count,
        )

        return self._ok(
            data=validated,
            total=len(validated),
            passed=pass_count,
            warnings=warn_count,
            failed=fail_count,
        )
