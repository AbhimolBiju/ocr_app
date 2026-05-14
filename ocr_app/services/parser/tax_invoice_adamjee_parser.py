import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date
)
from ..structured_schema import finalize_tax_invoice_output


class AdamjeeTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")
        self.tables = layout_data.get("tables", [])

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------------------------------
        # INSURER NAME
        # ---------------------------------------------------
        data["insurer_name"] = ConfidenceEngine.wrap_field(
            "Adamjee",
            "high",
            "insurer",
        )

        # ---------------------------------------------------
        # CUSTOMER NAME
        # ---------------------------------------------------
        customer_name = self._extract(
            r"NAME\s*OF\s*INSURED\s*:?\s*([^\n\r]+)"
        )

        if customer_name:
            customer_name = customer_name.replace(":", "").strip()

        data["customer_name"] = self._field(customer_name)

        # ---------------------------------------------------
        # BROKER NAME
        # ---------------------------------------------------
        broker_name = self._extract_broker_name()

        data["broker_name"] = self._field(broker_name)

        # ---------------------------------------------------
        # PROMISE CHECK
        # ---------------------------------------------------
        data["is_promise_broker"] = ConfidenceEngine.wrap_field(
            bool(
                broker_name
                and "promise insurance" in broker_name.lower()
            ),
            "high" if broker_name else "low",
            "promise",
        )

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        invoice_date = self._extract_invoice_date()

        data["invoice_date"] = self._field(invoice_date)

        # ---------------------------------------------------
        # BRANCH
        # ---------------------------------------------------
        branch = self._extract(
            r"BRANCH\s*:?\s*([^\n\r]+)"
        )

        if branch:
            branch = branch.replace(":", "").strip()

        data["branch"] = self._field(branch)

        # ---------------------------------------------------
        # POLICY TYPE
        # ---------------------------------------------------
        policy_type = self._extract(
            r"POLICY\s*TYPE\s*:?\s*([^\n\r]+)"
        )

        if policy_type:
            policy_type = policy_type.replace(":", "").strip()

        data["policy_type"] = self._field(policy_type)

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        policy_number = self._extract(
            r"POLICY\s*NO\s*:?\s*([A-Z0-9\-\/]+)"
        )

        data["policy_number"] = self._field(policy_number)

        # ---------------------------------------------------
        # TAX INVOICE NUMBER
        # ---------------------------------------------------
        tax_invoice = self._extract_invoice_number()

        data["tax_invoice_number"] = self._field(tax_invoice)

        # ---------------------------------------------------
        # POLICY PERIOD
        # ---------------------------------------------------
        start_date, end_date = extract_policy_date_range(
            self.text
        )

        if start_date is None or end_date is None:

            period_match = re.search(
                r"PERIOD\s*OF\s*INSURANCE\s*:?\s*FROM\s*"
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}\s+\d{2}:\d{2})"
                r".*?"
                r"TO\s*"
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}\s+\d{2}:\d{2})",
                self.text,
                re.IGNORECASE | re.DOTALL
            )

            if period_match:

                start_date = normalize_date(
                    period_match.group(1).strip()
                )

                end_date = normalize_date(
                    period_match.group(2).strip()
                )

        data["policy_start_date"] = self._field(start_date)

        data["policy_end_date"] = self._field(end_date)

        # ---------------------------------------------------
        # PREMIUM CURRENCY
        # ---------------------------------------------------
        data["premium_currency"] = ConfidenceEngine.wrap_field(
            "AED",
            "high",
            "currency",
        )

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        data["premium_amount"] = self._field(
            amounts.get("premium_amount"),
            "high" if amounts.get("premium_amount") is not None else "missing",
        )

        data["net_premium"] = self._field(
            amounts.get("net_premium"),
            "high" if amounts.get("net_premium") is not None else "missing",
        )

        data["total_premium"] = self._field(
            amounts.get("total_premium"),
            "high" if amounts.get("total_premium") is not None else "missing",
        )

        data["vat_amount"] = self._field(
            amounts.get("vat_amount"),
            "high" if amounts.get("vat_amount") is not None else "missing",
        )

        data["net_due"] = self._field(
            amounts.get("net_due"),
            "high" if amounts.get("net_due") is not None else "missing",
        )

        data["total"] = self._field(
            amounts.get("total"),
            "high" if amounts.get("total") is not None else "missing",
        )

        # ---------------------------------------------------
        # CALCULATED FIELDS
        # ---------------------------------------------------
        data["invoice_date_calc"] = data["invoice_date"]

        data["due_date"] = data["invoice_date"]

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # FIELD WRAPPER
    # ---------------------------------------------------
    def _field(self, value, reliability=None):

        if reliability:

            return ConfidenceEngine.wrap_field(
                value,
                reliability,
                "adamjee",
            )

        if value not in (None, "", [], {}):

            return ConfidenceEngine.wrap_field(
                value,
                "high",
                "adamjee",
            )

        return ConfidenceEngine.wrap_field(
            value,
            "missing",
            "adamjee",
        )

    # ---------------------------------------------------
    # BROKER NAME
    # ---------------------------------------------------
    def _extract_broker_name(self):

        inline = re.search(
            r"(?:Broker|Brokerage|Intermediary)\s*(?:Name)?\s*:?\s*([^\n\r]+)",
            self.text,
            re.IGNORECASE,
        )

        if inline:

            val = inline.group(1).strip(" :,-")

            if val and len(val) > 2:
                return val

        lines = [
            x.strip()
            for x in self.text.splitlines()
        ]

        for i, line in enumerate(lines):

            if line.strip().lower() in ["to", "to,"]:

                for j in range(i + 1, min(i + 5, len(lines))):

                    candidate = lines[j].strip()

                    if (
                        "account no" in candidate.lower()
                        or "document no" in candidate.lower()
                        or "date" in candidate.lower()
                    ):
                        break

                    if (
                        "insurance" in candidate.lower()
                        or "broker" in candidate.lower()
                        or "services" in candidate.lower()
                    ):

                        candidate = re.sub(
                            r"P\.?O\.?\s*BOX.*",
                            "",
                            candidate,
                            flags=re.IGNORECASE
                        )

                        candidate = candidate.strip(" ,:-")

                        if len(candidate) > 3:
                            return candidate

        return None

    # ---------------------------------------------------
    # TAX INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_invoice_number(self):

        text = self.text

        patterns = [

            r"DOCUMENT\s*NO\s*[:\-]?\s*([0-9]{5,})",

            r"TAX\s*INVOICE\s*NO\.?\s*[:\-]?\s*([0-9]{5,})",

            r"INVOICE\s*(?:NO|NUMBER)\.?\s*[:\-]?\s*([0-9]{5,})",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                invalid_values = [

                    "VAT",
                    "REGISTRATION",
                    "NO",
                    "DATE",
                    "POLICY",

                ]

                if value.upper() in invalid_values:
                    continue

                return value

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        compact = re.sub(
            r"\s+",
            " ",
            self.text
        )

        patterns = [

            r"DATE\s*OF\s*ISSUE\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",

            r"DOCUMENT\s*DATE\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",

            r"INVOICE\s*DATE\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",

            r"\bDATE\b\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                compact,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                return normalize_date(value)

        lines = [
            x.strip()
            for x in self.text.splitlines()
            if x.strip()
        ]

        for line in lines[:25]:

            if "policy no" in line.lower():
                continue

            if "reference no" in line.lower():
                continue

            if "endorsement" in line.lower():
                continue

            m = re.search(
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                line
            )

            if m:
                return normalize_date(
                    m.group(1)
                )

        return None

    # ---------------------------------------------------
    # AMOUNTS
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {
            "premium_amount": None,
            "net_premium": None,
            "total_premium": None,
            "vat_amount": None,
            "net_due": None,
            "total": None,
        }

        text = self.text

        # ---------------------------------------------------
        # NET PREMIUM
        # ---------------------------------------------------
        patterns_net = [

            r"Premium\s*Excluding\s*VAT\s*Amount\s*:?\s*([\d,]+\.\d{2})",

            r"NET\s*PREMIUM\s*:?\s*([\d,]+\.\d{2})",

            r"([\d,]+\.\d{2})\s*(?:\n|\r|\s)*VAT@\s*5%",

        ]

        for pattern in patterns_net:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                result["net_premium"] = float(
                    match.group(1).replace(",", "")
                )

                break

        # ---------------------------------------------------
        # VAT AMOUNT
        # ---------------------------------------------------
        vat_patterns = [

            r"VAT@\s*5%\s*:?\s*([\d,]+\.\d{2})",

            r"VAT\s*Amount\s*:?\s*([\d,]+\.\d{2})",

        ]

        for pattern in vat_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                result["vat_amount"] = float(
                    match.group(1).replace(",", "")
                )

                break

        # ---------------------------------------------------
        # TOTAL AMOUNT
        # ---------------------------------------------------
        total_patterns = [

            r"Premium\s*Including\s*VAT\s*Amount\s*:?\s*([\d,]+\.\d{2})",

            r"TOTAL\s*PREMIUM\s*:?\s*AED\s*([\d,]+\.\d{2})",

            r"Net\s*Premium\s*:?\s*Premium\s*Including\s*VAT\s*Amount\s*:?\s*([\d,]+\.\d{2})",

            r"Total\s*:?\s*([\d,]+\.\d{2})",

            r"Grand\s*Total\s*:?\s*([\d,]+\.\d{2})",

        ]

        for pattern in total_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                val = float(
                    match.group(1).replace(",", "")
                )

                result["premium_amount"] = val
                result["total_premium"] = val
                result["net_due"] = val
                result["total"] = val

                break

        # ---------------------------------------------------
        # CALCULATE TOTAL IF MISSING
        # ---------------------------------------------------
        if (
            result["total"] is None
            and result["net_premium"] is not None
            and result["vat_amount"] is not None
        ):

            total = round(
                result["net_premium"] + result["vat_amount"],
                2
            )

            result["premium_amount"] = total
            result["total_premium"] = total
            result["net_due"] = total
            result["total"] = total

        # ---------------------------------------------------
        # CALCULATE NET PREMIUM IF MISSING
        # ---------------------------------------------------
        if (
            result["net_premium"] is None
            and result["total"] is not None
            and result["vat_amount"] is not None
        ):

            result["net_premium"] = round(
                result["total"] - result["vat_amount"],
                2
            )

        return result

    # ---------------------------------------------------
    # GENERIC EXTRACT
    # ---------------------------------------------------
    def _extract(self, pattern):

        match = re.search(
            pattern,
            self.text,
            re.IGNORECASE | re.MULTILINE
        )

        if match:
            return match.group(1).strip()

        return None