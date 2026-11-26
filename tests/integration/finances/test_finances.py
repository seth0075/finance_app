from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from finance_app.core import database
from finance_app.core.database import Base
from finance_app.features.finances import viewmodel


@pytest.fixture
def vm(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=engine))
    return viewmodel.FinanceViewModel()


def account(vm, name, kind, opening, limit=""):
    assert vm.saveAccount("", name, kind, "2024-01-01", opening, limit) == ""
    return next(item["id"] for item in vm.accounts if item["name"] == name)


def transaction(
    vm,
    title,
    kind,
    amount,
    account_id,
    destination="",
    category="Food",
    day="2024-01-10",
    recurrence="none",
    active=False,
):
    return vm.saveTransaction(
        "",
        day,
        title,
        kind,
        amount,
        account_id,
        destination,
        category,
        recurrence,
        active,
    )


def test_balances_transfers_categories_and_charts(vm):
    bank = account(vm, "Checking", "bank", "1000.00")
    credit = account(vm, "Card", "credit", "100.00", "1000.00")
    assert transaction(vm, "Salary", "income", "500", bank, category="Salary") == ""
    assert transaction(vm, "Food", "expense", "200", credit) == ""
    assert transaction(vm, "Payment", "transfer", "150", bank, destination=credit) == ""
    summary = vm.summaryFor("Month", "2024-01-20")
    assert (
        summary["income"],
        summary["expenses"],
        summary["net"],
        summary["available"],
    ) == ("$500.00", "$200.00", "$1,200.00", "$850.00")
    assert {row["name"]: row["balanceDisplay"] for row in summary["accounts"]} == {
        "Checking": "$1,350.00",
        "Card": "$150.00",
    }
    assert [(row["name"], row["amount"]) for row in summary["pie"]] == [
        ("Food", "$200.00")
    ]
    assert summary["bars"][9]["income"] == 50000
    assert summary["bars"][9]["expense"] == 20000
    assert summary["lines"][-1]["balance"] == 120000
    assert "Salary" in viewmodel.FinanceViewModel().categories
    assert vm.deleteAccount(bank)
    assert vm.saveAccount(bank, "Checking", "credit", "2024-01-01", "1000", "1000")
    assert transaction(vm, "Invalid", "transfer", "5", bank, destination=bank)
    assert transaction(vm, "Invalid amount", "income", "1.234", bank)


def test_subscription_forecasts_are_not_recorded(vm):
    bank = account(vm, "Checking", "bank", "100")
    today = date.today()
    month = today.month % 12 + 1
    year = today.year + (1 if today.month == 12 else 0)
    next_month = date(year, month, 1)
    assert (
        transaction(
            vm,
            "Streaming",
            "expense",
            "12.99",
            bank,
            day=today.isoformat(),
            recurrence="monthly",
            active=True,
        )
        == ""
    )
    summary = vm.summaryFor("Month", next_month.isoformat())
    assert summary["expenses"] == "$0.00"
    assert len(summary["forecasts"]) == 1
    assert summary["forecasts"][0]["amount"] == "$12.99"
    assert len(vm.transactions) == 1
    assert list(
        viewmodel.subscription_dates(
            date(2024, 1, 31), "monthly", date(2024, 2, 1), date(2024, 3, 31)
        )
    ) == [date(2024, 2, 29), date(2024, 3, 31)]
    assert list(
        viewmodel.subscription_dates(
            date(2024, 2, 29), "yearly", date(2025, 1, 1), date(2025, 12, 31)
        )
    ) == [date(2025, 2, 28)]
    entry = vm.transactions[0]
    assert (
        vm.saveTransaction(
            entry["id"],
            entry["date"],
            entry["title"],
            entry["kind"],
            entry["amount"],
            bank,
            "",
            entry["category"],
            "monthly",
            False,
        )
        == ""
    )
    assert vm.summaryFor("Month", next_month.isoformat())["forecasts"] == []


