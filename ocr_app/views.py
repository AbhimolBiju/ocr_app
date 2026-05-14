from django.shortcuts import render

from .services.azure_ocr import extract_text_from_pdf
from .services.doc_type import detect_document_type
from .services.layout_extractor import LayoutExtractor

import os
import json
from datetime import datetime

# ---------------------------------------------------
# DJANGO MODEL
# ---------------------------------------------------
from .models import Document

# ---------------------------------------------------
# CREDIT NOTE
# ---------------------------------------------------
from .services.parser.credit_note_parser import (
    parse_credit_note
)

from .services.validator.credit_note_validator import (
    validate_credit_note
)

# ---------------------------------------------------
# QIC
# ---------------------------------------------------
from .services.parser.tax_invoice_qic_parser import (
    QICTaxInvoiceParser
)

# ---------------------------------------------------
# DNI
# ---------------------------------------------------
from .services.parser.tax_invoice_dni_parser import (
    DNITaxInvoiceParser
)

from .services.validator.tax_invoice_qic_validator import (
    QICTaxInvoiceValidator
)

# ---------------------------------------------------
# ADAMJEE
# ---------------------------------------------------
from .services.parser.tax_invoice_adamjee_parser import (
    AdamjeeTaxInvoiceParser
)

# ---------------------------------------------------
# SHARJAH
# ---------------------------------------------------
from .services.parser.tax_invoice_sharjah_parser import (
    SharjahTaxInvoiceParser
)

# ---------------------------------------------------
# METHAQ
# ---------------------------------------------------
from .services.parser.tax_invoice_methaq_parser import (
    MethaqTaxInvoiceParser
)

# ---------------------------------------------------
# ARABIA
# ---------------------------------------------------
from .services.parser.tax_invoice_arabia_parser import (
    ArabiaTaxInvoiceParser
)

# ---------------------------------------------------
# RAK
# ---------------------------------------------------
from .services.parser.tax_invoice_rak_parser import (
    RAKTaxInvoiceParser
)

# ---------------------------------------------------
# NIA
# ---------------------------------------------------
from .services.parser.nia_router import (
    NIATaxInvoiceRouter
)

# ---------------------------------------------------
# ALLIANCE
# ---------------------------------------------------
from .services.parser.tax_invoice_alliance_parser import (
    AllianceTaxInvoiceParser
)

# ---------------------------------------------------
# WATANIA
# ---------------------------------------------------
from .services.parser.tax_invoice_watania_parser import (
    WataniaTaxInvoiceParser
)

# ---------------------------------------------------
# AL SAGR
# ---------------------------------------------------
from .services.parser.tax_invoice_alsagr_parser import (
    AlSagrTaxInvoiceParser
)

# ---------------------------------------------------
# FIDELITY
# ---------------------------------------------------
from .services.parser.tax_invoice_fidelity_parser import (
    parse_fidelity_debit_note
)


