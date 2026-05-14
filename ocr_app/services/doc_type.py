import re


def detect_document_type(text):

    # ---------------------------------------------------
    # SAFE LOWER TEXT
    # ---------------------------------------------------
    text = text or ""

    text_lower = text.lower()

    # ---------------------------------------------------
    # NORMALIZED OCR TEXT
    # ---------------------------------------------------
    normalized = re.sub(
        r"\s+",
        " ",
        text_lower
    )

    # ---------------------------------------------------
    # CREDIT NOTE
    # ---------------------------------------------------
    if "credit note" in normalized:
        return "credit_note"

    # ---------------------------------------------------
    # DNI (KEEP BEFORE QIC)
    # ---------------------------------------------------
    if (
        "dubai national insurance" in normalized
        or re.search(r"\bdni\b", normalized)
    ):
        return "tax_invoice_dni"

    # ---------------------------------------------------
    # WATANIA (KEEP BEFORE RAK)
    # ---------------------------------------------------
    # IMPORTANT:
    # Watania documents contain DN- patterns
    # which were incorrectly routing to RAK.
    # ---------------------------------------------------
    if (
        "watania takaful" in normalized
        or "watania takaful general" in normalized
        or "watania takaful general pjsc" in normalized
        or "800 watania" in normalized
        or "national takaful company" in normalized
    ):
        return "tax_invoice_watania"

    # ---------------------------------------------------
    # QIC
    # ---------------------------------------------------
    if (
        (
            "tax invoice" in normalized
            or "debit note" in normalized
        )
        and (
            "qic" in normalized
            or "qatar insurance" in normalized
        )
    ):
        return "tax_invoice_qic"

    # ---------------------------------------------------
    # ADAMJEE
    # ---------------------------------------------------
    if (
        (
            "debit note" in normalized
            or "tax invoice" in normalized
        )
        and "adamjee" in normalized
    ):
        return "tax_invoice_adamjee"

    # ---------------------------------------------------
    # FIDELITY UNITED
    # ---------------------------------------------------
    if (
        (
            "debit note" in normalized
            or "tax invoice" in normalized
        )
        and (
            "fidelity united" in normalized
            or "fidelity" in normalized
        )
    ):
        return "tax_invoice_fidelity"

    # ---------------------------------------------------
    # SHARJAH INSURANCE
    # ---------------------------------------------------
    if (
        (
            "debit note" in normalized
            or "tax invoice" in normalized
        )
        and "sharjah insurance" in normalized
    ):
        return "tax_invoice_sharjah"

    # ---------------------------------------------------
    # METHAQ
    # ---------------------------------------------------
    if (
        (
            "debit note" in normalized
            or "tax invoice" in normalized
        )
        and (
            "methaq" in normalized
            or "methaq takaful" in normalized
        )
    ):
        return "tax_invoice_methaq"

    # ---------------------------------------------------
    # ARABIA INSURANCE
    # ---------------------------------------------------
    if (
        (
            "tax invoice" in normalized
            or "debit" in normalized
        )
        and (
            "arabia insurance" in normalized
            or "arabia insurance co" in normalized
        )
    ):
        return "tax_invoice_arabia"

    # ---------------------------------------------------
    # RAK INSURANCE
    # ---------------------------------------------------
    # IMPORTANT:
    # Removed generic "dn-" match because
    # Watania also uses DN- document numbers.
    # ---------------------------------------------------
    if (
        "rak insurance" in normalized
        or "rakinsurance" in normalized
        or "rak vinyl" in normalized
        or "ras al khaimah national insurance" in normalized
    ):
        return "tax_invoice_rak"

    # ---------------------------------------------------
    # NIA
    # ---------------------------------------------------
    if (
        "new india assurance" in normalized
        or "the new india assurance" in normalized
        or "nia trn" in normalized
    ):
        return "tax_invoice_nia"

    # ---------------------------------------------------
    # ALLIANCE INSURANCE
    # ---------------------------------------------------
    if (
        "alliance insurance" in normalized
        or "alliance insurance psc" in normalized
        or "motordepartment" in normalized
        or "vehicle details" in normalized
    ):
        return "tax_invoice_alliance"

    # ---------------------------------------------------
    # AL SAGR
    # ---------------------------------------------------
    if (
        "al sagr" in normalized
        or "alsagr" in normalized
        or "al sagr national insurance" in normalized
    ):
        return "tax_invoice_alsagr"

    # ---------------------------------------------------
    # GENERIC TAX INVOICE
    # ---------------------------------------------------
    if "tax invoice" in normalized:
        return "tax_invoice"

    # ---------------------------------------------------
    # GENERIC DEBIT NOTE
    # ---------------------------------------------------
    if "debit note" in normalized:
        return "debit_note"

    # ---------------------------------------------------
    # GENERIC INVOICE
    # ---------------------------------------------------
    if "invoice" in normalized:
        return "invoice"

    # ---------------------------------------------------
    # POLICY
    # ---------------------------------------------------
    if "policy" in normalized:
        return "insurance_policy"

    # ---------------------------------------------------
    # INSURANCE FALLBACK
    # ---------------------------------------------------
    insurance_keywords = (

        "insurance",
        "policy",
        "premium",
        "insured",
        "broker",

    )

    if any(k in normalized for k in insurance_keywords):
        return "invoice"

    # ---------------------------------------------------
    # UNKNOWN
    # ---------------------------------------------------
    return "unknown"