def test_future_charts_include_forecasts_until_period_starts(vm, monkeypatch):
    class FixedDate(date):
        current = date(2024, 1, 20)

        @classmethod
        def today(cls):
            return cls.current

    monkeypatch.setattr(viewmodel, "date", FixedDate)
    bank = account(vm, "Checking", "bank", "100")
    assert not transaction(
        vm, "Monthly", "expense", "10", bank, day="2024-01-10",
        recurrence="monthly", active=True,
    )
    assert not transaction(
        vm, "Inactive", "expense", "2", bank, day="2024-01-12",
        recurrence="monthly", active=False,
    )
    assert not transaction(
        vm, "Annual", "expense", "20", bank, category="Health", day="2020-02-29",
        recurrence="yearly", active=True,
    )
    assert not transaction(vm, "Recorded", "expense", "3", bank, day="2024-02-10")
    assert not transaction(
        vm, "Pay", "income", "50", bank, category="Income", day="2024-02-15"
    )
    february = vm.summaryFor("Month", "2024-02-01")
    assert february["futureEstimate"]
    assert february["expenses"] == "$3.00"
    assert {row["name"]: row["value"] for row in february["pie"]} == {
        "Food": 1300,
        "Health": 2000,
    }
    assert february["bars"][9]["expense"] == 1300
    assert february["bars"][28]["expense"] == 2000
    assert february["lines"][-1]["expense"] == 3300
    assert february["lines"][-1]["income"] == 5000
    assert february["lines"][-1]["balance"] == 13500
    assert len(vm.transactions) == 5

    next_year = vm.summaryFor("Year", "2025-01-01")
    assert next_year["futureEstimate"]
    assert next_year["bars"][0]["expense"] == 1000
    assert next_year["bars"][1]["expense"] == 3000
    assert next_year["lines"][-1]["expense"] == 14000
    assert next_year["lines"][-1]["balance"] == 13500

    FixedDate.current = date(2024, 2, 9)
    upcoming = vm.summaryFor("Day", "2024-02-10")
    assert upcoming["futureEstimate"]
    assert upcoming["bars"][-1]["expense"] == 1300
    assert upcoming["pie"][0]["value"] == 1300
    later_day = vm.summaryFor("Day", "2024-02-15")
    assert later_day["bars"][1]["expense"] == 1300
    assert later_day["lines"][-1]["expense"] == 1300
    assert later_day["pie"] == []

    FixedDate.current = date(2024, 2, 10)
    current_day = vm.summaryFor("Day", "2024-02-10")
    assert not current_day["futureEstimate"]
    assert current_day["bars"][-1]["expense"] == 300
    assert current_day["pie"][0]["value"] == 300
    current_month = vm.summaryFor("Month", "2024-02-01")
    assert not current_month["futureEstimate"]
    assert current_month["lines"][-1]["expense"] == 300
    assert current_month["pie"][0]["value"] == 300
    assert not vm.summaryFor("Year", "2024-01-01")["futureEstimate"]
    assert vm.summaryFor("Year", "2024-01-01")["lines"][-1]["expense"] == 1500


def test_day_year_ranges_and_historical_openings(vm):
    bank = account(vm, "Checking", "bank", "100")
    assert transaction(vm, "Expense", "expense", "25", bank) == ""
    before = vm.summaryFor("Day", "2023-12-31")
    assert before["net"] == "$0.00"
    year = vm.summaryFor("Year", "2024-06-01")
    assert len(year["bars"]) == 12
    assert year["bars"][0]["expense"] == 2500
    assert year["lines"][0]["balance"] == 7500
    assert vm.summaryFor("Day", "invalid")["error"]


def test_preopening_transactions_reconstruct_snapshot_and_transfer_balances(vm):
    bank = account(vm, "Checking", "bank", "100")
    assert vm.saveAccount("", "Card", "credit", "2024-01-05", "40", "1000") == ""
    credit = next(item["id"] for item in vm.accounts if item["name"] == "Card")
    assert transaction(vm, "Older expense", "expense", "20", bank, day="2023-12-30") == ""
    assert transaction(vm, "Older income", "income", "10", bank, day="2023-12-31") == ""
    assert transaction(vm, "Payment", "transfer", "10", bank, destination=credit, day="2023-12-31") == ""
    assert transaction(vm, "Card purchase", "expense", "5", credit, day="2024-01-03") == ""
    assert transaction(vm, "New expense", "expense", "5", bank, day="2024-01-06") == ""
    before = vm.summaryFor("Day", "2023-12-29")
    assert before["net"] == "$0.00"
    day1 = vm.summaryFor("Day", "2023-12-30")
    assert day1["net"] == "$100.00"
    assert day1["lines"][-1]["balance"] == 10000
    day2 = vm.summaryFor("Day", "2023-12-31")
    assert {row["name"]: row["balanceDisplay"] for row in day2["accounts"]} == {
        "Checking": "$100.00", "Card": "$35.00"
    }
    assert day2["net"] == "$65.00"
    assert day2["available"] == "$965.00"
    assert day2["lines"][-1]["balance"] == 6500
    opening = vm.summaryFor("Day", "2024-01-05")
    assert opening["net"] == "$60.00"
    assert opening["lines"][-1]["balance"] == 6000
    after = vm.summaryFor("Day", "2024-01-06")
    assert after["net"] == "$55.00"
    assert after["lines"][-1]["balance"] == 5500
    assert vm.saveAccount(bank, "Checking", "bank", "2024-01-07", "100", "") == ""
    assert vm.summaryFor("Day", "2024-01-07")["net"] == "$60.00"


