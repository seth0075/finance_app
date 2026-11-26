import csv
from datetime import date
from pathlib import Path

from PySide6.QtCore import (
    QDate,
    QDateTime,
    QMetaObject,
    QObject,
    QPointF,
    Qt,
    QTime,
    QUrl,
)
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import getCppPointer, wrapInstance
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.finances import viewmodel


def find_item(item, name):
    if item.objectName() == name and item.isVisible():
        return item
    for child in item.childItems():
        result = find_item(child, name)
        if result is not None:
            return result
    return None


def click(window, item):
    assert item is not None
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    assert 0 <= center.x() < window.width() and 0 <= center.y() < window.height()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=center.toPoint())
    QTest.qWait(50)


def scroll_to(window, item):
    scroll = window.findChild(QObject, "financeScroll")
    flickable = scroll.property("contentItem")
    content = flickable.property("contentItem")
    position = item.mapToItem(content, QPointF()).y()
    flickable.setProperty(
        "contentY",
        max(0, min(position - 80, flickable.property("contentHeight") - flickable.property("height"))),
    )
    QTest.qWait(50)


def test_finance_manual_entry_and_views(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=database))
    finance = viewmodel.FinanceViewModel()
    task, calendar = QObject(), QObject()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    engine.setInitialProperties(
        {
            "taskViewModel": task,
            "calendarViewModel": calendar,
            "financeViewModel": finance,
        }
    )
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(150)
    click(window, find_item(window.contentItem(), "financeNewAccount"))
    find_item(window.contentItem(), "financeAccountName").setProperty(
        "text", "Checking"
    )
    find_item(window.contentItem(), "financeOpeningAmount").setProperty(
        "text", "1000.00"
    )
    click(window, find_item(window.contentItem(), "financeSaveAccount"))
    assert len(finance.accounts) == 1
    click(window, find_item(window.contentItem(), "financeNewTransaction"))
    click(window, find_item(window.contentItem(), "financeSaveTransaction"))
    assert find_item(window.contentItem(), "financeTransactionError").isVisible()
    find_item(window.contentItem(), "financeTransactionTitle").setProperty(
        "text", "Streaming"
    )
    find_item(window.contentItem(), "financeTransactionAmount").setProperty(
        "text", "12.99"
    )
    click(window, find_item(window.contentItem(), "financeSaveTransaction"))
    assert "account" in find_item(window.contentItem(), "financeTransactionError").property("text")
    find_item(window.contentItem(), "financeTransactionAccount").setProperty("currentIndex", 0)
    category = find_item(window.contentItem(), "financeTransactionCategory")
    category.setProperty("currentIndex", len(finance.categories))
    find_item(window.contentItem(), "financeCustomCategory").setProperty(
        "text", "Media"
    )
    find_item(window.contentItem(), "financeTransactionRepeat").setProperty(
        "currentIndex", 1
    )
    click(window, find_item(window.contentItem(), "financeSaveTransaction"))
    assert len(finance.transactions) == 1
    assert finance.transactions[0]["recurrence"] == "monthly"
    assert finance.transactions[0]["subscriptionActive"]
    assert finance.transactions[0]["category"] == "Media"
    assert finance.transactions[0]["accountId"] == finance.accounts[0]["id"]
    assert "Checking" in find_item(window.contentItem(), "financeTransactionAccountLabel").property("text")
    assert (
        find_item(window.contentItem(), "financeExpenses").property("value") == "$12.99"
    )
    for mode in ("Day", "Year", "Month"):
        click(window, find_item(window.contentItem(), "finance" + mode + "Button"))
        assert (
            find_item(window.contentItem(), "financesPage").property("viewMode") == mode
        )
        assert (
            find_item(window.contentItem(), "financeExpenses").property("value")
            == "$12.99"
        )
    scroll = window.findChild(QObject, "financeScroll")
    flickable = scroll.property("contentItem")
    scroll_to(window, find_item(window.contentItem(), "financeChartPanelpie"))
    for kind in ("pie", "bar", "line"):
        chart = find_item(window.contentItem(), "financeChart" + kind)
        assert chart is not None and chart.width() >= 120 and chart.height() > 0
    image = window.grabWindow()
    for kind, color in (("pie", "#7395f5"), ("bar", "#f07878")):
        chart = find_item(window.contentItem(), "financeChart" + kind)
        origin = chart.mapToScene(QPointF())
        assert any(
            image.pixelColor(x, y).name() == color
            for x in range(
                max(0, int(origin.x())),
                min(image.width(), int(origin.x() + chart.width())),
                2,
            )
            for y in range(
                max(0, int(origin.y())),
                min(image.height(), int(origin.y() + chart.height())),
                2,
            )
        )
    flickable.setProperty("contentY", 0)
    QTest.qWait(50)
    click(window, find_item(window.contentItem(), "financeNewAccount"))
    find_item(window.contentItem(), "financeAccountName").setProperty("text", "Card")
    find_item(window.contentItem(), "financeAccountKind").setProperty("currentIndex", 1)
    find_item(window.contentItem(), "financeOpeningAmount").setProperty("text", "100")
    find_item(window.contentItem(), "financeCreditLimit").setProperty("text", "1000")
    click(window, find_item(window.contentItem(), "financeSaveAccount"))
    assert len(finance.accounts) == 2
    assert (
        find_item(window.contentItem(), "financeBalance").property("value") == "$887.01"
    )
    click(window, find_item(window.contentItem(), "financeNewTransaction"))
    find_item(window.contentItem(), "financeTransactionTitle").setProperty(
        "text", "Card payment"
    )
    find_item(window.contentItem(), "financeTransactionAmount").setProperty(
        "text", "100"
    )
    find_item(window.contentItem(), "financeTransactionKind").setProperty(
        "currentIndex", 2
    )
    accounts = finance.accounts
    find_item(window.contentItem(), "financeTransactionAccount").setProperty(
        "currentIndex",
        next(i for i, item in enumerate(accounts) if item["name"] == "Checking"),
    )
    find_item(window.contentItem(), "financeTransactionDestination").setProperty(
        "currentIndex",
        next(i for i, item in enumerate(accounts) if item["name"] == "Card"),
    )
    click(window, find_item(window.contentItem(), "financeSaveTransaction"))
    assert len(finance.transactions) == 2
    assert (
        find_item(window.contentItem(), "financeBalance").property("value") == "$887.01"
    )
    assert (
        find_item(window.contentItem(), "financeCredit").property("value")
        == "$1,000.00"
    )
    assert (
        find_item(window.contentItem(), "financeExpenses").property("value") == "$12.99"
    )
    scroll_to(window, find_item(window.contentItem(), "financeAccountRow"))
    click(window, find_item(window.contentItem(), "financeAccountRow"))
    assert find_item(window.contentItem(), "financeAccountName").property("text") == "Card"
    find_item(window.contentItem(), "financeCreditLimit").setProperty("text", "1200")
    click(window, find_item(window.contentItem(), "financeSaveAccount"))
    assert find_item(window.contentItem(), "financeCredit").property("value") == "$1,200.00"
    window.setProperty("currentPage", "Dashboard")
    window.setProperty("currentPage", "Finances")
    QTest.qWait(50)
    assert (
        find_item(window.contentItem(), "financeBalance").property("value") == "$887.01"
    )
    scroll = window.findChild(QObject, "financeScroll")
    flickable = scroll.property("contentItem")
    subscriptions = find_item(window.contentItem(), "financeSubscriptionList")
    content = flickable.property("contentItem")
    position = subscriptions.mapToItem(content, QPointF()).y()
    flickable.setProperty("contentY", min(position - 100, flickable.property("contentHeight") - flickable.property("height")))
    QTest.qWait(50)
    click(window, find_item(window.contentItem(), "financeSubscriptionRow"))
    active = find_item(window.contentItem(), "financeSubscriptionActive")
    assert active.property("checked")
    click(window, active)
    click(window, find_item(window.contentItem(), "financeSaveTransaction"))
    assert not next(item for item in finance.transactions if item["title"] == "Streaming")["subscriptionActive"]
    click(window, find_item(window.contentItem(), "financeSubscriptionRow"))
    click(window, find_item(window.contentItem(), "financeDeleteTransaction"))
    confirmation = window.findChild(QObject, "financeConfirmDeleteTransaction")
    assert confirmation is not None and confirmation.property("visible")
    assert QMetaObject.invokeMethod(confirmation, "accept")
    QTest.qWait(50)
    assert [item["title"] for item in finance.transactions] == ["Card payment"]
    assert not warnings, "\n".join(warnings)


