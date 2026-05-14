from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings


class LayoutExtractor:
    def __init__(self):
        self.client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_KEY)
        )

    # ----------------------------------------
    # MAIN EXTRACT FUNCTION
    # Supports:
    # - Django UploadedFile
    # - File path (optional)
    # ----------------------------------------
    def extract(self, file_input):
        try:
            # If it's a file path
            if isinstance(file_input, str):
                with open(file_input, "rb") as f:
                    poller = self.client.begin_analyze_document(
                        model_id="prebuilt-layout",
                        document=f
                    )
            else:
                # Uploaded file (Django InMemoryUploadedFile)
                file_input.seek(0)
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=file_input.read() if not isinstance(file_input, str) else open(file_input, "rb").read()
                )

            result = poller.result()
            return self._convert_to_json(result)

        except Exception as e:
            return {
                "error": f"Layout extraction failed: {str(e)}"
            }

    # ----------------------------------------
    # CONVERT AZURE RESPONSE → CLEAN JSON
    # ----------------------------------------
    def _convert_to_json(self, result):
        data = {
            "full_text": result.content if result.content else "",
            "pages": [],
            "tables": [],
            "key_value_pairs": []
        }

        # ----------------------------------------
        # PAGES + LINES
        # ----------------------------------------
        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "lines": []
            }

            for line in page.lines:
                page_data["lines"].append({
                    "text": line.content,
                    "polygon": line.polygon  # useful later if needed
                })

            data["pages"].append(page_data)

        # ----------------------------------------
        # TABLES (VERY IMPORTANT FOR AMOUNTS)
        # ----------------------------------------
        for table in result.tables:
            table_data = {
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": [],
                "grid": []
            }

            # Build empty grid
            grid = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]

            for cell in table.cells:
                grid[cell.row_index][cell.column_index] = cell.content

                table_data["cells"].append({
                    "row": cell.row_index,
                    "column": cell.column_index,
                    "text": cell.content
                })

            table_data["grid"] = grid
            data["tables"].append(table_data)

        # ----------------------------------------
        # KEY VALUE PAIRS (if detected)
        # ----------------------------------------
        if hasattr(result, "key_value_pairs") and result.key_value_pairs:
            for kv in result.key_value_pairs:
                key = kv.key.content if kv.key else ""
                value = kv.value.content if kv.value else ""

                data["key_value_pairs"].append({
                    "key": key,
                    "value": value
                })

        return data