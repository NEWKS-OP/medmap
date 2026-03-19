"""
Module 4: NLP (BONUS)
Extracts structured data from nursing notes using spaCy.

Extracts:
1. Pain level (0-10)
2. Mobility status (INDEPENDENT / ASSISTED / WHEELCHAIR / BED_BOUND)
3. Wound grade (1-4 or HEALING)
4. Deterioration signs (boolean + list)
"""

import logging
import re
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ─── Pain level patterns ───────────────────────────────────────────
# Matches: "pain level 5/10", "pain score 7", "VAS 3", "pain 8/10"
_PAIN_NUMERIC_RE = re.compile(
    r"(?:pain\s*(?:level|score)?|vas)\s*[:=]?\s*(\d{1,2})\s*(?:/\s*10)?",
    re.IGNORECASE,
)

# Qualitative pain descriptors mapped to numeric estimates
_PAIN_QUALITATIVE = {
    "no pain": 0,
    "pain free": 0,
    "schmerzfrei": 0,
    "mild pain": 3,
    "leichte schmerzen": 3,
    "moderate pain": 5,
    "mittlere schmerzen": 5,
    "severe pain": 8,
    "starke schmerzen": 8,
    "schmerzen": 4,  # generic German "pain"
}

_PAIN_QUAL_RE = re.compile(
    "|".join(re.escape(k) for k in _PAIN_QUALITATIVE),
    re.IGNORECASE,
)


def extract_pain_level(text: str) -> Optional[int]:
    """Extract pain level (0-10) from nursing note text."""
    if not text or not isinstance(text, str):
        return None

    # Try numeric first
    m = _PAIN_NUMERIC_RE.search(text)
    if m:
        val = int(m.group(1))
        if 0 <= val <= 10:
            return val
        return min(val, 10)

    # Try qualitative
    m = _PAIN_QUAL_RE.search(text)
    if m:
        return _PAIN_QUALITATIVE[m.group(0).lower()]

    return None


# ─── Mobility status patterns ─────────────────────────────────────
_MOBILITY_KEYWORDS: dict[str, str] = {
    # BED_BOUND
    "bed-bound": "BED_BOUND",
    "bed bound": "BED_BOUND",
    "bettlägerig": "BED_BOUND",
    "immobile": "BED_BOUND",
    "immobil": "BED_BOUND",
    "unable to mobilise": "BED_BOUND",
    "unable to mobilize": "BED_BOUND",
    # WHEELCHAIR
    "wheelchair": "WHEELCHAIR",
    "rollstuhl": "WHEELCHAIR",
    # ASSISTED
    "assisted": "ASSISTED",
    "with assistance": "ASSISTED",
    "mit hilfe": "ASSISTED",
    "walker": "ASSISTED",
    "rollator": "ASSISTED",
    "mobilised with": "ASSISTED",
    "mobilized with": "ASSISTED",
    # INDEPENDENT
    "independent": "INDEPENDENT",
    "selbständig": "INDEPENDENT",
    "selbstständig": "INDEPENDENT",
    "ambulating": "INDEPENDENT",
    "ambulant": "INDEPENDENT",
    "mobilised": "INDEPENDENT",
    "mobilized": "INDEPENDENT",
    "mobilized to corridor": "INDEPENDENT",
    "mobilized to chair": "INDEPENDENT",
}

# Sort by length descending so longer matches take priority
_MOBILITY_SORTED = sorted(_MOBILITY_KEYWORDS.items(), key=lambda x: -len(x[0]))

_MOBILITY_RE = re.compile(
    "|".join(re.escape(k) for k, _ in _MOBILITY_SORTED),
    re.IGNORECASE,
)


def extract_mobility_status(text: str) -> Optional[str]:
    """Extract mobility status from nursing note text.

    Returns one of: INDEPENDENT, ASSISTED, WHEELCHAIR, BED_BOUND, or None.
    """
    if not text or not isinstance(text, str):
        return None

    m = _MOBILITY_RE.search(text)
    if m:
        return _MOBILITY_KEYWORDS[m.group(0).lower()]

    return None


# ─── Wound grade patterns ─────────────────────────────────────────
_WOUND_GRADE_RE = re.compile(
    r"(?:wound\s+grade|grade)\s*(\d)",
    re.IGNORECASE,
)

_WOUND_STAGE_RE = re.compile(
    r"(?:stage|stufe)\s*(\d)\s*(?:pressure|dekubitus)?",
    re.IGNORECASE,
)

_WOUND_HEALING_KEYWORDS = [
    "healing well",
    "wound without irritation",
    "wunde reizlos",
    "healing nicely",
    "granulating",
    "granulierend",
    "good healing",
    "gute heilung",
]

_WOUND_HEALING_RE = re.compile(
    "|".join(re.escape(k) for k in _WOUND_HEALING_KEYWORDS),
    re.IGNORECASE,
)


