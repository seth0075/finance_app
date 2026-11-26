from decimal import Decimal

import httpx
import keyring.errors
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.finances import viewmodel as finance_module
from finance_app.features.finances.models import (
    FinanceTransaction,
    PlaidImportedTransaction,
)
from finance_app.integrations.plaid import client as client_module
from finance_app.integrations.plaid import viewmodel as plaid_module
from finance_app.integrations.plaid.client import PlaidAPIError


@pytest.fixture
def plaid(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(finance_module, "SessionLocal", sessions)
    monkeypatch.setattr(plaid_module, "SessionLocal", sessions)
    monkeypatch.setattr(plaid_module, "get_credential", lambda name: None)
    finance = finance_module.FinanceViewModel()
    assert not finance.saveAccount("", "Checking", "bank", "2024-01-01", "100", "")
    result = plaid_module.PlaidViewModel(finance)
    result._environment = "sandbox"
    result._complete(
        "refresh",
        (
            plaid_module.describe_accounts(
                [
                    {
                        "account_id": "remote",
                        "name": "Checking",
                        "mask": "1234",
                        "type": "depository",
                        "balances": {
                            "current": Decimal("12.34"),
                            "iso_currency_code": "USD",
                        },
                    }
                ]
            ),
            [
                {
                    "account_id": "remote",
                    "transaction_id": "one",
                    "date": "2023-12-01",
                    "name": "Lunch",
                    "amount": Decimal("5.00"),
                    "iso_currency_code": "USD",
                    "pending": False,
                },
                {
                    "account_id": "remote",
                    "transaction_id": "two",
                    "date": "2023-12-01",
                    "name": "Lunch",
                    "amount": Decimal("5.00"),
                    "iso_currency_code": "USD",
                    "pending": False,
                },
                {
                    "account_id": "remote",
                    "transaction_id": "three",
                    "date": "2024-01-02",
                    "name": "Refund",
                    "amount": Decimal("-2.00"),
                    "iso_currency_code": "USD",
                    "pending": False,
                },
                {
                    "account_id": "remote",
                    "transaction_id": "pending",
                    "date": "2024-01-02",
                    "name": "Pending",
                    "amount": Decimal("1.00"),
                    "iso_currency_code": "USD",
                    "pending": True,
                },
                {
                    "account_id": "remote",
                    "transaction_id": "foreign",
                    "date": "2024-01-02",
                    "name": "Foreign",
                    "amount": Decimal("1.00"),
                    "iso_currency_code": "CAD",
                    "pending": False,
                },
            ],
            "HISTORICAL_UPDATE_COMPLETE",
        ),
        "",
    )
    return result, finance, sessions


def test_preview_import_deduplicates_and_preserves_opening_snapshot(plaid):
    model, finance, _ = plaid
    assert model.accounts[0]["balance"] == "$12.34"
    account_id = finance.accounts[0]["id"]
    result = model.preview("remote", account_id)
    rows = result["rows"]
    assert [row["selected"] for row in rows] == [True, False, True, False, False]
    assert [row["kind"] for row in rows[:3]] == ["expense", "expense", "income"]
    assert "Pending" in rows[3]["status"]
    assert "USD" in rows[4]["status"]
    assert model.importSelected([0, 3])["error"]
    assert not finance.transactions
    assert model.importSelected([0, 1, 2]) == {"error": "", "imported": 3}
    assert finance.accounts[0]["openingAmount"] == "100.00"
    assert finance.summaryFor("Day", "2024-01-02")["net"] == "$102.00"
    again = model.preview("remote", account_id)["rows"]
    assert all(
        not row["valid"] and "Already imported" in row["status"] for row in again[:3]
    )


def test_existing_duplicate_stale_preview_and_account_type(plaid):
    model, finance, _ = plaid
    bank = finance.accounts[0]["id"]
    assert not finance.saveTransaction(
        "", "2023-12-01", "Lunch", "expense", "5", bank, "", "Food", "none", False
    )
    assert not model.preview("remote", bank)["rows"][0]["selected"]
    assert not finance.saveAccount("", "Card", "credit", "2024-01-01", "0", "100")
    card = next(a["id"] for a in finance.accounts if a["kind"] == "credit")
    assert "same account type" in model.preview("remote", card)["error"]
    assert not model.preview("remote", bank)["error"]
    assert not finance.saveAccount("", "Other", "bank", "2024-01-01", "0", "")
    assert "changed" in model.importSelected([0])["error"]


def test_import_failure_rolls_back_ids_and_transactions(plaid):
    model, finance, sessions = plaid
    assert not model.preview("remote", finance.accounts[0]["id"])["error"]
    engine = sessions.kw["bind"]

    def fail_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith("insert into plaid_imported_transactions"):
            raise IntegrityError(statement, None, Exception("synthetic"))

    event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        assert "No transactions were added" in model.importSelected([0, 2])["error"]
    finally:
        event.remove(engine, "before_cursor_execute", fail_insert)
    with sessions() as session:
        assert not list(session.scalars(select(FinanceTransaction)))
        assert not list(session.scalars(select(PlaidImportedTransaction)))


def test_delete_all_allows_plaid_reimport_and_invalidates_preview(plaid):
    model, finance, sessions = plaid
    account_id = finance.accounts[0]["id"]
    assert not finance.saveTransaction(
        "", "2024-01-03", "Subscription", "expense", "10",
        account_id, "", "Media", "monthly", True,
    )
    assert not model.preview("remote", account_id)["error"]
    assert model.importSelected([0, 2])["imported"] == 2
    lunch = next(t for t in finance.transactions if t["title"] == "Lunch")
    assert not finance.deleteTransaction(lunch["id"])
    assert "Already imported" in model.preview("remote", account_id)["rows"][0]["status"]
    assert not model.preview("remote", account_id)["error"]

    assert not finance.deleteAllTransactions()
    assert not finance.transactions
    assert finance.accounts[0]["id"] == account_id
    assert finance.accounts[0]["openingAmount"] == "100.00"
    assert finance.summaryFor("Day", "2024-01-03")["net"] == "$100.00"
    assert "Media" in finance.categories
    assert model.connected
    assert "changed" in model.importSelected([1])["error"]
    with sessions() as session:
        assert not list(session.scalars(select(PlaidImportedTransaction)))
    assert model.preview("remote", account_id)["rows"][0]["selected"]
    assert model.importSelected([0])["imported"] == 1


def test_delete_all_rolls_back_plaid_ids_on_failure(plaid):
    model, finance, sessions = plaid
    account_id = finance.accounts[0]["id"]
    assert not model.preview("remote", account_id)["error"]
    assert model.importSelected([0])["imported"] == 1
    engine = sessions.kw["bind"]

    def fail_delete(connection, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith("delete from finance_transactions"):
            raise IntegrityError(statement, None, Exception("synthetic"))

    event.listen(engine, "before_cursor_execute", fail_delete)
    try:
        assert "No transactions were removed" in finance.deleteAllTransactions()
    finally:
        event.remove(engine, "before_cursor_execute", fail_delete)
    with sessions() as session:
        assert len(list(session.scalars(select(FinanceTransaction)))) == 1
        assert len(list(session.scalars(select(PlaidImportedTransaction)))) == 1
    assert len(finance.transactions) == 1


def test_sync_paginates_and_retries_mutation():
    class Client:
        def __init__(self):
            self.calls = []
            self.failed = False

        def get_accounts(self, token):
            return {"accounts": [{"account_id": "a"}]}

        def sync_transactions(self, token, cursor):
            self.calls.append(cursor)
            if cursor == "next" and not self.failed:
                self.failed = True
                raise PlaidAPIError(
                    "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION", "test"
                )
            if not cursor:
                return {
                    "added": [{"transaction_id": "a"}],
                    "modified": [],
                    "removed": [],
                    "next_cursor": "next",
                    "has_more": True,
                }
            return {
                "added": [{"transaction_id": "b"}],
                "modified": [],
                "removed": [{"transaction_id": "a"}],
                "next_cursor": "done",
                "has_more": False,
                "transactions_update_status": "INITIAL_UPDATE_COMPLETE",
            }

    client = Client()
    accounts, transactions, status = plaid_module.fetch_snapshot(client, "fake-token")
    assert accounts == [{"account_id": "a"}]
    assert transactions == [{"transaction_id": "b"}]
    assert status == "INITIAL_UPDATE_COMPLETE"
    assert client.calls == ["", "next", "", "next"]


@pytest.mark.parametrize(
    ("balances", "balance", "limit"),
    [
        (
            {
                "current": Decimal("-12.34"),
                "limit": Decimal("500.00"),
                "iso_currency_code": "USD",
            },
            "-12.34",
            "500.00",
        ),
        ({"current": 0, "limit": 0, "iso_currency_code": "USD"}, "0.00", "0.00"),
        ({"current": None, "limit": None, "iso_currency_code": "USD"}, "", ""),
        ({"current": 50, "limit": 500, "iso_currency_code": "CAD"}, "", ""),
        ({"current": "invalid", "limit": -1, "iso_currency_code": "USD"}, "", ""),
    ],
)
def test_describe_accounts_exposes_only_usable_balance_and_limit(
    balances, balance, limit
):
    account = plaid_module.describe_accounts(
        [{"account_id": "remote", "type": "credit", "balances": balances}]
    )[0]
    assert account["balanceAmount"] == balance
    assert account["creditLimitAmount"] == limit
    assert (account["balance"] == "Unavailable") == (balance == "")
    assert (account["creditLimit"] == "Unavailable") == (limit == "")


@pytest.mark.parametrize(
    ("status", "message"),
    [
        ("NOT_READY", "still loading transactions"),
        ("INITIAL_UPDATE_COMPLETE", "older history is still loading"),
        ("HISTORICAL_UPDATE_COMPLETE", "transaction history is ready"),
        ("TRANSACTIONS_UPDATE_STATUS_UNKNOWN", "did not report"),
        (None, "did not report"),
    ],
)
def test_refresh_reports_transaction_history_status(plaid, monkeypatch, status, message):
    model, _, _ = plaid
    monkeypatch.setattr(plaid_module, "get_credential", lambda name: "test-token")

    class Client:
        def __init__(self, environment):
            assert environment == "sandbox"

        def get_accounts(self, token):
            assert token == "test-token"
            return {"accounts": []}

        def sync_transactions(self, token, cursor):
            assert token == "test-token" and cursor == ""
            page = {
                "added": [],
                "modified": [],
                "removed": [],
                "next_cursor": "done",
                "has_more": False,
            }
            if status is not None:
                page["transactions_update_status"] = status
            return page

    monkeypatch.setattr(plaid_module, "PlaidClient", Client)
    model._complete("refresh", model._do_refresh("sandbox"), "")
    assert message in model.status


def test_client_link_request_and_initial_sync_omit_cursor(monkeypatch):
    secrets = {"plaid_client_id": "test-client", "plaid_sandbox_secret": "test-secret"}
    monkeypatch.setattr(client_module, "get_credential", secrets.get)
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"result": 1})

    monkeypatch.setattr(client_module.httpx, "post", fake_post)
    client = client_module.PlaidClient("sandbox")
    client.create_link_token()
    client.sync_transactions("test-access")
    assert calls[0][0] == "https://sandbox.plaid.com/link/token/create"
    assert calls[0][1]["json"]["transactions"]["days_requested"] == 730
    assert calls[0][1]["json"]["hosted_link"] == {}
    assert "cursor" not in calls[1][1]["json"]
    assert calls[0][1]["headers"]["PLAID-SECRET"] == "test-secret"


