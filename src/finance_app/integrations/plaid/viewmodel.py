import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from threading import Thread

import httpx
import keyring.errors
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from finance_app.core.credentials import (
    delete_credential,
    get_credential,
    save_credential,
)
from finance_app.core.database import SessionLocal
from finance_app.features.finances.amounts import amount_input, money
from finance_app.features.finances.models import (
    FinanceAccount,
    FinanceTransaction,
    PlaidImportedTransaction,
    new_id,
)
from finance_app.integrations.plaid.client import PlaidAPIError, PlaidClient

logger = logging.getLogger(__name__)


class PlaidRecoveryError(Exception):
    pass


def amount_cents(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid amount.") from exc
    if (
        not amount.is_finite()
        or amount * 100 != (amount * 100).to_integral_value()
        or abs(amount) > Decimal("999999999999.99")
    ):
        raise ValueError("Invalid amount.")
    return int(amount * 100)


def fetch_snapshot(client, token):
    accounts = client.get_accounts(token)["accounts"]
    for attempt in range(3):
        cursor = ""
        cursors = set()
        transactions = {}
        try:
            for _ in range(200):
                page = client.sync_transactions(token, cursor)
                for item in page["added"] + page["modified"]:
                    transactions[item["transaction_id"]] = item
                for item in page["removed"]:
                    transactions.pop(item["transaction_id"], None)
                next_cursor = page["next_cursor"]
                if not page["has_more"]:
                    return (
                        accounts,
                        list(transactions.values()),
                        page.get(
                            "transactions_update_status",
                            "TRANSACTIONS_UPDATE_STATUS_UNKNOWN",
                        ),
                    )
                if not next_cursor or next_cursor in cursors:
                    raise ValueError("Plaid returned an invalid pagination cursor.")
                cursors.add(next_cursor)
                cursor = next_cursor
            raise ValueError("Plaid transaction history exceeds the supported limit.")
        except PlaidAPIError as exc:
            if (
                exc.code != "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION"
                or attempt == 2
            ):
                raise
    raise ValueError("Could not retrieve transaction history.")


def describe_accounts(accounts):
    result = []
    for account in accounts:
        if account.get("type") not in ("credit", "depository"):
            continue
        balances = account.get("balances") or {}
        current = balances.get("current")
        limit = balances.get("limit")
        current_amount = ""
        limit_amount = ""
        display = "Unavailable"
        limit_display = "Unavailable"
        try:
            if (
                current is not None
                and balances.get("iso_currency_code") == "USD"
                and not balances.get("unofficial_currency_code")
            ):
                current_cents = amount_cents(current)
                current_amount = amount_input(current_cents)
                display = money(current_cents)
        except ValueError:
            display = "Unavailable"
        try:
            if (
                account["type"] == "credit"
                and limit is not None
                and balances.get("iso_currency_code") == "USD"
                and not balances.get("unofficial_currency_code")
            ):
                limit_cents = amount_cents(limit)
                if limit_cents >= 0:
                    limit_amount = amount_input(limit_cents)
                    limit_display = money(limit_cents)
        except ValueError:
            limit_display = "Unavailable"
        name = account.get("name") or "Account"
        mask = account.get("mask") or ""
        result.append(
            {
                "id": account["account_id"],
                "name": name,
                "displayName": name + (f" · {mask}" if mask else ""),
                "mask": mask,
                "kind": "credit" if account["type"] == "credit" else "bank",
                "balance": display,
                "balanceAmount": current_amount,
                "creditLimitAmount": limit_amount,
                "creditLimit": limit_display,
                "currency": balances.get("iso_currency_code") or "unknown currency",
            }
        )
    return result


class PlaidViewModel(QObject):
    changed = Signal()
    _finished = Signal(str, object, str)

    def __init__(self, finance, parent=None):
        super().__init__(parent)
        self._finance = finance
        self._busy = False
        self._environment = ""
        self._link_token = ""
        self._accounts = []
        self._transactions = []
        self._preview = None
        self._status = "Not connected. Configure Plaid to link an account."
        self._finished.connect(self._complete)
        try:
            environment = get_credential("plaid_active_environment")
            if environment in ("sandbox", "production") and get_credential(
                f"plaid_{environment}_access_token"
            ):
                self._environment = environment
                self._status = "Connected. Refresh to load accounts and transactions."
        except keyring.errors.KeyringError:
            logger.error("Could not read Plaid credentials from the credential store.")
            self._status = (
                "Could not read Plaid credentials from the system credential store."
            )

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(bool, notify=changed)
    def connected(self):
        return bool(self._environment)

    @Property(bool, notify=changed)
    def linkPending(self):
        return bool(self._link_token)

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(str, notify=changed)
    def environment(self):
        return self._environment

    @Property("QVariantList", notify=changed)
    def accounts(self):
        return self._accounts

    def _start(self, operation, args=()):
        if self._busy:
            return
        self._busy = True
        self._status = "Contacting Plaid..."
        self.changed.emit()
        Thread(target=self._run, args=(operation, args), daemon=True).start()

    def _run(self, operation, args):
        try:
            result = getattr(self, f"_do_{operation}")(*args)
            self._finished.emit(operation, result, "")
        except PlaidRecoveryError as exc:
            logger.error("Plaid credential recovery failed.")
            self._finished.emit(operation, None, str(exc))
        except (
            PlaidAPIError,
            httpx.HTTPError,
            keyring.errors.KeyringError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
        ) as exc:
            code = (
                exc.code
                if isinstance(exc, PlaidAPIError)
                and isinstance(exc.code, str)
                and re.fullmatch(r"[A-Z0-9_]+", exc.code)
                else type(exc).__name__
            )
            logger.error("Plaid %s failed (%s).", operation, code)
            if code == "ITEM_LOGIN_REQUIRED":
                self._finished.emit(
                    operation,
                    None,
                    "Plaid requires you to reconnect. Disconnect the item in Settings, then link it again and review duplicates.",
                )
                return
            self._finished.emit(
                operation,
                None,
                f"Plaid {operation} failed ({code}). Check your credentials, access, and connection.",
            )
        except Exception as exc:  # noqa: BLE001 - prevent a worker failure leaving the UI busy
            logger.error(
                "Plaid %s failed unexpectedly (%s).", operation, type(exc).__name__
            )
            self._finished.emit(
                operation,
                None,
                f"Plaid {operation} failed unexpectedly. Please try again.",
            )

    def _do_link(self, environment, client_id, secret):
        save_credential("plaid_client_id", client_id)
        save_credential(f"plaid_{environment}_secret", secret)
        response = PlaidClient(environment).create_link_token()
        return environment, response["link_token"], response["hosted_link_url"]

    def _do_finish(self, environment, link_token):
        client = PlaidClient(environment)
        sessions = client.get_link_session(link_token)["link_sessions"]
        results = [
            item
            for session in sessions
            for item in (session.get("results") or {}).get("item_add_results", [])
            if item.get("public_token")
        ]
        if not results:
            return None
        if len(results) != 1:
            raise ValueError("Expected one linked item.")
        token = client.exchange_public_token(results[0]["public_token"])["access_token"]
        try:
            save_credential(f"plaid_{environment}_access_token", token)
            save_credential("plaid_active_environment", environment)
        except keyring.errors.KeyringError:
            try:
                client.remove_item(token)
            except PlaidAPIError, httpx.HTTPError, ValueError:
                logger.error(
                    "Could not remove Plaid item after credential storage failed."
                )
                raise PlaidRecoveryError(
                    "Could not save credentials or remove the Plaid item. Remove it in the Plaid dashboard to stop possible billing."
                ) from None
            try:
                if get_credential(f"plaid_{environment}_access_token"):
                    delete_credential(f"plaid_{environment}_access_token")
            except keyring.errors.KeyringError:
                logger.error(
                    "Could not remove Plaid token after credential storage failed."
                )
            raise
        return environment

    def _do_refresh(self, environment):
        token = get_credential(f"plaid_{environment}_access_token")
        if not token:
            raise ValueError("Missing access token.")
        accounts, transactions, update_status = fetch_snapshot(
            PlaidClient(environment), token
        )
        return describe_accounts(accounts), transactions, update_status

    def _do_disconnect(self, environment):
        token = get_credential(f"plaid_{environment}_access_token")
        if not token:
            raise ValueError("Missing access token.")
        PlaidClient(environment).remove_item(token)
        delete_credential(f"plaid_{environment}_access_token")
        delete_credential("plaid_active_environment")

    @Slot(str, object, str)
    def _complete(self, operation, result, error):
        self._busy = False
        if error:
            self._status = error
        elif operation == "link":
            self._pending_environment, self._link_token, url = result
            link_url = QUrl(url)
            if (
                link_url.scheme() != "https"
                or link_url.host() != "secure.plaid.com"
                or not QDesktopServices.openUrl(link_url)
            ):
                self._link_token = ""
                self._status = "Could not open the browser. Try linking again."
            else:
                self._status = (
                    "Complete Plaid Link in your browser, then choose Finish linking."
                )
        elif operation == "finish":
            if result is None:
                self._status = (
                    "Link is not complete. Finish in your browser and try again."
                )
            else:
                self._environment = result
                self._link_token = ""
                self._status = "Connected. Refresh to load accounts and transactions."
        elif operation == "refresh":
            accounts, transactions, update_status = result
            self._accounts = accounts
            self._transactions = transactions
            self._preview = None
            history_status = {
                "NOT_READY": "Plaid is still loading transactions. Refresh again later.",
                "INITIAL_UPDATE_COMPLETE": "Recent transactions are ready; older history is still loading. Refresh again later.",
                "HISTORICAL_UPDATE_COMPLETE": "Plaid transaction history is ready to review.",
            }.get(
                update_status,
                "Plaid did not report whether transaction history is complete. Refresh again later.",
            )
            self._status = (
                "Accounts refreshed; balances may be cached. " + history_status
            )
        elif operation == "disconnect":
            self._environment = ""
            self._accounts = []
            self._transactions = []
            self._preview = None
            self._status = (
                "Disconnected. Previously imported transactions remain in the app."
            )
        self.changed.emit()

    @Slot(str, str, str)
    def link(self, environment, client_id, secret):
        if self.connected or self.linkPending:
            self._status = "Finish or disconnect the existing connection first."
            self.changed.emit()
        elif (
            environment not in ("sandbox", "production")
            or not client_id.strip()
            or not secret.strip()
        ):
            self._status = (
                "Enter a Plaid client ID and the secret for the selected environment."
            )
            self.changed.emit()
        else:
            self._start("link", (environment, client_id.strip(), secret.strip()))

    @Slot()
    def finishLink(self):
        if self._link_token:
            self._start("finish", (self._pending_environment, self._link_token))

    @Slot()
    def cancelLink(self):
        if not self._busy:
            self._link_token = ""
            self._status = "Link cancelled. If you finished in the browser, remove any unused item in your Plaid dashboard."
            self.changed.emit()

    @Slot()
    def refresh(self):
        if self.connected:
            self._start("refresh", (self._environment,))

    @Slot()
    def disconnect(self):
        if self.connected:
            self._start("disconnect", (self._environment,))

    @Slot(str, str, result="QVariantMap")
    def preview(self, remote_id, account_id):
        self._preview = None
        remote = next((a for a in self._accounts if a["id"] == remote_id), None)
        account = next(
            (a for a in self._finance.accounts if a["id"] == account_id), None
        )
        if remote is None or account is None:
            return {"error": "Choose a linked account and a local account."}
        if remote["kind"] != account["kind"]:
            return {"error": "Choose a local account with the same account type."}
        existing = {
            (t["date"], t["title"].strip().casefold(), t["kind"], t["amountCents"])
            for t in self._finance.transactions
            if t["accountId"] == account_id
        }
        with SessionLocal() as session:
            imported = set(session.scalars(select(PlaidImportedTransaction.source_id)))
        rows = []
        seen = set()
        for item in self._transactions:
            if item.get("account_id") != remote_id:
                continue
            row = {
                "sourceId": "",
                "date": str(item.get("date") or ""),
                "title": str(item.get("name") or ""),
                "amount": "",
                "kind": "",
                "valid": False,
                "selected": False,
                "status": "",
            }
            try:
                source_id = self._environment + ":" + item["transaction_id"]
                if len(source_id) > 256:
                    raise ValueError("Invalid transaction ID.")
                row["sourceId"] = source_id
                if item.get("pending"):
                    raise ValueError("Pending transactions cannot be imported.")
                if item.get("iso_currency_code") != "USD":
                    raise ValueError("Only USD transactions can be imported.")
                day = date.fromisoformat(row["date"]).isoformat()
                title = row["title"].strip()
                if not title or len(title) > 200:
                    raise ValueError("Description must contain 1–200 characters.")
                cents = amount_cents(item["amount"])
                if not cents:
                    raise ValueError("Amount must be greater than zero.")
                kind = "expense" if cents > 0 else "income"
                cents = abs(cents)
                row.update(
                    date=day,
                    title=title,
                    amount=money(cents),
                    amountCents=cents,
                    kind=kind,
                )
                key = (day, title.casefold(), kind, cents)
                if source_id in imported:
                    raise ValueError("Already imported from Plaid.")
                warning = (
                    "Possible duplicate in local transactions."
                    if key in existing
                    else ("Possible duplicate in this import." if key in seen else "")
                )
                seen.add(key)
                row.update(valid=True, selected=not warning, status=warning)
            except (ValueError, KeyError, TypeError) as exc:
                row["status"] = (
                    str(exc)
                    if isinstance(exc, ValueError)
                    else "Invalid transaction data."
                )
            rows.append(row)
        self._preview = {
            "rows": [r.copy() for r in rows],
            "accountId": account_id,
            "revision": self._finance._revision,
        }
        return {"error": "", "rows": rows}

    @Slot("QVariantList", result="QVariantMap")
    def importSelected(self, indices):
        preview = self._preview
        if preview is None or preview["revision"] != self._finance._revision:
            return {"error": "Data changed. Generate a new preview."}
        if not indices:
            return {"error": "Select at least one valid transaction."}
        if any(
            not isinstance(i, int)
            or isinstance(i, bool)
            or i < 0
            or i >= len(preview["rows"])
            for i in indices
        ) or len(indices) != len(set(indices)):
            return {"error": "Invalid selection."}
        rows = [preview["rows"][i] for i in indices]
        if any(not row["valid"] for row in rows):
            return {"error": "Invalid transactions cannot be imported."}
        try:
            with SessionLocal() as session:
                if session.get(FinanceAccount, preview["accountId"]) is None:
                    return {"error": "The local account no longer exists."}
                source_ids = [row["sourceId"] for row in rows]
                for start in range(0, len(source_ids), 500):
                    if session.scalar(
                        select(PlaidImportedTransaction.source_id).where(
                            PlaidImportedTransaction.source_id.in_(source_ids[start:start + 500])
                        ).limit(1)
                    ):
                        return {
                            "error": "A transaction was already imported. Generate a new preview."
                        }
                for row in rows:
                    transaction_id = new_id()
                    transaction = FinanceTransaction(
                        id=transaction_id,
                        date=date.fromisoformat(row["date"]),
                        title=row["title"],
                        kind=row["kind"],
                        amount_cents=row["amountCents"],
                        account_id=preview["accountId"],
                        category="Uncategorized",
                        recurrence="none",
                        subscription_active=False,
                    )
                    session.add(transaction)
                    session.add(
                        PlaidImportedTransaction(
                            source_id=row["sourceId"], transaction_id=transaction_id
                        )
                    )
                session.commit()
        except SQLAlchemyError as exc:
            logger.error("Plaid import failed (%s).", type(exc).__name__)
            return {"error": "Could not save the import. No transactions were added."}
        self._preview = None
        self._finance._refresh()
        return {"error": "", "imported": len(rows)}
