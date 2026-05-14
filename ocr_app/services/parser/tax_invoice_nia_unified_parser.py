import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    clean_customer_name,
    collapse_whitespace,
)


class NIATaxInvoiceUnifiedParser:

    def __init__(self, layout_data):

        raw = layout_data.get("full_text", "") or ""

        # normalize spacing only (safe for OCR)
        self.text = re.sub(r"\s+", " ", raw)
        self.upper = self.text.upper()

    # ---------------------------------------------------
    # SAFE REGEX HELPER (prevents "no such group" crash)
    # ---------------------------------------------------
    def _search(self, pattern, group=1):

        m = re.search(pattern, self.text, re.IGNORECASE)

        if not m:
            return None

        try:
            return m.group(group).strip()
        except IndexError:
            return None

    # ---------------------------------------------------
    # MAIN PARSE
    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------
        # INSURER
        # ---------------------------
        data["insurer_name"] = ConfidenceEngine.wrap_field(
            "NIA Insurance", "high", "insurer"
        )

        # ---------------------------
        # INVOICE NUMBER
        # ---------------------------
        inv = self._search(r"Invoice\s*No\s*[:\-]?\s*([A-Z0-9\-\/]+)")

        data["tax_invoice_number"] = ConfidenceEngine.wrap_field(
            inv,
            "high" if inv else "missing",
            "invoice_no"
        )

        # ---------------------------
        # INVOICE DATE
        # ---------------------------
        date = self._search(r"Date\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})")

        data["invoice_date"] = ConfidenceEngine.wrap_field(
            date,
            "high" if date else "missing",
            "invoice_date"
        )

        # ---------------------------
        # CUSTOMER
        # ---------------------------
        cust = self._search(r"Insured\s*(.+?)\s*(TRN|Broker|Account)")

        if cust:
            cust = collapse_whitespace(cust)
            cust = clean_customer_name(cust)

        data["customer_name"] = ConfidenceEngine.wrap_field(
            cust,
            "high" if cust else "missing",
            "customer"
        )

        # ---------------------------
        # BROKER
        # ---------------------------
        broker = self._search(r"Broker\s*(.+?)\s*(Account|Invoice|TRN)")

        data["broker_name"] = ConfidenceEngine.wrap_field(
            broker,
            "high" if broker else "missing",
            "broker"
        )

        data["is_promise_broker"] = ConfidenceEngine.wrap_field(
            broker is not None and "PROMISE" in (broker or "").upper(),
            "high" if broker else "low",
            "promise"
        )

        # ---------------------------
        # POLICY NUMBER
        # ---------------------------
        pol = self._search(r"Policy\s*Number\s*[:\-]?\s*(P\/[\d\/]+)")

        data["policy_number"] = ConfidenceEngine.wrap_field(
            pol,
            "high" if pol else "missing",
            "policy_no"
        )

        # ---------------------------
        # POLICY PERIOD
        # ---------------------------
        period = re.search(
            r"(\d{2}/\d{2}/\d{4})\s*TO\s*(\d{2}/\d{2}/\d{4})",
            self.text,
            re.IGNORECASE
        )

        data["policy_start_date"] = ConfidenceEngine.wrap_field(
            period.group(1) if period else None,
            "high" if period else "missing",
            "start"
        )

        data["policy_end_date"] = ConfidenceEngine.wrap_field(
            period.group(2) if period else None,
            "high" if period else "missing",
            "end"
        )

        # ---------------------------
        # AMOUNTS
        # ---------------------------
        def amt(pattern):
            m = re.search(pattern, self.text, re.IGNORECASE)
            return float(m.group(1).replace(",", "")) if m else None

        net = amt(r"Premium\s*Total\s*([\d,]+\.\d{2})")
        vat = amt(r"VAT\s*5\s*%?\s*([\d,]+\.\d{2})")
        total = amt(r"Grand\s*Total\s*([\d,]+\.\d{2})")

        data["net_premium"] = ConfidenceEngine.wrap_field(net, "high" if net else "missing", "net")
        data["vat_amount"] = ConfidenceEngine.wrap_field(vat, "high" if vat else "missing", "vat")
        data["total"] = ConfidenceEngine.wrap_field(total, "high" if total else "missing", "total")

        data["premium_currency"] = ConfidenceEngine.wrap_field("AED", "high", "currency")

        return data


# ---------------------------------------------------
# COMPATIBILITY WRAPPER (DO NOT BREAK ROUTER)
# ---------------------------------------------------
class NIATaxInvoiceLegacyParser(NIATaxInvoiceUnifiedParser):
    pass


class NIATaxInvoiceV2Parser(NIATaxInvoiceUnifiedParser):
    pass