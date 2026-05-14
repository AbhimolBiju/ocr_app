import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    clean_customer_name,
    collapse_whitespace,
)


class NIATaxInvoiceV2Parser:

    def __init__(self, layout_data):

        # ⚠️ IMPORTANT: DO NOT OVER-NORMALIZE OCR TEXT
        self.text = layout_data.get("full_text", "") or ""

        # preserve real OCR structure
        self.lines = self.text.splitlines()
        self.lines = [ln.strip() for ln in self.lines if ln.strip()]

    # ---------------------------------------------------
    # CORE BLOCK EXTRACTOR (FIXED INDENTATION)
    # ---------------------------------------------------
    def _get_block_value(self, labels):

        text = self.text.lower()

        for label in labels:

            label = label.lower().replace(":", "").strip()

            if label in text:

                parts = text.split(label)

                if len(parts) > 1:

                    candidate = parts[1].strip()

                    # stop at next known field boundary
                    stop_words = [
                        "insured", "broker", "policy", "invoice",
                        "premium", "vat", "grand", "trn", "account"
                    ]

                    for w in stop_words:
                        candidate = candidate.split(w)[0]

                    return candidate.strip()

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
        inv = self._get_block_value(["invoice no", "invoice number"])

        if inv:
            m = re.search(r"\d[\d\-]+", inv)
            inv = m.group(0) if m else None

        data["tax_invoice_number"] = ConfidenceEngine.wrap_field(
            inv, "high" if inv else "missing", "invoice_no"
        )

        # ---------------------------
        # INVOICE DATE
        # ---------------------------
        date = self._get_block_value(["date", "invoice date"])

        if date:
            m = re.search(r"\d{2}/\d{2}/\d{4}", date)
            date = m.group(0) if m else None

        data["invoice_date"] = ConfidenceEngine.wrap_field(
            date, "high" if date else "missing", "invoice_date"
        )

        # ---------------------------
        # CUSTOMER
        # ---------------------------
        cust = self._get_block_value(["insured"])

        if cust:
            cust = re.split(
                r"\bTRN\b|\bBROKER\b",
                cust,
                flags=re.IGNORECASE
            )[0]

            cust = collapse_whitespace(cust)
            cust = clean_customer_name(cust)

        data["customer_name"] = ConfidenceEngine.wrap_field(
            cust, "high" if cust else "missing", "customer"
        )

        # ---------------------------
        # BROKER
        # ---------------------------
        broker = self._get_block_value(["broker"])

        data["broker_name"] = ConfidenceEngine.wrap_field(
            broker, "high" if broker else "missing", "broker"
        )

        # ---------------------------
        # POLICY NUMBER
        # ---------------------------
        pol = self._get_block_value(["policy number", "policy no"])

        if pol:
            m = re.search(r"P\/[\d\/]+", pol)
            pol = m.group(0) if m else None

        data["policy_number"] = ConfidenceEngine.wrap_field(
            pol, "high" if pol else "missing", "policy_no"
        )

        # ---------------------------
        # POLICY PERIOD
        # ---------------------------
        period = re.search(
            r"(\d{2}/\d{2}/\d{4})\s*TO\s*(\d{2}/\d{2}/\d{4})",
            self.text
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
        def find_amount(label):

            capture = False

            for line in self.lines:

                l = line.lower()

                if label in l:
                    capture = True
                    continue

                if capture:

                    m = re.search(r"[\d,]+\.\d{2}", l)

                    if m:
                        return float(m.group(0).replace(",", ""))

                    if l:
                        return None

            return None

        net = find_amount("premium total")
        vat = find_amount("vat")
        total = find_amount("grand total")

        data["net_premium"] = ConfidenceEngine.wrap_field(
            net, "high" if net else "missing", "net"
        )

        data["vat_amount"] = ConfidenceEngine.wrap_field(
            vat, "high" if vat else "missing", "vat"
        )

        data["total"] = ConfidenceEngine.wrap_field(
            total, "high" if total else "missing", "total"
        )

        data["premium_currency"] = ConfidenceEngine.wrap_field(
            "AED", "high", "currency"
        )

        return data


NIAABUTaxInvoiceParser = NIATaxInvoiceV2Parser