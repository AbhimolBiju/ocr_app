# tax_invoice_alsagr_parser.py

import re

from ..confidence import ConfidenceEngine
from ..structured_schema import finalize_tax_invoice_output


class AlSagrTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")
        self.lines = self.text.split("\n")

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------------------------------
        # INSURER NAME
        # ---------------------------------------------------
        data["insurer_name"] = {
            "value": "Al Sagr National Insurance",
            "confidence": 100
        }

        # ---------------------------------------------------
        # TAX INVOICE NUMBER
        # ---------------------------------------------------
        value = self._extract_invoice_number()

        data["tax_invoice_number"] = {
            "value": value,
            "confidence": ConfidenceEngine.calculate(
                value
            )
        }

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        value = self._extract_invoice_date()

        data["invoice_date"] = {
            "value": value,
            "confidence": ConfidenceEngine.calculate(
                value
            )
        }

        # ---------------------------------------------------
        # CUSTOMER NAME
        # ---------------------------------------------------
        value = self._extract_customer_name()

        data["customer_name"] = {
            "value": value,
            "confidence": ConfidenceEngine.calculate(
                value
            )
        }

        # ---------------------------------------------------
        # BROKER NAME
        # ---------------------------------------------------
        broker_name = self._extract_broker_name()

        data["broker_name"] = {
            "value": broker_name,
            "confidence": ConfidenceEngine.calculate(
                broker_name
            )
        }

        # ---------------------------------------------------
        # PROMISE BROKER CHECK
        # ---------------------------------------------------
        broker_text = (broker_name or "").upper()

        data["is_promise_broker"] = {
            "value": (
                "PROMISE INSURANCE" in broker_text
            ),
            "confidence": 100
        }

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        value = self._extract_policy_number()

        data["policy_number"] = {
            "value": value,
            "confidence": ConfidenceEngine.calculate(
                value
            )
        }

        # ---------------------------------------------------
        # POLICY TYPE
        # ---------------------------------------------------
        value = self._extract_policy_type()

        data["policy_type"] = {
            "value": value,
            "confidence": ConfidenceEngine.calculate(
                value
            )
        }

        # ---------------------------------------------------
        # POLICY PERIOD
        # ---------------------------------------------------
        start_date, end_date = (
            self._extract_policy_period()
        )

        data["policy_start_date"] = {
            "value": start_date,
            "confidence": ConfidenceEngine.calculate(
                start_date
            )
        }

        data["policy_end_date"] = {
            "value": end_date,
            "confidence": ConfidenceEngine.calculate(
                end_date
            )
        }

        # ---------------------------------------------------
        # CURRENCY
        # ---------------------------------------------------
        data["premium_currency"] = {
            "value": "AED",
            "confidence": 100
        }

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        net_premium = amounts.get(
            "net_premium"
        )

        vat_amount = amounts.get(
            "vat_amount"
        )

        total = amounts.get(
            "total"
        )

        data["net_premium"] = {
            "value": net_premium,
            "confidence": ConfidenceEngine.calculate(
                net_premium
            )
        }

        data["vat_amount"] = {
            "value": vat_amount,
            "confidence": ConfidenceEngine.calculate(
                vat_amount
            )
        }

        data["total"] = {
            "value": total,
            "confidence": ConfidenceEngine.calculate(
                total
            )
        }

        data["total_premium"] = {
            "value": total,
            "confidence": ConfidenceEngine.calculate(
                total
            )
        }

        data["net_due"] = {
            "value": total,
            "confidence": ConfidenceEngine.calculate(
                total
            )
        }

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_invoice_number(self):

        patterns = [

            r"Invoice\s*Number\s*[\n: ]+\s*([A-Z0-9\-\/]+)",

            r"Tax\s*Invoice\s*No\.?\s*[\n: ]+\s*([A-Z0-9\-\/]+)",

            r"Invoice\s*No\.?\s*[\n: ]+\s*([A-Z0-9\-\/]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                if len(value) >= 4:
                    return value

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        patterns = [

            r"Invoice\s*Date\s*[\n: ]+\s*(\d{2}/\d{2}/\d{4})",

            r"Date\s*[\n: ]+\s*(\d{2}/\d{2}/\d{4})",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                return match.group(1).strip()

        return None

    # ---------------------------------------------------
    # CUSTOMER NAME
    # ---------------------------------------------------
    def _extract_customer_name(self):

        patterns = [

            r"Insured\s*Name\s*[\n: ]+\s*(.+)",

            r"Customer\s*Name\s*[\n: ]+\s*(.+)",

            r"Insured\s*[\n: ]+\s*(.+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = value.split("\n")[0]

                value = re.sub(
                    r"\s+",
                    " ",
                    value
                )

                value = value.strip()

                if len(value) >= 3:
                    return value

        return None

    # ---------------------------------------------------
    # BROKER NAME
    # ---------------------------------------------------
    def _extract_broker_name(self):

        patterns = [

            r"Broker\s*Name\s*[\n: ]+\s*(.+)",

            r"Broker\s*[\n: ]+\s*(.+)",

            r"Agent\s*[\n: ]+\s*(.+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = value.split("\n")[0]

                value = re.sub(
                    r"\s+",
                    " ",
                    value
                )

                return value.strip()

        return None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [

            r"Policy\s*No\.?\s*[\n: ]+\s*([A-Z0-9\/\-]+)",

            r"Policy\s*Number\s*[\n: ]+\s*([A-Z0-9\/\-]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                if (
                    "/" in value
                    or "-" in value
                ):
                    return value

        return None

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        patterns = [

            r"Policy\s*Type\s*[\n: ]+\s*(.+)",

            r"Insurance\s*Type\s*[\n: ]+\s*(.+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = value.split("\n")[0]

                value = re.sub(
                    r"\s+",
                    " ",
                    value
                )

                return value.strip()

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        patterns = [

            # STANDARD
            r"Period\s*of\s*Ins\.?\s*[\n: ]+\s*"
            r"(\d{2}/\d{2}/\d{4})\s*to\s*"
            r"(\d{2}/\d{2}/\d{4})",

            # PERIOD OF INSURANCE
            r"Period\s*of\s*Insurance\s*[\n: ]+\s*"
            r"(\d{2}/\d{2}/\d{4})\s*to\s*"
            r"(\d{2}/\d{2}/\d{4})",

            # EXTENDED PERIOD
            r"Extended\s*Period\s*[\n: ]+\s*"
            r"(\d{2}/\d{2}/\d{4})\s*to\s*"
            r"(\d{2}/\d{2}/\d{4})",

            # FROM / TO FORMAT
            r"FROM\s*"
            r"(\d{2}/\d{2}/\d{4})"
            r".*?TO\s*"
            r"(\d{2}/\d{2}/\d{4})",

        ]

        compact_text = re.sub(
            r"\s+",
            " ",
            self.text
        )

        for pattern in patterns:

            match = re.search(
                pattern,
                compact_text,
                re.IGNORECASE
            )

            if match:

                start_date = match.group(1).strip()
                end_date = match.group(2).strip()

                if start_date != end_date:

                    return (
                        start_date,
                        end_date
                    )

        # ---------------------------------------------------
        # FALLBACK:
        # TAKE FIRST 2 VALID DATES
        # ---------------------------------------------------
        dates = re.findall(
            r"\d{2}/\d{2}/\d{4}",
            compact_text
        )

        if len(dates) >= 2:

            return (
                dates[0],
                dates[1]
            )

        return None, None

    # ---------------------------------------------------
    # AMOUNT EXTRACTION
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {

            "net_premium": None,
            "vat_amount": None,
            "total": None
        }

        # ---------------------------------------------------
        # TOTAL FIRST
        # ---------------------------------------------------
        total_match = re.search(
            r"Total\s*Amount.*?([\d,]+\.\d{2})",
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if total_match:

            try:

                total = float(
                    total_match.group(1)
                    .replace(",", "")
                )

                vat_amount = round(
                    total * 5 / 105,
                    2
                )

                net_premium = round(
                    total - vat_amount,
                    2
                )

                result["net_premium"] = (
                    net_premium
                )

                result["vat_amount"] = (
                    vat_amount
                )

                result["total"] = total

                return result

            except:
                pass

        # ---------------------------------------------------
        # FALLBACK PREMIUM
        # ---------------------------------------------------
        premium_match = re.search(
            r"5%\s*[\n ]+([\d,]+\.\d+)",
            self.text,
            re.IGNORECASE
        )

        if premium_match:

            try:

                net_premium = float(
                    premium_match.group(1)
                    .replace(",", "")
                )

                vat_amount = round(
                    net_premium * 0.05,
                    2
                )

                total = round(
                    net_premium + vat_amount,
                    2
                )

                result["net_premium"] = (
                    net_premium
                )

                result["vat_amount"] = (
                    vat_amount
                )

                result["total"] = total

            except:
                pass

        return result