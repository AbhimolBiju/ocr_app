import re
from ..confidence import ConfidenceEngine


class NIATaxInvoiceLegacyParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")
        self.lines = self.text.split("\n")

        self.normalized_text = re.sub(
            r"\s+",
            " ",
            self.text
        )

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        data = {}

        data["insurer_name"] = ConfidenceEngine.wrap_field(
            "NIA Insurance",
            "high",
            "insurer",
        )

        tax_invoice_number = self._extract_tax_invoice_number()
        data["tax_invoice_number"] = self._field(
            tax_invoice_number,
            "high" if tax_invoice_number else "missing",
        )

        invoice_date = self._extract_invoice_date()
        data["invoice_date"] = self._field(
            invoice_date,
            "high" if invoice_date else "missing",
        )

        customer_name = self._extract_customer_name()
        data["customer_name"] = self._field(
            customer_name,
            "high" if customer_name else "missing",
        )

        policy_number = self._extract_policy_number()
        data["policy_number"] = self._field(
            policy_number,
            "high" if policy_number else "missing",
        )

        policy_type = self._extract_policy_type()
        data["policy_type"] = self._field(
            policy_type,
            "medium" if policy_type else "missing",
        )

        start_date, end_date = self._extract_policy_period()

        data["policy_start_date"] = self._field(
            start_date,
            "high" if start_date else "missing",
        )

        data["policy_end_date"] = self._field(
            end_date,
            "high" if end_date else "missing",
        )

        broker_name = self._extract_broker()
        data["broker_name"] = self._field(
            broker_name,
            "high" if broker_name else "missing",
        )

        promise = bool(
            broker_name
            and "PROMISE" in broker_name.upper()
        )
        data["is_promise_broker"] = ConfidenceEngine.wrap_field(
            promise,
            "high" if broker_name else "low",
            "promise",
        )

        branch = self._extract_branch()
        data["branch"] = self._field(
            branch,
            "high" if branch else "missing",
        )

        data["premium_currency"] = ConfidenceEngine.wrap_field(
            "AED",
            "high",
            "currency",
        )

        amounts = self._extract_amounts()

        net_amt = amounts.get("net_premium")
        vat_amt = amounts.get("vat_amount")
        tot_amt = amounts.get("total")

        data["net_premium"] = self._field(
            net_amt,
            "high" if net_amt is not None else "missing",
        )
        data["vat_amount"] = self._field(
            vat_amt,
            "high" if vat_amt is not None else "missing",
        )
        data["total_premium"] = self._field(
            tot_amt,
            "high" if tot_amt is not None else "missing",
        )
        data["net_due"] = self._field(
            tot_amt,
            "high" if tot_amt is not None else "missing",
        )
        data["total"] = self._field(
            tot_amt,
            "high" if tot_amt is not None else "missing",
        )

        data["invoice_date_calc"] = self._field(
            invoice_date,
            "high" if invoice_date else "missing",
        )
        data["due_date"] = self._field(
            invoice_date,
            "medium" if invoice_date else "missing",
        )

        data["premium_amount"] = self._field(
            net_amt,
            "high" if net_amt is not None else "missing",
        )

        return data

    # ---------------------------------------------------
    # FIELD WRAPPER
    # ---------------------------------------------------
    def _field(self, value, confidence=None):

        if isinstance(confidence, str):
            return ConfidenceEngine.wrap_field(
                value,
                confidence,
                "nia_legacy",
            )
        if confidence is None:
            return ConfidenceEngine.wrap_field(
                value,
                "high" if value not in (None, "", [], {}) else "missing",
                "nia_legacy",
            )
        if confidence >= 90:
            rel = "high"
        elif confidence >= 50:
            rel = "medium"
        else:
            rel = "low"
        return ConfidenceEngine.wrap_field(value, rel, "nia_legacy")

    # ---------------------------------------------------
    # TAX INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_tax_invoice_number(self):

        match = re.search(
            r"Tax\s*Invoice\s*No\.?\s*:?\s*([A-Z0-9]+)",
            self.normalized_text,
            re.IGNORECASE
        )

        return match.group(1).strip() if match else None

    # ---------------------------------------------------
    # CUSTOMER NAME
    # ---------------------------------------------------
    def _extract_customer_name(self):

        match = re.search(
            r":\s*([A-Z0-9\s\.\-&]+L\.L\.C)",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()
            value = re.sub(r"\s+", " ", value)

            if "PROMISE" not in value.upper():
                return value

        return None

    # ---------------------------------------------------
    # POLICY NUMBER (FIXED - OCR SAFE)
    # ---------------------------------------------------
    def _extract_policy_number(self):

        match = re.search(
            r"Policy\s*No\.?\s*:?\s*([A-Z0-9\/\-]+)",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        for i, line in enumerate(self.lines):

            if "POLICY NO" in line.upper():

                for j in range(i, min(i + 4, len(self.lines))):

                    nxt = self.lines[j].strip()

                    if ":" in nxt:
                        nxt = nxt.split(":")[-1].strip()

                    match = re.search(r"([0-9]{3,}\/[A-Z0-9\/\-]+)", nxt)

                    if match:
                        return match.group(1).strip()

        return None

    # ---------------------------------------------------
    # POLICY TYPE (FIXED - FINAL STABLE VERSION)
    # ---------------------------------------------------
    def _extract_policy_type(self):

        found = False

        for i, line in enumerate(self.lines):

            clean = line.strip().upper()

            # detect label
            if "POLICY TYPE" in clean:
                found = True
                continue

            if not found:
                continue

            # skip noise
            if not clean:
                continue

            if "نوع" in clean:
                continue

            if "POLICY PERIOD" in clean:
                break

            clean = clean.lstrip(":").strip()

            clean = re.sub(r"\s+", " ", clean)

            if "MOTOR" in clean.upper():
                return clean.strip()

        # fallback
        match = re.search(
            r"Policy\s*Type\s*:?\s*([A-Z\s\-\/]+)",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()
            if "MOTOR" in value.upper():
                return value

        return None

    # ---------------------------------------------------
    # CLEANER
    # ---------------------------------------------------
    def _clean_policy_type(self, value):

        if not value:
            return None

        value = value.strip()

        value = re.sub(r"[^\w\s\-\/]", "", value)
        value = re.sub(r"\s+", " ", value).strip()

        if len(value) < 3:
            return None

        return value

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        match = re.search(
            r"Policy\s*Period\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{2})",
            self.normalized_text,
            re.IGNORECASE
        )

        return match.group(1) if match else None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        match = re.search(
            r"Policy\s*Period\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{2})\s*to\s*(\d{1,2}-[A-Za-z]{3}-\d{2})",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1), match.group(2)

        return None, None

    # ---------------------------------------------------
    # BROKER
    # ---------------------------------------------------
    def _extract_broker(self):

        if "PROMISE INSURANCE SERVICES" in self.normalized_text.upper():
            return "PROMISE INSURANCE SERVICES LLC"

        return None

    # ---------------------------------------------------
    # BRANCH
    # ---------------------------------------------------
    def _extract_branch(self):

        upper = self.normalized_text.upper()

        if "ABU DHABI" in upper:
            return "ABU DHABI"

        if "DUBAI" in upper:
            return "DUBAI"

        if "SHARJAH" in upper:
            return "SHARJAH"

        if "RAK" in upper:
            return "RAK"

        return None

    # ---------------------------------------------------
    # AMOUNTS
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {
            "net_premium": None,
            "vat_amount": None,
            "total": None
        }

        match = re.search(
            r"Taxable\s*Amount\(AED\).*?([\d,]+\.\d+)",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            result["net_premium"] = float(match.group(1).replace(",", ""))

        match = re.search(
            r"VAT\s*Amount\(AED\).*?([\d,]+\.\d+)",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            result["vat_amount"] = float(match.group(1).replace(",", ""))

        match = re.search(
            r"Total\(AED\).*?([\d,]+\.\d+)",
            self.normalized_text,
            re.IGNORECASE
        )

        if match:
            result["total"] = float(match.group(1).replace(",", ""))

        return result


class NIATaxInvoiceParser:

    def __init__(self, layout_data):

        self._layout_data = layout_data

    def parse(self):

        from .nia_router import NIATaxInvoiceRouter

        return NIATaxInvoiceRouter(self._layout_data).parse()