from datetime import date, datetime
from decimal import Decimal

import pytest

from backend.framework import Field
from backend.framework.validation import clean_value


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("text", "  text  ", "text"),
        ("textarea", "a\nb", "a\nb"),
        ("integer", "42", 42),
        ("integer", -3, -3),
        ("decimal", "12.50", Decimal("12.50")),
        ("decimal", "1e2", Decimal("100")),
        ("boolean", True, True),
        ("boolean", False, False),
        ("date", "2026-11-01", date(2026, 11, 1)),
        ("email", "HELLO@example.com", "hello@example.com"),
        ("url", "https://example.com/path", "https://example.com/path"),
    ],
)
def test_field_coercion(kind, value, expected):
    assert clean_value(Field("value", "Value", kind=kind), value) == expected


@pytest.mark.parametrize(
    "kind,value",
    [
        ("integer", True),
        ("integer", "1.5"),
        ("integer", 2**40),
        ("decimal", "NaN"),
        ("decimal", "Infinity"),
        ("decimal", "10000000000"),
        ("decimal", "1.001"),
        ("decimal", 0.1),
        ("boolean", "true"),
        ("boolean", 1),
        ("date", "2026-02-30"),
        ("date", datetime(2026, 1, 1)),
        ("email", "no-email"),
        ("url", "javascript:alert(1)"),
        ("url", "https://user:password@example.com"),
        ("text", []),
    ],
)
def test_field_rejects_wrong_types(kind, value):
    with pytest.raises(ValueError):
        clean_value(Field("value", "Value", kind=kind), value)


def test_required_bounds_choices_and_pattern():
    assert clean_value(Field("amount", "Amount", kind="decimal", minimum=0.1), "0.10") == Decimal("0.10")
    with pytest.raises(ValueError):
        clean_value(Field("name", "Name", required=True), "  ")
    with pytest.raises(ValueError):
        clean_value(Field("name", "Name", max_length=3), "four")
    with pytest.raises(ValueError):
        clean_value(Field("count", "Count", kind="integer", minimum=0, maximum=10), -1)
    choice = Field("status", "Status", kind="choice", choices=(("open", "Open"), ("closed", "Closed")))
    assert clean_value(choice, "open") == "open"
    with pytest.raises(ValueError):
        clean_value(choice, "invented")
    with pytest.raises(ValueError):
        clean_value(Field("slug", "URL", pattern=r"[a-z-]+"), "BAD!")
    for kind in ["date", "integer", "decimal"]:
        assert clean_value(Field("value", "Value", kind=kind), None) is None
