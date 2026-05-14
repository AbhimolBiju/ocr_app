def validate_credit_note(data):
    errors = []

    if not data.get("policy_number"):
        errors.append("Missing policy number")

    if not data.get("insured_name"):
        errors.append("Missing insured name")

    if not data.get("total_amount"):
        errors.append("Missing total amount")

    return errors