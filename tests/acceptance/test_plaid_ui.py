from pathlib import Path

import pytest
from PySide6.QtCore import QDate, QMetaObject, QObject, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import getCppPointer, wrapInstance
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.finances import viewmodel as finance_module
from finance_app.integrations.plaid import viewmodel as plaid_module


def find_item(item, name):
    if item.objectName() == name and item.isVisible():
        return item
    for child in item.childItems():
        result = find_item(child, name)
        if result is not None:
            return result
    return None


def click(window, item):
    assert item is not None and item.isEnabled()
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    assert 0 <= center.x() < window.width() and 0 <= center.y() < window.height()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=center.toPoint())
    QTest.qWait(50)


def scroll_to(window, item):
    scroll = window.findChild(QObject, "financeScroll").property("contentItem")
    position = item.mapToItem(scroll.property("contentItem"), QPointF()).y()
    scroll.setProperty(
        "contentY",
        max(0, min(position - 80, scroll.property("contentHeight") - scroll.property("height"))),
    )
    QTest.qWait(50)


def test_plaid_settings_and_import_flow(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    sessions = sessionmaker(bind=database)
    monkeypatch.setattr(finance_module, "SessionLocal", sessions)
    monkeypatch.setattr(plaid_module, "SessionLocal", sessions)
    monkeypatch.setattr(plaid_module, "get_credential", lambda name: None)
    finance = finance_module.FinanceViewModel()
    plaid = plaid_module.PlaidViewModel(finance)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    task, calendar = QObject(), QObject()
    engine.setInitialProperties(
        {
            "taskViewModel": task,
            "calendarViewModel": calendar,
            "financeViewModel": finance,
            "plaidViewModel": plaid,
        }
    )
    qml = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1200, 900)
    window.setProperty("currentPage", "Settings")
    QTest.qWait(100)
    icon = find_item(window.contentItem(), "plaidFinanceIcon")
    google_icon = find_item(window.contentItem(), "googleCalendarIcon")
    assert icon is not None and google_icon is not None
    assert (icon.width(), icon.height()) == (google_icon.width(), google_icon.height())
    origin = icon.mapToScene(QPointF())
    image = window.grabWindow()
    assert any(
        image.pixelColor(x, y).name() == "#22675b"
        for x in range(int(origin.x()), int(origin.x() + icon.width()))
        for y in range(int(origin.y()), int(origin.y() + icon.height()))
    )
    click(window, find_item(window.contentItem(), "plaidConnect"))
    assert find_item(window.contentItem(), "plaidSecret") is not None
    dialog = window.findChild(QObject, "plaidCredentialsDialog")
    assert QMetaObject.invokeMethod(dialog, "close")
    plaid._environment = "sandbox"
    plaid._complete(
        "refresh",
        (
            plaid_module.describe_accounts(
                [
                    {
                        "account_id": "remote",
                        "name": "Linked checking",
                        "mask": "1234",
                        "type": "depository",
                        "balances": {"current": 50, "iso_currency_code": "USD"},
                    }
                ]
            ),
            [
                {
                    "account_id": "remote",
                    "transaction_id": "one",
                    "date": "2024-01-01",
                    "name": "Purchase",
                    "amount": 5,
                    "iso_currency_code": "USD",
                    "pending": False,
                },
                {
                    "account_id": "remote",
                    "transaction_id": "two",
                    "date": "2024-01-02",
                    "name": "Pending",
                    "amount": 5,
                    "iso_currency_code": "USD",
                    "pending": True,
                },
            ],
            "HISTORICAL_UPDATE_COMPLETE",
        ),
        "",
    )
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    assert (
        find_item(window.contentItem(), "financePlaidImport").property("text")
        == "Import transactions"
    )
    scroll_to(window, find_item(window.contentItem(), "financePlaidImport"))
    click(window, find_item(window.contentItem(), "financePlaidImport"))
    assert "select or create" in find_item(
        window.contentItem(), "plaidAccountHelp"
    ).property("text")
    import_dialog = window.findChild(QObject, "plaidImportDialog")
    assert QMetaObject.invokeMethod(import_dialog, "close")
    assert not finance.saveAccount(
        "", "Local checking", "bank", "2024-01-01", "100", ""
    )
    saved_accounts, saved_transactions = plaid.accounts, plaid._transactions
    plaid._complete("refresh", (saved_accounts, [], "NOT_READY"), "")
    click(window, find_item(window.contentItem(), "financePlaidImport"))
    find_item(window.contentItem(), "plaidRemoteAccount").setProperty("currentIndex", 0)
    find_item(window.contentItem(), "plaidLocalAccount").setProperty("currentIndex", 0)
    click(window, find_item(window.contentItem(), "plaidPreview"))
    assert "no transactions" in find_item(
        window.contentItem(), "plaidEmptyHistory"
    ).property("text")
    assert QMetaObject.invokeMethod(import_dialog, "close")
    plaid._complete(
        "refresh",
        (saved_accounts, saved_transactions, "HISTORICAL_UPDATE_COMPLETE"),
        "",
    )
    click(window, find_item(window.contentItem(), "financePlaidImport"))
    find_item(window.contentItem(), "plaidRemoteAccount").setProperty("currentIndex", 0)
    find_item(window.contentItem(), "plaidLocalAccount").setProperty("currentIndex", 0)
    click(window, find_item(window.contentItem(), "plaidPreview"))
    assert (
        find_item(window.contentItem(), "plaidImportSelection").property("text")
        == "1 of 2 rows selected"
    )
    click(window, find_item(window.contentItem(), "plaidImport"))
    assert [item["title"] for item in finance.transactions] == ["Purchase"]
    assert not warnings, "\n".join(warnings)
    assert app