def test_edits_and_reopening_preserve_accounts_transactions_and_categories(vm):
    bank = account(vm, "Checking", "bank", "100")
    assert transaction(vm, "Original", "expense", "10.10", bank, category="Travel") == ""
    original = vm.transactions[0]
    assert vm.saveTransaction(
        original["id"], "2024-01-11", "Updated", "expense", "20.25",
        bank, "", "travel", "none", False,
    ) == ""
    assert vm.saveAccount(bank, "Checking", "bank", "2024-01-01", "200", "") == ""
    reopened = viewmodel.FinanceViewModel()
    assert reopened.transactions[0]["category"] == "Travel"
    assert reopened.summaryFor("Month", "2024-01-01")["net"] == "$179.75"
    assert reopened.deleteTransaction(original["id"]) == ""
    assert "Travel" in reopened.categories
    assert reopened.deleteAccount(bank) == ""


def test_bulk_categories_are_atomic_and_colors_persist(vm):
    bank = account(vm, "Checking", "bank", "100")
    other = account(vm, "Savings", "bank", "0")
    assert not transaction(vm, "Lunch", "expense", "10", bank)
    assert not transaction(vm, "Dinner", "expense", "20", bank)
    assert not transaction(vm, "Later", "expense", "30", bank, day="2025-01-10")
    assert not transaction(vm, "Transfer", "transfer", "5", bank, destination=other)
    by_name = {item["title"]: item["id"] for item in vm.transactions}
    ids = [by_name["Lunch"], by_name["Dinner"]]

    assert vm.saveCategory("Travel", "red", True)
    assert vm.saveCategory("food", "#123456", True)
    assert not vm.saveCategory("Travel", "#12ab34", True)
    assert vm.assignCategory([], "Travel")
    assert vm.assignCategory([ids[0], ids[0]], "Travel")
    assert vm.assignCategory([ids[0], "missing"], "Travel")
    assert vm.assignCategory([ids[0], by_name["Transfer"]], "Travel")
    assert vm.assignCategory(ids, "missing")
    assert all(t["category"] == "Food" for t in vm.transactions if t["kind"] == "expense")

    engine = viewmodel.SessionLocal.kw["bind"]

    def fail_update(connection, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith("update finance_transactions"):
            raise IntegrityError(statement, None, Exception("synthetic"))

    event.listen(engine, "before_cursor_execute", fail_update)
    try:
        assert "No transactions were changed" in vm.assignCategory(ids, "Travel")
    finally:
        event.remove(engine, "before_cursor_execute", fail_update)
    assert all(t["category"] == "Food" for t in viewmodel.FinanceViewModel().transactions if t["kind"] == "expense")
    assert not vm.assignCategory(ids, "Travel")
    reopened = viewmodel.FinanceViewModel()
    assert {t["title"]: t["category"] for t in reopened.transactions} == {
        "Lunch": "Travel", "Dinner": "Travel", "Later": "Food", "Transfer": ""
    }
    assert next(c for c in reopened.categoryDetails if c["name"] == "Travel")["color"] == "#12AB34"
    assert reopened.summaryFor("Month", "2024-01-10")["pie"][0]["color"] == "#12AB34"
    assert not reopened.saveCategory("Travel", "#ABCDEF", False)
    assert viewmodel.FinanceViewModel().summaryFor("Month", "2024-01-10")["pie"][0]["color"] == "#ABCDEF"


def test_category_color_migration_preserves_existing_data(monkeypatch, tmp_path):
    url = f"sqlite:///{(tmp_path / 'finance.db').as_posix()}"
    monkeypatch.setattr(database, "DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "af17de081539")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO finance_categories (name) VALUES ('Existing')"))
    monkeypatch.setattr(database, "engine", engine)
    with pytest.raises(RuntimeError, match="Finance database needs upgrading"):
        database.initialize_database()
    command.upgrade(config, "head")
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=engine))
    vm = viewmodel.FinanceViewModel()
    assert next(c for c in vm.categoryDetails if c["name"] == "Existing")["color"] == ""
    assert not vm.saveCategory("Existing", "#123456", False)
    assert viewmodel.FinanceViewModel().categoryDetails
    command.downgrade(config, "af17de081539")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT name FROM finance_categories WHERE name = 'Existing'")) == "Existing"
