"""One validation contract for HTML forms, API requests, and direct service calls."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from email_validator import EmailNotValidError, validate_email

from backend.common.errors import ValidationError


def clean_value(field, value):
    kind = field.kind
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ValueError("Use true or false.")
        return value
    if value is None or value == "":
        if field.required:
            raise ValueError("This field is required.")
        return None if kind in {"date", "integer", "decimal"} else ""
    if kind == "integer":
        if isinstance(value, bool) or not (
            isinstance(value, int) or isinstance(value, str) and re.fullmatch(r"-?\d+", value)
        ):
            raise ValueError("Use a whole number.")
        value = int(value)
        if not -(2**31) <= value < 2**31:
            raise ValueError("The number is outside the supported range.")
    elif kind == "decimal":
        if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
            raise ValueError("Use a decimal string, such as 19.95, to preserve precision.")
        try:
            value = Decimal(value)
            if (
                not value.is_finite()
                or abs(value) >= Decimal("10000000000")
                or value != value.quantize(Decimal("0.01"))
            ):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            raise ValueError("Use a finite amount with at most two decimal places and less than 10 billion.") from None
    elif kind == "date":
        if isinstance(value, datetime):
            raise ValueError("Use a date without a time.")
        try:
            return value if isinstance(value, date) else date.fromisoformat(value)
        except (ValueError, TypeError):
            raise ValueError("Use a valid date in YYYY-MM-DD format.") from None
    else:
        if not isinstance(value, str):
            raise ValueError("Use text for this field.")
        value = value.strip()
        if field.required and not value:
            raise ValueError("This field is required.")
        if len(value) > field.max_length:
            raise ValueError(f"Use at most {field.max_length} characters.")
        if field.pattern and not re.fullmatch(field.pattern, value):
            raise ValueError("Use the required format.")
        if kind == "choice" and value not in {x[0] for x in field.choices}:
            raise ValueError("Choose a listed value.")
        if kind == "email" and value:
            try:
                value = validate_email(value, check_deliverability=False).normalized.casefold()
            except EmailNotValidError:
                raise ValueError("Enter a valid email address.") from None
        if kind == "url" and value:
            try:
                url = urlsplit(value)
                if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None:
                    raise ValueError
            except ValueError:
                raise ValueError("Use an http(s) URL without credentials.") from None
        return value
    minimum = Decimal(str(field.minimum)) if kind == "decimal" and field.minimum is not None else field.minimum
    maximum = Decimal(str(field.maximum)) if kind == "decimal" and field.maximum is not None else field.maximum
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError("The number is outside this field's allowed range.")
    return value


def clean_payload(resource, payload, partial=False):
    if not isinstance(payload, dict):
        raise ValidationError({"body": ["Send a JSON object."]})
    names = {f.name for f in resource.fields}
    errors = {name: ["This field is not editable."] for name in set(payload) - names - {"version"}}
    output = {}
    for field in resource.fields:
        if partial and field.name not in payload:
            continue
        try:
            output[field.name] = clean_value(field, payload.get(field.name, field.default))
        except ValueError as error:
            errors[field.name] = [str(error)]
    if errors:
        raise ValidationError(errors)
    return output