def extract_wound_grade(text: str) -> Optional[str]:
    """Extract wound grade from nursing note text.

    Returns "1"-"4" or "HEALING", or None.
    """
    if not text or not isinstance(text, str):
        return None

    # Try "wound grade X"
    m = _WOUND_GRADE_RE.search(text)
    if m:
        grade = int(m.group(1))
        if 1 <= grade <= 4:
            return str(grade)

    # Try "stage X pressure"
    m = _WOUND_STAGE_RE.search(text)
    if m:
        grade = int(m.group(1))
        if 1 <= grade <= 4:
            return str(grade)

    # Try healing keywords
    if _WOUND_HEALING_RE.search(text):
        return "HEALING"

    return None


# ─── Deterioration signs ──────────────────────────────────────────
_DETERIORATION_SIGNS: dict[str, str] = {
    # English signs
    "confused": "confused",
    "confusion": "confused",
    "disoriented": "disoriented",
    "deteriorating": "deteriorating",
    "deteriorated": "deteriorating",
    "agitated": "agitated",
    "refused medication": "refused_medication",
    "refused food": "refused_food",
    "refused": "refused",
    "unresponsive": "unresponsive",
    "lethargic": "lethargic",
    "dyspnea": "dyspnea",
    "dyspnea on exertion": "dyspnea",
    "tachycardic": "tachycardic",
    "hypotensive": "hypotensive",
    "elevated temperature": "fever",
    "fever": "fever",
    "desaturation": "desaturation",
    "reduced appetite": "reduced_appetite",
    # German signs
    "verschlechtert": "deteriorating",
    "verwirrt": "confused",
    "desorientiert": "disoriented",
    "aggressiv": "agitated",
    "unruhig": "agitated",
    "reduzierter az": "deteriorating",
    "fieber": "fever",
    "atemnot": "dyspnea",
    "appetitlos": "reduced_appetite",
    "übelkeit": "nausea",
    "nausea": "nausea",
    "schwindel": "dizziness",
    "dizziness": "dizziness",
}

_DETERIORATION_SORTED = sorted(_DETERIORATION_SIGNS.items(), key=lambda x: -len(x[0]))

_DETERIORATION_RE = re.compile(
    "|".join(re.escape(k) for k, _ in _DETERIORATION_SORTED),
    re.IGNORECASE,
)


def extract_deterioration_signs(text: str) -> tuple[bool, list[str]]:
    """Extract deterioration signs from nursing note text.

    Returns (flag, list_of_unique_signs).
    """
    if not text or not isinstance(text, str):
        return False, []

    found = set()
    for m in _DETERIORATION_RE.finditer(text):
        sign = _DETERIORATION_SIGNS[m.group(0).lower()]
        found.add(sign)

    signs = sorted(found)
    return bool(signs), signs


# ─── Shift normalization ──────────────────────────────────────────
_SHIFT_MAP: dict[str, str] = {
    "early shift": "Early",
    "frühschicht": "Early",
    "late shift": "Late",
    "spätschicht": "Late",
    "night shift": "Night",
    "nachtschicht": "Night",
}


def normalize_shift(raw_shift: str) -> str:
    """Normalize shift string to Early/Late/Night."""
    if not raw_shift or not isinstance(raw_shift, str):
        return "Early"

    cleaned = raw_shift.strip().lower()
    # Remove garbage characters (e.g. "Nachtschichtö", "Night shiftä")
    cleaned = re.sub(r"[^a-zäöüß\s]", "", cleaned).strip()

    for pattern, normalized in _SHIFT_MAP.items():
        if pattern in cleaned:
            return normalized

    # Fallback: try partial match
    if "early" in cleaned or "früh" in cleaned:
        return "Early"
    if "late" in cleaned or "spät" in cleaned:
        return "Late"
    if "night" in cleaned or "nacht" in cleaned:
        return "Night"

    return "Early"


# ─── Main analysis function ───────────────────────────────────────

def analyze_note(text: str) -> dict:
    """Run all NLP extractors on a single nursing note.

    Returns dict with keys: pain_level, mobility_status, wound_grade,
    deterioration_flag, deterioration_signs.
    """
    pain = extract_pain_level(text)
    mobility = extract_mobility_status(text)
    wound = extract_wound_grade(text)
    det_flag, det_signs = extract_deterioration_signs(text)

    return {
        "pain_level": pain,
        "mobility_status": mobility,
        "wound_grade": wound,
        "deterioration_flag": det_flag,
        "deterioration_signs": det_signs,
    }


# ─── NursingNLPAnalyzer class ─────────────────────────────────────

