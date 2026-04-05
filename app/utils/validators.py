from datetime import date
from app.models.user import Role
from app.models.financial_record import RecordType


def validate_user_create(data: dict) -> list[str]:
    """returns validation error messages for user creation."""
    errors = []

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", Role.VIEWER)

    if not username:
        errors.append("username is required")
    elif len(username) < 3:
        errors.append("username must be at least 3 characters")
    elif len(username) > 80:
        errors.append("username must be at most 80 characters")

    if not email:
        errors.append("email is required")
    elif "@" not in email or "." not in email.split("@")[-1]:
        errors.append("email is not valid")

    if not password:
        errors.append("password is required")
    elif len(password) < 6:
        errors.append("password must be at least 6 characters")

    if role not in Role.ALL:
        errors.append(f"role must be one of: {', '.join(Role.ALL)}")

    return errors


def validate_user_update(data: dict) -> list[str]:
    """returns validation error messages for user update."""
    errors = []

    if "role" in data and data["role"] not in Role.ALL:
        errors.append(f"role must be one of: {', '.join(Role.ALL)}")

    if "is_active" in data and not isinstance(data["is_active"], bool):
        errors.append("is_active must be a boolean")

    if "email" in data:
        email = data["email"].strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("email is not valid")

    return errors


def validate_record_create(data: dict) -> list[str]:
    """returns validation error messages for record creation."""
    errors = []

    amount = data.get("amount")
    record_type = data.get("type", "").strip()
    category = data.get("category", "").strip()
    record_date = data.get("date", "")

    if amount is None:
        errors.append("amount is required")
    else:
        try:
            val = float(amount)
            if val <= 0:
                errors.append("amount must be greater than 0")
        except (TypeError, ValueError):
            errors.append("amount must be a valid number")

    if not record_type:
        errors.append("type is required")
    elif record_type not in RecordType.ALL:
        errors.append(f"type must be one of: {', '.join(RecordType.ALL)}")

    if not category:
        errors.append("category is required")
    elif len(category) > 80:
        errors.append("category must be at most 80 characters")

    if not record_date:
        errors.append("date is required")
    else:
        try:
            date.fromisoformat(str(record_date))
        except ValueError:
            errors.append("date must be in YYYY-MM-DD format")

    return errors


def validate_record_update(data: dict) -> list[str]:
    """returns validation error messages for record update."""
    errors = []

    if "amount" in data:
        try:
            val = float(data["amount"])
            if val <= 0:
                errors.append("amount must be greater than 0")
        except (TypeError, ValueError):
            errors.append("amount must be a valid number")

    if "type" in data and data["type"] not in RecordType.ALL:
        errors.append(f"type must be one of: {', '.join(RecordType.ALL)}")

    if "category" in data:
        if not data["category"].strip():
            errors.append("category cannot be empty")
        elif len(data["category"]) > 80:
            errors.append("category must be at most 80 characters")

    if "date" in data:
        try:
            date.fromisoformat(str(data["date"]))
        except ValueError:
            errors.append("date must be in YYYY-MM-DD format")

    return errors
