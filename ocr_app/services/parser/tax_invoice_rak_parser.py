import re
from datetime import datetime

from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date,
)

from ..structured_schema import (
    finalize_tax_invoice_output
)


class RAKTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")
        self.tables = layout_data.get("tables", [])

        self.lines = self._deduplicate_lines(
            self.text.split("\n")
        )

    # ---------------------------------------------------
    # REMOVE DUPLICATE OCR LINES
    # ---------------------------------------------------
    def _deduplicate_lines(self, lines):

        seen = set()
        cleaned = []

        for line in lines:

            norm = line.strip()

            if not norm:
                continue

            if norm in seen:
                continue

            seen.add(norm)
            cleaned.append(norm)

        return cleaned

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------------------------------
        # INSURER
        # ---------------------------------------------------
        data["insurer_name"] = "RAK Insurance"

        # ---------------------------------------------------
        # TAX INVOICE NUMBER
        # ---------------------------------------------------
        data["tax_invoice_number"] = self._extract(
            r"(DN-\d{2}-\d{2}-\d{2}-[A-Z]{3}-\d+)"
        )

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        data["invoice_date"] = self._extract_invoice_date()

        # ---------------------------------------------------
        # CUSTOMER
        # ---------------------------------------------------
        data["customer_name"] = (
            self._extract_customer_name()
        )

        # ---------------------------------------------------
        # BROKER
        # ---------------------------------------------------
        broker_name = self._extract_broker_name()

        data["broker_name"] = broker_name

        data["is_promise_broker"] = False

        if broker_name:

            if "promise insurance" in broker_name.lower():

                data["is_promise_broker"] = True

        # ---------------------------------------------------
        # BRANCH
        # ---------------------------------------------------
        data["branch"] = self._extract_branch()

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        data["policy_number"] = self._extract(
            r"(P\/\d+\/[A-Z]+\/[A-Z]+\/\d+\/\d+)"
        )

        # ---------------------------------------------------
        # POLICY TYPE
        # ---------------------------------------------------
        data["policy_type"] = (
            self._extract_policy_type()
        )

        # ---------------------------------------------------
        # POLICY PERIOD
        # ---------------------------------------------------
        period = self._extract_policy_period()

        data["policy_start_date"] = (
            period.get("policy_start_date")
        )

        data["policy_end_date"] = (
            period.get("policy_end_date")
        )

        # ---------------------------------------------------
        # VEHICLE
        # ---------------------------------------------------
        data["vehicle"] = self._extract_vehicle()

        # ---------------------------------------------------
        # CURRENCY
        # ---------------------------------------------------
        data["premium_currency"] = (
            self._extract_currency()
        )

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        data["premium_amount"] = (
            amounts.get("premium_amount")
        )

        data["net_premium"] = (
            amounts.get("net_premium")
        )

        data["vat_amount"] = (
            amounts.get("vat_amount")
        )

        data["total_premium"] = (
            amounts.get("total_premium")
        )

        data["net_due"] = (
            amounts.get("net_due")
        )

        data["total"] = (
            amounts.get("total")
        )

        # ---------------------------------------------------
        # EXTRA
        # ---------------------------------------------------
        data["invoice_date_calc"] = (
            data["invoice_date"]
        )

        data["due_date"] = (
            data["invoice_date"]
        )

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # CLEAN TEXT
    # ---------------------------------------------------
    def _clean_text(self, text):

        if not text:
            return None

        text = re.sub(
            r'[\u0600-\u06FF]+',
            '',
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        return text if len(text) > 1 else None

    # ---------------------------------------------------
    # REMOVE DUPLICATE WORDS
    # ---------------------------------------------------
    def _dedupe_phrase(self, text):

        if not text:
            return None

        words = text.split()

        result = []
        seen = set()

        for word in words:

            upper = word.upper()

            if upper in seen:
                continue

            seen.add(upper)
            result.append(word)

        return " ".join(result).strip()

    # ---------------------------------------------------
    # CUSTOMER NAME
    # ---------------------------------------------------
    def _extract_customer_name(self):

        patterns = [

            r"Account\s*Name\s*:?\s*([^\n\r]+)",

            r"Customer\s*Name\s*:?\s*([^\n\r]+)",

            r"Insured\s*Name\s*:?\s*([^\n\r]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = self._clean_text(
                    match.group(1)
                )

                if value:
                    return value

        return None

    # ---------------------------------------------------
    # BROKER
    # ---------------------------------------------------
    def _extract_broker_name(self):

        match = re.search(
            r"PROMISE\s+INSURANCE\s+SERVICES(?:\s+LLC)?",
            self.text,
            re.IGNORECASE
        )

        if match:
            return match.group(0).strip()

        patterns = [

            r"Broker\s*:?\s*([^\n\r]+)",

            r"Intermediary\s*:?\s*([^\n\r]+)",

            r"Agent\s*:?\s*([^\n\r]+)",
        ]

        for pattern in patterns:

            value = self._extract(pattern)

            if value:

                value = self._clean_text(value)

                if value:
                    return value

        return None

    # ---------------------------------------------------
    # BRANCH
    # ---------------------------------------------------
    def _extract_branch(self):

        branch = self._extract(
            r"Branch\s*:?\s*([^\n\r]+)"
        )

        if branch:

            branch = branch.split(
                "Policy"
            )[0].strip()

            return self._clean_text(branch)

        return None

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        patterns = [

            r"Policy\s*Type\s*:?\s*([^\n\r]+)",

            r"Class\s*of\s*Insurance\s*:?\s*([^\n\r]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = self._clean_text(
                    match.group(1)
                )

                if value:
                    return value

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        result = {

            "policy_start_date": None,
            "policy_end_date": None,
        }

        # ---------------------------------------------------
        # GLOBAL DATE RANGE SEARCH (DEDUPED OCR SAFE)
        # ---------------------------------------------------
        deduped_text = "\n".join(self.lines)

        start_date, end_date = (
            extract_policy_date_range(
                deduped_text
            )
        )

        if self._is_valid_period(
            start_date,
            end_date
        ):

            result["policy_start_date"] = (
                normalize_date(start_date)
            )

            result["policy_end_date"] = (
                normalize_date(end_date)
            )

            return result

        # ---------------------------------------------------
        # POLICY INCEPTION / EXPIRY
        # ---------------------------------------------------
        inception = self._extract(
            r"Policy\s*Inception\s*Date\s*:?\s*([^\n\r]+)"
        )

        expiry = self._extract(
            r"Policy\s*Expiry\s*Date\s*:?\s*([^\n\r]+)"
        )

        if inception and expiry:

            result["policy_start_date"] = (
                normalize_date(inception)
            )

            result["policy_end_date"] = (
                normalize_date(expiry)
            )

            return result

        # ---------------------------------------------------
        # PERIOD BLOCK SEARCH
        # ---------------------------------------------------
        for i, line in enumerate(self.lines):

            if re.search(
                r"Period\s*of\s*Insurance",
                line,
                re.IGNORECASE
            ):

                block = " ".join(
                    self.lines[i:i + 10]
                )

                start_date, end_date = (
                    extract_policy_date_range(
                        block
                    )
                )

                if self._is_valid_period(
                    start_date,
                    end_date
                ):

                    result["policy_start_date"] = (
                        normalize_date(start_date)
                    )

                    result["policy_end_date"] = (
                        normalize_date(end_date)
                    )

                    return result

        return result

    def _is_valid_period(
        self,
        start_date,
        end_date
    ):

        if not start_date or not end_date:
            return False

        try:

            sd = datetime.strptime(
                normalize_date(start_date),
                "%d/%m/%Y"
            )

            ed = datetime.strptime(
                normalize_date(end_date),
                "%d/%m/%Y"
            )

            return sd < ed

        except:
            return False

    # ---------------------------------------------------
    # VEHICLE
    # ---------------------------------------------------
    def _extract_vehicle(self):

        for line in self.lines:

            if any(
                x.lower() in line.lower()
                for x in [
                    "vehicle make",
                    "nissan",
                    "toyota",
                    "honda",
                    "hyundai",
                ]
            ):

                return self._clean_text(line)

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        patterns = [

            r"Invoice\s*Date\s*:?\s*(\d{1,2}[-/][A-Za-z]+[-/]\d{4})",

            r"Date\s*:?\s*(\d{1,2}[-/][A-Za-z]+[-/]\d{4})",

            r"Invoice\s*Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                return normalize_date(
                    match.group(1)
                )

        dates = re.findall(

            r"\d{1,2}[-/][A-Za-z]+[-/]\d{4}",

            self.text
        )

        if dates:

            return normalize_date(
                dates[0]
            )

        return None

    # ---------------------------------------------------
    # CURRENCY
    # ---------------------------------------------------
    def _extract_currency(self):

        currencies = [

            "AED",
            "USD",
            "EUR",
            "SAR",
            "QAR",
        ]

        text_upper = self.text.upper()

        for currency in currencies:

            if currency in text_upper:
                return currency

        return "AED"

    # ---------------------------------------------------
    # AMOUNTS
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {

            "premium_amount": None,
            "net_premium": None,
            "vat_amount": None,
            "total_premium": None,
            "net_due": None,
            "total": None,
        }

        text = self.text

        # ---------------------------------------------------
        # VAT
        # ---------------------------------------------------
        vat_match = re.search(

            r"VAT.*?([\d,]+\.\d{2})",

            text,

            re.IGNORECASE | re.DOTALL
        )

        if vat_match:

            result["vat_amount"] = (
                self._to_float(
                    vat_match.group(1)
                )
            )

        # ---------------------------------------------------
        # TOTAL
        # ---------------------------------------------------
        total_patterns = [

            r"Gross\s*Amount\s*:?\s*([\d,]+\.\d{2})",

            r"Total\s*Amount\s*:?\s*([\d,]+\.\d{2})",

            r"Amount\s*Due\s*:?\s*([\d,]+\.\d{2})",
        ]

        for pattern in total_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                total = self._to_float(
                    match.group(1)
                )

                result["total"] = total
                result["total_premium"] = total
                result["net_due"] = total

                break

        # ---------------------------------------------------
        # NET PREMIUM
        # ---------------------------------------------------
        premium_patterns = [

            r"Premium\s*Due\s*:?\s*([\d,]+\.\d{2})",

            r"Net\s*Premium\s*:?\s*([\d,]+\.\d{2})",
        ]

        for pattern in premium_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                value = self._to_float(
                    match.group(1)
                )

                result["premium_amount"] = value
                result["net_premium"] = value

                break

        # ---------------------------------------------------
        # FALLBACK
        # ---------------------------------------------------
        if (
            result["total"] is None
            and result["net_premium"] is not None
            and result["vat_amount"] is not None
        ):

            total = round(

                result["net_premium"]
                + result["vat_amount"],

                2
            )

            result["total"] = total
            result["total_premium"] = total
            result["net_due"] = total

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

            if match.groups():
                return match.group(1).strip()

            return match.group(0).strip()

        return None

    # ---------------------------------------------------
    # FLOAT
    # ---------------------------------------------------
    def _to_float(self, value):

        try:

            value = (
                str(value)
                .replace(",", "")
                .replace("(", "-")
                .replace(")", "")
                .strip()
            )

            return float(value)

        except:

            return None