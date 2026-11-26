import pytest

from finance_app.features.finances.amounts import amount_input, money, parse_amount


@pytest.mark.parametrize(
    ("value", "cents"),
    [
        (" 0.1 ", 10),
        ("1234.50", 123450),
        ("-2.05", -205),
        ("999999999999.99", 99999999999999),
    ],
)
def test_amounts_round_trip_without_float_rounding(value, cents):
    assert parse_amount(value, signed=True) == cents
    assert parse_amount(amount_input(cents), signed=True) == cents


@pytest.mark.parametrize("value", ["-1", "1.001", "1e2", "1,000", "1000000000000", ""])
def test_invalid_unsigned_amounts_are_rejected(value):
    with pytest.raises(ValueError):
        parse_amount(value)


def test_negative_currency_display():
    assert money(-123456) == "-$1,234.56"
