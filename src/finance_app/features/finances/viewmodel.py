import calendar
import logging
import re
from collections import defaultdict
from datetime import date, timedelta

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import SQLAlchemyError

from finance_app.core.database import SessionLocal
from finance_app.features.finances import csv_import
from finance_app.features.finances.amounts import amount_input, money, parse_amount
from finance_app.features.finances.models import (
    FinanceAccount,
    FinanceCategory,
    FinanceTransaction,
    PlaidImportedTransaction,
)

CATEGORIES = (
    "Uncategorized",
    "Housing",
    "Food",
    "Transport",
    "Utilities",
    "Shopping",
    "Health",
    "Entertainment",
    "Income",
)
COLORS = (
    "#7395F5",
    "#62C6A0",
    "#E9B76B",
    "#F07878",
    "#AB91E8",
    "#65B6D7",
    "#E78CAD",
    "#B6CE6B",
)
logger = logging.getLogger(__name__)


def parse_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Enter a date in YYYY-MM-DD format.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Enter a valid date in YYYY-MM-DD format.") from exc


def period_range(mode, day):
    if mode == "Day":
        return day, day
    if mode == "Month":
        return day.replace(day=1), day.replace(
            day=calendar.monthrange(day.year, day.month)[1]
        )
    if mode == "Year":
        return date(day.year, 1, 1), date(day.year, 12, 31)
    raise ValueError("Choose Day, Month, or Year.")