def upload_view(request):

    context = {
        "results": []
    }

    if request.method == "POST":

        files = request.FILES.getlist("files")

        if not files:

            context["error"] = "No files uploaded"

            return render(
                request,
                "upload.html",
                context
            )

        extractor = LayoutExtractor()

        for f in files:

            try:

                f.seek(0)

                # ---------------------------------------------------
                # OCR
                # ---------------------------------------------------
                ocr_result = extract_text_from_pdf(f)

                if isinstance(ocr_result, dict):

                    text = ocr_result.get("text", "")
                    confidence = ocr_result.get("confidence", 0)
                    tables = ocr_result.get("tables", [])

                else:

                    text = str(ocr_result)
                    confidence = 0
                    tables = []

                print("\n===== OCR TEXT START =====\n")
                print(text[:1500])
                print("\n===== OCR TEXT END =====\n")

                # ---------------------------------------------------
                # DOCUMENT TYPE
                # ---------------------------------------------------
                doc_type = detect_document_type(text)

                print(f"\nDetected Document Type: {doc_type}\n")

                parsed_data = {}
                errors = []

                # ---------------------------------------------------
                # FALLBACK
                # ---------------------------------------------------
                if (
                    doc_type == "unknown"
                    and "invoice" in text.lower()
                ):
                    doc_type = "tax_invoice_qic"

                # ---------------------------------------------------
                # CREDIT NOTE
                # ---------------------------------------------------
                if doc_type == "credit_note":

                    parsed_output = parse_credit_note(
                        text,
                        tables
                    )

                    if (
                        isinstance(parsed_output, dict)
                        and "data" in parsed_output
                    ):
                        parsed_data = parsed_output.get(
                            "data",
                            {}
                        )

                    else:
                        parsed_data = parsed_output

                    errors = validate_credit_note(
                        parsed_data
                    )

                # ---------------------------------------------------
                # FIDELITY
                # ---------------------------------------------------
                elif doc_type == "tax_invoice_fidelity":

                    parsed_output = (
                        parse_fidelity_debit_note(text)
                    )

                    if (
                        isinstance(parsed_output, dict)
                        and "data" in parsed_output
                    ):
                        parsed_data = parsed_output.get(
                            "data",
                            {}
                        )

                    else:
                        parsed_data = parsed_output

                    try:

                        validator = (
                            QICTaxInvoiceValidator(
                                parsed_data
                            )
                        )

                        validation = (
                            validator.validate()
                        )

                        errors = validation.get(
                            "errors",
                            []
                        )

                    except Exception as e:

                        print(
                            "Validation Error:",
                            e
                        )

                        errors = []

                # ---------------------------------------------------
                # TAX INVOICE FLOW
                # ---------------------------------------------------
                elif doc_type in [

                    "tax_invoice_qic",
                    "tax_invoice_dni",
                    "tax_invoice_adamjee",
                    "tax_invoice_sharjah",
                    "tax_invoice_methaq",
                    "tax_invoice_arabia",
                    "tax_invoice_rak",
                    "tax_invoice_nia",
                    "tax_invoice_alliance",
                    "tax_invoice_watania",
                    "tax_invoice_alsagr",
                    "invoice",

                ]:

                    f.seek(0)

                    layout_data = extractor.extract(f)

                    print("\n===== LAYOUT KEYS =====\n")
                    print(layout_data.keys())

                    # ---------------------------------------------------
                    # SELECT PARSER
                    # ---------------------------------------------------
                    if doc_type == "tax_invoice_qic":

                        parser = (
                            QICTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_dni":

                        parser = (
                            DNITaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_adamjee":

                        parser = (
                            AdamjeeTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_sharjah":

                        parser = (
                            SharjahTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_methaq":

                        parser = (
                            MethaqTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_arabia":

                        parser = (
                            ArabiaTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_rak":

                        parser = (
                            RAKTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_nia":

                        parser = (
                            NIATaxInvoiceRouter(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_alliance":

                        parser = (
                            AllianceTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_watania":

                        parser = (
                            WataniaTaxInvoiceParser(
                                layout_data
                            )
                        )

                    elif doc_type == "tax_invoice_alsagr":

                        parser = (
                            AlSagrTaxInvoiceParser(
                                layout_data
                            )
                        )

                    else:

                        parser = (
                            QICTaxInvoiceParser(
                                layout_data
                            )
                        )

                    # ---------------------------------------------------
                    # PARSE
                    # ---------------------------------------------------
                    parsed_output = parser.parse()

                    if (
                        isinstance(parsed_output, dict)
                        and "data" in parsed_output
                    ):
                        parsed_data = parsed_output.get(
                            "data",
                            {}
                        )

                    else:
                        parsed_data = parsed_output

                    # ---------------------------------------------------
                    # VALIDATION
                    # ---------------------------------------------------
                    try:

                        validator = (
                            QICTaxInvoiceValidator(
                                parsed_data
                            )
                        )

                        validation = (
                            validator.validate()
                        )

                        errors = validation.get(
                            "errors",
                            []
                        )

                    except Exception as e:

                        print(
                            "Validation Error:",
                            e
                        )

                        errors = []

                else:

                    errors.append(
                        "Unsupported or unknown document type"
                    )

                # ---------------------------------------------------
                # SAVE TO SQLITE DATABASE
                # ---------------------------------------------------
                try:

                    f.seek(0)

                    Document.objects.create(

                        file=f,

                        extracted_text=text,

                        parsed_data=parsed_data,

                        document_type=doc_type,

                        confidence_score=float(
                            parsed_data.get(
                                "confidence_score",
                                0
                            )
                        ),

                        is_valid=(
                            len(errors) == 0
                        ),

                        validation_errors=errors,

                        insurer_name=parsed_data.get(
                            "insurer_name"
                        ),

                        customer_name=parsed_data.get(
                            "customer_name"
                        ),

                        policy_number=parsed_data.get(
                            "policy_number"
                        ),

                        tax_invoice_number=parsed_data.get(
                            "tax_invoice_number"
                        ),

                        invoice_date=parsed_data.get(
                            "invoice_date"
                        ),
                    )

                    print(
                        f"Saved to DB: {f.name}"
                    )

                except Exception as db_error:

                    print(
                        "DB SAVE ERROR:",
                        db_error
                    )

            
                # ---------------------------------------------------
                # APPEND RESULT
                # ---------------------------------------------------
                context["results"].append({

                    "file": f.name,

                    "text": text[:1500],

                    "doc_type": doc_type,

                    "confidence": round(
                        confidence,
                        2
                    ),

                    "parsed": parsed_data,

                    "errors": errors

                })

            except Exception as e:

                context["results"].append({

                    "file": f.name,

                    "error": str(e)

                })

    return render(
        request,
        "upload.html",
        context
    )