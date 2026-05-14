import re

from ..structured_schema import finalize_tax_invoice_output


class SharjahTaxInvoiceParser:

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
        data["insurer_name"] = "Sharjah Insurance"

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        invoice_date = self._extract(
            r"(\d{2}/\d{2}/\d{4})"
        )

        data["invoice_date"] = invoice_date

        # ---------------------------------------------------
        # CUSTOMER NAME
        # ---------------------------------------------------
        customer_name = self._extract(
            r"Assured\s*Name\s*:?\s*([^\n\r]+)"
        )

        if customer_name:

            customer_name = (
                customer_name
                .replace(":", "")
                .replace("\n", " ")
                .strip()
            )

            # remove arabic
            customer_name = re.sub(
                r"[\u0600-\u06FF]+",
                "",
                customer_name
            )

            customer_name = " ".join(
                customer_name.split()
            )

        data["customer_name"] = customer_name

        # ---------------------------------------------------
        # BROKER NAME
        # ---------------------------------------------------
        broker_name = self._extract(
            r"Account\s*Name\s*:?\s*([^\n\r]+)"
        )

        if broker_name:

            broker_name = (
                broker_name
                .replace(":", "")
                .replace("\n", " ")
                .strip()
            )

            broker_name = " ".join(
                broker_name.split()
            )

        data["broker_name"] = broker_name

        # ---------------------------------------------------
        # PROMISE CHECK
        # ---------------------------------------------------
        data["is_promise_broker"] = False

        if broker_name:

            if "promise insurance" in broker_name.lower():

                data["is_promise_broker"] = True

        # ---------------------------------------------------
        # BRANCH
        # ---------------------------------------------------
        branch = self._extract(
            r"Branch\s*:?\s*([^\n\r]+)"
        )

        if branch:

            branch = (
                branch
                .replace(":", "")
                .replace("\n", " ")
                .strip()
            )

            # remove arabic OCR
            branch = branch.split("مكتب")[0].strip()

            branch = " ".join(
                branch.split()
            )

        data["branch"] = branch

        # ---------------------------------------------------
        # POLICY TYPE
        # ---------------------------------------------------
        policy_type = self._extract(
            r"Policy\s*Type\s*:?\s*([^\n\r]+)"
        )

        if policy_type:

            policy_type = (
                policy_type
                .replace(":", "")
                .replace("\n", " ")
                .strip()
            )

            policy_type = " ".join(
                policy_type.split()
            )

        data["policy_type"] = policy_type

        # ---------------------------------------------------
        # TAX INVOICE NUMBER
        # ---------------------------------------------------
        tax_invoice = self._extract(
            r"(\d{4}-\d{2}-\d+)"
        )

        data["tax_invoice_number"] = tax_invoice

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        data["policy_number"] = (
            self._extract_policy_number()
        )

        # ---------------------------------------------------
        # POLICY PERIOD
        # ---------------------------------------------------
        data["policy_start_date"] = None
        data["policy_end_date"] = None

        period_match = re.search(
            r"(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})",
            self.text,
            re.IGNORECASE
        )

        if period_match:

            data["policy_start_date"] = (
                period_match.group(1).strip()
            )

            data["policy_end_date"] = (
                period_match.group(2).strip()
            )

        # ---------------------------------------------------
        # CURRENCY
        # ---------------------------------------------------
        data["premium_currency"] = "AED"

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        data["premium_amount"] = amounts.get(
            "premium_amount"
        )

        data["net_premium"] = amounts.get(
            "net_premium"
        )

        data["total_premium"] = amounts.get(
            "total_premium"
        )

        data["vat_amount"] = amounts.get(
            "vat_amount"
        )

        data["net_due"] = amounts.get(
            "net_due"
        )

        data["total"] = amounts.get(
            "total"
        )

        # ---------------------------------------------------
        # EXTRA
        # ---------------------------------------------------
        data["invoice_date_calc"] = invoice_date
        data["due_date"] = invoice_date
        data["field_confidence"] = {
            "tax_invoice_number": self._confidence_with_label(
                data["tax_invoice_number"],
                [r"Tax\s*Invoice", r"\d{4}-\d{2}-\d+"],
            ),
            "invoice_date": self._confidence_with_label(
                data["invoice_date"],
                [r"\bDate\b"],
            ),
            "customer_name": self._confidence_with_label(
                data["customer_name"],
                [r"Assured\s*Name"],
            ),
            "broker_name": self._confidence_with_label(
                data["broker_name"],
                [r"Account\s*Name"],
            ),
            "policy_number": self._confidence_with_label(
                data["policy_number"],
                [r"Policy\s*No"],
            ),
            "policy_type": self._confidence_with_label(
                data["policy_type"],
                [r"Policy\s*Type"],
            ),
            "policy_start_date": self._confidence_with_label(
                data["policy_start_date"],
                [r"to"],
            ),
            "policy_end_date": self._confidence_with_label(
                data["policy_end_date"],
                [r"to"],
            ),
            "net_premium": self._confidence_with_label(
                data["net_premium"],
                [r"TOTAL"],
            ),
            "vat_amount": self._confidence_with_label(
                data["vat_amount"],
                [r"VAT"],
            ),
            "total": self._confidence_with_label(
                data["total"],
                [r"TOTAL"],
            ),
        }

        return finalize_tax_invoice_output(data)

    # ---------------------------------------------------
    # POLICY NUMBER EXTRACTOR
    # ---------------------------------------------------
    def _extract_policy_number(self):

        match = re.search(
            r"Policy\s*No\.?\s*:?\s*([A-Z0-9\/\-]+)",
            self.text,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            if value != "-":
                return value

        # OCR multiline fallback
        lines = self.text.splitlines()

        for i, line in enumerate(lines):

            if "policy no" in line.lower():

                for j in range(
                    i + 1,
                    min(i + 4, len(lines))
                ):

                    candidate = (
                        lines[j].strip()
                    )

                    if re.match(
                        r"^[A-Z0-9\/\-]+$",
                        candidate
                    ):

                        if "/" in candidate:

                            return candidate

        return None

    # ---------------------------------------------------
    # AMOUNTS
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {

            "premium_amount": None,
            "net_premium": None,
            "total_premium": None,
            "vat_amount": None,
            "net_due": None,
            "total": None,
        }

        # ---------------------------------------------------
        # TOTAL AMOUNT
        # ---------------------------------------------------
        total_match = re.search(
            r"TOTAL.*?([\d,]+\.\d{2})",
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        total = None

        if total_match:

            total = self._to_float(
                total_match.group(1)
            )

            result["premium_amount"] = total
            result["total_premium"] = total
            result["net_due"] = total
            result["total"] = total

        # ---------------------------------------------------
        # VAT + NET PREMIUM
        # ---------------------------------------------------
        if total:

            vat = round(total * 5 / 105, 2)

            net = round(total - vat, 2)

            result["vat_amount"] = vat
            result["net_premium"] = net

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
            return match.group(1).strip()

        return None

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

    def _label_present(self, patterns):

        for pattern in patterns:
            if re.search(pattern, self.text, re.IGNORECASE):
                return True
        return False

    def _confidence_with_label(self, value, label_patterns):

        if value in (None, "", []):
            return 12

        score = 74
        if self._label_present(label_patterns):
            score += 18

        return min(96, score)