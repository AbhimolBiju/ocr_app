import re

def parse_credit_note(text, tables=None):
    data = {}

    # Basic fields
    data["to_address"] = extract(r'To:\s*(.+)', text)
    data["account_number"] = extract(r'Account No\.\s*:\s*(\d+)', text)
    data["date"] = extract(r'Date\s*:\s*(\d{2}/\d{2}/\d{4})', text)
    data["branch"] = extract(r'Branch\s*:\s*(\w+)', text)
    data["department"] = extract(r'Department\s*:\s*(\w+)', text)
    data["product"] = extract(r'Product\s*:\s*(.+)', text)

    # Policy
    data["policy_number"] = extract(r'Policy No\.\s*:\s*(\d+)', text)

    policy_period = extract(r'Policy Period\s*:\s*(.+)', text)
    if policy_period:
        parts = policy_period.split("To")
        if len(parts) == 2:
            data["policy_start_date"] = parts[0].strip()
            data["policy_end_date"] = parts[1].strip()

    # Person + vehicle
    data["insured"] = extract(r'Insured\s*:\s*(.+)', text)
    data["engine_number"] = extract(r'Engine No\.\s*:\s*(\w+)', text)
    data["chassis_number"] = extract(r'Chassis No\.\s*:\s*(\w+)', text)

    # Document
    data["document_number"] = extract(r'Doc No\.\s*:\s*([\d\s-]+)', text)

    # TABLE EXTRACTION (IMPORTANT)
    data["items"] = []

    if tables:
        for table in tables:
            for row_index, row in table.items():
                if row_index == 0:
                    continue  # skip header

                row_values = list(row.values())

                if len(row_values) >= 6:
                    item = {
                        "description": row_values[1],
                        "qty": row_values[2],
                        "unit_price": row_values[3],
                        "taxable_amount": row_values[4],
                        "vat": row_values[5],
                        "total": row_values[-1]
                    }
                    data["items"].append(item)

                    # extract TOTAL from table
                    if "TOTAL" in row_values[0].upper():
                        data["total_amount"] = row_values[-1]

    return data


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None