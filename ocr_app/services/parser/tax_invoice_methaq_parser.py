import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    extract_policy_date_range,
    normalize_date
)
from ..structured_schema import (
    finalize_tax_invoice_output
)


class MethaqTaxInvoiceParser:

    def __init__(self, layout_data):
        self.text = layout_data.get("full_text", "")
        self.lines = [l.strip() for l in self.text.splitlines() if l.strip()]

    # ---------------------------------------------------
    # MAIN
    # ---------------------------------------------------
    def parse(self):

        CE = ConfidenceEngine

        def w(val, rel="medium", salt="methaq"):
            return CE.wrap_field(val, rel, salt)

        data = {}

        data["insurer_name"] = w("Methaq", "high", "insurer")

        invoice_date = self._extract_invoice_date()
        data["invoice_date"] = w(
            invoice_date,
            "high" if invoice_date else "missing",
            "idate"
        )

        # -------------------------
        # CUSTOMER NAME
        # -------------------------
        customer_name = self._extract_customer_name()

        if customer_name:
            customer_name = re.sub(
                r"\s+",
                " ",
                customer_name
            ).strip(": ").strip()

        data["customer_name"] = w(
            customer_name,
            "high" if customer_name else "missing",
            "cust",
        )

        broker_name = self._extract_broker_name()

        data["broker_name"] = w(
            broker_name,
            "high" if broker_name else "missing",
            "brok"
        )

        policy_number = self._extract_policy_number()

        data["policy_number"] = w(
            policy_number,
            "high" if policy_number else "missing",
            "pol"
        )

        tax_invoice = self._extract_invoice_number()

        data["tax_invoice_number"] = w(
            tax_invoice,
            "high" if tax_invoice else "missing",
            "taxno"
        )

        start_date, end_date = self._extract_policy_period()

        data["policy_start_date"] = w(
            start_date,
            "high" if start_date else "missing",
            "ps"
        )

        data["policy_end_date"] = w(
            end_date,
            "high" if end_date else "missing",
            "pe"
        )

        data["premium_currency"] = w(
            "AED",
            "high",
            "cur"
        )

        # -------------------------
        # POLICY TYPE
        # -------------------------
        policy_type = self._extract_policy_type()

        data["policy_type"] = w(
            policy_type,
            "high" if policy_type else "missing",
            "ptype"
        )

        # -------------------------
        # AMOUNTS
        # -------------------------
        amounts = self._extract_amounts()

        def amt(v, salt):
            return w(
                v,
                "high" if v is not None else "missing",
                salt
            )

        net_premium = amounts.get("net_premium")
        vat_amount = amounts.get("vat_amount")
        total = amounts.get("total")

        data["net_premium"] = amt(net_premium, "netp")
        data["vat_amount"] = amt(vat_amount, "vat")

        data["total"] = amt(total, "tot")
        data["net_due"] = amt(total, "netd")
        data["total_premium"] = amt(total, "totp")

        data["invoice_date_calc"] = data["invoice_date"]
        data["due_date"] = data["invoice_date"]

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        # line-based extraction
        for line in self.lines:

            if "policy type" in line.lower():

                parts = line.split(":")

                if len(parts) > 1:

                    val = parts[1].strip()

                    val = val.split("\n")[0]

                    val = re.split(
                        r"\b(Net\s*due|Amount|Premium|Authorised|AED)\b",
                        val,
                        flags=re.IGNORECASE
                    )[0]

                    val = val.strip(" :-\t")

                    if len(val) > 2:
                        return val

        # fallback extraction
        m = re.search(
            r"Policy\s*Type\s*:?\s*([A-Za-z\s\-]+)",
            self.text,
            re.IGNORECASE
        )

        if m:

            val = m.group(1)

            val = val.split("\n")[0]

            val = re.split(
                r"\b(Net\s*due|Amount|Premium|Authorised|AED)\b",
                val,
                flags=re.IGNORECASE
            )[0]

            val = val.strip(" :-\t")

            if len(val) > 2:
                return val

        return None

    # ---------------------------------------------------
    # CUSTOMER NAME (FIXED)
    # ---------------------------------------------------
    def _extract_customer_name(self):

        text = self.text

        # -----------------------------------
        # CASE 1 : PARTICIPANT NAME
        # (Debit Note documents)
        # -----------------------------------
        m = re.search(
            r"Participant\s*Name\s*:?\s*([^\n\r]+)",
            text,
            re.IGNORECASE
        )

        if m:

            val = m.group(1).strip()

            # hard cleanup
            val = re.split(
                r"(Insurance\s*Policy|Methaq\s*reference|Period\s*of\s*Insurance|Policy\s*Type)",
                val,
                flags=re.IGNORECASE
            )[0]

            val = val.strip(" :-")

            if len(val) > 3:
                return val

        # -----------------------------------
        # CASE 2 : TO:
        # (Tax Invoice documents)
        # -----------------------------------
        m = re.search(
            r"To\s*:\s*([^\n\r]+)",
            text,
            re.IGNORECASE
        )

        if m:

            val = m.group(1).strip()

            val = re.split(
                r"(TRN|Insured|Email|Tel)",
                val,
                flags=re.IGNORECASE
            )[0]

            val = val.strip(" :-")

            if len(val) > 3:
                return val

        # -----------------------------------
        # CASE 3 : INSURED:
        # -----------------------------------
        m = re.search(
            r"Insured\s*:?\s*([^\n\r]+)",
            text,
            re.IGNORECASE
        )

        if m:

            val = m.group(1).strip()

            val = re.split(
                r"(TRN|Email|Tel)",
                val,
                flags=re.IGNORECASE
            )[0]

            val = val.strip(" :-")

            if len(val) > 3:
                return val

        return None

    # ---------------------------------------------------
    # INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_invoice_number(self):

        patterns = [
            r"Invoice\s*Number\s*:?\s*([A-Z0-9/\-]+)",
            r"Doc\s*Number\s*:?\s*([A-Z0-9/\-]+)",
            r"Debit\s*Note\s*([A-Z0-9/\-]+)",
        ]

        for p in patterns:

            m = re.search(
                p,
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

        patterns = [
            r"Issue\s*Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            r"Doc\s*Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        ]

        for p in patterns:

            m = re.search(
                p,
                self.text,
                re.IGNORECASE
            )

            if m:
                return normalize_date(m.group(1))

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        m = re.search(
            r"From\s*:?\s*(\d{1,2}[-/]\w+[-/]\d{4}).{0,80}?To\s*:?\s*(\d{1,2}[-/]\w+[-/]\d{4})",
            self.text,
            re.DOTALL | re.IGNORECASE
        )

        if m:

            start_date = normalize_date(m.group(1))
            end_date = normalize_date(m.group(2))

            return start_date, end_date

        return None, None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [
            r"Insurance\s*Policy\s*No\s*:?\s*([A-Z0-9/\-]+)",
            r"Policy\s*No\s*:?\s*([A-Z0-9/\-]+)",
        ]

        for p in patterns:

            m = re.search(
                p,
                self.text,
                re.IGNORECASE
            )

            if m:
                return m.group(1).strip()

        return None

    # ---------------------------------------------------
    # BROKER
    # ---------------------------------------------------
    def _extract_broker_name(self):

        patterns = [
            r"Intermediary\s*Name\s*:?\s*([^\n\r]+)",
            r"Producer\s*:?\s*([^\n\r]+)",
        ]

        for p in patterns:

            m = re.search(
                p,
                self.text,
                re.IGNORECASE
            )

            if m:

                val = m.group(1).strip()

                if len(val) > 2:
                    return val

        return None

    # ---------------------------------------------------
    # AMOUNTS (FIXED)
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {}

        def clean_number(x):

            try:
                return round(
                    float(x.replace(",", "").strip()),
                    2
                )
            except:
                return None

        # -----------------------------------
        # TOTAL / NET DUE
        # -----------------------------------
        m = re.search(
            r"Net\s*due\s*to\s*you\s*:?\s*([\d,]+\.\d{2,3})",
            self.text,
            re.IGNORECASE
        )

        if m:

            total = clean_number(m.group(1))

            if total is not None:
                result["total"] = total

        # -----------------------------------
        # PREMIUM + VAT
        # -----------------------------------
        m = re.search(
            r"Being\s*Policy\s*Contribution\s*VAT\s*5%\s*([\d,]+\.\d{2,3})\s+([\d,]+\.\d{2,3})",
            self.text,
            re.IGNORECASE
        )

        if m:

            premium = clean_number(m.group(1))
            vat = clean_number(m.group(2))

            if premium is not None:
                result["net_premium"] = premium

            if vat is not None:
                result["vat_amount"] = vat

        # -----------------------------------
        # FALLBACK
        # -----------------------------------
        if (
            "net_premium" not in result
            or "vat_amount" not in result
        ):

            numbers = re.findall(
                r"([\d,]+\.\d{2,3})",
                self.text
            )

            cleaned = []

            for n in numbers:

                val = clean_number(n)

                if val is not None:
                    cleaned.append(val)

            if len(cleaned) >= 2:

                if "net_premium" not in result:
                    result["net_premium"] = cleaned[0]

                if "vat_amount" not in result:
                    result["vat_amount"] = cleaned[1]

        return result