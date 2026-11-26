import csv

import pytest
from PySide6.QtCore import QUrl
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.finances import viewmodel
from finance_app.features.finances.models import FinanceCategory


@pytest.fixture
def vm(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=engine))
    result = viewmodel.FinanceViewModel()
    assert result.saveAccount("", "Checking", "bank", "2024-01-01", "100", "") == ""
    return result


def write_csv(tmp_path, rows, name="example.csv", delimiter=","):
    path = tmp_path / name
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream, delimiter=delimiter).writerows(rows)
    return QUrl.fromLocalFile(str(path))


def settings(vm, **kwargs):
    options = {
        "accountId": vm.accounts[0]["id"],
        "date": 2,
        "description": 1,
        "amount": 4,
        "type": 3,
        "category": -1,
        "dateFormat": "us2",
        "direction": "type",
        "debitText": "Debit",
        "creditText": "Credit",
    }
    return {**options, **kwargs}


def test_preview_import_duplicates_and_balance(vm, tmp_path):
    file_url = write_csv(
        tmp_path,
        [
            [
                "Account Number",
                "Transaction Description",
                "Transaction Date",
                "Transaction Type",
                "Transaction Amount",
                "Balance",
            ],
            ["0000", "Lunch", "11/01/24", "Debit", "10.25", "89.75"],
            ["0000", "Lunch", "11/01/24", "Debit", "10.25", "79.50"],
            ["0000", "Refund", "11/02/24", "Credit", "5.00", "84.50"],
            ["0000", "Bad date", "11/99/24", "Debit", "1.00", "83.50"],
            ["0000", "Older", "12/31/23", "Debit", "1.00", "82.50"],
        ],
    )
    loaded = vm.loadCsv(file_url, "comma")
    assert not loaded["error"]
    assert loaded["suggestions"]["direction"] == "type"
    assert loaded["suggestions"]["dateFormat"] == "us2"
    preview = vm.previewCsv(settings(vm))
    rows = preview["rows"]
    assert [row["selected"] for row in rows] == [True, False, True, False, True]
    assert "duplicate" in rows[1]["status"]
    assert "invalid" in rows[3]["status"].lower()
    assert rows[4]["valid"]
    assert vm.importCsv([0, 3])["error"]
    assert not vm.transactions
    result = vm.importCsv([0, 1, 2, 4])
    assert result == {"error": "", "imported": 4}
    assert len(vm.transactions) == 4
    assert {item["category"] for item in vm.transactions} == {"Uncategorized"}
    assert vm.accounts[0]["openingAmount"] == "100.00"
    assert vm.accounts[0]["openedOn"] == "2024-01-01"
    assert vm.summaryFor("Day", "2023-12-31")["net"] == "$100.00"
    summary = vm.summaryFor("Month", "2024-11-01")
    assert (summary["income"], summary["expenses"], summary["net"]) == (
        "$5.00",
        "$20.50",
        "$84.50",
    )
    again = vm.previewCsv(settings(vm))
    assert [row["selected"] for row in again["rows"][:3]] == [False, False, False]
    assert "existing" in again["rows"][0]["status"]


def test_signed_mapping_categories_and_stale_preview(vm, tmp_path):
    file_url = write_csv(
        tmp_path,
        [
            ["Date", "Payee", "Amount", "Category"],
            ["2024-02-03", "Groceries", "-$1,234.50", "Food"],
            ["2024-02-04", "Pay", "+2000.00", "Salary"],
            ["2024-02-05", "Fee", "(2.50)", ""],
        ],
        delimiter=";",
    )
    assert not vm.loadCsv(file_url, "semicolon")["error"]
    options = settings(
        vm,
        date=0,
        description=1,
        amount=2,
        type=-1,
        category=3,
        dateFormat="iso",
        direction="signed",
    )
    preview = vm.previewCsv(options)
    assert [(row["kind"], row["amount"]) for row in preview["rows"]] == [
        ("expense", "$1,234.50"),
        ("income", "$2,000.00"),
        ("expense", "$2.50"),
    ]
    assert vm.saveAccount("", "Savings", "bank", "2024-01-01", "0", "") == ""
    assert "changed" in vm.importCsv([0])["error"]
    assert not vm.transactions
    assert not vm.previewCsv(options)["error"]
    assert vm.importCsv([0, 1, 2])["imported"] == 3
    assert "Salary" in viewmodel.FinanceViewModel().categories
    assert vm.summaryFor("Month", "2024-02-01")["net"] == "$863.00"