def subscription_dates(start, frequency, first, last):
    interval = 1 if frequency == "monthly" else 12
    months = (first.year - start.year) * 12 + first.month - start.month
    index = max(1, months // interval)
    while True:
        month_index = start.year * 12 + start.month - 1 + index * interval
        year, month = divmod(month_index, 12)
        if year > 9999:
            break
        month += 1
        candidate = date(
            year, month, min(start.day, calendar.monthrange(year, month)[1])
        )
        if candidate > last:
            break
        if candidate >= first:
            yield candidate
        index += 1


class FinanceViewModel(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._csv_document = None
        self._csv_preview = None
        self._revision = 0
        with SessionLocal() as session:
            existing = {
                name.casefold()
                for name in session.scalars(select(FinanceCategory.name))
            }
            session.add_all(
                FinanceCategory(name=name)
                for name in CATEGORIES
                if name.casefold() not in existing
            )
            session.commit()
        self._refresh()

    def _refresh(self):
        with SessionLocal() as session:
            self._accounts = [
                {
                    "id": a.id,
                    "name": a.name,
                    "kind": a.kind,
                    "openedOn": a.opened_on.isoformat(),
                    "openingCents": a.opening_cents,
                    "openingAmount": amount_input(a.opening_cents),
                    "creditLimitCents": a.credit_limit_cents,
                    "creditLimit": amount_input(a.credit_limit_cents)
                    if a.credit_limit_cents is not None
                    else "",
                }
                for a in session.scalars(
                    select(FinanceAccount).order_by(FinanceAccount.name)
                )
            ]
            category_rows = list(
                session.scalars(select(FinanceCategory).order_by(FinanceCategory.name))
            )
            self._categories = [category.name for category in category_rows]
            self._category_details = [
                {"name": category.name, "color": category.color or ""}
                for category in category_rows
            ]
            self._category_colors = {
                category.name: category.color for category in category_rows
            }
            self._transactions = [
                {
                    "id": t.id,
                    "date": t.date.isoformat(),
                    "title": t.title,
                    "kind": t.kind,
                    "amountCents": t.amount_cents,
                    "amount": amount_input(t.amount_cents),
                    "accountId": t.account_id,
                    "destinationId": t.destination_id or "",
                    "category": t.category or "",
                    "recurrence": t.recurrence,
                    "subscriptionActive": t.subscription_active,
                }
                for t in session.scalars(
                    select(FinanceTransaction).order_by(
                        FinanceTransaction.date, FinanceTransaction.id
                    )
                )
            ]
        self._revision += 1
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def accounts(self):
        return self._accounts

    @Property("QVariantList", notify=changed)
    def categories(self):
        return self._categories

    @Property("QVariantList", notify=changed)
    def categoryDetails(self):
        return self._category_details

    @Property("QVariantList", notify=changed)
    def transactions(self):
        return self._transactions

    @Slot(QUrl, str, result="QVariantMap")
    def loadCsv(self, file_url, delimiter):
        self._csv_document = None
        self._csv_preview = None
        path = file_url.toLocalFile()
        if not path:
            return {"error": "Choose a local CSV file."}
        try:
            document = csv_import.read_csv(path, delimiter)
        except ValueError as exc:
            return {"error": str(exc)}
        self._csv_document = document
        return {
            "error": "",
            "headers": document.headers,
            "suggestions": csv_import.suggestions(document),
            "rowCount": len(document.rows),
        }

    @Slot("QVariantMap", result="QVariantMap")
    def previewCsv(self, options):
        self._csv_preview = None
        if self._csv_document is None:
            return {"error": "Choose a CSV file first."}
        account_id = options.get("accountId", "")
        account = next((item for item in self._accounts if item["id"] == account_id), None)
        if account is None:
            return {"error": "Choose an account for the import."}
        try:
            rows = csv_import.preview_rows(self._csv_document, options, account, self._transactions)
        except ValueError as exc:
            return {"error": str(exc)}
        self._csv_preview = {
            "accountId": account_id,
            "revision": self._revision,
            "rows": [row.copy() for row in rows],
        }
        return {"error": "", "rows": rows}

    @Slot("QVariantList", result="QVariantMap")
    def importCsv(self, indices):
        preview = self._csv_preview
        if preview is None or preview["revision"] != self._revision:
            return {"error": "The data changed. Generate a new preview before importing."}
        if not indices:
            return {"error": "Select at least one valid row to import."}
        if any(not isinstance(index, int) or isinstance(index, bool) or index < 0
               or index >= len(preview["rows"]) for index in indices) or len(set(indices)) != len(indices):
            return {"error": "The row selection is invalid. Generate a new preview."}
        rows = [preview["rows"][index] for index in indices]
        if any(not row["valid"] for row in rows):
            return {"error": "Invalid rows cannot be imported."}
        try:
            with SessionLocal() as session:
                account = session.get(FinanceAccount, preview["accountId"])
                if account is None:
                    return {"error": "The account no longer exists."}
                categories = {name.casefold(): name for name in session.scalars(select(FinanceCategory.name))}
                for row in rows:
                    category = row["category"]
                    if category.casefold() not in categories:
                        categories[category.casefold()] = category
                        session.add(FinanceCategory(name=category))
                    session.add(FinanceTransaction(
                        date=date.fromisoformat(row["date"]), title=row["title"], kind=row["kind"],
                        amount_cents=row["amountCents"], account_id=account.id, destination_id=None,
                        category=categories[category.casefold()], recurrence="none", subscription_active=False,
                    ))
                session.commit()
        except SQLAlchemyError as exc:
            logger.error("CSV import failed (%s).", type(exc).__name__)
            return {"error": "Could not save the import. No transactions were added."}
        self._csv_preview = None
        self._refresh()
        return {"error": "", "imported": len(rows)}

    @Slot(str, str, str, str, str, str, result=str)
    def saveAccount(
        self, account_id, name, kind, opened_on, opening_amount, credit_limit
    ):
        name = name.strip()
        if not name or len(name) > 100:
            return "Enter an account name of up to 100 characters."
        if kind not in ("bank", "credit"):
            return "Choose a bank or credit-card account."
        try:
            opened = parse_date(opened_on)
            opening = parse_amount(opening_amount, signed=True)
            limit = parse_amount(credit_limit) if kind == "credit" else None
        except ValueError as exc:
            return str(exc)
        with SessionLocal() as session:
            account = session.get(FinanceAccount, account_id) if account_id else None
            if account_id and account is None:
                return "This account no longer exists."
            if any(
                a.id != account_id and a.name.casefold() == name.casefold()
                for a in session.scalars(select(FinanceAccount))
            ):
                return "An account with this name already exists."
            if account is not None:
                first_transaction = session.scalar(
                    select(FinanceTransaction.date)
                    .where(
                        or_(
                            FinanceTransaction.account_id == account_id,
                            FinanceTransaction.destination_id == account_id,
                        )
                    )
                    .order_by(FinanceTransaction.date)
                    .limit(1)
                )
                if first_transaction and account.kind != kind:
                    return "An account with transactions cannot change type."
            else:
                account = FinanceAccount()
                session.add(account)
            account.name, account.kind, account.opened_on = name, kind, opened
            account.opening_cents, account.credit_limit_cents = opening, limit
            session.commit()
        self._refresh()
        return ""

    @Slot(str, result=str)
    def deleteAccount(self, account_id):
        with SessionLocal() as session:
            account = session.get(FinanceAccount, account_id)
            if account is None:
                return "This account no longer exists."
            if session.scalar(
                select(FinanceTransaction.id)
                .where(
                    or_(
                        FinanceTransaction.account_id == account_id,
                        FinanceTransaction.destination_id == account_id,
                    )
                )
                .limit(1)
            ):
                return "Remove this account's transactions before deleting it."
            session.delete(account)
            session.commit()
        self._refresh()
        return ""

    @Slot(str, str, str, str, str, str, str, str, str, bool, result=str)
    def saveTransaction(
        self,
        transaction_id,
        day_string,
        title,
        kind,
        amount,
        account_id,
        destination_id,
        category,
        recurrence,
        active,
    ):
        title, category = title.strip(), category.strip()
        if not title or len(title) > 200:
            return "Enter a description of up to 200 characters."
        if kind not in ("income", "expense", "transfer"):
            return "Choose income, expense, or transfer."
        if recurrence not in ("none", "monthly", "yearly") or (
            kind != "expense" and recurrence != "none"
        ):
            return "Only expenses can be subscriptions."
        if kind != "transfer" and (not category or len(category) > 100):
            return "Enter a category of up to 100 characters."
        try:
            day, cents = parse_date(day_string), parse_amount(amount)
        except ValueError as exc:
            return str(exc)
        if cents <= 0:
            return "Enter an amount greater than zero."
        with SessionLocal() as session:
            transaction = (
                session.get(FinanceTransaction, transaction_id)
                if transaction_id
                else None
            )
            if transaction_id and transaction is None:
                return "This transaction no longer exists."
            account = session.get(FinanceAccount, account_id)
            if account is None:
                return "Choose an account."
            destination = (
                session.get(FinanceAccount, destination_id)
                if kind == "transfer"
                else None
            )
            if kind == "transfer" and (
                destination is None or destination.id == account.id
            ):
                return "Choose two different accounts for a transfer."
            if kind != "transfer":
                existing = next(
                    (
                        name
                        for name in session.scalars(select(FinanceCategory.name))
                        if name.casefold() == category.casefold()
                    ),
                    None,
                )
                if existing:
                    category = existing
                else:
                    session.add(FinanceCategory(name=category))
            if transaction is None:
                transaction = FinanceTransaction()
                session.add(transaction)
            transaction.date, transaction.title, transaction.kind = day, title, kind
            transaction.amount_cents, transaction.account_id = cents, account_id
            transaction.destination_id = destination.id if destination else None
            transaction.category = category if kind != "transfer" else None
            transaction.recurrence = recurrence
            transaction.subscription_active = active and recurrence != "none"
            session.commit()
        self._refresh()
        return ""

    @Slot(str, str, bool, result=str)
    def saveCategory(self, name, color, create):
        name = name.strip()
        if not name or len(name) > 100:
            return "Enter a category name of up to 100 characters."
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            return "Enter a color in #RRGGBB format."
        try:
            with SessionLocal() as session:
                existing = next(
                    (
                        category
                        for category in session.scalars(select(FinanceCategory))
                        if category.name.casefold() == name.casefold()
                    ),
                    None,
                )
                if create and existing is not None:
                    return "A category with this name already exists."
                if not create and existing is None:
                    return "This category no longer exists."
                if existing is None:
                    existing = FinanceCategory(name=name)
                    session.add(existing)
                existing.color = color.upper()
                session.commit()
        except SQLAlchemyError as exc:
            logger.error("Could not save finance category (%s).", type(exc).__name__)
            return "Could not save the category."
        self._refresh()
        return ""

    @Slot("QVariantList", str, result=str)
    def assignCategory(self, transaction_ids, category_name):
        if (
            not transaction_ids
            or any(not isinstance(item, str) or not item for item in transaction_ids)
            or len(transaction_ids) != len(set(transaction_ids))
        ):
            return "Select at least one valid transaction."
        try:
            with SessionLocal() as session:
                category = session.get(FinanceCategory, category_name)
                if category is None:
                    return "Choose an existing category."
                transactions = []
                for start in range(0, len(transaction_ids), 500):
                    transactions.extend(
                        session.scalars(
                            select(FinanceTransaction).where(
                                FinanceTransaction.id.in_(
                                    transaction_ids[start : start + 500]
                                )
                            )
                        )
                    )
                if len(transactions) != len(transaction_ids) or any(
                    t.kind == "transfer" for t in transactions
                ):
                    return "A selected transaction is missing or is a transfer. Refresh and try again."
                for transaction in transactions:
                    transaction.category = category.name
                session.commit()
        except SQLAlchemyError as exc:
            logger.error("Could not assign finance category (%s).", type(exc).__name__)
            return "Could not assign the category. No transactions were changed."
        self._refresh()
        return ""

    @Slot(str, result=str)
    def deleteTransaction(self, transaction_id):
        with SessionLocal() as session:
            transaction = session.get(FinanceTransaction, transaction_id)
            if transaction is None:
                return "This transaction no longer exists."
            session.delete(transaction)
            session.commit()
        self._refresh()
        return ""

    @Slot(result=str)
    def deleteAllTransactions(self):
        try:
            with SessionLocal() as session:
                session.execute(delete(PlaidImportedTransaction))
                session.execute(delete(FinanceTransaction))
                session.commit()
        except SQLAlchemyError as exc:
            logger.error("Could not delete all transactions (%s).", type(exc).__name__)
            return "Could not delete transactions. No transactions were removed."
        self._refresh()
        return ""

    def _balance_events(self):
        accounts = {account["id"]: account for account in self._accounts}
        starts = {account["id"]: account["openedOn"] for account in self._accounts}
        baselines = {account["id"]: account["openingCents"] for account in self._accounts}
        events = []
        for transaction in self._transactions:
            source = accounts[transaction["accountId"]]
            sign = -1 if source["kind"] == "bank" else 1
            if transaction["kind"] == "income":
                sign = -sign
            impacts = [(source["id"], sign * transaction["amountCents"])]
            if transaction["kind"] == "transfer":
                destination = accounts[transaction["destinationId"]]
                sign = 1 if destination["kind"] == "bank" else -1
                impacts.append((destination["id"], sign * transaction["amountCents"]))
            for account_id, delta in impacts:
                day = transaction["date"]
                events.append((day, account_id, delta))
                if day < accounts[account_id]["openedOn"]:
                    starts[account_id] = min(starts[account_id], day)
                    # Reverse earlier activity from the opening-date snapshot.
                    baselines[account_id] -= delta
        events.extend((starts[account_id], account_id, balance) for account_id, balance in baselines.items())
        return starts, events

    def _subscription_occurrences(self, first, last):
        accounts = {account["id"]: account for account in self._accounts}
        forecasts = []
        if first <= last:
            for transaction in self._transactions:
                if transaction["subscriptionActive"]:
                    for occurrence in subscription_dates(
                        date.fromisoformat(transaction["date"]),
                        transaction["recurrence"],
                        first,
                        last,
                    ):
                        forecasts.append(
                            {
                                "date": occurrence.isoformat(),
                                "title": transaction["title"],
                                "amount": money(transaction["amountCents"]),
                                "amountCents": transaction["amountCents"],
                                "category": transaction["category"],
                                "accountName": accounts[transaction["accountId"]]["name"],
                            }
                        )
        forecasts.sort(key=lambda t: (t["date"], t["title"].casefold()))
        return forecasts

    @Slot(str, str, result="QVariantMap")
    def summaryFor(self, mode, day_string):
        try:
            day = parse_date(day_string)
            start, end = period_range(mode, day)
        except ValueError as exc:
            return {"error": str(exc)}
        accounts = {a["id"]: a for a in self._accounts}
        starts, events = self._balance_events()
        balances = {account_id: 0 for account_id, start_date in starts.items() if start_date <= end.isoformat()}
        for event_date, account_id, delta in events:
            if event_date <= end.isoformat():
                balances[account_id] += delta
        selected = []
        income = expenses = 0
        categories = defaultdict(int)
        for t in self._transactions:
            if start.isoformat() <= t["date"] <= end.isoformat():
                row = {
                    **t,
                    "accountName": accounts[t["accountId"]]["name"],
                    "destinationName": accounts[t["destinationId"]]["name"]
                    if t["destinationId"]
                    else "",
                    "displayAmount": money(t["amountCents"]),
                    "categoryColor": self._category_colors.get(t["category"]) or "",
                }
                selected.append(row)
                if t["kind"] == "income":
                    income += t["amountCents"]
                elif t["kind"] == "expense":
                    expenses += t["amountCents"]
                    categories[t["category"]] += t["amountCents"]
        rows = []
        net = available = 0
        for account in self._accounts:
            if account["id"] not in balances:
                rows.append(
                    {**account, "balanceDisplay": "Not open", "availableDisplay": ""}
                )
                continue
            balance = balances[account["id"]]
            net += balance if account["kind"] == "bank" else -balance
            credit = (
                account["creditLimitCents"] - balance
                if account["kind"] == "credit"
                else None
            )
            if credit is not None:
                available += credit
            rows.append(
                {
                    **account,
                    "balanceDisplay": money(balance),
                    "availableDisplay": money(credit) if credit is not None else "",
                }
            )
        today = date.today()
        future_estimate = start > today
        forecasts = []
        if today < date.max:
            first = max(start, today + timedelta(days=1))
            forecasts = self._subscription_occurrences(first, end)
        chart_forecasts = forecasts if future_estimate else []
        if future_estimate and mode == "Day":
            first = max(
                today + timedelta(days=1),
                start - timedelta(days=min(6, start.toordinal() - 1)),
            )
            chart_forecasts = self._subscription_occurrences(first, end)
        if future_estimate:
            for forecast in forecasts:
                categories[forecast["category"]] += forecast["amountCents"]
        pie = [
            {
                "name": name,
                "value": value,
                "amount": money(value),
                "color": self._category_colors.get(name) or COLORS[index % len(COLORS)],
            }
            for index, (name, value) in enumerate(
                sorted(categories.items(), key=lambda item: (-item[1], item[0]))
            )
        ]
        bars, lines = self._charts(mode, start, end, chart_forecasts)
        return {
            "error": "",
            "futureEstimate": future_estimate,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "income": money(income),
            "expenses": money(expenses),
            "net": money(net),
            "available": money(available),
            "accounts": rows,
            "transactions": list(reversed(selected)),
            "pie": pie,
            "bars": bars,
            "lines": lines,
            "forecasts": forecasts,
        }

    def _charts(self, mode, start, end, forecasts):
        if mode == "Day":
            first = start - timedelta(days=min(6, start.toordinal() - 1))
            buckets = [
                (first + timedelta(days=i), first + timedelta(days=i))
                for i in range((end - first).days + 1)
            ]
        elif mode == "Month":
            buckets = [
                (start + timedelta(days=i), start + timedelta(days=i))
                for i in range((end - start).days + 1)
            ]
        else:
            buckets = [
                (
                    date(start.year, month, 1),
                    date(start.year, month, calendar.monthrange(start.year, month)[1]),
                )
                for month in range(1, 13)
            ]
        _, events = self._balance_events()
        signs = {a["id"]: 1 if a["kind"] == "bank" else -1 for a in self._accounts}
        deltas = [(day, signs[account_id] * delta) for day, account_id, delta in events]
        deltas.sort()
        position = index = cumulative_income = cumulative_expenses = 0
        bars, lines = [], []
        for first, last in buckets:
            while index < len(deltas) and deltas[index][0] <= last.isoformat():
                position += deltas[index][1]
                index += 1
            transactions = [
                t
                for t in self._transactions
                if first.isoformat() <= t["date"] <= last.isoformat()
            ]
            income = sum(
                t["amountCents"] for t in transactions if t["kind"] == "income"
            )
            expense = sum(
                t["amountCents"] for t in transactions if t["kind"] == "expense"
            )
            expense += sum(
                t["amountCents"]
                for t in forecasts
                if first.isoformat() <= t["date"] <= last.isoformat()
            )
            cumulative_income += income
            cumulative_expenses += expense
            label = first.strftime("%b") if mode == "Year" else first.strftime("%m/%d")
            bars.append({"label": label, "income": income, "expense": expense})
            lines.append(
                {
                    "label": label,
                    "income": cumulative_income,
                    "expense": cumulative_expenses,
                    "balance": position,
                }
            )
        return bars, lines
