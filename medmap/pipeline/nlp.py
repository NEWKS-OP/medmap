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