def test_bad_files_and_mapping_are_reported(vm, tmp_path):
    multi = write_csv(
        tmp_path,
        [
            ["Account Number", "Date", "Description", "Amount"],
            ["0000", "2024-01-01", "One", "-1"],
            ["0001", "2024-01-02", "Two", "-1"],
        ],
    )
    assert "multiple account" in vm.loadCsv(multi, "comma")["error"].lower()
    bad = tmp_path / "bad.csv"
    bad.write_bytes(b"Date,Description,Amount\n\xff")
    assert "UTF-8" in vm.loadCsv(QUrl.fromLocalFile(str(bad)), "comma")["error"]
    malformed = write_csv(
        tmp_path,
        [["Date", "Description", "Amount"], ["2024-01-01", "One"]],
        name="short.csv",
    )
    assert not vm.loadCsv(malformed, "comma")["error"]
    options = settings(
        vm,
        date=0,
        description=1,
        amount=2,
        type=-1,
        category=-1,
        dateFormat="iso",
        direction="signed",
    )
    assert "different columns" in vm.previewCsv({**options, "description": 0})["error"]
    row = vm.previewCsv(options)["rows"][0]
    assert not row["valid"] and "Column count" in row["status"]
    assert vm.importCsv([0])["error"]
    assert not vm.transactions


def test_separate_amount_columns_and_invalid_rows(vm, tmp_path):
    file_url = write_csv(
        tmp_path,
        [
            ["Date", "Description", "Debit", "Credit", "Category"],
            ["2024-01-02", "Purchase", "3.25", "", "Food"],
            ["2024-01-03", "Refund", "", "2.00", "Food"],
            ["2024-01-04", "Ambiguous", "1.00", "1.00", ""],
            ["2024-01-05", "Empty", "", "0", ""],
        ],
    )
    loaded = vm.loadCsv(file_url, "comma")
    assert loaded["suggestions"]["direction"] == "columns"
    options = {**loaded["suggestions"], "accountId": vm.accounts[0]["id"]}
    rows = vm.previewCsv(options)["rows"]
    assert [(row["kind"], row["valid"]) for row in rows] == [
        ("expense", True),
        ("income", True),
        ("", False),
        ("", False),
    ]
    assert vm.importCsv([0, 1])["imported"] == 2
    assert vm.summaryFor("Month", "2024-01-01")["net"] == "$98.75"


def test_reverse_signed_amounts(vm, tmp_path):
    file_url = write_csv(tmp_path, [
        ["Date", "Description", "Amount"],
        ["2024-01-02", "Purchase", "3.25"],
        ["2024-01-03", "Refund", "-2.00"],
    ])
    loaded = vm.loadCsv(file_url, "comma")
    options = {**loaded["suggestions"], "accountId": vm.accounts[0]["id"], "direction": "reverse"}
    rows = vm.previewCsv(options)["rows"]
    assert [row["kind"] for row in rows] == ["expense", "income"]


def test_database_failure_rolls_back_transactions_and_categories(vm, tmp_path):
    file_url = write_csv(
        tmp_path,
        [
            ["Date", "Description", "Amount", "Category"],
            ["2024-01-02", "First", "-3", "New category"],
            ["2024-01-03", "Second", "-4", "New category"],
        ],
    )
    loaded = vm.loadCsv(file_url, "comma")
    options = {**loaded["suggestions"], "accountId": vm.accounts[0]["id"]}
    assert not vm.previewCsv(options)["error"]
    engine = viewmodel.SessionLocal.kw["bind"]

    def fail_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith("insert into finance_transactions"):
            raise IntegrityError(statement, None, Exception("synthetic failure"))

    event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        assert "No transactions were added" in vm.importCsv([0, 1])["error"]
    finally:
        event.remove(engine, "before_cursor_execute", fail_insert)
    fresh = viewmodel.FinanceViewModel()
    assert not fresh.transactions
    with viewmodel.SessionLocal() as session:
        assert "New category" not in list(session.scalars(select(FinanceCategory.name)))


def test_delete_all_invalidates_csv_preview(vm, tmp_path):
    url = write_csv(tmp_path, [["Date", "Description", "Amount"], ["2024-01-02", "Purchase", "-3"]])
    loaded = vm.loadCsv(url, "comma")
    options = {**loaded["suggestions"], "accountId": vm.accounts[0]["id"]}
    assert not vm.previewCsv(options)["error"]
    assert not vm.deleteAllTransactions()
    assert "changed" in vm.importCsv([0])["error"]
