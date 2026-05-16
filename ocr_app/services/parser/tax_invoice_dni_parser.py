import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date
)
from ..structured_schema import finalize_tax_invoice_output


class DNITaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get("full_text", "")

        self.tables = layout_data.get("tables", [])

        self.lines = [
            ln.strip()
            for ln in self.text.splitlines()
            if ln.strip()
        ]

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

        start_date, end_date = self._extract_policy_period()
        amounts = self._extract_amounts()

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
                amounts.get("total"),
                "high" if amounts.get("total") is not None else "missing",
                "prem"
            ),

            "net_premium": w(
                amounts.get("net_premium"),
                "high" if amounts.get("net_premium") is not None else "missing",
                "net"
            ),

            "total_premium": w(
                amounts.get("total"),
                "high" if amounts.get("total") is not None else "missing",
                "tot"
            ),

            "vat_amount": w(
                amounts.get("vat_amount"),
                "high" if amounts.get("vat_amount") is not None else "missing",
                "vat"
            ),

            "net_due": w(
                amounts.get("total"),
                "high" if amounts.get("total") is not None else "missing",
                "due"
            ),

            "total": w(
                amounts.get("total"),
                "high" if amounts.get("total") is not None else "missing",
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
            "data": finalize_tax_invoice_output(wrapped)
        }

    # ---------------------------------------------------
    # CUSTOMER NAME (FIXED)
    # ---------------------------------------------------
    def _extract_customer_name(self):

        # ---------------------------------------------
        # PRIORITY 1 : ASSURED NAME
        # ---------------------------------------------
        for i, line in enumerate(self.lines):

            if re.fullmatch(
                r"Assured\s*Name",
                line,
                re.IGNORECASE
            ):

                for j in range(
                    i + 1,
                    min(i + 5, len(self.lines))
                ):

                    candidate = self.lines[j].strip()

                    # stop at next field
                    if re.search(
                        r"^(Class|Sub\s*class|Account|Registration|Vehicle|Engine|Chassis|Policy|Tax)",
                        candidate,
                        re.IGNORECASE
                    ):
                        break

                    # remove bracket ids
                    candidate = re.sub(
                        r"\(.*?\)",
                        "",
                        candidate
                    ).strip()

                    # remove phone numbers
                    candidate = re.sub(
                        r"\b\d{5,}\b",
                        "",
                        candidate
                    ).strip()

                    # remove address/location junk
                    if re.search(
                        r"(UNITED\s*ARAB\s*EMIRATES|ABU\s*DHABI|DUBAI|UAE)",
                        candidate,
                        re.IGNORECASE
                    ):
                        continue

                    candidate = re.sub(
                        r"\s+",
                        " ",
                        candidate
                    ).strip(" :-")

                    if len(candidate) > 4:
                        return candidate

        # ---------------------------------------------
        # PRIORITY 2 : TO BLOCK
        # ---------------------------------------------
        capture = False
        collected = []

        for line in self.lines:

            raw = line.strip()

            if re.fullmatch(
                r"To",
                raw,
                re.IGNORECASE
            ):
                capture = True
                continue

            if not capture:
                continue

            # stop conditions
            if re.search(
                r"(Insured\s*TAX|Tax\s*Invoice|Division|Department|Policy)",
                raw,
                re.IGNORECASE
            ):
                break

            # remove ids like (7301021)
            raw = re.sub(
                r"\(.*?\)",
                "",
                raw
            ).strip()

            # skip address/location
            if re.search(
                r"(ABU\s*DHABI|DUBAI|UNITED\s*ARAB\s*EMIRATES|UAE)",
                raw,
                re.IGNORECASE
            ):
                continue

            # skip phone numbers
            if re.fullmatch(r"[\d\s\-+]+", raw):
                continue

            # cleanup
            raw = re.sub(
                r"\s+",
                " ",
                raw
            ).strip(" :-")

            # important:
            # stop OCR pollution like "0 ADB F"
            if re.search(
                r"\bADB\b",
                raw,
                re.IGNORECASE
            ):
                continue

            # likely real name
            if (
                len(raw) > 4
                and re.search(r"[A-Z]", raw)
            ):
                collected.append(raw)

            # usually first clean line is enough
            if collected:
                break

        if collected:

            value = " ".join(collected)

            value = re.sub(
                r"\s+",
                " ",
                value
            ).strip()

            if len(value) > 4:
                return value

        return None

    # ---------------------------------------------------
    # BROKER
    # ---------------------------------------------------
    def _extract_broker_name(self):

        m = re.search(
            r"Account\s*No\s*[\n:]+\s*[A-Z0-9\-\/]+\s+([^\n\r]+)",
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

        m = re.search(
            r"Sub\s*class\s*[\n:]+\s*([^\n\r]+)",
            self.text,
            re.I
        )

        if m:
            return m.group(1).strip()

        m = re.search(
            r"Policy\s*Type\s*:?\s*([^\n\r]+)",
            self.text,
            re.I
        )

        if m:
            return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        def clean(val):

            val = re.sub(r"\s+", "", val)

            m = re.search(
                r"\d{2,}\/\d+\/[A-Z0-9]+\/\d+\/\d+",
                val
            )

            if m:
                return m.group(0)

            m = re.search(
                r"\d+\/[A-Z0-9\/\-]{6,}",
                val
            )

            if m:
                return m.group(0)

            return None

        for i, line in enumerate(self.lines):

            if re.search(
                r"Policy\s*(No|Number)",
                line,
                re.I
            ):

                for j in range(
                    i + 1,
                    min(i + 10, len(self.lines))
                ):

                    cand = self.lines[j].strip()

                    if not cand:
                        continue

                    if re.search(
                        r"(Assured|Class|Account|Division|Tax Invoice)",
                        cand,
                        re.I
                    ):
                        break

                    result = clean(cand)

                    if result:
                        return result

        return None

    # ---------------------------------------------------
    # INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_invoice_number(self):

        m = re.search(
            r"Tax\s*Invoice\s*No\s*[\n:]+\s*([A-Z0-9/\-]+)",
            self.text,
            re.I
        )

        if m:
            return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        m = re.search(
            r"Invoice\s*Date\s*[\n:]+\s*([A-Z0-9\-\/]+)",
            self.text,
            re.I
        )

        if m:
            return normalize_date(m.group(1))

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        start_date, end_date = extract_policy_date_range(
            self.text
        )

        return (
            normalize_date(start_date)
            if start_date else None,

            normalize_date(end_date)
            if end_date else None
        )

    # ---------------------------------------------------
    # AMOUNTS
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {
            "net_premium": None,
            "vat_amount": None,
            "total": None
        }

        numbers = re.findall(
            r"([\d,]+\.\d{2})",
            self.text
        )

        cleaned = []

        for n in numbers:

            try:
                cleaned.append(
                    float(n.replace(",", ""))
                )

            except:
                pass

        if len(cleaned) >= 3:

            result["net_premium"] = cleaned[-3]
            result["vat_amount"] = cleaned[-2]
            result["total"] = cleaned[-1]

        return result