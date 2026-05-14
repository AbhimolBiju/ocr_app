import re
from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date
)
from ..structured_schema import finalize_tax_invoice_output


class DNITaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get(
            "full_text",
            ""
        )

        self.tables = layout_data.get(
            "tables",
            []
        )

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        CE = ConfidenceEngine

        def w(val, rel="medium", salt="dni"):
            return CE.wrap_field(val, rel, salt)

        customer_name = self._extract_customer_name()

        broker_name = self._extract_broker_name()

        policy_type = self._extract_policy_type()

        policy_number = self._extract_policy_number()

        invoice_number = self._extract_invoice_number()

        invoice_date = self._extract_invoice_date()

        start_date, end_date = (
            self._extract_policy_period()
        )

        wrapped = {

            "insurer_name": w(
                "Dubai National Insurance",
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
                    and "promise" in broker_name.lower()
                ),
                "high",
                "promise"
            ),

            "invoice_date": w(
                invoice_date,
                "high" if invoice_date else "missing",
                "date"
            ),

            "branch": w(
                None,
                "missing",
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
                "pno"
            ),

            "tax_invoice_number": w(
                invoice_number,
                "high" if invoice_number else "missing",
                "inv"
            ),

            "policy_start_date": w(
                start_date,
                "high" if start_date else "missing",
                "start"
            ),

            "policy_end_date": w(
                end_date,
                "high" if end_date else "missing",
                "end"
            ),

            "premium_currency": w(
                "AED",
                "high",
                "cur"
            ),

            "premium_amount": w(
                None,
                "missing",
                "prem"
            ),

            "net_premium": w(
                None,
                "missing",
                "net"
            ),

            "total_premium": w(
                None,
                "missing",
                "tot"
            ),

            "vat_amount": w(
                None,
                "missing",
                "vat"
            ),

            "net_due": w(
                None,
                "missing",
                "due"
            ),

            "total": w(
                None,
                "missing",
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

        return {
            "data": finalize_tax_invoice_output(
                wrapped
            )
        }

    # ---------------------------------------------------
    # CUSTOMER
    # ---------------------------------------------------
    def _extract_customer_name(self):

        patterns = [

            r"Assured\s*:?\s*([^\n\r]+)",

            r"Insured\s*:?\s*([^\n\r]+)",

        ]

        for pattern in patterns:

            m = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if m:

                value = m.group(1).strip()

                value = re.split(
                    r"\b(TRN|Broker|Invoice|Date)\b",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

                if len(value) > 2:
                    return value

        return None

    # ---------------------------------------------------
    # BROKER
    # ---------------------------------------------------
    def _extract_broker_name(self):

        patterns = [

            r"Broker\s*:?\s*([^\n\r]+)",

            r"Agent\s*:?\s*([^\n\r]+)",

        ]

        for pattern in patterns:

            m = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if m:
                return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        patterns = [

            r"Sub\s*Class\s*:?\s*([^\n\r]+)",

            r"Policy\s*Type\s*:?\s*([^\n\r]+)",

        ]

        for pattern in patterns:

            m = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if m:
                return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [

            r"(?:Policy\s*No\.?|Policy\s*Number)\s*:?\s*([A-Z0-9/\-]+)",

        ]

        for pattern in patterns:

            m = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if m:
                return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_invoice_number(self):

        patterns = [

            r"(?:Invoice|Tax\s*Invoice)\s*(?:No\.?|Number)\s*:?\s*([A-Z0-9/\-]+)",

        ]

        for pattern in patterns:

            m = re.search(
                pattern,
                self.text,
                re.IGNORECASE
            )

            if m:
                return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        match = re.search(
            r"Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            self.text,
            re.IGNORECASE
        )

        if match:
            return normalize_date(
                match.group(1)
            )

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        return extract_policy_date_range(
            self.text
        )