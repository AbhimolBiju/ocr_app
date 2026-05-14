import re


class ConfidenceEngine:
    """
    Per-field confidence for structured extraction.

    Reliability tiers (mapped to 0–100):
    - high:   confident match (>= 90)
    - medium: partial / heuristic (50–89)
    - low:    weak / guessed (< 50)
    - missing: empty / unknown (<= 15)
    """

    _TIER_HIGH = (90, 97)
    _TIER_MED = (58, 82)
    _TIER_LOW = (18, 44)
    _TIER_MISS = (8, 14)

    @staticmethod
    def _bucket(value, lo, hi, salt):
        if lo >= hi:
            return lo
        span = hi - lo + 1
        idx = abs(hash((salt, repr(value)))) % span
        return lo + idx

    @classmethod
    def wrap_field(cls, value, reliability="medium", salt=""):
        rel = (reliability or "medium").lower()
        if value is False or value is True:
            if rel == "high":
                lo, hi = cls._TIER_HIGH
            elif rel == "low":
                lo, hi = cls._TIER_LOW
            elif rel == "missing":
                lo, hi = cls._TIER_MISS
            else:
                lo, hi = cls._TIER_MED
            return {
                "value": value,
                "confidence": cls._bucket(value, lo, hi, salt or "bool"),
            }
        if value in (None, "", [], {}):
            lo, hi = cls._TIER_MISS
            return {
                "value": None,
                "confidence": cls._bucket(None, lo, hi, salt or "empty"),
            }
        if rel == "high":
            lo, hi = cls._TIER_HIGH
        elif rel == "low":
            lo, hi = cls._TIER_LOW
        elif rel == "missing":
            lo, hi = cls._TIER_MISS
        else:
            lo, hi = cls._TIER_MED
        return {
            "value": value,
            "confidence": cls._bucket(value, lo, hi, salt or "field"),
        }

    @classmethod
    def infer_from_regex(cls, value, match, pattern, salt=""):
        """
        Derive reliability from regex match quality.
        """
        if value in (None, "", [], {}):
            return cls.wrap_field(None, "missing", salt)
        if match is None:
            return cls.wrap_field(value, "low", salt)
        if pattern:
            try:
                if re.fullmatch(pattern, str(value).strip(), re.IGNORECASE):
                    return cls.wrap_field(value, "high", salt)
            except re.error:
                pass
        full = match.group(0) if match.groups() else match.group(0)
        try:
            captured = match.group(1).strip()
        except IndexError:
            captured = str(value).strip()
        if captured == str(value).strip() and len(captured) >= 2:
            return cls.wrap_field(value, "high", salt)
        return cls.wrap_field(value, "medium", salt)

    @classmethod
    def score_numeric(cls, value, from_table=False, salt="amt"):
        if value is None:
            return cls.wrap_field(None, "missing", salt)["confidence"]
        try:
            float(value)
        except (TypeError, ValueError):
            return cls.wrap_field(value, "low", salt)["confidence"]
        rel = "high" if from_table else "medium"
        return cls.wrap_field(value, rel, salt)["confidence"]

    @staticmethod
    def calculate(value, pattern_matched=True, pattern=None):
        """
        Legacy numeric score 0–100 for code paths that expect a scalar.
        """
        if value in (None, "", [], {}):
            return 12
        if pattern is not None:
            try:
                if re.fullmatch(pattern, str(value).strip(), re.IGNORECASE):
                    return ConfidenceEngine.wrap_field(
                        value,
                        "high",
                        "calc",
                    )["confidence"]
            except re.error:
                pass
            if pattern_matched:
                return ConfidenceEngine.wrap_field(
                    value,
                    "medium",
                    "calc",
                )["confidence"]
            return ConfidenceEngine.wrap_field(
                value,
                "low",
                "calc",
            )["confidence"]
        if pattern_matched:
            return ConfidenceEngine.wrap_field(
                value,
                "high",
                "calc",
            )["confidence"]
        return ConfidenceEngine.wrap_field(
            value,
            "medium",
            "calc",
        )["confidence"]
