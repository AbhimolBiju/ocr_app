import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date
)
from ..structured_schema import finalize_tax_invoice_output


class QICTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")
        self.tables = layout_data.get("tables", [])

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        CE = ConfidenceEngine

        def w(val, rel="medium", salt="qic"):
            return CE.wrap_field(val, rel, salt)

        insurer = self._extract_insurer_name()

        customer_name = self._extract_customer_name()

        broker_name = self._extract_broker_name()

        invoice_date = self._extract_invoice_date()

        branch = self._extract(
            r"Branch\s*:\s*([^\n\r]+)"
        )

        policy_type = self._extract(
            r"Product\s*:\s*(.+)"
        )

        policy_number = self._extract_policy_number()

        tax_invoice_number = (
            self._extract_tax_invoice_number()
        )

        policy_start_date, policy_end_date = (
            self._extract_policy_period()
        )

        currency, currency_explicit = (
            self._extract_currency()
        )

        table_data = self._extract_table_data()

        premium_amount = table_data.get(
            "premium_amount"
        )

        net_premium = table_data.get(
            "net_premium"
        )

        total_premium = table_data.get(
            "total_premium"
        )

        vat_amount = table_data.get(
            "vat_amount"
        )

        net_due = table_data.get(
            "net_due"
        )

        wrapped = {

            "insurer_name": w(
                insurer,
                "high",
                "insurer"
            ),

            "customer_name": w(
                customer_name,
                "high" if customer_name else "missing",
                "customer"
            ),

            "broker_name": w(
                broker_name,
                "high" if broker_name else "missing",
                "broker"
            ),

            "is_promise_broker": w(
                bool(
                    broker_name
                    and "promise insurance" in broker_name.lower()
                ),
                "high" if broker_name else "low",
                "promise"
            ),

            "invoice_date": w(
                invoice_date,
                "high" if invoice_date else "missing",
                "invdate"
            ),

            "branch": w(
                branch,
                "high" if branch else "missing",
                "branch"
            ),

            "policy_type": w(
                policy_type,
                "high" if policy_type else "missing",
                "ptype"
            ),

            "policy_number": w(
                policy_number,
                "high" if policy_number else "missing",
                "pol"
            ),

            "tax_invoice_number": w(
                tax_invoice_number,
                "high" if tax_invoice_number else "missing",
                "taxno"
            ),

            "policy_start_date": w(
                policy_start_date,
                "high" if policy_start_date else "missing",
                "pstart"
            ),

            "policy_end_date": w(
                policy_end_date,
                "high" if policy_end_date else "missing",
                "pend"
            ),

            "premium_currency": w(
                currency,
                "high",
                "currency"
            ),

            "premium_amount": w(
                premium_amount,
                "high" if premium_amount is not None else "missing",
                "premium"
            ),

            "net_premium": w(
                net_premium,
                "high" if net_premium is not None else "missing",
                "netpremium"
            ),

            "total_premium": w(
                total_premium,
                "high" if total_premium is not None else "missing",
                "totalpremium"
            ),

            "vat_amount": w(
                vat_amount,
                "high" if vat_amount is not None else "missing",
                "vat"
            ),

            "net_due": w(
                net_due,
                "high" if net_due is not None else "missing",
                "netdue"
            ),

            "total": w(
                total_premium,
                "high" if total_premium is not None else "missing",
                "total"
            ),

            "invoice_date_calc": w(
                invoice_date,
                "high" if invoice_date else "missing",
                "idc"
            ),

            "due_date": w(
                invoice_date,
                "medium" if invoice_date else "missing",
                "due"
            ),
        }

        return finalize_tax_invoice_output(
            wrapped
        )

    # ---------------------------------------------------
    # INSURER NAME
    # ---------------------------------------------------
    def _extract_insurer_name(self):

        text_upper = self.text.upper()

        insurer_map = {

            "QATAR INSURANCE": "QIC",
            "QIC": "QIC",

        }

        for keyword, insurer in insurer_map.items():

            if keyword in text_upper:
                return insurer

        return "QIC"

    # ---------------------------------------------------
    # CUSTOMER NAME
    # ---------------------------------------------------
    def _extract_customer_name(self):

        patterns = [

            r"Insured\s*:?\s*([^\n\r]+)",
            r"Customer\s*Name\s*:?\s*([^\n\r]+)",
            r"Insured\s*Name\s*:?\s*([^\n\r]+)",
            r"Policy\s*Holder\s*:?\s*([^\n\r]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = re.split(
                    r"(Policy|Broker|Invoice|Date|TRN)",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

                if len(value) > 2:
                    return value

        return None

    # ---------------------------------------------------
    # BROKER NAME
    # ---------------------------------------------------
    def _extract_broker_name(self):

        patterns = [

            r"Broker\s*:?\s*([^\n\r]+)",
            r"Broker\s*Name\s*:?\s*([^\n\r]+)",
            r"Intermediary\s*:?\s*([^\n\r]+)",
            r"Agent\s*:?\s*([^\n\r]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                value = re.split(
                    r"(Policy|Invoice|Date|TRN)",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

                if len(value) > 2:
                    return value

        return None

    # ---------------------------------------------------
    # POLICY NUMBER (FIXED)
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [

            r"Policy\s*No\.?\s*:?\s*([A-Za-z0-9\s\-\/]+)",
            r"Policy\s*Number\s*:?\s*([A-Za-z0-9\s\-\/]+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if match:

                value = (
                    match.group(1)
                    .replace(" ", "")
                    .strip()
                )

                # FIX GREEDY OCR
                value = re.split(
                    r"POLICY|PERIOD|FROM|TO|DATE",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

                value = re.sub(
                    r"[^A-Z0-9/\-]",
                    "",
                    value.upper()
                )

                if len(value) >= 5:
                    return value

        return None

    # ---------------------------------------------------
    # TAX INVOICE NUMBER (FIXED)
    # ---------------------------------------------------
    def _extract_tax_invoice_number(self):

        patterns = [

            r"Doc\s*No\.?\s*:?\s*([A-Z0-9\s\-\/]+)",

            r"(?:Tax\s*Invoice|Invoice)\s*(?:No\.?|Number)\s*:?\s*([A-Z0-9\s\-\/]+)",

        ]

        for pattern in patterns:

            m = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if m:

                value = (
                    m.group(1)
                    .replace(" ", "")
                    .strip()
                )

                # FIX GREEDY OCR
                value = re.split(
                    r"DATE|POLICY|PERIOD|FROM|TO",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

                value = re.sub(
                    r"[^A-Z0-9/\-]",
                    "",
                    value.upper()
                )

                if len(value) >= 4:
                    return value

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        # ---------------------------------------------------
        # METHOD 1
        # ---------------------------------------------------
        lines = self.text.splitlines()

        for i, line in enumerate(lines):

            if re.search(
                r"(Policy\s*Period|Period\s*of\s*Insurance)",
                line,
                re.IGNORECASE
            ):

                block = " ".join(
                    lines[i:i+3]
                )

                start_date, end_date = (
                    extract_policy_date_range(
                        block
                    )
                )

                if (
                    start_date
                    and end_date
                    and start_date != end_date
                ):
                    return start_date, end_date

        # ---------------------------------------------------
        # METHOD 2
        # ---------------------------------------------------
        start_date, end_date = (
            extract_policy_date_range(
                self.text
            )
        )

        if (
            start_date
            and end_date
            and start_date != end_date
        ):
            return start_date, end_date

        return None, None

    # ---------------------------------------------------
    # TABLE PARSER
    # ---------------------------------------------------
    def _extract_table_data(self):

        result = {

            "premium_amount": None,
            "net_premium": None,
            "total_premium": None,
            "vat_amount": None,
            "net_due": None,

        }

        best_row = None

        for table in self.tables:

            grid = table.get("grid", [])

            for row in grid:

                row_text = " ".join(
                    [str(x) for x in row]
                ).lower()

                if any(
                    x in row_text
                    for x in [
                        "grand total",
                        "total due",
                        "invoice total",
                        "total"
                    ]
                ):

                    best_row = row

        if not best_row:
            return result

        numbers = self._extract_numbers(
            best_row
        )

        if len(numbers) >= 2:

            total = abs(numbers[-1])
            vat = abs(numbers[-2])

            if total >= vat:

                net = round(
                    total - vat,
                    2
                )

                result["premium_amount"] = total
                result["net_premium"] = net
                result["total_premium"] = total
                result["vat_amount"] = vat
                result["net_due"] = total

        return result

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        patterns = [

            r"(?:Invoice\s*Date|Date)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",

        ]

        compact = re.sub(
            r"\s+",
            " ",
            self.text
        )

        for pattern in patterns:

            m = re.search(
                pattern,
                compact,
                re.IGNORECASE
            )

            if m:
                return normalize_date(
                    m.group(1)
                )

        return None

    # ---------------------------------------------------
    # CURRENCY
    # ---------------------------------------------------
    def _extract_currency(self):

        if "AED" in self.text.upper():
            return "AED", True

        return "AED", False

    # ---------------------------------------------------
    # GENERIC EXTRACT
    # ---------------------------------------------------
    def _extract(self, pattern):

        match = re.search(
            pattern,
            self.text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return None

    # ---------------------------------------------------
    # EXTRACT NUMBERS
    # ---------------------------------------------------
    def _extract_numbers(self, row):

        nums = []

        for cell in row:

            try:

                value = (
                    str(cell)
                    .replace(",", "")
                    .replace("(", "-")
                    .replace(")", "")
                    .strip()
                )

                nums.append(float(value))

            except:
                continue

        return nums