def test_finance_page_handles_missing_viewmodel(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    task, calendar = QObject(), QObject()
    engine.setInitialProperties({"taskViewModel": task, "calendarViewModel": calendar})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects()
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    assert not find_item(window.contentItem(), "financeNewAccount").isEnabled()
    assert not warnings, "\n".join(warnings)


def test_category_order_layout_and_future_chart_rollover(monkeypatch):
    class FixedDate(date):
        current = date(2024, 1, 20)

        @classmethod
        def today(cls):
            return cls.current

    monkeypatch.setattr(viewmodel, "date", FixedDate)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=database))
    finance = viewmodel.FinanceViewModel()
    assert not finance.saveAccount("", "Checking", "bank", "2024-01-01", "100", "")
    account_id = finance.accounts[0]["id"]
    for day, title, category in (
        ("2024-01-05", "Older uncategorized", "Uncategorized"),
        ("2024-01-22", "Newer uncategorized", "Uncategorized"),
        ("2024-01-28", "Newer food", "Food"),
        ("2024-01-11", "Older food", "Food"),
    ):
        assert not finance.saveTransaction(
            "", day, title, "expense", "5", account_id, "", category, "none", False
        )
    ids = {item["title"]: item["id"] for item in finance.transactions}
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    task, calendar = QObject(), QObject()
    engine.setInitialProperties(
        {"taskViewModel": task, "calendarViewModel": calendar, "financeViewModel": finance}
    )
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1200, 900)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    page = window.findChild(QObject, "financesPage")
    page.setProperty("selectedDate", QDateTime(QDate(2024, 1, 15), QTime(12, 0)))
    line = find_item(window.contentItem(), "financeChartPanelline")
    heading = find_item(window.contentItem(), "financeAccountsHeading")
    assert line.mapToScene(QPointF(0, line.height())).y() < heading.mapToScene(QPointF()).y()
    button = find_item(window.contentItem(), "financeAssignCategories")
    scroll_to(window, button)
    click(window, button)
    positions = [
        find_item(window.contentItem(), "financeCategoryRowCheck" + ids[title])
        .mapToScene(QPointF()).y()
        for title in (
            "Newer uncategorized", "Older uncategorized", "Newer food", "Older food"
        )
    ]
    assert positions == sorted(positions) and len(set(positions)) == 4
    click(window, find_item(window.contentItem(), "financeCancelCategory"))
    page.setProperty("selectedDate", QDateTime(QDate(2024, 2, 1), QTime(12, 0)))
    QTest.qWait(50)
    pie = find_item(window.contentItem(), "financeChartPanelpie")
    assert "expected" in pie.property("title")
    assert line.property("expected")
    FixedDate.current = date(2024, 2, 1)
    page.setProperty("todayKey", "2024-02-01")
    QTest.qWait(50)
    assert pie.property("title") == "Expenses by category"
    assert not line.property("expected")
    assert not warnings, "\n".join(warnings)