@pytest.mark.parametrize(
    ("remote_type", "local_kind", "kind_index", "existing", "available"),
    [
        ("depository", "bank", 0, False, True),
        ("credit", "credit", 1, True, True),
        ("credit", "credit", 1, False, False),
    ],
)
def test_plaid_import_creates_and_selects_local_account(
    monkeypatch, remote_type, local_kind, kind_index, existing, available
):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    sessions = sessionmaker(bind=database)
    monkeypatch.setattr(finance_module, "SessionLocal", sessions)
    monkeypatch.setattr(plaid_module, "SessionLocal", sessions)
    monkeypatch.setattr(plaid_module, "get_credential", lambda name: None)
    finance = finance_module.FinanceViewModel()
    if existing:
        assert not finance.saveAccount("", "Z existing", "bank", "2024-01-01", "0", "")
    plaid = plaid_module.PlaidViewModel(finance)
    plaid._environment = "sandbox"
    plaid._complete(
        "refresh",
        (
            plaid_module.describe_accounts(
                [
                    {
                        "account_id": "remote",
                        "name": "Linked account",
                        "mask": "1234",
                        "type": remote_type,
                        "balances": {
                            "current": 50 if available else None,
                            "limit": 500 if available else None,
                            "iso_currency_code": "USD",
                        },
                    }
                ]
            ),
            [
                {
                    "account_id": "remote",
                    "transaction_id": "one",
                    "date": "2024-01-02",
                    "name": "Purchase",
                    "amount": 5,
                    "iso_currency_code": "USD",
                    "pending": False,
                }
            ],
            "HISTORICAL_UPDATE_COMPLETE",
        ),
        "",
    )
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    task, calendar = QObject(), QObject()
    engine.setInitialProperties(
        {
            "taskViewModel": task,
            "calendarViewModel": calendar,
            "financeViewModel": finance,
            "plaidViewModel": plaid,
        }
    )
    qml = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Finances")
    QTest.qWait(100)
    scroll_to(window, find_item(window.contentItem(), "financePlaidImport"))
    click(window, find_item(window.contentItem(), "financePlaidImport"))
    assert not find_item(window.contentItem(), "plaidNewAccount").isEnabled()
    find_item(window.contentItem(), "plaidRemoteAccount").setProperty("currentIndex", 0)
    click(window, find_item(window.contentItem(), "plaidNewAccount"))
    assert (
        find_item(window.contentItem(), "financeAccountKind").property("currentIndex")
        == kind_index
    )
    assert (
        find_item(window.contentItem(), "financeAccountName").property("text")
        == "Linked account · 1234"
    )
    assert ("$50.00" if available else "Unavailable") in find_item(
        window.contentItem(), "financePlaidBalance"
    ).property("text")
    assert (
        find_item(window.contentItem(), "financeOpeningAmount").property("text") == ""
    )
    if local_kind == "credit":
        assert ("$500.00" if available else "Unavailable") in find_item(
            window.contentItem(), "financePlaidCreditLimit"
        ).property("text")
        assert find_item(window.contentItem(), "financeCreditLimit").property(
            "text"
        ) == ("500.00" if available else "")
    find_item(window.contentItem(), "financeAccountKind").setProperty(
        "currentIndex", 1 - kind_index
    )
    assert not find_item(window.contentItem(), "financeUsePlaidSnapshot").isEnabled()
    find_item(window.contentItem(), "financeAccountKind").setProperty(
        "currentIndex", kind_index
    )
    click(window, find_item(window.contentItem(), "financeCancelAccount"))
    assert len(finance.accounts) == int(existing)
    click(window, find_item(window.contentItem(), "plaidNewAccount"))
    click(window, find_item(window.contentItem(), "financeSaveAccount"))
    assert find_item(window.contentItem(), "financeAccountError").isVisible()
    tomorrow = QDate.currentDate().addDays(1).toString("yyyy-MM-dd")
    if available:
        click(window, find_item(window.contentItem(), "financeUsePlaidSnapshot"))
    else:
        assert not find_item(
            window.contentItem(), "financeUsePlaidSnapshot"
        ).isEnabled()
        find_item(window.contentItem(), "financeAccountDate").setProperty(
            "text", tomorrow
        )
        find_item(window.contentItem(), "financeOpeningAmount").setProperty(
            "text", "50.00"
        )
        find_item(window.contentItem(), "financeCreditLimit").setProperty("text", "500")
    assert (
        find_item(window.contentItem(), "financeAccountDate").property("text")
        == tomorrow
    )
    assert (
        find_item(window.contentItem(), "financeOpeningAmount").property("text")
        == "50.00"
    )
    click(window, find_item(window.contentItem(), "financeSaveAccount"))
    account = next(a for a in finance.accounts if a["name"] == "Linked account · 1234")
    assert account["kind"] == local_kind
    assert account["openingAmount"] == "50.00"
    assert account["openedOn"] == tomorrow
    if local_kind == "credit":
        assert account["creditLimit"] == "500.00"
    local = find_item(window.contentItem(), "plaidLocalAccount")
    assert finance.accounts[local.property("currentIndex")]["id"] == account["id"]
    import_dialog = window.findChild(QObject, "plaidImportDialog")
    assert QMetaObject.invokeMethod(import_dialog, "close")
    assert any(a["id"] == account["id"] for a in finance.accounts)
    click(window, find_item(window.contentItem(), "financePlaidImport"))
    find_item(window.contentItem(), "plaidRemoteAccount").setProperty("currentIndex", 0)
    index = next(i for i, a in enumerate(finance.accounts) if a["id"] == account["id"])
    find_item(window.contentItem(), "plaidLocalAccount").setProperty(
        "currentIndex", index
    )
    click(window, find_item(window.contentItem(), "plaidPreview"))
    click(window, find_item(window.contentItem(), "plaidImport"))
    assert finance.transactions[0]["accountId"] == account["id"]
    assert finance.transactions[0]["title"] == "Purchase"
    today = QDate.currentDate().toString("yyyy-MM-dd")
    summary = finance.summaryFor("Day", today)
    imported_account = next(a for a in summary["accounts"] if a["id"] == account["id"])
    assert imported_account["balanceDisplay"] == "$50.00"
    assert not warnings, "\n".join(warnings)
    assert app
