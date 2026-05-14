"""
Shared OCR / invoice text helpers for parsing quality.
Used by all tax invoice parsers.
"""

import re


# ---------------------------------------------------
# OCR NORMALIZATION
# ---------------------------------------------------
def normalize_ocr_text(text):
    """
    Global normalization before line/regex parsing.
    Preserves newline boundaries; cleans OCR junk and spaces.
    """

    if not text or not isinstance(text, str):
        return ""

    raw = (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    out_lines = []

    for line in raw.split("\n"):

        s = line

        s = re.sub(r"~{2,}", " ", s)
        s = re.sub(r'"{3,}', " ", s)
        s = re.sub(r"'{3,}", " ", s)
        s = re.sub(r"0{6,}", " ", s)

        s = re.sub(
            r"([!?.,;:])\1{2,}",
            r"\1",
            s
        )

        s = re.sub(
            r"[-_=]{4,}",
            " ",
            s
        )

        s = re.sub(
            r"[ \t]+",
            " ",
            s
        ).strip()

        out_lines.append(s)

    body = "\n".join(out_lines)

    body = re.sub(
        r"\n{4,}",
        "\n\n\n",
        body
    )

    return body.strip()


# ---------------------------------------------------
# DEDUPE CHARACTER NOISE
# ---------------------------------------------------
def dedupe_repeated_char_noise(s):

    if not s:
        return s

    t = re.sub(r"0{4,}", " ", s)
    t = re.sub(r"~{2,}", " ", t)

    t = re.sub(r'"{2,}', '"', t)
    t = re.sub(r"'{2,}", "'", t)

    t = re.sub(
        r"([.,])\1+",
        r"\1",
        t
    )

    return t


# ---------------------------------------------------
# COLLAPSE WHITESPACE
# ---------------------------------------------------
def collapse_whitespace(s):

    if not s:
        return s

    return re.sub(
        r"\s+",
        " ",
        s
    ).strip()


# ---------------------------------------------------
# REMOVE EMIRATE JUNK
# ---------------------------------------------------
def strip_trailing_emirate_junk(name):

    if not name:
        return name

    t = name.strip()

    junk = (
        r",?\s*("
        r"SHARJAH|"
        r"ABU\s*DHABI|"
        r"DUBAI|"
        r"AJMAN|"
        r"FUJAIRAH|"
        r"RAS\s*AL\s*KHAIMAH|"
        r"UMM\s*AL\s*QUWAIN"
        r")\s*$"
    )

    t = re.sub(
        junk,
        "",
        t,
        flags=re.IGNORECASE
    )

    return t.strip(" ,.-")


# ---------------------------------------------------
# CLEAN CUSTOMER NAME
# ---------------------------------------------------
def clean_customer_name(raw):

    if not raw:
        return None

    s = dedupe_repeated_char_noise(raw)

    s = collapse_whitespace(s)

    s = strip_trailing_emirate_junk(s)

    s = s.strip(" \t\"'~+")

    s = re.sub(r",+$", "", s)

    s = s.rstrip("-")

    if len(s) < 2:
        return None

    return s


# ---------------------------------------------------
# NULL CONFIDENCE
# ---------------------------------------------------
def semantic_null_confidence(salt=""):

    span = 13
    lo = 18

    idx = abs(
        hash(("sem_null", salt))
    ) % span

    return lo + idx


# ---------------------------------------------------
# CUSTOMER VALIDATION
# ---------------------------------------------------
def customer_name_semantic_invalid(value):

    if not value or not str(value).strip():
        return True

    s = str(value).strip()

    if re.search(r"\d", s):
        return True

    if re.search(
        r"\b("
        r"NISSAN|TOYOTA|HONDA|FORD|"
        r"URVAN|HIACE|CHASSIS|"
        r"REG\.?\s*NO|VEHICLE|MODEL|MAKE"
        r")\b",
        s,
        re.IGNORECASE,
    ):
        return True

    if re.search(
        r"[^\w\s,.\-&'()/+]{4,}",
        s
    ):
        return True

    if re.search(
        r"(.)\1{4,}",
        re.sub(r"\s", "", s)
    ):
        return True

    return False


# ---------------------------------------------------
# POLICY TYPE VALIDATION
# ---------------------------------------------------
def policy_type_semantic_invalid(value):

    if not value:
        return True

    s = str(value).strip()

    if re.search(
        r"\b("
        r"P\/\d|CHASSIS|REG\.?\s*NO|"
        r"ENGINE|VIN|NISSAN|TOYOTA|"
        r"HONDA|FORD|URVAN|HIACE"
        r")\b",
        s,
        re.IGNORECASE,
    ):
        return True

    if (
        re.search(r"\d{3,}", s)
        and not re.search(
            r"(?:"
            r"MOTOR|COMPREHENSIVE|"
            r"THIRD|TPL|INSURANCE|"
            r"LIABILITY"
            r")\b",
            s,
            re.IGNORECASE,
        )
    ):
        return True

    return False


# ---------------------------------------------------
# INVOICE VALIDATION
# ---------------------------------------------------
def invoice_number_semantic_invalid(value):

    if not value:
        return True

    s = str(value).strip()

    if re.search(r"\s", s):
        return True

    if re.search(
        r"\b("
        r"INVOICE|TAX|DOCUMENT|"
        r"NUMBER|DATE"
        r")\b",
        s,
        re.I,
    ):
        return True

    if len(s) > 60:
        return True

    if not re.search(r"[A-Z0-9]", s, re.I):
        return True

    return False


# ---------------------------------------------------
# DATE VALIDATION
# ---------------------------------------------------
def date_field_semantic_invalid(value):

    if not value:
        return True

    s = str(value).strip()

    if re.search(r"[A-Za-z]{3,}", s):

        if not re.search(
            r"[A-Za-z]{3}[-/]",
            s
        ):
            return True

    if not re.fullmatch(
        r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}",
        s,
    ):

        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            s,
        ):

            if not re.fullmatch(
                r"\d{1,2}-[A-Za-z]{3}-\d{2,4}",
                s,
                re.IGNORECASE,
            ):
                return True

    return False


