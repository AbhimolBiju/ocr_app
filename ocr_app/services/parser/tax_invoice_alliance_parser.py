import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date,
)
from ..structured_schema import (
    finalize_tax_invoice_output,
)


class AllianceTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get(
            "full_text",
            ""
        )

        self.lines = [
            ln.strip()
            for ln in self.text.split("\n")
            if ln.strip()
        ]

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        CE = ConfidenceEngine

        def wrap(val, rel="high", salt="alliance"):

            return CE.wrap_field(
                val,
                rel if val else "missing",
                salt,
            )

        data = {}

        # ---------------------------------------------------
        # INSURER
        # ---------------------------------------------------
        data["insurer_name"] = wrap(
            "Alliance Insurance",
            "high",
            "insurer",
        )

        # ---------------------------------------------------
        # TAX INVOICE NUMBER
        # ---------------------------------------------------
        tax_invoice = self._extract_invoice_number()

        data["tax_invoice_number"] = wrap(
            tax_invoice,
            "high" if tax_invoice else "missing",
            "invoice",
        )

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        invoice_date = self._extract_invoice_date()

        data["invoice_date"] = wrap(
            invoice_date,
            "high" if invoice_date else "missing",
            "invdate",
        )

        # ---------------------------------------------------
        # CUSTOMER
        # ---------------------------------------------------
        customer = self._extract_customer_name()

        data["customer_name"] = wrap(
            customer,
            "high" if customer else "missing",
            "customer",
        )

        # ---------------------------------------------------
        # BROKER
        # ---------------------------------------------------
        broker = self._extract_broker_name()

        data["broker_name"] = wrap(
            broker,
            "high" if broker else "missing",
            "broker",
        )

        # ---------------------------------------------------
        # PROMISE CHECK
        # ---------------------------------------------------
        data["is_promise_broker"] = wrap(
            bool(
                broker
                and "promise insurance" in broker.lower()
            ),
            "high" if broker else "low",
            "promise",
        )

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        policy_number = self._extract_policy_number()

        data["policy_number"] = wrap(
            policy_number,
            "high" if policy_number else "missing",
            "policy",
        )

        # ---------------------------------------------------
        # POLICY TYPE
        # ---------------------------------------------------
        policy_type = self._extract_policy_type()

        data["policy_type"] = wrap(
            policy_type,
            "high" if policy_type else "missing",
            "ptype",
        )

        # ---------------------------------------------------
        # POLICY PERIOD
        # ---------------------------------------------------
        start_date, end_date = self._extract_policy_period()

        data["policy_start_date"] = wrap(
            start_date,
            "high" if start_date else "missing",
            "start",
        )

        data["policy_end_date"] = wrap(
            end_date,
            "high" if end_date else "missing",
            "end",
        )

        # ---------------------------------------------------
        # CURRENCY
        # ---------------------------------------------------
        data["premium_currency"] = wrap(
            "AED",
            "high",
            "currency",
        )

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        data["premium_amount"] = wrap(
            amounts.get("total"),
            "high" if amounts.get("total") is not None else "missing",
            "premium",
        )

        data["net_premium"] = wrap(
            amounts.get("net_premium"),
            "high" if amounts.get("net_premium") is not None else "missing",
            "net",
        )

        data["vat_amount"] = wrap(
            amounts.get("vat_amount"),
            "high" if amounts.get("vat_amount") is not None else "missing",
            "vat",
        )

        data["total"] = wrap(
            amounts.get("total"),
            "high" if amounts.get("total") is not None else "missing",
            "total",
        )

        data["total_premium"] = wrap(
            amounts.get("total"),
            "high" if amounts.get("total") is not None else "missing",
            "totprem",
        )

        data["net_due"] = wrap(
            amounts.get("total"),
            "high" if amounts.get("total") is not None else "missing",
            "due",
        )

        # ---------------------------------------------------
        # BRANCH
        # ---------------------------------------------------
        data["branch"] = wrap(
            None,
            "missing",
            "branch",
        )

        # ---------------------------------------------------
        # CALCULATED
        # ---------------------------------------------------
        data["invoice_date_calc"] = wrap(
            invoice_date,
            "high" if invoice_date else "missing",
            "calc",
        )

        data["due_date"] = wrap(
            invoice_date,
            "medium" if invoice_date else "missing",
            "due",
        )

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # CUSTOMER
    # ---------------------------------------------------
    def _extract_customer_name(self):

        patterns = [

            r"Insured\s*:?\s*([^\n\r]+)",

            r"Customer\s*Name\s*:?\s*([^\n\r]+)",

            r"Name\s*of\s*Insured\s*:?\s*([^\n\r]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE,
            )

            if match:

                value = match.group(1).strip()

                value = re.sub(
                    r"\s+",
                    " ",
                    value,
                )

                value = re.split(
                    r"(policy|invoice|date|vat)",
                    value,
                    flags=re.IGNORECASE,
                )[0].strip()

                if len(value) > 2:
                    return value

        return None

    # ---------------------------------------------------
    # BROKER
    # ---------------------------------------------------
    def _extract_broker_name(self):

        labels = [

            "Broker",
            "Broker Name",
            "Agent",
            "Agent/Broker",
        ]

        for i, line in enumerate(self.lines):

            for label in labels:

                if re.search(label, line, re.IGNORECASE):

                    inline = re.split(
                        rf"{label}\s*:?",
                        line,
                        maxsplit=1,
                        flags=re.IGNORECASE,
                    )

                    if len(inline) > 1:

                        value = inline[1].strip(" :-")

                        if (
                            value
                            and len(value) > 2
                        ):
                            return value

                    for j in range(
                        i + 1,
                        min(i + 5, len(self.lines))
                    ):

                        cand = self.lines[j]

                        if re.search(
                            r"(policy|invoice|date|premium|vat)",
                            cand,
                            re.IGNORECASE,
                        ):
                            break

                        if len(cand) > 2:
                            return cand

        return None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [

            r"Policy\s*No\.?\s*:?\s*([A-Z0-9/\-]+)",

            r"Policy\s*Number\s*:?\s*([A-Z0-9/\-]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE,
            )

            if match:

                value = match.group(1).strip()

                if self._valid_policy(value):
                    return value

        for i, line in enumerate(self.lines):

            if re.search(
                r"Policy\s*(No|Number)",
                line,
                re.IGNORECASE,
            ):

                for j in range(
                    i + 1,
                    min(i + 4, len(self.lines))
                ):

                    cand = self.lines[j]

                    if self._valid_policy(cand):
                        return cand

        return None

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        patterns = [

            r"Policy\s*Type\s*:?\s*([^\n\r]+)",

            r"Class\s*:\s*([^\n\r]+)",

            r"Insurance\s*Type\s*:?\s*([^\n\r]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE,
            )

            if match:

                value = match.group(1).strip()

                if (
                    value
                    and not re.search(r"\d{4,}", value)
                ):
                    return value

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        for i, line in enumerate(self.lines):

            if re.search(
                r"(policy\s*period|period\s*of\s*insurance)",
                line,
                re.IGNORECASE,
            ):

                block = " ".join(
                    self.lines[i:i + 6]
                )

                start_date, end_date = (
                    extract_policy_date_range(block)
                )

                if (
                    start_date
                    and end_date
                    and start_date != end_date
                ):
                    return (
                        normalize_date(start_date),
                        normalize_date(end_date),
                    )

        start_date, end_date = (
            extract_policy_date_range(
                "\n".join(self.lines)
            )
        )

        if (
            start_date
            and end_date
            and start_date != end_date
        ):
            return (
                normalize_date(start_date),
                normalize_date(end_date),
            )

        return None, None

    # ---------------------------------------------------
    # INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_invoice_number(self):

        patterns = [

            r"Invoice\s*Ref\s*No\.?\s*:?\s*([A-Z0-9/\-]+)",

            r"Invoice\s*No\.?\s*:?\s*([A-Z0-9/\-]+)",

            r"Tax\s*Invoice\s*No\.?\s*:?\s*([A-Z0-9/\-]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE,
            )

            if match:
                return match.group(1).strip()

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        patterns = [

            r"Invoice\s*Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",

            r"Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE,
            )

            if match:

                value = match.group(1).strip()

                return (
                    normalize_date(value)
                    or value
                )

        return None

    # ---------------------------------------------------
    # AMOUNTS
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {

            "net_premium": None,
            "vat_amount": None,
            "total": None,
        }

        text = self.text

        # ---------------------------------------------------
        # VAT
        # ---------------------------------------------------
        vat_match = re.search(
            r"VAT\s*(?:Amount)?\s*:?\s*([\d,]+\.\d+)",
            text,
            re.IGNORECASE,
        )

        if vat_match:

            result["vat_amount"] = float(
                vat_match.group(1).replace(",", "")
            )

        # ---------------------------------------------------
        # NET PREMIUM
        # ---------------------------------------------------
        premium_match = re.search(
            r"(?:Net\s*Premium|Premium)\s*:?\s*([\d,]+\.\d+)",
            text,
            re.IGNORECASE,
        )

        if premium_match:

            result["net_premium"] = float(
                premium_match.group(1).replace(",", "")
            )

        # ---------------------------------------------------
        # TOTAL
        # ---------------------------------------------------
        total_match = re.search(
            r"(?:Total|Gross\s*Premium|Amount\s*Due)\s*:?\s*([\d,]+\.\d+)",
            text,
            re.IGNORECASE,
        )

        if total_match:

            result["total"] = float(
                total_match.group(1).replace(",", "")
            )

        # ---------------------------------------------------
        # FALLBACK
        # ---------------------------------------------------
        if (
            result["total"] is None
            and result["net_premium"] is not None
            and result["vat_amount"] is not None
        ):

            result["total"] = round(
                result["net_premium"]
                + result["vat_amount"],
                2
            )

        return result

    # ---------------------------------------------------
    # VALIDATE POLICY
    # ---------------------------------------------------
    def _valid_policy(self, value):

        if not value:
            return False

        value = value.strip().upper()

        if re.search(
            r"(DATE|VAT|TOTAL|PREMIUM|BROKER|INVOICE)",
            value,
        ):
            return False

        if len(value) < 6:
            return False

        if not re.search(r"\d", value):
            return False

        return True