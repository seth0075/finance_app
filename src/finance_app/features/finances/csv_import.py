import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from finance_app.features.finances.amounts import money, parse_amount

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10000
DELIMITERS = {"comma": ",", "semicolon": ";", "tab": "\t"}
DATE_FORMATS = {
    "iso": ("%Y-%m-%d", r"\d{4}-\d{2}-\d{2}"),
    "us4": ("%m/%d/%Y", r"\d{1,2}/\d{1,2}/\d{4}"),
    "us2": ("%m/%d/%y", r"\d{1,2}/\d{1,2}/\d{2}"),
    "eu4": ("%d/%m/%Y", r"\d{1,2}/\d{1,2}/\d{4}"),
}


@dataclass(frozen=True)
class CsvDocument:
    headers: list[str]
    rows: list[tuple[int, list[str]]]


def normalize_header(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def read_csv(path, delimiter):
    if delimiter not in DELIMITERS:
        raise ValueError("Choose a supported CSV delimiter.")
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError("Could not read the selected CSV file.") from exc
    if len(data) > MAX_BYTES:
        raise ValueError("CSV files must be 5 MB or smaller.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Save the CSV as UTF-8 and try again.") from exc
    reader = csv.reader(
        io.StringIO(text, newline=""), delimiter=DELIMITERS[delimiter], strict=True
    )
    try:
        headers = next(reader, None)
        if not headers or not any(header.strip() for header in headers):
            raise ValueError("The CSV must have a header row.")
        headers = [
            header.strip() or f"Column {index + 1}"
            for index, header in enumerate(headers)
        ]
        rows = []
        while True:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            if not any(value.strip() for value in row):
                continue
            rows.append((line, row))
            if len(rows) > MAX_ROWS:
                raise ValueError(
                    "CSV files may contain at most 10,000 transaction rows."
                )
    except csv.Error as exc:
        raise ValueError(
            "The CSV is malformed; check its quoting and delimiter."
        ) from exc
    if not rows:
        raise ValueError("The CSV has no transaction rows.")
    account_columns = [
        i
        for i, header in enumerate(headers)
        if normalize_header(header) == "accountnumber"
    ]
    for column in account_columns:
        accounts = {
            row[column].strip()
            for _, row in rows
            if len(row) > column and row[column].strip()
        }
        if len(accounts) > 1:
            raise ValueError(
                "This file contains multiple account numbers. Import one account per file."
            )
    return CsvDocument(headers, rows)


def suggestions(document):
    normalized = [normalize_header(header) for header in document.headers]

    def find(*names):
        return next(
            (normalized.index(name) for name in names if name in normalized), -1
        )

    date_column = find("transactiondate", "date", "posteddate", "postingdate")
    type_column = find("transactiontype", "type")
    result = {
        "date": date_column,
        "description": find("transactiondescription", "description", "memo", "payee"),
        "amount": find("transactionamount", "amount"),
        "type": type_column,
        "category": find("category"),
        "debitAmount": find("debit", "withdrawal", "withdrawals"),
        "creditAmount": find("credit", "deposit", "deposits"),
        "direction": "type"
        if "transactiontype" in normalized and "transactionamount" in normalized
        else "signed",
        "dateFormat": "iso",
    }
    if (
        result["amount"] < 0
        and result["debitAmount"] >= 0
        and result["creditAmount"] >= 0
    ):
        result["direction"] = "columns"
    if date_column >= 0:
        sample = next(
            (
                row[date_column].strip()
                for _, row in document.rows
                if len(row) > date_column and row[date_column].strip()
            ),
            "",
        )
        if re.fullmatch(DATE_FORMATS["us2"][1], sample):
            result["dateFormat"] = "us2"
        elif re.fullmatch(DATE_FORMATS["us4"][1], sample):
            first = int(sample.split("/")[0])
            result["dateFormat"] = "eu4" if first > 12 else "us4"
    return result


def import_amount(value):
    value = value.strip()
    parentheses = value.startswith("(") and value.endswith(")")
    if parentheses:
        value = value[1:-1].strip()
    if not re.fullmatch(
        r"[+-]?\$?(?:\d{1,3}(?:,\d{3})+|\d{1,12})(?:\.\d{1,2})?", value
    ):
        raise ValueError("Enter a valid amount with at most two decimal places.")
    if parentheses and value.startswith(("-", "+")):
        raise ValueError("The amount has conflicting signs.")
    normalized = value.replace("$", "").replace(",", "").lstrip("+")
    if parentheses:
        normalized = "-" + normalized
    return parse_amount(normalized, signed=True)


def preview_rows(document, options, account, existing):
    columns = {}
    for key in (
        "date",
        "description",
        "amount",
        "type",
        "category",
        "debitAmount",
        "creditAmount",
    ):
        index = options.get(key, -1)
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < -1
            or index >= len(document.headers)
        ):
            raise ValueError("Choose valid CSV columns.")
        columns[key] = index
    if any(columns[key] < 0 for key in ("date", "description")):
        raise ValueError("Choose date and description columns.")
    date_format = options.get("dateFormat")
    if date_format not in DATE_FORMATS:
        raise ValueError("Choose a date format.")
    direction = options.get("direction")
    if direction not in ("signed", "reverse", "type", "columns"):
        raise ValueError("Choose how transaction directions are represented.")
    amount_keys = (
        ("debitAmount", "creditAmount") if direction == "columns" else ("amount",)
    )
    if any(columns[key] < 0 for key in amount_keys):
        raise ValueError("Choose the required amount columns.")
    required = [columns[key] for key in ("date", "description", *amount_keys)]
    if len(set(required)) != len(required):
        raise ValueError("Date, description, and amounts must use different columns.")
    debit = options.get("debitText", "").strip().casefold()
    credit = options.get("creditText", "").strip().casefold()
    if direction == "type":
        if columns["type"] < 0:
            raise ValueError("Choose the transaction type column.")
        if not debit or not credit or debit == credit:
            raise ValueError("Enter different debit and credit type values.")
        if columns["type"] in required:
            raise ValueError("The transaction type must use a different column.")
    if columns["category"] >= 0 and (
        columns["category"] in required
        or (direction == "type" and columns["category"] == columns["type"])
    ):
        raise ValueError("The category must use a different column.")
    seen = {
        (
            item["date"],
            item["title"].strip().casefold(),
            item["kind"],
            item["amountCents"],
        )
        for item in existing
        if item["accountId"] == account["id"] and item["kind"] in ("income", "expense")
    }
    in_file = set()
    result = []
    date_pattern = DATE_FORMATS[date_format][1]
    date_strptime = DATE_FORMATS[date_format][0]
    for line, values in document.rows:
        row = {
            "line": line,
            "date": "",
            "title": "",
            "amount": "",
            "kind": "",
            "category": "",
            "valid": False,
            "selected": False,
            "status": "",
        }
        for field, column in (("date", "date"), ("title", "description")):
            if 0 <= columns[column] < len(values):
                row[field] = values[columns[column]].strip()
        if direction != "columns" and 0 <= columns["amount"] < len(values):
            row["amount"] = values[columns["amount"]].strip()
        try:
            if len(values) != len(document.headers):
                raise ValueError("Column count does not match the header.")
            title = values[columns["description"]].strip()
            if not title or len(title) > 200:
                raise ValueError("Description must contain 1–200 characters.")
            value = values[columns["date"]].strip()
            if not re.fullmatch(date_pattern, value):
                raise ValueError("Date does not match the selected format.")
            try:
                day = datetime.strptime(value, date_strptime).date()
            except ValueError as exc:
                raise ValueError("Date is invalid.") from exc
            if direction == "columns":
                debit_value = values[columns["debitAmount"]].strip()
                credit_value = values[columns["creditAmount"]].strip()
                debit_cents = import_amount(debit_value) if debit_value else 0
                credit_cents = import_amount(credit_value) if credit_value else 0
                if bool(debit_cents) == bool(credit_cents):
                    raise ValueError(
                        "Exactly one debit or credit amount must be nonzero."
                    )
                cents = debit_cents or credit_cents
                kind = "expense" if debit_cents else "income"
            else:
                cents = import_amount(values[columns["amount"]])
            if cents == 0:
                raise ValueError("Amount must be greater than zero.")
            if direction == "type":
                transaction_type = values[columns["type"]].strip().casefold()
                if transaction_type not in (debit, credit):
                    raise ValueError("Type does not match the debit or credit values.")
                kind = "expense" if transaction_type == debit else "income"
            elif direction != "columns":
                kind = "income" if (cents > 0) == (direction == "signed") else "expense"
            cents = abs(cents)
            category = (
                values[columns["category"]].strip() if columns["category"] >= 0 else ""
            )
            category = category or "Uncategorized"
            if len(category) > 100:
                raise ValueError("Category must be at most 100 characters.")
            key = (day.isoformat(), title.casefold(), kind, cents)
            warning = (
                "Possible match in existing transactions."
                if key in seen
                else ("Possible duplicate in this file." if key in in_file else "")
            )
            in_file.add(key)
            row.update(
                date=day.isoformat(),
                title=title,
                amount=money(cents),
                amountCents=cents,
                kind=kind,
                category=category,
                valid=True,
                selected=not warning,
                status=warning,
            )
        except ValueError as exc:
            row["status"] = str(exc)
        result.append(row)
    return result
