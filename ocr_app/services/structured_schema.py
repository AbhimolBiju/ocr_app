# Canonical tax-invoice field names

CANONICAL_TAX_INVOICE_FIELDS = [
    "insurer_name",
    "customer_name",
    "broker_name",
    "is_promise_broker",
    "invoice_date",
    "branch",
    "policy_type",
    "policy_number",
    "tax_invoice_number",
    "policy_start_date",
    "policy_end_date",
    "premium_currency",
    "net_premium",
    "total_premium",
    "vat_amount",
    "total",
    "net_due",
    "invoice_date_calc",
    "due_date",
]


def is_wrapped_field(obj):
    return isinstance(obj, dict) and "value" in obj


def _safe_wrap(value, key):

    from .confidence import ConfidenceEngine

    if value in (None, "", [], {}):
        return ConfidenceEngine.wrap_field(None, "missing", key)

    return ConfidenceEngine.wrap_field(value, "high", key)


def finalize_tax_invoice_output(data):

    from .unified_tax_output import unify_parsed_tax_invoice

    if not isinstance(data, dict):
        data = {}

    work = dict(data)

    for key in CANONICAL_TAX_INVOICE_FIELDS:

        raw = work.get(key)

        # already properly wrapped
        if isinstance(raw, dict) and "value" in raw:
            continue

        work[key] = _safe_wrap(raw, key)

    return unify_parsed_tax_invoice(work)