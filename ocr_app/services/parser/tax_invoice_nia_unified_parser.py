import re

from ..confidence import ConfidenceEngine
from ..parsing_text_utils import (
    clean_customer_name,
    collapse_whitespace,
    normalize_date,
)
from ..structured_schema import finalize_tax_invoice_output


class NIATaxInvoiceUnifiedParser:

    def __init__(self, layout_data):

        raw = layout_data.get("full_text", "") or ""

        self.raw_text = raw

        self.text = re.sub(r"[ \t]+", " ", raw)
        self.upper = self.text.upper()

    # ---------------------------------------------------
    def _search(self, pattern, group=1, flags=re.IGNORECASE):

        m = re.search(pattern, self.raw_text, flags)

        if not m:
            return None

        try:
            return m.group(group).strip()
        except:
            return None

    # ---------------------------------------------------
    def _clean_value(self, value):

        if not value:
            return None

        value = collapse_whitespace(value)
        value = re.sub(r"[\|\[\]\{\}]", " ", value)

        return value.strip()

    # ---------------------------------------------------
    def _extract_amount(self, pattern):

        m = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)

        if not m:
            return None

        try:
            return float(m.group(1).replace(",", "").strip())
        except:
            return None

    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------------------------------
        # INSURER
        data["insurer_name"] = ConfidenceEngine.wrap_field(
            "NIA Insurance", "high", "insurer"
        )

        # ---------------------------------------------------
        # INVOICE NUMBER
        invoice_number = None

        for pattern in [
            r"Tax\s*Invoice\s*No\s*[:\-]?\s*([A-Z0-9\-\/]+)",
            r"Invoice\s*No\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        ]:
            invoice_number = self._search(pattern)

            if invoice_number:
                break

        invoice_number = self._clean_value(invoice_number)

        data["tax_invoice_number"] = ConfidenceEngine.wrap_field(
            invoice_number,
            "high" if invoice_number else "missing",
            "invoice_no"
        )

        # ---------------------------------------------------
        # CUSTOMER NAME
        customer = None

        for pattern in [
            r"Insured\s*[:\-]?\s*([^\n\r]+)",
            r"Name\s*[:\-]?\s*:?\s*([^\n\r]+)",
        ]:

            customer = self._search(pattern)

            if customer:
                break

        if not customer:

            lines = [
                l.strip()
                for l in self.raw_text.splitlines()
                if l.strip()
            ]

            for i, line in enumerate(lines):

                if re.search(r"\bInsured\b", line, re.IGNORECASE):

                    for j in range(i + 1, min(i + 6, len(lines))):

                        candidate = lines[j]

                        if re.search(
                            r"(TRN|Account|Broker|Policy|Invoice|Date|P\.O|P\.BOX|Code)",
                            candidate,
                            re.IGNORECASE
                        ):
                            continue

                        if re.fullmatch(r"[\d\W]+", candidate):
                            continue

                        if len(candidate) < 4:
                            continue

                        customer = candidate
                        break

                if customer:
                    break

        if customer:

            customer = self._clean_value(customer)

            customer = re.split(
                r"(Address|Tax\s*Invoice|Policy|TRN|Account|Broker)",
                customer,
                flags=re.IGNORECASE
            )[0].strip()

            customer = clean_customer_name(customer)

            customer = re.sub(
                r"[\u0600-\u06FF]+",
                "",
                customer
            ).strip()

            if len(customer) < 3:
                customer = None

        data["customer_name"] = ConfidenceEngine.wrap_field(
            customer,
            "high" if customer else "missing",
            "customer"
        )

        # ---------------------------------------------------
        # BROKER (FIXED OCR MULTI-LINE EXTRACTION)
        broker = None

        broker_block_match = re.search(
            r"Code\s*.*?(?:\n|\r\n?)+.*?:\s*(.*?)\s*NIA\s*TRN",
            self.raw_text,
            re.IGNORECASE | re.DOTALL
        )

        if broker_block_match:

            broker_text = broker_block_match.group(1)

            broker_text = broker_text.replace("\n", " ")
            broker_text = broker_text.replace("\r", " ")

            broker_text = collapse_whitespace(broker_text)

            # remove code numbers
            broker_text = re.sub(
                r"^\d+\-?",
                "",
                broker_text
            )

            # remove bracket ids
            broker_text = re.sub(
                r"\(\d+\)",
                "",
                broker_text
            )

            # remove OCR junk words
            broker_text = re.sub(
                r"\bONLINE\b",
                "",
                broker_text,
                flags=re.I
            )

            broker_text = re.sub(
                r"\bMOTOR\b",
                "",
                broker_text,
                flags=re.I
            )

            broker_text = collapse_whitespace(
                broker_text
            ).strip(" -:")

            if "PROMISE" in broker_text.upper():
                broker = "PROMISE INSURANCE SERVICES LLC"
            else:
                broker = broker_text

        # fallback
        if not broker:

            m = re.search(
                r"Broker\s*[:\-]?\s*(.+)",
                self.raw_text,
                re.IGNORECASE
            )

            if m:
                broker = m.group(1).strip()

        if broker:

            broker = self._clean_value(broker)

            if re.fullmatch(r"[\u0600-\u06FF\s]+", broker):
                broker = None

        data["broker_name"] = ConfidenceEngine.wrap_field(
            broker,
            "high" if broker else "missing",
            "broker"
        )

        data["is_promise_broker"] = ConfidenceEngine.wrap_field(
            bool(broker and "PROMISE" in broker.upper()),
            "high" if broker else "low",
            "promise"
        )

        # ---------------------------------------------------
        # POLICY NUMBER
        policy_number = None

        m = re.search(
            r"Policy\s*(?:No|Number)\s*[:\-]?\s*([A-Z0-9\/\-]+)",
            self.raw_text,
            re.IGNORECASE
        )

        if m:

            candidate = m.group(1).strip()

            if len(candidate) >= 6:
                policy_number = candidate

        if not policy_number:

            lines = [
                l.strip()
                for l in self.raw_text.splitlines()
                if l.strip()
            ]

            for i, line in enumerate(lines):

                if re.search(r"Policy\s*(No|Number)", line, re.I):

                    for j in range(i + 1, min(i + 8, len(lines))):

                        candidate = re.sub(
                            r"^[:\-\s]+",
                            "",
                            lines[j].strip()
                        )

                        if re.fullmatch(
                            r"[A-Z0-9]+[\/\-][A-Z0-9\/\-]+",
                            candidate
                        ):
                            policy_number = candidate
                            break

                if policy_number:
                    break

        if policy_number:

            policy_number = re.sub(
                r"[^A-Z0-9\/\-]",
                "",
                policy_number
            )

            if len(policy_number) < 6:
                policy_number = None

        data["policy_number"] = ConfidenceEngine.wrap_field(
            policy_number,
            "high" if policy_number else "missing",
            "policy_no"
        )

        # ---------------------------------------------------
        # POLICY TYPE
        policy_type = None

        lines = [
            l.strip()
            for l in self.raw_text.splitlines()
            if l.strip()
        ]

        for i, line in enumerate(lines):

            if re.search(r"Policy\s*Type", line, re.I):

                for j in range(i, min(i + 5, len(lines))):

                    txt = lines[j].strip()

                    if ":" in txt:

                        after_colon = txt.split(":", 1)[1].strip()

                        if re.search(
                            r"(MOTOR|COMPREHENSIVE|TPL|THIRD|FIRE|LIFE)",
                            after_colon,
                            re.I
                        ):
                            policy_type = after_colon
                            break

                    if re.fullmatch(
                        r"[A-Z\s&]+",
                        txt
                    ) and re.search(
                        r"(MOTOR|COMPREHENSIVE|TPL|THIRD|FIRE|LIFE)",
                        txt,
                        re.I
                    ):
                        policy_type = txt
                        break

                if policy_type:
                    policy_type = collapse_whitespace(policy_type)
                    policy_type = re.sub(
                        r"^[:\-\s]+",
                        "",
                        policy_type
                    ).strip()

                break

        data["policy_type"] = ConfidenceEngine.wrap_field(
            policy_type,
            "high" if policy_type else "missing",
            "policy_type"
        )

        # ---------------------------------------------------
        # POLICY PERIOD
        start_date = None
        end_date = None

        period_match = re.search(
            r"(Policy\s*Period|Period\s*of\s*Insurance)\s*[:\-]?\s*"
            r"([0-9]{1,2}[\/\-][A-Za-z0-9]{1,}[\/\-][0-9]{2,4})\s*(?:to|TO|-)\s*"
            r"([0-9]{1,2}[\/\-][A-Za-z0-9]{1,}[\/\-][0-9]{2,4})",
            self.text,
            re.IGNORECASE
        )

        if period_match:

            start_date = normalize_date(period_match.group(2))
            end_date = normalize_date(period_match.group(3))

        data["policy_start_date"] = ConfidenceEngine.wrap_field(
            start_date,
            "high" if start_date else "missing",
            "start"
        )

        data["policy_end_date"] = ConfidenceEngine.wrap_field(
            end_date,
            "high" if end_date else "missing",
            "end"
        )

        # ---------------------------------------------------
        # INVOICE DATE
        invoice_date = None

        for pattern in [
            r"Invoice\s*Date\s*[:\-]?\s*([A-Z0-9\-\/]+)",
            r"Date\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        ]:

            val = self._search(pattern)

            if val:
                invoice_date = normalize_date(val)
                break

        if not invoice_date:
            invoice_date = start_date

        data["invoice_date"] = ConfidenceEngine.wrap_field(
            invoice_date,
            "high" if invoice_date else "missing",
            "invoice_date"
        )

        # ---------------------------------------------------
        # AMOUNTS
        net_premium = self._extract_amount(
            r"Taxable\s*Amount\(AED\).*?([\d,]+\.\d{2})"
        )

        vat_amount = self._extract_amount(
            r"VAT\s*Amount\(AED\).*?([\d,]+\.\d{2})"
        )

        total = self._extract_amount(
            r"Total\(AED\).*?([\d,]+\.\d{2})"
        )

        if total is None:

            amounts = re.findall(
                r"([\d,]+\.\d{2})",
                self.text
            )

            cleaned = []

            for a in amounts:

                try:
                    cleaned.append(
                        float(a.replace(",", ""))
                    )
                except:
                    pass

            if len(cleaned) >= 3:

                net_premium = cleaned[-3]
                vat_amount = cleaned[-2]
                total = cleaned[-1]

        data["net_premium"] = ConfidenceEngine.wrap_field(
            net_premium,
            "high" if net_premium else "missing",
            "net"
        )

        data["vat_amount"] = ConfidenceEngine.wrap_field(
            vat_amount,
            "high" if vat_amount else "missing",
            "vat"
        )

        data["total"] = ConfidenceEngine.wrap_field(
            total,
            "high" if total else "missing",
            "total"
        )

        data["total_premium"] = data["total"]
        data["net_due"] = data["total"]

        data["premium_currency"] = ConfidenceEngine.wrap_field(
            "AED",
            "high",
            "currency"
        )

        return finalize_tax_invoice_output(data)


class NIATaxInvoiceLegacyParser(NIATaxInvoiceUnifiedParser):
    pass


class NIATaxInvoiceV2Parser(NIATaxInvoiceUnifiedParser):
    pass