def test_hosted_link_exchange_and_disconnect(plaid, monkeypatch):
    model, _, _ = plaid
    values = {}
    monkeypatch.setattr(plaid_module, "get_credential", values.get)
    monkeypatch.setattr(
        plaid_module,
        "save_credential",
        lambda key, value: values.__setitem__(key, value),
    )
    monkeypatch.setattr(plaid_module, "delete_credential", lambda key: values.pop(key))
    removed = []

    class Client:
        def __init__(self, environment):
            assert environment == "sandbox"

        def create_link_token(self):
            return {
                "link_token": "test-link",
                "hosted_link_url": "https://secure.plaid.com/hl/test",
            }

        def get_link_session(self, token):
            assert token == "test-link"
            return {
                "link_sessions": [
                    {"results": {"item_add_results": [{"public_token": "test-public"}]}}
                ]
            }

        def exchange_public_token(self, token):
            assert token == "test-public"
            return {"access_token": "test-access"}

        def remove_item(self, token):
            removed.append(token)

    monkeypatch.setattr(plaid_module, "PlaidClient", Client)
    assert model._do_link("sandbox", "test-client", "test-secret")[1] == "test-link"
    assert model._do_finish("sandbox", "test-link") == "sandbox"
    assert values["plaid_sandbox_access_token"] == "test-access"
    assert values["plaid_active_environment"] == "sandbox"
    model._do_disconnect("sandbox")
    assert removed == ["test-access"]
    assert "plaid_sandbox_access_token" not in values
    assert "plaid_active_environment" not in values


def test_failed_storage_attempts_item_removal(plaid, monkeypatch):
    model, _, _ = plaid
    removed = []

    class Client:
        def __init__(self, environment):
            pass

        def get_link_session(self, token):
            return {
                "link_sessions": [
                    {"results": {"item_add_results": [{"public_token": "test-public"}]}}
                ]
            }

        def exchange_public_token(self, token):
            return {"access_token": "test-access"}

        def remove_item(self, token):
            removed.append(token)

    monkeypatch.setattr(plaid_module, "PlaidClient", Client)

    def fail_save(key, value):
        raise keyring.errors.KeyringError("synthetic")

    monkeypatch.setattr(plaid_module, "save_credential", fail_save)
    with pytest.raises(keyring.errors.KeyringError):
        model._do_finish("sandbox", "test-link")
    assert removed == ["test-access"]


def test_login_required_gives_reconnect_guidance(plaid, monkeypatch):
    model, _, _ = plaid

    def fail_refresh(environment):
        raise PlaidAPIError("ITEM_LOGIN_REQUIRED", "synthetic")

    monkeypatch.setattr(model, "_do_refresh", fail_refresh)
    model._run("refresh", ("sandbox",))
    assert "Disconnect" in model.status and "link it again" in model.status
