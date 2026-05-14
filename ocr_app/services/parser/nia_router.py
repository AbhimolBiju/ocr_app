import re

from .tax_invoice_nia_unified_parser import NIATaxInvoiceUnifiedParser
from .tax_invoice_dni_parser import DNITaxInvoiceParser


class NIATaxInvoiceRouter:

    def __init__(self, layout_data):

        self.layout_data = layout_data

        self.text = layout_data.get("full_text", "") or ""
        self.upper_text = self.text.upper()

    # ---------------------------------------------------
    # MAIN ROUTER
    # ---------------------------------------------------
    def parse(self):

        u = self.upper_text
        c = re.sub(r"\s+", "", u)

        # ---------------------------------------------------
        # 1. DNI (HIGHEST PRIORITY)
        # ---------------------------------------------------
        if any(x in u for x in [
            "DUBAI NATIONAL INSURANCE",
            "DNI PJSC",
            "DNI",
        ]):

            print("\n[ROUTER] DNI Parser Selected\n")

            return DNITaxInvoiceParser(self.layout_data).parse()

        # ---------------------------------------------------
        # 2. EVERYTHING ELSE = NIA UNIFIED
        # ---------------------------------------------------
        nia_signals = [
            "THE NEW INDIA ASSURANCE",
            "NEW INDIA ASSURANCE",
            "INSURED",
            "BROKER",
            "TRN NO",
        ]

        is_nia = any(sig in u for sig in nia_signals)

        if is_nia:

            print("\n[ROUTER] NIA Unified Parser Selected\n")

            return NIATaxInvoiceUnifiedParser(self.layout_data).parse()

        # ---------------------------------------------------
        # 3. FALLBACK (SAFETY NET)
        # ---------------------------------------------------
        print("\n[ROUTER] Default NIA Unified Fallback\n")

        return NIATaxInvoiceUnifiedParser(self.layout_data).parse()