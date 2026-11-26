import re


def parse_amount(value, *, signed=False):
    value = value.strip()
    pattern = r"-?\d{1,12}(?:\.\d{1,2})?" if signed else r"\d{1,12}(?:\.\d{1,2})?"
    if not re.fullmatch(pattern, value):
        raise ValueError(
            "Enter an amount with up to 12 digits and at most two decimal places."
        )
    negative = value.startswith("-")
    whole, _, fraction = value.lstrip("-").partition(".")
    cents = int(whole) * 100 + int((fraction + "00")[:2])
    return -cents if negative else cents


def money(cents):
    return f"{'-' if cents < 0 else ''}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def amount_input(cents):
    return f"{'-' if cents < 0 else ''}{abs(cents) // 100}.{abs(cents) % 100:02d}"
