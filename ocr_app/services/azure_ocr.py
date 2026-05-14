from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings


def extract_text_from_pdf(file):
    try:
        client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_KEY)
        )

        print("File name:", file.name)

        file.seek(0)
        file_bytes = file.read()

        print("File size (bytes):", len(file_bytes))

        if len(file_bytes) == 0:
            return {
                "text": "",
                "confidence": 0,
                "tables": [],
                "error": "Empty file"
            }

        # ✅ FIXED LINE (IMPORTANT)
        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            body=file_bytes
        )

        result = poller.result()

        full_text = result.content if result.content else ""

        print("\n===== OCR TEXT =====\n")
        print(full_text[:1000])

        conf_scores = []
        for page in getattr(result, "pages", None) or []:
            for word in getattr(page, "words", None) or []:
                c = getattr(word, "confidence", None)
                if c is not None:
                    try:
                        conf_scores.append(float(c))
                    except (TypeError, ValueError):
                        continue
        if conf_scores:
            ocr_conf = max(0.0, min(1.0, sum(conf_scores) / len(conf_scores)))
        elif len(full_text) > 400:
            ocr_conf = 0.82
        elif len(full_text) > 40:
            ocr_conf = 0.68
        else:
            ocr_conf = 0.0

        return {
            "text": full_text,
            "confidence": round(ocr_conf, 3),
            "tables": []
        }

    except Exception as e:
        print("❌ OCR ERROR:", str(e))
        return {
            "text": "",
            "confidence": 0,
            "tables": [],
            "error": str(e)
        }