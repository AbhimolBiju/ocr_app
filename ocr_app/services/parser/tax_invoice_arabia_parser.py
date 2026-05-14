import re
from datetime import datetime

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import extract_policy_date_range
from ..structured_schema import finalize_tax_invoice_output


class ArabiaTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")
        self.tables = layout_data.get("tables", [])

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------------------------------
        # INSURER
        # ---------------------------------------------------
        data["insurer_name"] = ConfidenceEngine.wrap_field(
            "Arabia Insurance",
            "high",
            "insurer",
        )

        # ---------------------------------------------------
        # INVOICE NUMBER
        # ---------------------------------------------------
        tax_invoice = self._extract(
            r"(TDN\s*\/\s*[A-Z]{2}\s*\/\s*\d{4}\s*\/\s*\d+)"
        )

        data["tax_invoice_number"] = self._build_field(
            tax_invoice,
            r"TDN\s*\/\s*[A-Z]{2}\s*\/\s*\d{4}\s*\/\s*\d+"
        )

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        invoice_date = self._extract_invoice_date()

        data["invoice_date"] = self._build_field(
            invoice_date,
            r"\d{2}/\d{2}/\d{4}"
        )

        # ---------------------------------------------------
        # CUSTOMER NAME
        # ---------------------------------------------------
        customer_name = self._extract_customer_name()

        data["customer_name"] = self._build_field(
            customer_name,
            r"[A-Za-z0-9&\.\- ]{3,}"
        )

        # ---------------------------------------------------
        # BROKER NAME
        # ---------------------------------------------------
        broker_name = self._extract_broker_name()

        data["broker_name"] = self._build_field(
            broker_name,
            r"[A-Za-z0-9&\.\- ]{3,}"
        )

        # ---------------------------------------------------
        # PROMISE CHECK
        # ---------------------------------------------------
        data["is_promise_broker"] = ConfidenceEngine.wrap_field(
            bool(
                broker_name
                and "PROMISE INSURANCE" in broker_name.upper()
            ),
            "high" if broker_name else "low",
            "promise",
        )

        # ---------------------------------------------------
        # BRANCH
        # ---------------------------------------------------
        branch = self._extract_branch()

        data["branch"] = self._build_field(
            branch,
            r"[A-Za-z ]{2,}"
        )

        # ---------------------------------------------------
        # POLICY TYPE
        # ---------------------------------------------------
        policy_type = self._extract_policy_type()

        data["policy_type"] = self._build_field(
            policy_type,
            r"[A-Za-z ]{2,}"
        )

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        policy_number = self._extract_policy_number()

        data["policy_number"] = self._build_field(
            policy_number,
            r"[A-Z0-9\/\-]+"
        )

        # ---------------------------------------------------
        # POLICY PERIOD
        # ---------------------------------------------------
        start_date, end_date = self._extract_policy_period()

        data["policy_start_date"] = self._build_field(
            start_date,
            r".+"
        )

        data["policy_end_date"] = self._build_field(
            end_date,
            r".+"
        )

        # ---------------------------------------------------
        # CURRENCY
        # ---------------------------------------------------
        currency = self._extract(
            r"Currency\s*([A-Z]{3})"
        )

        currency = currency or "AED"

        data["premium_currency"] = self._build_field(
            currency,
            r"[A-Z]{3}"
        )

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        data["net_premium"] = self._build_amount_field(
            amounts.get("net_premium")
        )

        data["vat_amount"] = self._build_amount_field(
            amounts.get("vat_amount")
        )

        data["total_premium"] = self._build_amount_field(
            amounts.get("total_premium")
        )

        data["net_due"] = self._build_amount_field(
            amounts.get("net_due")
        )

        data["total"] = self._build_amount_field(
            amounts.get("total")
        )

        # ---------------------------------------------------
        # EXTRA FIELDS
        # ---------------------------------------------------
        data["invoice_date_calc"] = self._build_field(
            invoice_date,
            r"\d{2}/\d{2}/\d{4}"
        )

        data["due_date"] = self._build_field(
            invoice_date,
            r"\d{2}/\d{2}/\d{4}"
        )

        data["premium_amount"] = self._build_amount_field(
            amounts.get("net_premium")
        )

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        text = re.sub(
            r"\s+",
            " ",
            self.text
        )

        patterns = [

            # MAIN CASE
            r"Tax\s*Invoice\s*Date\s*[:\-]?\s*([0-9]{2}-[A-Z]{3}-[0-9]{2,4})",

            # INLINE OCR CASE
            r"Invoice\s*Date\s*([0-9]{2}-[A-Z]{3}-[0-9]{2,4})",

            # GENERIC FALLBACK
            r"([0-9]{2}-[A-Z]{3}-[0-9]{2,4})",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                raw_date = (
                    match.group(1)
                    .strip()
                    .upper()
                )

                for fmt in [

                    "%d-%b-%y",
                    "%d-%b-%Y",

                ]:

                    try:

                        parsed = datetime.strptime(
                            raw_date,
                            fmt
                        )

                        return parsed.strftime(
                            "%d/%m/%Y"
                        )

                    except:
                        pass

                return raw_date

        return None

    # ---------------------------------------------------
    # CUSTOMER NAME
    # ---------------------------------------------------
    def _extract_customer_name(self):

        text = self.text

        # INLINE CASE
        match = re.search(
            r"Customer\s*:?\s*([A-Za-z0-9&\.\- ]+)",
            text,
            re.IGNORECASE
        )

        if match:

            candidate = match.group(1).strip()

            candidate = re.split(
                r"\d{3,}|United Arab Emirates|\n",
                candidate
            )[0].strip()

            if len(candidate) > 2:
                return candidate

        # LINE FALLBACK
        lines = text.split("\n")

        for i, line in enumerate(lines):

            if "Customer" in line:

                same = (
                    line
                    .split("Customer")[-1]
                    .replace(":", "")
                    .strip()
                )

                if same and len(same) > 2:
                    return same

                for j in range(i + 1, min(i + 5, len(lines))):

                    candidate = lines[j].strip()

                    if (
                        candidate
                        and not re.search(r"\d{5,}", candidate)
                    ):
                        return candidate

        return None

    # ---------------------------------------------------
    # BRANCH
    # ---------------------------------------------------
    def _extract_branch(self):

        text = self.text

        match = re.search(
            r"Branch\s*([^\n]+?)\s*Department",
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        # fallback
        match = re.search(
            r"Branch\s*([^\n]+)",
            text,
            re.IGNORECASE
        )

        if match:

            value = match.group(1)

            value = value.split(
                "Paid Up Capital"
            )[0]

            value = value.split(
                "Subject"
            )[0]

            return value.strip()

        return None

    # ---------------------------------------------------
    # BROKER NAME
    # ---------------------------------------------------
    def _extract_broker_name(self):

        text = self.text
        lines = text.splitlines()

        patterns = [

            r"(?:Insurance\s*Broker|Broker|Brokerage|Intermediary)\s*(?:Name)?\s*:?\s*([^\n\r]+)",

            r"Through\s*(?:Broker|Intermediary)?\s*:?\s*([^\n\r]+)",

            r"Broker\s*Name\s*:?\s*([^\n\r]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = re.split(
                    r"(policy|invoice|date|department|currency)",
                    value,
                    flags=re.IGNORECASE
                )[0].strip()

                if len(value) > 2:
                    return value

        # MULTI-LINE FALLBACK
        for i, line in enumerate(lines):

            if re.search(
                r"(broker|intermediary)",
                line,
                re.IGNORECASE
            ):

                same = re.split(
                    r"(broker|intermediary)",
                    line,
                    flags=re.IGNORECASE
                )[-1]

                same = same.replace(":", "").strip()

                if (
                    same
                    and len(same) > 2
                    and not re.search(
                        r"(policy|invoice|date)",
                        same,
                        re.IGNORECASE
                    )
                ):
                    return same

                for j in range(
                    i + 1,
                    min(i + 5, len(lines))
                ):

                    candidate = lines[j].strip()

                    if not candidate:
                        continue

                    if re.search(
                        r"(policy|invoice|date|currency|premium)",
                        candidate,
                        re.IGNORECASE
                    ):
                        break

                    if len(candidate) > 2:
                        return candidate

        return None

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        patterns = [

            r"Department\s*:?\s*([A-Za-z ]+)",

            r"Description\s*:?\s*([A-Za-z ]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = re.sub(
                    r"\s+",
                    " ",
                    value
                )

                if len(value) > 2:
                    return value

        return None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [

            r"Policy\s*No\s*[:\-]?\s*([A-Z0-9\/\-]+)",

            r"Motor\s*Insurance\s*Policy\s*No\s*([A-Z0-9\/\-]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                if len(value) >= 5:
                    return value

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        text = self.text
        lines = text.splitlines()

        # METHOD 1
        for i, line in enumerate(lines):

            if re.search(
                r"(period\s*of\s*insurance|insurance\s*period)",
                line,
                re.IGNORECASE
            ):

                block = " ".join(
                    lines[i:i + 6]
                )

                start_date, end_date = (
                    extract_policy_date_range(block)
                )

                if self._is_valid_period(
                    start_date,
                    end_date
                ):

                    return start_date, end_date

        return None, None

    def _is_valid_period(self, start_date, end_date):

        if not start_date or not end_date:
            return False

        def to_dt(v):

            try:
                return datetime.strptime(
                    v,
                    "%d/%m/%Y"
                )

            except:
                return None

        sd = to_dt(start_date)
        ed = to_dt(end_date)

        if not sd or not ed:
            return False

        return sd < ed

    # ---------------------------------------------------
    # AMOUNT EXTRACTION
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {
            "net_premium": None,
            "vat_amount": None,
            "total_premium": None,
            "net_due": None,
            "total": None,
        }

        text = re.sub(
            r"\s+",
            " ",
            self.text
        )

        # NET PREMIUM
        net_patterns = [

            r"Policy\s*Premium\s*([\d,]+\.\d+)",

            r"Gross\s*Premium\s*([\d,]+\.\d+)",

        ]

        for pattern in net_patterns:

            net_match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if net_match:

                result["net_premium"] = self._to_float(
                    net_match.group(1)
                )

                break

        # VAT
        vat_patterns = [

            r"Taxe\s*Value\s*([\d,]+\.\d+)",

            r"Tax\s*Value\s*([\d,]+\.\d+)",

            r"VAT\s*Amount\s*([\d,]+\.\d+)",

        ]

        for pattern in vat_patterns:

            vat_match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if vat_match:

                result["vat_amount"] = self._to_float(
                    vat_match.group(1)
                )

                break

        # TOTAL
        total_patterns = [

            r"Gross\s*Prem\s*with\s*VAT\s*([\d,]+\.\d+)",

            r"Total\s*Amount\s*([\d,]+\.\d+)",

        ]

        for pattern in total_patterns:

            total_match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if total_match:

                total = self._to_float(
                    total_match.group(1)
                )

                result["total_premium"] = total
                result["net_due"] = total
                result["total"] = total

                break

        # FALLBACK TOTAL
        if (
            result["total"] is None
            and result["net_premium"] is not None
            and result["vat_amount"] is not None
        ):

            total = round(

                result["net_premium"]
                + result["vat_amount"],

                3
            )

            result["total_premium"] = total
            result["net_due"] = total
            result["total"] = total

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
    # BUILD NORMAL FIELD
    # ---------------------------------------------------
    def _build_field(self, value, regex_pattern):

        confidence = ConfidenceEngine.calculate(
            value,
            pattern=regex_pattern,
        )

        return {
            "value": value,
            "confidence": confidence
        }

    # ---------------------------------------------------
    # BUILD AMOUNT FIELD
    # ---------------------------------------------------
    def _build_amount_field(self, value):

        confidence = ConfidenceEngine.calculate(
            value,
            pattern=r"^\d+(\.\d+)?$",
        )

        return {
            "value": value,
            "confidence": confidence
        }

    # ---------------------------------------------------
    # FLOAT CLEANER
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