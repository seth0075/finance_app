from datetime import date, datetime, time
from pathlib import Path

from PySide6.QtCore import Property, QMetaObject, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import getCppPointer, wrapInstance
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.calendar import viewmodel as calendar_module
from finance_app.features.tasks import repository
from finance_app.features.tasks.viewmodel import TaskViewModel
from finance_app.integrations.google_calendar import sync as google_sync
from finance_app.integrations.google_calendar.models import GoogleCalendar, GoogleEvent
from tests.acceptance.ui_helpers import click, find_item, find_items


class GoogleViewModel(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.is_connected = True
        self.refreshes = 0
        self.client_file = None

    @Property(bool, notify=changed)
    def connected(self):
        return self.is_connected

    @Property(bool, notify=changed)
    def busy(self):
        return False

    @Property(str, notify=changed)
    def status(self):
        return "Connected"

    @Property(str, notify=changed)
    def cacheCoverage(self):
        return "Cached dates"

    @Property(bool, notify=changed)
    def hasCache(self):
        return self.is_connected

    @Slot()
    def refresh(self):
        self.refreshes += 1

    @Slot()
    def disconnectAccount(self):
        self.is_connected = False
        self.changed.emit()

    @Slot(QUrl)
    def connectAccount(self, file_url):
        self.client_file = file_url.toLocalFile()


def test_google_settings_and_read_only_calendar(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    sessions = sessionmaker(bind=database)
    monkeypatch.setattr(repository, "SessionLocal", sessions)
    monkeypatch.setattr(calendar_module, "SessionLocal", sessions)
    today = date.today()
    with sessions() as session:
        google_sync.replace_cache(
            session,
            (
                [GoogleCalendar(id="remote", name="Google Work", color="#123456")],
                [
                    GoogleEvent(
                        id="e",
                        calendar_id="remote",
                        title="Imported event",
                        starts_at=datetime.combine(today, time.min),
                        ends_at=datetime.combine(today, time.min),
                        all_day=True,
                    )
                ],
                today,
                today,
            ),
        )
    tasks = TaskViewModel()
    calendar = calendar_module.CalendarViewModel()
    google = GoogleViewModel()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    engine.setInitialProperties(
        {
            "taskViewModel": tasks,
            "calendarViewModel": calendar,
            "googleViewModel": google,
        }
    )
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Settings")
    QTest.qWait(100)
    icon = find_item(window.contentItem(), "googleCalendarIcon", visible=True)
    assert icon is not None and icon.width() > 0 and icon.height() > 0
    assert (
        find_item(window.contentItem(), "googleStatus").property("text") == "Connected"
    )
    click(window, find_item(window.contentItem(), "refreshGoogleButton", visible=True))
    assert google.refreshes == 1
    window.setProperty("currentPage", "Calendar")
    QTest.qWait(100)
    entry = find_item(window.contentItem(), "calendarEntry", visible=True)
    assert entry is not None and not entry.isEnabled()
    entries = window.findChild(QObject, "calendarEntries")
    click(window, find_item(window.contentItem(), "manageCalendarsButton"))
    toggle = find_item(
        window.contentItem(), "calendarVisibilitygoogle:remote", visible=True
    )
    assert toggle is not None and toggle.isEnabled() and toggle.property("checked")
    click(window, toggle)
    assert entries.property("count") == 0
    manager = window.findChild(QObject, "calendarManager")
    assert QMetaObject.invokeMethod(manager, "close")
    click(window, find_item(window.contentItem(), "manageCalendarsButton"))
    toggle = find_item(
        window.contentItem(), "calendarVisibilitygoogle:remote", visible=True
    )
    assert not toggle.property("checked")
    click(window, toggle)
    assert entries.property("count") == 1
    assert QMetaObject.invokeMethod(manager, "close")
    click(window, find_item(window.contentItem(), "newEventButton"))
    click(window, find_item(window.contentItem(), "eventCalendar", visible=True))
    options = find_items(window.contentItem(), "comboOptionText")
    assert [option.property("text") for option in options] == ["Personal"]
    click(window, options[0].parentItem())
    dialog = window.findChild(QObject, "eventDialog")
    assert QMetaObject.invokeMethod(dialog, "close")
    window.setProperty("currentPage", "Settings")
    QTest.qWait(100)
    click(
        window, find_item(window.contentItem(), "disconnectGoogleButton", visible=True)
    )
    click(
        window, find_item(window.contentItem(), "cancelGoogleDisconnect", visible=True)
    )
    assert google.connected
    click(
        window, find_item(window.contentItem(), "disconnectGoogleButton", visible=True)
    )
    click(
        window, find_item(window.contentItem(), "confirmGoogleDisconnect", visible=True)
    )
    assert not google.connected
    click(window, find_item(window.contentItem(), "connectGoogleButton", visible=True))
    client_file = tmp_path / "synthetic-client.json"
    client_file.write_text("{}", encoding="utf-8")
    picker = window.findChild(QObject, "googleClientPicker")
    assert picker is not None and picker.property("visible")
    assert picker.setProperty("selectedFile", QUrl.fromLocalFile(str(client_file)))
    assert Path(picker.property("selectedFile").toLocalFile()) == client_file
    assert QMetaObject.invokeMethod(picker, "accepted")
    QTest.qWait(50)
    assert Path(google.client_file) == client_file
    assert QMetaObject.invokeMethod(picker, "close")
    unexpected = [
        warning
        for warning in warnings
        if not (
            warning.startswith(
                "qrc:/qt-project.org/imports/QtQuick/Dialogs/quickimpl/qml/SideBar.qml:"
            )
            and "The current style does not support customization of this control"
            in warning
        )
    ]
    assert not unexpected, "\n".join(unexpected)
