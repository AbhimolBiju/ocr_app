import re

from ..unified_tax_output import (
    unify_parsed_tax_invoice
)


class WataniaTaxInvoiceParser:

    def __init__(self, layout_data):

        self.text = layout_data.get(
            "full_text",
            ""
        )

        self.lines = self.text.split("\n")

    # ---------------------------------------------------
    # MAIN PARSER
    # ---------------------------------------------------
    def parse(self):

        data = {}

        # ---------------------------------------------------
        # INSURER
        # ---------------------------------------------------
        data["insurer_name"] = (
            "Watania Takaful"
        )

        # ---------------------------------------------------
        # TAX INVOICE NUMBER
        # ---------------------------------------------------
        data["tax_invoice_number"] = (
            self._extract_tax_invoice_number()
        )

        # ---------------------------------------------------
        # INVOICE DATE
        # ---------------------------------------------------
        data["invoice_date"] = (
            self._extract_invoice_date()
        )

        # ---------------------------------------------------
        # CUSTOMER NAME
        # ---------------------------------------------------
        data["customer_name"] = (
            self._extract_customer_name()
        )

        # ---------------------------------------------------
        # BROKER NAME
        # ---------------------------------------------------
        data["broker_name"] = (
            self._extract_broker_name()
        )

        broker_text = (
            data["broker_name"] or ""
        ).upper()

        data["is_promise_broker"] = (
            "PROMISE INSURANCE" in broker_text
        )

        # ---------------------------------------------------
        # POLICY NUMBER
        # ---------------------------------------------------
        data["policy_number"] = (
            self._extract_policy_number()
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
        start_date, end_date = (
            self._extract_policy_period()
        )

        data["policy_start_date"] = (
            start_date
        )

        data["policy_end_date"] = (
            end_date
        )

        # ---------------------------------------------------
        # CURRENCY
        # ---------------------------------------------------
        data["premium_currency"] = (
            "AED"
        )

        # ---------------------------------------------------
        # AMOUNTS
        # ---------------------------------------------------
        amounts = self._extract_amounts()

        data["net_premium"] = (
            amounts.get("net_premium")
        )

        data["vat_amount"] = (
            amounts.get("vat_amount")
        )

        data["total"] = (
            amounts.get("total")
        )

        data["total_premium"] = (
            amounts.get("total")
        )

        data["net_due"] = (
            amounts.get("total")
        )

        # ---------------------------------------------------
        # FIELD CONFIDENCE
        # ---------------------------------------------------
        data["field_confidence"] = {

            "tax_invoice_number":
                self._confidence_with_label(
                    data["tax_invoice_number"],
                    [
                        r"Document\s+No",
                        r"Original\s+Tax\s+Invoice\s+No",
                    ]
                ),

            "invoice_date":
                self._confidence_with_label(
                    data["invoice_date"],
                    [
                        r"Invoice\s+Date",
                    ]
                ),

            "customer_name":
                self._confidence_with_label(
                    data["customer_name"],
                    [
                        r"Client\s+Name",
                    ]
                ),

            "broker_name":
                self._confidence_with_label(
                    data["broker_name"],
                    [
                        r"Broker\s+Name",
                    ]
                ),

            "policy_number":
                self._confidence_with_label(
                    data["policy_number"],
                    [
                        r"Takaful\s+Certificate",
                    ]
                ),

            "policy_type":
                self._confidence_with_label(
                    data["policy_type"],
                    [
                        r"Takaful\s+Certificate\s+Type",
                    ]
                ),

            "policy_start_date":
                self._confidence_with_label(
                    data["policy_start_date"],
                    [
                        r"period\s+of",
                        r"Policy\s+Period",
                    ]
                ),

            "policy_end_date":
                self._confidence_with_label(
                    data["policy_end_date"],
                    [
                        r"period\s+of",
                        r"Policy\s+Period",
                    ]
                ),

            "net_premium":
                self._confidence_with_label(
                    data["net_premium"],
                    [
                        r"Total\s+Commission",
                        r"Commission\s+Amount\s+Due",
                        r"Total\s+Contribution",
                    ]
                ),

            "vat_amount":
                self._confidence_with_label(
                    data["vat_amount"],
                    [
                        r"VAT\s*5%",
                    ]
                ),

            "total":
                self._confidence_with_label(
                    data["total"],
                    [
                        r"Grand\s+Total",
                        r"Total\s+Amount\s+Payable",
                        r"Total\s+[\\d,]+\\.\\d+\\s+AED",
                    ]
                ),
        }

        return unify_parsed_tax_invoice(
            data
        )

    # ---------------------------------------------------
    # TAX INVOICE NUMBER
    # ---------------------------------------------------
    def _extract_tax_invoice_number(self):

        patterns = [

            r"Document\s+No\.\s*:\s*([A-Z0-9\-]+)",

            r"Original\s+Tax\s+Invoice\s+No\.\s*:\s*([A-Z0-9\-]+)",

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
                    .strip()
                )

                if len(value) >= 5:
                    return value

        return None

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    def _extract_invoice_date(self):

        match = re.search(
            r"Invoice\s+Date\s*:\s*(\d{2}/\d{2}/\d{4})",
            self.text,
            re.IGNORECASE
        )

        if match:

            return (
                match.group(1)
                .strip()
            )

        return None

    # ---------------------------------------------------
    # CUSTOMER NAME
    # ---------------------------------------------------
    def _extract_customer_name(self):

        patterns = [

            r"Client\s+Name\s*:\s*([^\n\r]+)",

            r"Original\s+Assured\s*:\s*[A-Z0-9\-]+\s+([A-Z\s]+)",

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
                    .strip()
                )

                value = re.sub(
                    r"\s+",
                    " ",
                    value
                )

                invalid = [

                    "AED",
                    "UAE",
                    "NULL",
                    "NIL",

                ]

                if (
                    value
                    and value.upper() not in invalid
                    and len(value) > 3
                ):

                    return value

        return None

    # ---------------------------------------------------
    # BROKER NAME
    # ---------------------------------------------------
    def _extract_broker_name(self):

        match = re.search(
            r"Broker\s+Name\s*:\s*([^\n\r]+)",
            self.text,
            re.IGNORECASE
        )

        if match:

            value = (
                match.group(1)
                .strip()
            )

            value = value.split("(")[0]

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            return value.strip()

        return None

    # ---------------------------------------------------
    # POLICY NUMBER
    # ---------------------------------------------------
    def _extract_policy_number(self):

        patterns = [

            r"in\s+respect\s+of\s+our\s+Takaful\s+Certificate\s+([A-Z0-9]+)",

            r"Takaful\s+Certificate\s+([A-Z0-9]+)",

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
                    .strip()
                )

                if len(value) >= 6:
                    return value

        return None

    # ---------------------------------------------------
    # POLICY TYPE
    # ---------------------------------------------------
    def _extract_policy_type(self):

        match = re.search(
            r"Takaful\s+Certificate\s+Type\s*:\s*([^\n\r]+)",
            self.text,
            re.IGNORECASE
        )

        if match:

            value = (
                match.group(1)
                .strip()
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            return value

        if "mumtaz" in self.text.lower():

            return "Mumtaz (2.0)"

        return None

    # ---------------------------------------------------
    # POLICY PERIOD
    # ---------------------------------------------------
    def _extract_policy_period(self):

        text = re.sub(
            r"\s+",
            " ",
            self.text
        )

        patterns = [

            r"for\s+the\s+period\s+of\s+"
            r"(\d{2}/\d{2}/\d{4})\s+to\s+"
            r"(\d{2}/\d{2}/\d{4})",

            r"period\s+of\s+insurance.*?"
            r"(\d{2}/\d{2}/\d{4}).*?"
            r"(\d{2}/\d{2}/\d{4})",

            r"policy\s+period.*?"
            r"(\d{2}/\d{2}/\d{4}).*?"
            r"(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            if match:

                start_date = (
                    match.group(1).strip()
                )

                end_date = (
                    match.group(2).strip()
                )

                return (
                    start_date,
                    end_date
                )

        return None, None

    # ---------------------------------------------------
    # AMOUNT EXTRACTION (FIXED)
    # ---------------------------------------------------
    def _extract_amounts(self):

        result = {

            "net_premium": None,
            "vat_amount": None,
            "total": None,

        }

        text = re.sub(
            r"\s+",
            " ",
            self.text
        )

        # ---------------------------------------------------
        # NET PREMIUM
        # ---------------------------------------------------
        patterns = [

            r"Total\s+Commission\s*:?\s*([\d,]+\.\d+)",

            r"Commission\s+Amount\s+Due\s*:?\s*([\d,]+\.\d+)",

            r"Total\s+Contribution\s*:?\s*([\d,]+\.\d+)",

            r"Contribution\s+Amount\s*:?\s*([\d,]+\.\d+)",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                try:

                    result["net_premium"] = float(
                        match.group(1).replace(",", "")
                    )

                    break

                except:
                    pass

        # ---------------------------------------------------
        # VAT
        # ---------------------------------------------------
        vat_patterns = [

            r"VAT\s*5%\s*:?\s*([\d,]+\.\d+)",

            r"VAT\s*5%.*?([\d,]+\.\d+)",

        ]

        for pattern in vat_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE | re.DOTALL
            )

            if match:

                try:

                    result["vat_amount"] = float(
                        match.group(1).replace(",", "")
                    )

                    break

                except:
                    pass

        # ---------------------------------------------------
        # TOTAL (FIXED)
        # ---------------------------------------------------
        total_patterns = [

            r"Total\s+([\d,]+\.\d+)\s*AED",

            r"Grand\s+Total\s+([\d,]+\.\d+)",

            r"Total\s+Amount\s+Payable\s*([\d,]+\.\d+)",

        ]

        for pattern in total_patterns:

            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE
            )

            if matches:

                try:

                    values = [
                        float(x.replace(",", ""))
                        for x in matches
                    ]

                    result["total"] = max(values)

                    break

                except:
                    pass

        # ---------------------------------------------------
        # FINAL FALLBACK
        # ---------------------------------------------------
        if (
            result["total"] is None
            and result["net_premium"] is not None
            and result["vat_amount"] is not None
        ):

            result["total"] = round(

                result["net_premium"]
                + result["vat_amount"],

                2
            )

        return result

    # ---------------------------------------------------
    # CONFIDENCE
    # ---------------------------------------------------
    def _label_present(self, patterns):

        for pattern in patterns:

            if re.search(
                pattern,
                self.text,
                re.IGNORECASE
            ):

                return True

        return False

    def _confidence_with_label(
        self,
        value,
        label_patterns
    ):

        if value in (
            None,
            "",
            []
        ):

            return 12

        score = 72

        if self._label_present(
            label_patterns
        ):

            score += 20

        return min(
            96,
            score
        )