class NursingNLPAnalyzer:
    """Batch NLP analyzer for nursing daily reports.

    Uses regex-based extraction (spaCy loaded optionally for future
    entity-based enhancements). Processes DataFrames with nursing notes
    and returns NursingNLPResult objects.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp = None
        self._load_spacy(model_name)

    def _load_spacy(self, model_name: str) -> None:
        """Try to load spaCy model. Non-fatal if unavailable."""
        try:
            import spacy
            self._nlp = spacy.load(model_name)
            logger.info("spaCy model '%s' loaded", model_name)
        except (ImportError, OSError) as e:
            logger.warning("spaCy model '%s' not available: %s. Using regex-only mode.", model_name, e)
            self._nlp = None

    def analyze_dataframe(self, df: pd.DataFrame) -> list[dict]:
        """Analyze all nursing notes in a DataFrame.

        Expects columns: CaseID (or coCaseId), Shift (or coShift),
        ReportDate (or coReport_date), NursingNote (or coNursing_note_free_text).

        Returns list of NursingNLPResult-compatible dicts.
        """
        if df is None or df.empty:
            return []

        # Detect column names (dirty vs mapped)
        col_map = self._detect_columns(df)
        if not col_map:
            logger.warning("Cannot detect nursing columns in DataFrame with cols: %s", list(df.columns))
            return []

        results = []
        for _, row in df.iterrows():
            case_id = str(row.get(col_map["case_id"], "") or "")
            shift_raw = str(row.get(col_map["shift"], "") or "")
            report_date = str(row.get(col_map["report_date"], "") or "")
            note = str(row.get(col_map["note"], "") or "")

            if not note or note.lower() in ("nan", "none", ""):
                continue

            nlp_result = analyze_note(note)
            nlp_result["case_id"] = case_id
            nlp_result["shift"] = normalize_shift(shift_raw)
            nlp_result["report_date"] = report_date
            results.append(nlp_result)

        logger.info("NLP analyzed %d nursing notes, %d had findings",
                     len(results),
                     sum(1 for r in results if r["pain_level"] is not None
                         or r["mobility_status"] is not None
                         or r["wound_grade"] is not None
                         or r["deterioration_flag"]))
        return results

    @staticmethod
    def _detect_columns(df: pd.DataFrame) -> Optional[dict[str, str]]:
        """Detect column names for nursing data across naming conventions."""
        cols = {c.lower(): c for c in df.columns}

        # Case ID
        case_id_col = None
        for candidate in ["caseid", "case_id", "cocaseid"]:
            if candidate in cols:
                case_id_col = cols[candidate]
                break
        if not case_id_col:
            return None

        # Shift
        shift_col = None
        for candidate in ["shift", "coshift"]:
            if candidate in cols:
                shift_col = cols[candidate]
                break

        # Report date
        date_col = None
        for candidate in ["reportdate", "report_date", "coreport_date"]:
            if candidate in cols:
                date_col = cols[candidate]
                break

        # Note text
        note_col = None
        for candidate in ["nursingnote", "nursing_note", "conursing_note_free_text", "note", "notes"]:
            if candidate in cols:
                note_col = cols[candidate]
                break
        if not note_col:
            return None

        return {
            "case_id": case_id_col,
            "shift": shift_col or case_id_col,  # fallback: won't crash
            "report_date": date_col or case_id_col,
            "note": note_col,
        }

    def analyze_all(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, list[dict]]:
        """Analyze all nursing DataFrames from the pipeline.

        Args:
            dataframes: {filename: DataFrame} from ingestion.

        Returns:
            {case_id: [NursingNLPResult-dict, ...]} grouped by patient.
        """
        all_results: list[dict] = []
        for fname, df in dataframes.items():
            if not self._is_nursing_data(fname, df):
                continue
            results = self.analyze_dataframe(df)
            all_results.extend(results)
            logger.info("NLP: processed %s → %d results", fname, len(results))

        # Group by case_id
        grouped: dict[str, list[dict]] = {}
        for r in all_results:
            cid = r["case_id"]
            grouped.setdefault(cid, []).append(r)

        logger.info("NLP: %d total results for %d patients", len(all_results), len(grouped))
        return grouped

    @staticmethod
    def _is_nursing_data(filename: str, df: pd.DataFrame) -> bool:
        """Check if a DataFrame contains nursing data."""
        fname_lower = filename.lower()
        if "nursing" in fname_lower:
            return True
        # Check columns
        cols_lower = {c.lower() for c in df.columns}
        return "nursingnote" in cols_lower or "conursing_note_free_text" in cols_lower

    def get_summary_stats(self, grouped_results: dict[str, list[dict]]) -> dict:
        """Get summary statistics from NLP results."""
        total_notes = sum(len(v) for v in grouped_results.values())
        pain_found = sum(
            1 for notes in grouped_results.values()
            for n in notes if n["pain_level"] is not None
        )
        mobility_found = sum(
            1 for notes in grouped_results.values()
            for n in notes if n["mobility_status"] is not None
        )
        wound_found = sum(
            1 for notes in grouped_results.values()
            for n in notes if n["wound_grade"] is not None
        )
        deterioration_found = sum(
            1 for notes in grouped_results.values()
            for n in notes if n["deterioration_flag"]
        )

        return {
            "total_notes_analyzed": total_notes,
            "total_patients": len(grouped_results),
            "pain_extracted": pain_found,
            "mobility_extracted": mobility_found,
            "wound_extracted": wound_found,
            "deterioration_flagged": deterioration_found,
            "extraction_rate": round(
                (pain_found + mobility_found + wound_found + deterioration_found)
                / max(total_notes * 4, 1) * 100, 1
            ),
        }
