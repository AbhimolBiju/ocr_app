# services/validator/tax_invoice_qic_validator.py


def _field_value(data, key):

    v = data.get(key)

    if isinstance(v, dict) and "value" in v:
        return v["value"]

    return v


class QICTaxInvoiceValidator:

    def __init__(self, data):
        self.data = data

    def validate(self):
        errors = []

        if not _field_value(self.data, "policy_number"):
            errors.append("Policy number missing")

        if not _field_value(self.data, "invoice_date"):
            errors.append("Invoice date missing")

        if not _field_value(self.data, "total"):
            errors.append("Total missing")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }