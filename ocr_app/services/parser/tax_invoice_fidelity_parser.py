import re
from datetime import datetime
from ..confidence import ConfidenceEngine

POLICY_RE = r"\d{2}/\d{4}/\d{2}[A-Z]/\d+"


def clean_lines(text):
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def normalize_date(value):

    if not value:
        return None

    value = re.sub(r"[.\-]", "/", value)

    try:
        return datetime.strptime(
            value,
            "%d/%m/%Y"
        ).strftime("%Y-%m-%d")

    except ValueError:
        return value


def clean_amount(value):

    if not value:
        return None

    value = value.replace(",", "").strip()

    match = re.search(
        r"\d+(?:\.\d{2})?",
        value
    )

    return match.group() if match else None


def get_value_after_label(lines, label, lookahead=4):

    label_lower = label.lower()

    for i, line in enumerate(lines):

        if label_lower in line.lower():

            if ":" in line:

                value = line.split(":", 1)[1].strip()

                if value:
                    return value

            # next useful line
            for nxt in lines[i + 1:i + 1 + lookahead]:

                cleaned = nxt.replace(":", "").strip()

                if cleaned:
                    return cleaned

    return None


def extract_invoice_number_strict(lines, compact_text):

    patterns = [
        r"(?:Tax\s*Invoice|Invoice)\s*(?:#|No\.?|Number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{3,})",
        r"Doc(?:ument)?\s*No\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{3,})",
    ]

    for line in lines:
        for pattern in patterns:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                return m.group(1).strip()

    for pattern in patterns:
        m = re.search(pattern, compact_text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return None


def is_amount(line):

    return bool(
        re.fullmatch(
            r"[\d,]+\.\d{2}",
            line.strip()
        )
    )


# ---------------------------------------------------
# CONFIDENCE FIELD BUILDER
# ---------------------------------------------------
def build_field(value, pattern):

    confidence = ConfidenceEngine.calculate(
        value,
        pattern=pattern,
    )

    return {
        "value": value,
        "confidence": confidence
    }


# ---------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------
def parse_fidelity_debit_note(raw_text):

    raw_data = {}

    lines = clean_lines(raw_text)

    compact_text = " ".join(lines)

    # ---------------------------------------------------
    # BASIC FIELDS
    # ---------------------------------------------------
    raw_data["document_type"] = (
        "TAX INVOICE"
        if "TAX INVOICE" in compact_text
        else None
    )

    raw_data["company_name"] = (
        "UNITED FIDELITY INSURANCE COMPANY"
        if "UNITED FIDELITY INSURANCE COMPANY" in compact_text
        else None
    )

    raw_data["is_fidelity"] = (
        "FIDELITY" in compact_text.upper()
        or "UNITED FIDELITY INSURANCE COMPANY"
        in compact_text.upper()
    )

    # ---------------------------------------------------
    # BRANCH
    # ---------------------------------------------------
    for line in lines:

        if line.startswith("BRANCH"):

            branch = (
                line
                .replace("BRANCH", "")
                .strip()
            )

            raw_data["branch"] = branch

            break

    # ---------------------------------------------------
    # INVOICE DATE
    # ---------------------------------------------------
    invoice_date = get_value_after_label(
        lines,
        "DATE"
    )

    if invoice_date:

        raw_data["invoice_date"] = normalize_date(
            invoice_date
        )

    # ---------------------------------------------------
    # INVOICE NUMBER
    # ---------------------------------------------------
    invoice_no = get_value_after_label(
        lines,
        "INVOICE #"
    )

    if invoice_no:
        clean = re.search(r"([A-Z0-9][A-Z0-9/\-]{3,})", invoice_no.upper())
        if clean:
            raw_data["invoice_number"] = clean.group(1).strip()

    if not raw_data.get("invoice_number"):
        raw_data["invoice_number"] = extract_invoice_number_strict(lines, compact_text)

    # ---------------------------------------------------
    # TAX REGISTRATION NUMBER
    # ---------------------------------------------------
    m = re.search(
        r"\b\d{15}\b",
        compact_text
    )

    if m:
        raw_data["tax_registration_number"] = m.group()

    # ---------------------------------------------------
    # ACCOUNT NUMBER
    # ---------------------------------------------------
    raw_data["account_number"] = get_value_after_label(
        lines,
        "ACCOUNT #"
    )

    # ---------------------------------------------------
    # TELEPHONE
    # ---------------------------------------------------
    raw_data["telephone"] = get_value_after_label(
        lines,
        "TEL"
    )

    # ---------------------------------------------------
    # EMIRATE FOR VAT
    # ---------------------------------------------------
    raw_data["emirate_for_vat"] = get_value_after_label(
        lines,
        "EMIRATES FOR VAT"
    )

    # ---------------------------------------------------
    # BROKER NAME
    # ---------------------------------------------------
    for i, line in enumerate(lines):

        if re.search(r"\b(Broker|Intermediary)\b", line, re.IGNORECASE):

            inline = re.split(
                r"\b(?:Broker|Intermediary)\b\s*:?",
                line,
                maxsplit=1,
                flags=re.IGNORECASE,
            )

            if len(inline) > 1:
                cand = inline[1].strip(" :,-")
                if cand and len(cand) > 2:
                    raw_data["broker_name"] = cand
                    break

            for nxt in lines[i + 1:i + 5]:
                cand = nxt.strip(" :,-")
                if not cand:
                    continue
                if re.search(r"(policy|date|invoice|amount|vat)", cand, re.IGNORECASE):
                    break
                if len(cand) > 2:
                    raw_data["broker_name"] = cand
                    break
            if raw_data.get("broker_name"):
                break

    for i, line in enumerate(lines):

        upper_line = line.upper().strip()

        if (
            "PROMISE INSURANCE" in upper_line
            or "PROMISE INSURANCE SERVICES"
            in upper_line
        ):

            raw_data["broker_name"] = line.strip()

            break

    # fallback
    if not raw_data.get("broker_name"):

        m = re.search(
            r"(PROMISE INSURANCE SERVICES(?: LLC)?)",
            compact_text,
            re.IGNORECASE,
        )

        if m:
            raw_data["broker_name"] = m.group(1).strip()

    if not raw_data.get("broker_name"):

        m = re.search(
            r"(?:Broker|Intermediary)\s*[:\-]?\s*([A-Z][A-Z0-9&\.\- ]{3,})",
            compact_text,
            re.IGNORECASE,
        )

        if m:
            raw_data["broker_name"] = m.group(1).strip(" :,-")

    if not raw_data.get("broker_name"):

        for i, line in enumerate(lines):
            if re.search(r"(for\s+and\s+on\s+behalf|authorized\s+signatory|signature)", line, re.IGNORECASE):
                for nxt in lines[max(0, i - 4):i]:
                    if re.search(r"(insurance|broker|services)", nxt, re.IGNORECASE):
                        cand = nxt.strip(" :,-")
                        if len(cand) > 2:
                            raw_data["broker_name"] = cand
                            break
                if raw_data.get("broker_name"):
                    break

    # ---------------------------------------------------
    # PROMISE BROKER CHECK
    # ---------------------------------------------------
    broker_name = raw_data.get(
        "broker_name",
        ""
    )

    raw_data["is_promise_broker"] = (
        "PROMISE INSURANCE"
        in broker_name.upper()
    )

    # ---------------------------------------------------
    # INSURED NAME
    # ---------------------------------------------------
    for i, line in enumerate(lines):

        if line == "INSURED":

            for nxt in lines[i + 1:i + 8]:

                if (
                    re.fullmatch(
                        r"[A-Z ]{5,}",
                        nxt
                    )
                    and "DATE" not in nxt
                ):

                    raw_data["insured_name"] = nxt.strip()

                    break

            break

        if line.startswith("INSURED "):

            raw_data["insured_name"] = (
                line.replace(
                    "INSURED",
                    "",
                    1
                ).strip()
            )

            break

    # ---------------------------------------------------
    # POLICY BLOCK
    # ---------------------------------------------------
    for i, line in enumerate(lines):

        if re.fullmatch(POLICY_RE, line):

            raw_data["policy_number"] = line

            # policy type
            for candidate in reversed(
                lines[max(0, i - 4):i]
            ):

                candidate_upper = (
                    candidate.upper().strip()
                )

                if (
                    "CLASS OF INSURANCE"
                    not in candidate_upper
                    and "POLICY"
                    not in candidate_upper
                    and not re.fullmatch(
                        POLICY_RE,
                        candidate.strip()
                    )
                    and len(candidate.strip()) > 3
                ):

                    raw_data["policy_type"] = (
                        candidate.strip()
                    )

                    break

            # dates
            if i + 1 < len(lines):

                m = re.search(
                    r"(\d{2}[./-]\d{2}[./-]\d{4})\s+TO\s+(\d{2}[./-]\d{2}[./-]\d{4})",
                    lines[i + 1],
                )

                if m:

                    raw_data["period_from"] = (
                        normalize_date(
                            m.group(1)
                        )
                    )

                    raw_data["period_to"] = (
                        normalize_date(
                            m.group(2)
                        )
                    )

            # vehicle
            if i + 2 < len(lines):

                m = re.search(
                    r"(.+?)\s*/\s*(\d+)",
                    lines[i + 2]
                )

                if m:

                    raw_data["vehicle_make"] = (
                        m.group(1).strip()
                    )

                    raw_data["vehicle_reg_no"] = (
                        m.group(2).strip()
                    )

            # chassis
            if i + 3 < len(lines):

                m = re.search(
                    r"([A-Z0-9]{17})\s*/\s*([A-Z0-9]+)",
                    lines[i + 3]
                )

                if m:

                    raw_data["chassis_number"] = (
                        m.group(1)
                    )

                    raw_data["engine_number"] = (
                        m.group(2)
                    )

            # vehicle value
            if i + 4 < len(lines):

                m = re.search(
                    r"AED\s*([\d,]+\.\d{2})",
                    lines[i + 4]
                )

                if m:

                    raw_data["vehicle_value"] = (
                        clean_amount(
                            m.group(1)
                        )
                    )

            break

    # ---------------------------------------------------
    # FALLBACKS
    # ---------------------------------------------------
    if "period_from" not in raw_data:

        m = re.search(
            r"PERIOD\s+(\d{2}[./-]\d{2}[./-]\d{4})\s+TO\s+(\d{2}[./-]\d{2}[./-]\d{4})",
            compact_text,
        )

        if m:

            raw_data["period_from"] = (
                normalize_date(
                    m.group(1)
                )
            )

            raw_data["period_to"] = (
                normalize_date(
                    m.group(2)
                )
            )

    if "vehicle_make" not in raw_data:

        m = re.search(
            r"VEHICLE MAKE/REG\.NO\s+(.+?)\s*/\s*(\d+)",
            compact_text
        )

        if m:

            raw_data["vehicle_make"] = (
                m.group(1).strip()
            )

            raw_data["vehicle_reg_no"] = (
                m.group(2).strip()
            )

    if "chassis_number" not in raw_data:

        m = re.search(
            r"\b([A-Z0-9]{17})\s*/\s*([A-Z0-9]+)",
            compact_text
        )

        if m:

            raw_data["chassis_number"] = (
                m.group(1)
            )

            raw_data["engine_number"] = (
                m.group(2)
            )

    if "vehicle_value" not in raw_data:

        m = re.search(
            r"AED\s*([\d,]+\.\d{2})",
            compact_text
        )

        if m:

            raw_data["vehicle_value"] = (
                clean_amount(
                    m.group(1)
                )
            )

    # ---------------------------------------------------
    # PREMIUM AMOUNT
    # ---------------------------------------------------
    for i, line in enumerate(lines):

        if "Payment Ref No" in line:

            for nxt in lines[i + 1:i + 5]:

                if is_amount(nxt):

                    raw_data["premium_amount"] = (
                        clean_amount(nxt)
                    )

                    break

    # ---------------------------------------------------
    # VAT + TOTAL
    # ---------------------------------------------------
    for i, line in enumerate(lines):

        # roadside
        if "ROAD SIDE ASSISTANCE" in line:

            m = re.search(
                r"([\d,]+\.\d{2})$",
                line
            )

            if m:

                raw_data[
                    "roadside_assistance_amount"
                ] = clean_amount(
                    m.group(1)
                )

            elif (
                i + 1 < len(lines)
                and is_amount(lines[i + 1])
            ):

                raw_data[
                    "roadside_assistance_amount"
                ] = clean_amount(
                    lines[i + 1]
                )

        # vat
        if "5% VAT" in line:

            m = re.search(
                r"([\d,]+\.\d{2})$",
                line
            )

            if m:

                raw_data["vat_amount"] = (
                    clean_amount(
                        m.group(1)
                    )
                )

            elif (
                i + 1 < len(lines)
                and is_amount(lines[i + 1])
            ):

                raw_data["vat_amount"] = (
                    clean_amount(
                        lines[i + 1]
                    )
                )

        # total
        if line.startswith("TOTAL"):

            m = re.search(
                r"([\d,]+\.\d{2})$",
                line
            )

            if m:

                raw_data["total_amount"] = (
                    clean_amount(
                        m.group(1)
                    )
                )

            else:

                for nxt in lines[i + 1:i + 5]:

                    if is_amount(nxt):

                        raw_data["total_amount"] = (
                            clean_amount(nxt)
                        )

                        break

    # ---------------------------------------------------
    # SUMMARY AMOUNTS
    # ---------------------------------------------------
    for i, line in enumerate(lines):

        if (
            line == "PREMIUM AMOUNT"
            and i + 1 < len(lines)
        ):

            raw_data[
                "premium_summary_amount"
            ] = clean_amount(
                lines[i + 1]
            )

        if (
            line == "VAT AMOUNT"
            and i + 1 < len(lines)
        ):

            raw_data[
                "vat_summary_amount"
            ] = clean_amount(
                lines[i + 1]
            )

        if raw_data.get(
            "premium_summary_amount"
        ):

            raw_data["premium_amount"] = (
                raw_data[
                    "premium_summary_amount"
                ]
            )

        if raw_data.get(
            "vat_summary_amount"
        ):

            raw_data["vat_amount"] = (
                raw_data[
                    "vat_summary_amount"
                ]
            )

    # ---------------------------------------------------
    # FINAL RESPONSE WITH CONFIDENCE
    # ---------------------------------------------------
    data = {}

    data["document_type"] = build_field(
        raw_data.get("document_type"),
        r"TAX INVOICE"
    )

    data["company_name"] = build_field(
        raw_data.get("company_name"),
        r"FIDELITY"
    )

    data["is_fidelity"] = ConfidenceEngine.wrap_field(
        raw_data.get("is_fidelity"),
        "high" if raw_data.get("is_fidelity") else "low",
        "fid_flag",
    )

    data["branch"] = build_field(
        raw_data.get("branch"),
        r"[A-Za-z ]+"
    )

    data["invoice_date"] = build_field(
        raw_data.get("invoice_date"),
        r"\d{4}-\d{2}-\d{2}"
    )

    data["invoice_number"] = build_field(
        raw_data.get("invoice_number"),
        r"[A-Z0-9\-\/]+"
    )

    data["tax_registration_number"] = build_field(
        raw_data.get("tax_registration_number"),
        r"\d{15}"
    )

    data["account_number"] = build_field(
        raw_data.get("account_number"),
        r"[A-Z0-9\-\/]+"
    )

    data["telephone"] = build_field(
        raw_data.get("telephone"),
        r"[\d\-\+]+"
    )

    data["emirate_for_vat"] = build_field(
        raw_data.get("emirate_for_vat"),
        r"[A-Za-z ]+"
    )

    data["broker_name"] = build_field(
        raw_data.get("broker_name"),
        r"[A-Za-z ]+"
    )

    data["is_promise_broker"] = ConfidenceEngine.wrap_field(
        raw_data.get(
            "is_promise_broker"
        ),
        "high" if raw_data.get("broker_name") else "low",
        "promise",
    )

    data["insured_name"] = build_field(
        raw_data.get("insured_name"),
        r"[A-Z ]+"
    )

    data["policy_number"] = build_field(
        raw_data.get("policy_number"),
        POLICY_RE
    )

    data["policy_type"] = build_field(
        raw_data.get("policy_type"),
        r"[A-Za-z ]+"
    )

    data["period_from"] = build_field(
        raw_data.get("period_from"),
        r"\d{4}-\d{2}-\d{2}"
    )

    data["period_to"] = build_field(
        raw_data.get("period_to"),
        r"\d{4}-\d{2}-\d{2}"
    )

    data["vehicle_make"] = build_field(
        raw_data.get("vehicle_make"),
        r"[A-Za-z0-9 ]+"
    )

    data["vehicle_reg_no"] = build_field(
        raw_data.get("vehicle_reg_no"),
        r"[A-Za-z0-9]+"
    )

    data["chassis_number"] = build_field(
        raw_data.get("chassis_number"),
        r"[A-Z0-9]{17}"
    )

    data["engine_number"] = build_field(
        raw_data.get("engine_number"),
        r"[A-Z0-9]+"
    )

    data["vehicle_value"] = build_field(
        raw_data.get("vehicle_value"),
        r"\d+(\.\d+)?"
    )

    data["premium_amount"] = build_field(
        raw_data.get("premium_amount"),
        r"\d+(\.\d+)?"
    )

    data["roadside_assistance_amount"] = build_field(
        raw_data.get(
            "roadside_assistance_amount"
        ),
        r"\d+(\.\d+)?"
    )

    data["vat_amount"] = build_field(
        raw_data.get("vat_amount"),
        r"\d+(\.\d+)?"
    )

    data["total_amount"] = build_field(
        raw_data.get("total_amount"),
        r"\d+(\.\d+)?"
    )

    from ..structured_schema import finalize_tax_invoice_output

    def gv(k):

        x = data.get(k)

        if isinstance(x, dict) and "value" in x:
            return x["value"]

        return x

    def cp(k, salt):

        x = data.get(k)

        if isinstance(x, dict) and "value" in x and "confidence" in x:
            return x

        return ConfidenceEngine.wrap_field(
            gv(k),
            "medium",
            salt,
        )

    total_v = gv("total_amount")
    prem_v = gv("premium_amount")
    vat_v = gv("vat_amount")

    try:
        net_v = (
            float(prem_v)
            if prem_v is not None
            else None
        )
    except (TypeError, ValueError):
        net_v = None

    canonical = {
        "insurer_name": cp("company_name", "insurer"),
        "customer_name": cp("insured_name", "cust"),
        "broker_name": cp("broker_name", "brok"),
        "is_promise_broker": data["is_promise_broker"],
        "invoice_date": cp("invoice_date", "idate"),
        "branch": cp("branch", "branch"),
        "policy_type": cp("policy_type", "ptype"),
        "policy_number": cp("policy_number", "pol"),
        "tax_invoice_number": cp("invoice_number", "taxno"),
        "policy_start_date": cp("period_from", "ps"),
        "policy_end_date": cp("period_to", "pe"),
        "premium_currency": ConfidenceEngine.wrap_field(
            "AED",
            "high",
            "cur",
        ),
        "premium_amount": ConfidenceEngine.wrap_field(
            prem_v,
            "high" if prem_v is not None else "missing",
            "pam",
        ),
        "net_premium": ConfidenceEngine.wrap_field(
            net_v,
            "high" if net_v is not None else "missing",
            "netp",
        ),
        "total_premium": ConfidenceEngine.wrap_field(
            total_v,
            "high" if total_v is not None else "missing",
            "totp",
        ),
        "vat_amount": ConfidenceEngine.wrap_field(
            vat_v,
            "high" if vat_v is not None else "missing",
            "vat",
        ),
        "net_due": ConfidenceEngine.wrap_field(
            total_v,
            "high" if total_v is not None else "missing",
            "netd",
        ),
        "total": ConfidenceEngine.wrap_field(
            total_v,
            "high" if total_v is not None else "missing",
            "tot",
        ),
        "invoice_date_calc": cp("invoice_date", "idc"),
        "due_date": cp("invoice_date", "due"),
    }

    return finalize_tax_invoice_output(canonical)