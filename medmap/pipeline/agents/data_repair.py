"""Data Repair agent: proposes automatic repairs for quarantined values.

Analyzes quarantined data passport entries and proposes fixes based on
statistical inference, pattern matching, and clinical rules.
"""

import logging
import sqlite3
from typing import Optional

from pipeline.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Repair strategies by problem type
REPAIR_STRATEGIES = {
    "MISSING_VALUE": "impute",
    "MISSING": "impute",
    "INVALID_FORMAT": "reformat",
    "INVALID": "reformat",
    "CLINICAL_OUTLIER": "clamp_or_flag",
    "OUTLIER": "clamp_or_flag",
    "TYPE_MISMATCH": "cast",
    "INVALID_GENDER": "normalize",
    "INVALID_DATE": "parse_date",
    "INVALID_SHIFT": "normalize_shift",
    "DUPLICATE": "deduplicate",
    "CORRECTED": "skip",
}


def propose_repair(passport: dict, db: sqlite3.Connection = None) -> dict:
    """Propose a repair for a single quarantined data passport entry.

    Returns dict with: passport_id, proposed_value, strategy, confidence, reasoning.
    """
    problem_type = passport.get("problem_type", "")
    raw_value = passport.get("raw_value", "")
    field_name = passport.get("field_name", "")
    case_id = passport.get("case_id", "")

    strategy = REPAIR_STRATEGIES.get(problem_type, "manual")

    if strategy == "skip":
        return _no_repair(passport, "Already corrected")
    elif strategy == "impute" and db:
        return _repair_impute(passport, db)
    elif strategy == "reformat":
        return _repair_reformat(passport)
    elif strategy == "clamp_or_flag":
        return _repair_clamp(passport)
    elif strategy == "cast":
        return _repair_cast(passport)
    elif strategy == "normalize":
        return _repair_normalize_gender(passport)
    elif strategy == "parse_date":
        return _repair_date(passport)
    elif strategy == "normalize_shift":
        return _repair_shift(passport)
    elif strategy == "deduplicate":
        return _no_repair(passport, "Duplicate — recommend keeping first occurrence")

    # Try generic strategies based on problem_detail
    detail = str(passport.get("problem_detail", "")).lower()
    if "date" in detail or "datum" in detail:
        return _repair_date(passport)
    if "gender" in detail or "geschlecht" in detail:
        return _repair_normalize_gender(passport)
    if "id" in detail and raw_value:
        return _repair_reformat(passport)

    return _no_repair(passport, f"No automatic repair strategy for {problem_type}")


def _repair_impute(passport: dict, db: sqlite3.Connection) -> dict:
    """Impute missing value using column median/mode from same table."""
    field = passport.get("field_name", "")
    table = passport.get("table_name", "")

    if not table or not field:
        return _no_repair(passport, "Cannot impute: missing table/field info")

    try:
        # Try median for numeric columns
        row = db.execute(
            f"SELECT AVG(CAST([{field}] AS REAL)) as median_val FROM [{table}] WHERE [{field}] IS NOT NULL"
        ).fetchone()

        if row and row["median_val"] is not None:
            val = round(row["median_val"], 2)
            return _make_repair(passport, str(val), "impute_median", 0.60,
                                f"Imputed with column median ({val})")
    except Exception:
        pass

    try:
        # Try mode for categorical columns
        row = db.execute(
            f"SELECT [{field}], COUNT(*) as cnt FROM [{table}] WHERE [{field}] IS NOT NULL GROUP BY [{field}] ORDER BY cnt DESC LIMIT 1"
        ).fetchone()

        if row and row[field]:
            return _make_repair(passport, str(row[field]), "impute_mode", 0.55,
                                f"Imputed with column mode ({row[field]})")
    except Exception:
        pass

    return _no_repair(passport, "Cannot impute — no valid values in column")


def _repair_reformat(passport: dict) -> dict:
    """Attempt to reformat invalid string values."""
    raw = str(passport.get("raw_value", "")).strip()
    if not raw:
        return _no_repair(passport, "Empty value — cannot reformat")

    # Remove common garbage characters
    cleaned = raw.replace("@", "").replace("#", "").replace("PRIORITY", "").strip()
    if cleaned and cleaned != raw:
        return _make_repair(passport, cleaned, "strip_garbage", 0.80,
                            f"Stripped invalid characters from '{raw}'")

    # Normalize whitespace
    import re
    normalized = re.sub(r'\s+', ' ', raw).strip()
    if normalized != raw:
        return _make_repair(passport, normalized, "normalize_whitespace", 0.85,
                            f"Normalized whitespace in '{raw[:50]}'")

    # Strip prefix from IDs like "CASE-" or "PAT_"
    field = passport.get("field_name", "").lower()
    if "id" in field:
        # Extract the numeric part
        match = re.search(r'(\d+)', raw)
        if match and len(match.group(1)) >= 2:
            return _make_repair(passport, match.group(1), "extract_id_number", 0.65,
                                f"Extracted numeric ID from '{raw}'")

    return _no_repair(passport, "No reformatting rule applies")


