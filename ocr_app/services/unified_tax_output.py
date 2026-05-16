"""
Unified flat JSON for all tax-invoice parsers.
"""

from .parsing_text_utils import normalize_date


UNIFIED_VALUE_KEYS = [

    "insurer_name",
    "tax_invoice_number",
    "invoice_date",
    "customer_name",
    "broker_name",
    "is_promise_broker",
    "policy_number",
    "policy_type",
    "policy_start_date",
    "policy_end_date",
    "premium_currency",
    "net_premium",
    "vat_amount",
    "total",
    "total_premium",
    "net_due",

]


DATE_KEYS = frozenset({

    "invoice_date",
    "policy_start_date",
    "policy_end_date",

})


FLOAT_KEYS = frozenset({

    "net_premium",
    "vat_amount",
    "total",
    "total_premium",
    "net_due",

})


# ---------------------------------------------------
# UNWRAP FIELD
# ---------------------------------------------------
def _unwrap_field(raw, key):

    # ---------------------------------------------------
    # WRAPPED FIELD
    # ---------------------------------------------------
    if isinstance(raw, dict):

        val = raw.get("value")

        try:

            conf = int(
                float(
                    raw.get("confidence", 0)
                )
            )

        except:

            conf = 0

        return (
            val,
            max(0, min(100, conf))
        )

    # ---------------------------------------------------
    # EMPTY VALUE
    # ---------------------------------------------------
    if raw in (None, "", [], {}):

        return None, 10

    # ---------------------------------------------------
    # DIRECT VALUE
    # ---------------------------------------------------
    return raw, 85


# ---------------------------------------------------
# FLOAT NORMALIZATION
# ---------------------------------------------------
def _to_float(val):

    if val is None:
        return None

    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)

    try:

        return float(
            str(val)
            .replace(",", "")
            .strip()
        )

    except:

        return None


# ---------------------------------------------------
# MISSING CHECK
# ---------------------------------------------------
def _value_missing(val, key):

    if key == "is_promise_broker":
        return val is None

    if val is None:
        return True

    if isinstance(val, str) and not val.strip():
        return True

    return False


# ---------------------------------------------------
# MAIN UNIFIER
# ---------------------------------------------------
def unify_parsed_tax_invoice(mixed):

    if not isinstance(mixed, dict):
        mixed = {}

    src = dict(mixed)

    pre_fc = src.get(
        "field_confidence",
        {}
    ) or {}

    values = {}
    fc = {}

    for k in UNIFIED_VALUE_KEYS:

        raw = src.get(k)

        val, conf = _unwrap_field(
            raw,
            k
        )

        # ---------------------------------------------------
        # PRESERVE EXISTING CONFIDENCE
        # ---------------------------------------------------
        if k in pre_fc:

            try:

                conf = int(
                    round(
                        float(pre_fc[k])
                    )
                )

            except:
                pass

        # ---------------------------------------------------
        # DATE NORMALIZATION
        # ---------------------------------------------------
        if k in DATE_KEYS:

            val = normalize_date(val)

        # ---------------------------------------------------
        # FLOAT NORMALIZATION
        # ---------------------------------------------------
        elif k in FLOAT_KEYS:

            val = _to_float(val)

        # ---------------------------------------------------
        # BOOLEAN NORMALIZATION
        # ---------------------------------------------------
        elif k == "is_promise_broker":

            # explicit parser value
            if val is not None:

                val = bool(val)

            else:

                broker = values.get("broker_name")

                if isinstance(broker, str):

                    broker_l = broker.lower()

                    val = (
                        "promise insurance" in broker_l
                        or "promiseinsure" in broker_l
                    )

                else:

                    val = False

        # ---------------------------------------------------
        # STRING CLEANUP
        # ---------------------------------------------------
        elif isinstance(val, str):

            val = val.strip() or None

        values[k] = val

        fc[k] = max(
            0,
            min(100, conf)
        )

    # ---------------------------------------------------
    # MISSING FIELDS
    # ---------------------------------------------------
    missing = [

        k for k in UNIFIED_VALUE_KEYS

        if _value_missing(
            values[k],
            k
        )

    ]

    extracted = (
        len(UNIFIED_VALUE_KEYS)
        - len(missing)
    )

    # ---------------------------------------------------
    # OVERALL CONFIDENCE
    # ---------------------------------------------------
    valid_scores = [

        v for v in fc.values()
        if v > 15

    ]

    overall = round(

        sum(valid_scores) / len(valid_scores),

        2

    ) if valid_scores else 0.0

    # ---------------------------------------------------
    # FINAL OUTPUT
    # ---------------------------------------------------
    out = {}

    for k in UNIFIED_VALUE_KEYS:
        out[k] = values[k]

    out["confidence_score"] = overall

    out["field_confidence"] = fc

    out["missing_fields"] = missing

    out["extracted_fields_count"] = extracted

    return out