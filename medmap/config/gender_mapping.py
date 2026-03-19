GENDER_MAP = {
    "M": "M",
    "male": "M",
    "männlich": "M",
    "mä": "M",
    "m": "M",
    "F": "F",
    "female": "F",
    "weiblich": "F",
    "f": "F",
    "N/A": None,
    "n/a": None,
    "": None,
    "na": None,
    "unknown": None,
    "keine": None,
}


def normalize_gender(value) -> str:
    if value is None:
        return None
    cleaned = str(value).strip()
    return GENDER_MAP.get(cleaned, GENDER_MAP.get(cleaned.lower()))