def _repair_clamp(passport: dict) -> dict:
    """Clamp clinical outlier to valid range boundary."""
    from config.clinical_rules import CLINICAL_RANGES

    field = passport.get("field_name", "")
    raw = passport.get("raw_value", "")

    # Find matching clinical range
    for range_key, (low, high) in CLINICAL_RANGES.items():
        if range_key.lower() in field.lower() or field.lower() in range_key.lower():
            try:
                val = float(raw)
                if val < low:
                    return _make_repair(passport, str(low), "clamp_low", 0.50,
                                        f"Clamped {val} to minimum {low}")
                elif val > high:
                    return _make_repair(passport, str(high), "clamp_high", 0.50,
                                        f"Clamped {val} to maximum {high}")
            except (ValueError, TypeError):
                pass

    return _no_repair(passport, "No clinical range found for clamping")


def _repair_cast(passport: dict) -> dict:
    """Attempt type casting."""
    raw = str(passport.get("raw_value", "")).strip()

    # Try to extract a number from a mixed string like "5@" or "123mg"
    import re
    match = re.search(r"[-+]?\d*\.?\d+", raw)
    if match:
        return _make_repair(passport, match.group(0), "extract_numeric", 0.75,
                            f"Extracted numeric value from '{raw}'")

    return _no_repair(passport, "Cannot cast value to expected type")


def _repair_normalize_gender(passport: dict) -> dict:
    """Normalize gender values."""
    raw = str(passport.get("raw_value", "")).strip().upper()
    gender_map = {
        "MALE": "M", "FEMALE": "F", "MÄNNLICH": "M", "WEIBLICH": "F",
        "MANN": "M", "FRAU": "F", "H": "M", "HOMME": "M", "FEMME": "F",
        "1": "M", "2": "F",
    }
    if raw in gender_map:
        return _make_repair(passport, gender_map[raw], "normalize_gender", 0.95,
                            f"Normalized gender '{raw}' → '{gender_map[raw]}'")
    return _no_repair(passport, f"Unknown gender value: {raw}")


def _repair_date(passport: dict) -> dict:
    """Attempt to parse and normalize a date string."""
    raw = str(passport.get("raw_value", "")).strip()
    if not raw:
        return _no_repair(passport, "Empty date value")

    from pipeline.cleaner import DataCleaner
    normalized = DataCleaner._normalize_single_date_static(raw)
    if normalized and normalized != raw:
        return _make_repair(passport, normalized, "parse_date", 0.80,
                            f"Parsed date '{raw}' → '{normalized}'")

    return _no_repair(passport, f"Cannot parse date: {raw}")


def _repair_shift(passport: dict) -> dict:
    """Normalize shift values."""
    from pipeline.nlp import normalize_shift
    raw = str(passport.get("raw_value", "")).strip()
    normalized = normalize_shift(raw)
    if normalized != "Early" or "early" in raw.lower() or "früh" in raw.lower():
        return _make_repair(passport, normalized, "normalize_shift", 0.85,
                            f"Normalized shift '{raw}' → '{normalized}'")
    return _no_repair(passport, f"Cannot normalize shift: {raw}")


def _make_repair(passport: dict, proposed_value: str, strategy: str,
                 confidence: float, reasoning: str) -> dict:
    """Build a repair proposal."""
    return {
        "passport_id": passport.get("passport_id"),
        "case_id": passport.get("case_id"),
        "field_name": passport.get("field_name"),
        "raw_value": passport.get("raw_value"),
        "proposed_value": proposed_value,
        "strategy": strategy,
        "confidence": confidence,
        "reasoning": reasoning,
        "auto_apply": confidence >= 0.80,
    }


def _no_repair(passport: dict, reasoning: str) -> dict:
    """Build a no-repair response."""
    return {
        "passport_id": passport.get("passport_id"),
        "case_id": passport.get("case_id"),
        "field_name": passport.get("field_name"),
        "raw_value": passport.get("raw_value"),
        "proposed_value": None,
        "strategy": "manual",
        "confidence": 0.0,
        "reasoning": reasoning,
        "auto_apply": False,
    }


class DataRepairAgent(BaseAgent):
    """Agent that proposes automatic repairs for quarantined data values."""

    def __init__(self):
        super().__init__("DataRepair")

    def run(self, context: dict) -> AgentResult:
        """Analyze quarantined passports and propose repairs.

        Reads from DB (context["db_conn"]) or context["pending_corrections"].
        Writes context["repair_proposals"].
        """
        db = context.get("db_conn")
        proposals = []

        # Get quarantined passports from DB
        passports = context.get("pending_corrections", [])
        if not passports and db:
            try:
                rows = db.execute(
                    "SELECT * FROM tbDataPassport WHERE status IN ('QUARANTINE', 'PENDING_REVIEW') LIMIT 500"
                ).fetchall()
                passports = [dict(r) for r in rows]
            except Exception as e:
                self.logger.warning("Failed to load passports: %s", e)

        if not passports:
            return self._ok(data=[], total=0, repairable=0, auto_apply=0)

        repairable = 0
        auto_apply = 0

        for passport in passports:
            proposal = propose_repair(passport, db)
            proposals.append(proposal)
            if proposal["proposed_value"] is not None:
                repairable += 1
                if proposal["auto_apply"]:
                    auto_apply += 1

        context["repair_proposals"] = proposals

        self.logger.info(
            "Data Repair: %d passports, %d repairable, %d auto-apply",
            len(passports), repairable, auto_apply,
        )

        return self._ok(
            data=proposals,
            total=len(passports),
            repairable=repairable,
            auto_apply=auto_apply,
        )