# ---------------------------------------------------
# MONTH MAP
# ---------------------------------------------------
_MONTH_MAP = {

    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


# ---------------------------------------------------
# NORMALIZE DATE
# ---------------------------------------------------
def normalize_date(value):

    if value is None:
        return None

    s = str(value).strip()

    if not s:
        return None

    s = re.sub(r"\s+", " ", s)

    # 02-Apr-2026
    m = re.match(
        r"^(\d{1,2})[-/]([A-Za-z]{3,9})[-/](\d{4})$",
        s,
        re.IGNORECASE,
    )

    if m:

        day = int(m.group(1))

        mon_raw = m.group(2).lower()[:3]

        year = int(m.group(3))

        month = _MONTH_MAP.get(mon_raw)

        if month and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"

    # Apr-02-2026
    m = re.match(
        r"^([A-Za-z]{3,9})[-/](\d{1,2})[-/](\d{4})$",
        s,
        re.IGNORECASE,
    )

    if m:

        mon_raw = m.group(1).lower()[:3]

        day = int(m.group(2))

        year = int(m.group(3))

        month = _MONTH_MAP.get(mon_raw)

        if month and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"

    # 2026-04-02
    m = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})$",
        s
    )

    if m:

        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))

        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"

    # 02/04/2026
    m = re.match(
        r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$",
        s,
    )

    if m:

        day = int(m.group(1))
        month = int(m.group(2))

        y_raw = m.group(3)

        year = int(y_raw)

        if len(y_raw) == 2:
            year = (
                2000 + year
                if year < 70
                else 1900 + year
            )

        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"

    # 02-Apr-26
    m = re.match(
        r"^(\d{1,2})[-]([A-Za-z]{3})[-](\d{2})$",
        s,
        re.IGNORECASE,
    )

    if m:

        day = int(m.group(1))

        mon_raw = m.group(2).lower()[:3]

        y2 = int(m.group(3))

        year = (
            2000 + y2
            if y2 < 70
            else 1900 + y2
        )

        month = _MONTH_MAP.get(mon_raw)

        if month and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}"

    return None


