from django.db import models


class Document(models.Model):

    # ---------------------------------------------------
    # DOCUMENT TYPE CHOICES
    # ---------------------------------------------------
    DOCUMENT_TYPES = [

        ("credit_note", "Credit Note"),

        ("tax_invoice_qic", "Tax Invoice - QIC"),

        ("tax_invoice_dni", "Tax Invoice - DNI"),

        ("tax_invoice_adamjee", "Tax Invoice - Adamjee"),

        ("tax_invoice_sharjah", "Tax Invoice - Sharjah"),

        ("tax_invoice_methaq", "Tax Invoice - Methaq"),

        ("tax_invoice_arabia", "Tax Invoice - Arabia"),

        ("tax_invoice_rak", "Tax Invoice - RAK"),

        ("tax_invoice_nia", "Tax Invoice - NIA"),

        ("tax_invoice_alliance", "Tax Invoice - Alliance"),

        ("tax_invoice_watania", "Tax Invoice - Watania"),

        ("tax_invoice_alsagr", "Tax Invoice - Al Sagr"),

        ("tax_invoice_fidelity", "Tax Invoice - Fidelity"),

        ("invoice", "Generic Invoice"),

        ("unknown", "Unknown"),

    ]

    # ---------------------------------------------------
    # FILE INFO
    # ---------------------------------------------------
    file = models.FileField(
        upload_to="documents/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    # ---------------------------------------------------
    # OCR OUTPUT
    # ---------------------------------------------------
    extracted_text = models.TextField(
        null=True,
        blank=True
    )

    # ---------------------------------------------------
    # PARSED JSON
    # ---------------------------------------------------
    parsed_data = models.JSONField(
        null=True,
        blank=True
    )

    # ---------------------------------------------------
    # DOCUMENT TYPE
    # ---------------------------------------------------
    document_type = models.CharField(
        max_length=100,
        choices=DOCUMENT_TYPES,
        default="unknown"
    )

    # ---------------------------------------------------
    # CONFIDENCE SCORE
    # ---------------------------------------------------
    confidence_score = models.FloatField(
        null=True,
        blank=True
    )

    # ---------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------
    is_valid = models.BooleanField(
        default=False
    )

    # ---------------------------------------------------
    # VALIDATION ERRORS
    # ---------------------------------------------------
    validation_errors = models.JSONField(
        null=True,
        blank=True
    )

    # ---------------------------------------------------
    # METADATA
    # ---------------------------------------------------
    insurer_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    customer_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    policy_number = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    tax_invoice_number = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    invoice_date = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    # ---------------------------------------------------
    # STRING REPRESENTATION
    # ---------------------------------------------------
    def __str__(self):

        return (
            f"{self.file.name} "
            f"({self.document_type})"
        )