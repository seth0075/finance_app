from decimal import Decimal

import pytest

from finance_app.integrations.plaid.viewmodel import amount_cents


@pytest.mark.parametrize(
    ("value", "expected"),
    [(Decimal("-12.34"), -1234), (0, 0), (Decimal("999999999999.99"), 99999999999999)],
)
def test_plaid_amounts_convert_exactly(value, expected):
    assert amount_cents(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1.001"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal(1000000000000),
        "invalid",
    ],
)
def test_plaid_rejects_non_currency_values(value):
    with pytest.raises(ValueError):
        amount_cents(value)