def test_bulk_category_dialog_and_separate_scrollbars(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=database))
    finance = viewmodel.FinanceViewModel()
    assert not finance.saveAccount("", "Checking", "bank", "2024-01-01", "100", "")
    assert not finance.saveAccount("", "Savings", "bank", "2024-01-01", "0", "")
    bank, savings = (item["id"] for item in finance.accounts)
    for i in range(12):
        assert not finance.saveTransaction(
            "", "2024-01-15", f"Purchase {i}", "expense", "5",
            bank, "", "Food", "none", False,
        )
    for day in ("2024-01-16", "2024-02-15", "2025-01-15"):
        assert not finance.saveTransaction(
            "", day, "Other period", "expense", "5", bank, "", "Food", "none", False,
        )
    assert not finance.saveTransaction(
        "", "2024-01-15", "Transfer", "transfer", "5", bank, savings, "", "none", False,
    )
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    task, calendar = QObject(), QObject()
    engine.setInitialProperties(
        {"taskViewModel": task, "calendarViewModel": calendar, "financeViewModel": finance}
    )
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1200, 900)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    page = window.findChild(QObject, "financesPage")
    page.setProperty("selectedDate", QDateTime(QDate(2024, 1, 15), QTime(12, 0)))
    click(window, find_item(window.contentItem(), "financeDayButton"))
    chart = find_item(window.contentItem(), "financeChartPanelline")
    button = find_item(window.contentItem(), "financeAssignCategories")
    assert chart.mapToScene(QPointF()).y() < button.mapToScene(QPointF()).y()
    scroll_to(window, button)
    page_bar = window.findChild(QObject, "financePageScrollBar")
    transaction_bar = window.findChild(QObject, "financeTransactionScrollBar")
    assert transaction_bar.width() > 0 and page_bar.width() > 0
    assert (
        transaction_bar.mapToScene(QPointF(transaction_bar.width(), 0)).x()
        < page_bar.mapToScene(QPointF()).x()
    )
    click(window, button)
    selection = find_item(window.contentItem(), "financeCategorySelection")
    assert selection.property("text") == "0 of 12 selected"
    click(window, find_item(window.contentItem(), "financeCategorySelectAll"))
    assert selection.property("text") == "12 of 12 selected"
    click(window, find_item(window.contentItem(), "financeCategorySelectAll"))
    ids = [
        item["id"]
        for item in finance.summaryFor("Day", "2024-01-15")["transactions"]
        if item["kind"] != "transfer"
    ][:2]
    for transaction_id in ids:
        click(window, find_item(window.contentItem(), "financeCategoryRowCheck" + transaction_id))
    assert selection.property("text") == "2 of 12 selected"
    category = find_item(window.contentItem(), "financeBulkCategory")
    category.setProperty("currentIndex", finance.categories.index("Food"))
    find_item(window.contentItem(), "financeCategoryColor").setProperty("text", "#123456")
    click(window, find_item(window.contentItem(), "financeApplyCategory"))
    assert "Save the category color" in find_item(window.contentItem(), "financeCategoryError").property("text")
    click(window, find_item(window.contentItem(), "financeSaveCategory"))
    assert finance.summaryFor("Day", "2024-01-15")["pie"][0]["color"] == "#123456"
    category.setProperty("currentIndex", len(finance.categories))
    find_item(window.contentItem(), "financeBulkCategoryName").setProperty("text", "Food")
    click(window, find_item(window.contentItem(), "financeSaveCategory"))
    assert "already exists" in find_item(window.contentItem(), "financeCategoryError").property("text")
    find_item(window.contentItem(), "financeBulkCategoryName").setProperty("text", "Weekend")
    click(window, find_item(window.contentItem(), "financeChooseCategoryColor"))
    picker = window.findChild(QObject, "financeCategoryColorPicker")
    picker.setProperty("selectedColor", QColor("#AA33CC"))
    assert QMetaObject.invokeMethod(picker, "accept")
    QTest.qWait(50)
    assert find_item(window.contentItem(), "financeCategoryColor").property("text") == "#AA33CC"
    click(window, find_item(window.contentItem(), "financeSaveCategory"))
    assert finance.categoryDetails[category.property("currentIndex")]["name"] == "Weekend"
    click(window, find_item(window.contentItem(), "financeApplyCategory"))
    assert all(t["category"] == ("Weekend" if t["id"] in ids else "Food")
               for t in finance.transactions if t["kind"] != "transfer")
    assert next(t for t in finance.transactions if t["kind"] == "transfer")["category"] == ""
    summary = finance.summaryFor("Day", "2024-01-15")
    assert next(p for p in summary["pie"] if p["name"] == "Weekend")["color"] == "#AA33CC"
    assert all(t["categoryColor"] == "#AA33CC" for t in summary["transactions"] if t["id"] in ids)
    assert find_item(window.contentItem(), "financeTransactionCategoryColor" + ids[0]) is not None
    for mode, count in (("Month", 13), ("Year", 14)):
        scroll = window.findChild(QObject, "financeScroll").property("contentItem")
        scroll.setProperty("contentY", 0)
        QTest.qWait(50)
        click(window, find_item(window.contentItem(), "finance" + mode + "Button"))
        button = find_item(window.contentItem(), "financeAssignCategories")
        scroll_to(window, button)
        click(window, button)
        assert find_item(window.contentItem(), "financeCategorySelection").property("text") == f"0 of {count} selected"
        click(window, find_item(window.contentItem(), "financeCancelCategory"))
    unexpected = [
        warning for warning in warnings
        if not (
            warning.startswith("qrc:/qt-project.org/imports/QtQuick/Dialogs/quickimpl/qml/ColorDialog.qml:")
            and "The current style does not support customization of this control" in warning
        )
    ]
    assert not unexpected, "\n".join(unexpected)