# ---------------------------------------------------
# DATE TOKEN
# ---------------------------------------------------
_DATE_TOKEN_PATTERN = (

    r"(?:"

    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"

    r"|"

    r"\d{4}-\d{1,2}-\d{1,2}"

    r"|"

    r"\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{2,4}"

    r"|"

    r"[A-Za-z]{3,9}[-/]\d{1,2}[-/]\d{2,4}"

    r")"
)


# ---------------------------------------------------
# POLICY DATE RANGE EXTRACTION
# ---------------------------------------------------
def extract_policy_date_range(text):
    """
    Extract policy period dates from common invoice phrasings.
    Returns normalized DD/MM/YYYY dates.
    """

    if not text:
        return None, None

    compact = re.sub(
        r"\s+",
        " ",
        str(text)
    )

    date_token = (
        r"(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|"
        r"\d{4}-\d{1,2}-\d{1,2}"
        r"|"
        r"\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{2,4}"
        r"|"
        r"[A-Za-z]{3,9}[-/]\d{1,2}[-/]\d{2,4}"
        r")"
    )

    patterns = [

        (
            r"(?:Policy\s*Period|"
            r"Period\s*of\s*(?:Insurance|Cover)|"
            r"Insurance\s*Period)"
            r"\s*[:\-]?\s*"
            r"(?:FROM\s*)?"
            r"(" + date_token + r")"
            r"(?:\s+\d{1,2}:\d{2}\s*(?:HRS|Hrs|hrs)?)?"
            r"\s*(?:TO|to|UNTIL|until|[-–—])\s*"
            r"(?:TO\s*)?"
            r"(" + date_token + r")"
            r"(?:\s+\d{1,2}:\d{2}\s*(?:HRS|Hrs|hrs)?)?"
        ),

        (
            r"\bFROM\s*[:\-]?\s*"
            r"(" + date_token + r")"
            r"(?:\s+\d{1,2}:\d{2}\s*(?:HRS|Hrs|hrs)?)?"
            r"\s*(?:TO|to|UNTIL|until|[-–—])\s*"
            r"(" + date_token + r")"
            r"(?:\s+\d{1,2}:\d{2}\s*(?:HRS|Hrs|hrs)?)?"
        ),
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            compact,
            re.IGNORECASE
        )

        if m:

            start = normalize_date(
                m.group(1)
            )

            end = normalize_date(
                m.group(2)
            )

            if start and end:
                return start, end

    # fallback
    dates = re.findall(
        date_token,
        compact,
        re.IGNORECASE
    )

    normalized = []

    for d in dates:

        nd = normalize_date(d)

        if nd and nd not in normalized:
            normalized.append(nd)

    if len(normalized) >= 2:
        return normalized[0], normalized[1]

    return None, None


# ---------------------------------------------------
# MERGE WRAPPED OCR LINES
# ---------------------------------------------------
def merge_wrapped_ocr_lines(text):

    if not text:
        return ""

    lines = [
        ln.rstrip()
        for ln in str(text).split("\n")
    ]

    out = []

    i = 0

    while i < len(lines):

        cur = lines[i].strip()

        if not cur:
            i += 1
            continue

        j = i + 1

        merged = cur

        while j < len(lines):

            nxt = lines[j].strip()

            if not nxt:
                break

            if re.match(
                r"^[A-Za-z][A-Za-z\s]{1,25}\s*:\s*",
                nxt
            ):
                break

            if re.match(
                r"^(TRN|Broker|Invoice|Date|Policy|Account)\b",
                nxt,
                re.IGNORECASE,
            ):
                break

            if re.match(
                r"^[\d,]+\.\d{2}$",
                nxt
            ):
                break

            if len(nxt) <= 2:
                break

            merged = f"{merged} {nxt}"

            j += 1

        out.append(
            collapse_whitespace(merged)
        )

        i = j

    return "\n".join(out).strip()