def test_delete_all_requires_confirmation_and_preserves_accounts(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=database))
    finance = viewmodel.FinanceViewModel()
    assert not finance.saveAccount("", "Checking", "bank", "2024-01-01", "100", "")
    account_id = finance.accounts[0]["id"]
    for day in ("2024-01-02", "2025-01-02"):
        assert not finance.saveTransaction("", day, "Purchase", "expense", "5", account_id, "", "Food", "none", False)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    task, calendar = QObject(), QObject()
    engine.setInitialProperties({"taskViewModel": task, "calendarViewModel": calendar, "financeViewModel": finance})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1200, 900)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    scroll_to(window, find_item(window.contentItem(), "financeDeleteAll"))
    click(window, find_item(window.contentItem(), "financeDeleteAll"))
    assert len(finance.transactions) == 2
    click(window, find_item(window.contentItem(), "financeCancelDeleteAll"))
    assert len(finance.transactions) == 2
    click(window, find_item(window.contentItem(), "financeDeleteAll"))
    def fail_delete(connection, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith("delete from finance_transactions"):
            raise IntegrityError(statement, None, Exception("synthetic"))

    event.listen(database, "before_cursor_execute", fail_delete)
    try:
        click(window, find_item(window.contentItem(), "financeConfirmDeleteAllButton"))
        assert "No transactions were removed" in find_item(window.contentItem(), "financeDeleteAllError").property("text")
        assert len(finance.transactions) == 2
    finally:
        event.remove(database, "before_cursor_execute", fail_delete)
    click(window, find_item(window.contentItem(), "financeConfirmDeleteAllButton"))
    assert not finance.transactions
    assert finance.accounts[0]["id"] == account_id
    assert find_item(window.contentItem(), "financeImportMessage").property("text") == "All transactions deleted."
    assert not warnings, "\n".join(warnings)


def test_csv_import_review_and_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=database))
    finance = viewmodel.FinanceViewModel()
    assert not finance.saveAccount("", "Checking", "bank", "2024-01-01", "100", "")
    path = tmp_path / "synthetic.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows([
            ["Transaction Date", "Transaction Description", "Transaction Type", "Transaction Amount"],
            ["01/02/24", "Lunch", "Debit", "5.00"],
            ["01/02/24", "Lunch", "Debit", "5.00"],
            ["01/03/24", "Invalid", "Other", "5.00"],
        ])
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    task, calendar = QObject(), QObject()
    engine.setInitialProperties({"taskViewModel": task, "calendarViewModel": calendar, "financeViewModel": finance})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    click(window, find_item(window.contentItem(), "financeImportCsv"))
    dialog = window.findChild(QObject, "financeCsvDialog")
    dialog.loadFile(QUrl.fromLocalFile(str(path)))
    click(window, find_item(window.contentItem(), "financeCsvPreview"))
    assert "account" in find_item(window.contentItem(), "financeCsvError").property("text")
    find_item(window.contentItem(), "financeCsvAccount").setProperty("currentIndex", 0)
    click(window, find_item(window.contentItem(), "financeCsvPreview"))
    assert find_item(window.contentItem(), "financeCsvSelection").property("text") == "1 of 3 rows selected"
    def visible_checks(item):
        found = [item] if item.objectName() == "financeCsvRowCheck" and item.isVisible() else []
        for child in item.childItems():
            found.extend(visible_checks(child))
        return found

    checks = visible_checks(window.contentItem())
    assert len(checks) == 3
    assert [item.property("checked") for item in checks] == [True, False, False]
    assert not checks[2].isEnabled()
    select_all = find_item(window.contentItem(), "financeCsvSelectAll")
    assert select_all.isEnabled(), (dialog.property("validCount"), select_all.property("text"))
    click(window, select_all)
    assert find_item(window.contentItem(), "financeCsvSelection").property("text") == "2 of 3 rows selected", warnings
    assert [item.property("checked") for item in checks] == [True, True, False]
    click(window, find_item(window.contentItem(), "financeCsvSelectAll"))
    assert [item.property("checked") for item in checks] == [False, False, False]
    click(window, find_item(window.contentItem(), "financeCsvSelectAll"))
    assert not finance.transactions
    click(window, find_item(window.contentItem(), "financeCsvImport"))
    assert len(finance.transactions) == 2
    assert find_item(window.contentItem(), "financeImportMessage").property("text") == "Imported 2 transactions."
    assert not finance.saveAccount("", "Savings", "bank", "2024-01-01", "0", "")
    click(window, find_item(window.contentItem(), "financeNewTransaction"))
    find_item(window.contentItem(), "financeTransactionDate").setProperty("text", "2024-01-05")
    find_item(window.contentItem(), "financeTransactionTitle").setProperty("text", "Manual")
    find_item(window.contentItem(), "financeTransactionAmount").setProperty("text", "1")
    savings_index = next(i for i, item in enumerate(finance.accounts) if item["name"] == "Savings")
    find_item(window.contentItem(), "financeTransactionAccount").setProperty("currentIndex", savings_index)
    click(window, find_item(window.contentItem(), "financeSaveTransaction"))
    assert next(item for item in finance.transactions if item["title"] == "Manual")["accountId"] == finance.accounts[savings_index]["id"]
    assert not warnings, "\n".join(warnings)
