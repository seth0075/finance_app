from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QDateTime,
    QMetaObject,
    QObject,
    QPointF,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import getCppPointer, wrapInstance
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.calendar import viewmodel as calendar_module
from finance_app.features.tasks import repository
from finance_app.features.tasks.viewmodel import TaskViewModel as RealTaskViewModel
from tests.acceptance.ui_helpers import click, find_item, find_items


class TaskViewModel(QObject):
    tasksChanged = Signal()

    def __init__(self):
        super().__init__()
        self.items = [
            {
                "id": "1",
                "title": "Example task",
                "description": "",
                "dueDate": "2026-11-25",
                "priority": 2,
                "completed": False,
                "subtasks": [],
            }
        ]
        self.created = []
        self.updated = []

    @Property("QVariantList", notify=tasksChanged)
    def tasks(self):
        return self.items

    @Slot(result=str)
    def today(self):
        return "2026-11-25"

    @Slot(str, result="QVariantMap")
    def dateRange(self, period):
        return {"start": self.today(), "end": self.today()}

    @Slot(str, bool)
    def setCompleted(self, task_id, completed):
        self.items[0]["completed"] = completed
        self.tasksChanged.emit()

    @Slot(str, str, str, int, result=bool)
    def addTask(self, title, description, due_date, priority):
        self.created.append((title, description, due_date, priority))
        return True

    @Slot(str, str, str, str, int, result=bool)
    def updateTask(self, task_id, title, description, due_date, priority):
        self.updated.append((task_id, title, description, due_date, priority))
        return True


def test_task_controls_and_new_dialog(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    viewmodel = TaskViewModel()
    calendar_viewmodel = QObject()
    engine.setInitialProperties({"taskViewModel": viewmodel, "calendarViewModel": calendar_viewmodel})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)

    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Tasks")
    QTest.qWait(100)

    checkbox = find_item(window.contentItem(), "taskCompletion")
    assert checkbox is not None
    indicator = find_item(checkbox, "checkIndicator")
    assert indicator is not None and indicator.property("radius") == indicator.width() / 2
    click(window, checkbox)
    assert viewmodel.items[0]["completed"] is True

    new_task = find_item(window.contentItem(), "newTaskButton")
    assert new_task is not None
    click(window, new_task)
    title = find_item(window.contentItem(), "taskTitleInput")
    assert title is not None and title.hasActiveFocus()
    title.setProperty("text", "New task")
    priority = find_item(window.contentItem(), "taskPriorityInput")
    assert priority is not None
    click(window, priority)
    QTest.keyClick(window, Qt.Key.Key_End)
    QTest.keyClick(window, Qt.Key.Key_Return)
    QTest.qWait(50)
    save = find_item(window.contentItem(), "saveTaskButton")
    assert save is not None and save.isEnabled()
    click(window, save)
    assert viewmodel.created == [("New task", "", "2026-11-25", 3)]

    edit = find_item(window.contentItem(), "editTaskButton")
    assert edit is not None
    click(window, edit)
    title = find_item(window.contentItem(), "taskTitleInput")
    assert title is not None and title.property("text") == "Example task"
    title.setProperty("text", "Edited task")
    save = find_item(window.contentItem(), "saveTaskButton")
    assert save is not None
    click(window, save)
    assert viewmodel.updated == [("1", "Edited task", "", "2026-11-25", 2)]
    assert not warnings, "\n".join(warnings)


def test_subtask_row_interactions_survive_refresh(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    monkeypatch.setattr(repository, "SessionLocal", sessionmaker(bind=database))
    repo = repository.TaskRepository()
    repo.add("Important", "", date.today(), 3)
    repo.add("Less important", "", date.today(), 1)

    viewmodel = RealTaskViewModel()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    calendar_viewmodel = QObject()
    engine.setInitialProperties({"taskViewModel": viewmodel, "calendarViewModel": calendar_viewmodel})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Tasks")
    QTest.qWait(100)

    label = find_item(window.contentItem(), "taskPriorityLabel")
    assert label is not None and label.property("text") == "High priority"
    toggle = find_item(window.contentItem(), "toggleSubtasksButton")
    assert toggle is not None
    click(window, toggle)
    entry = find_item(window.contentItem(), "subtaskInput")
    assert entry is not None and entry.isVisible()
    entry.setProperty("text", "First step")
    add = find_item(window.contentItem(), "addSubtaskButton")
    assert add is not None and add.isEnabled()
    click(window, add)
    assert repo.get_all()[0]["subtasks"][0]["title"] == "First step"
    entry = find_item(window.contentItem(), "subtaskInput")
    assert entry is not None and entry.isVisible()

    checkbox = find_item(window.contentItem(), "subtaskCompletion")
    assert checkbox is not None
    click(window, checkbox)
    tasks = repo.get_all()
    assert [task["title"] for task in tasks] == ["Less important", "Important"]
    assert tasks[-1]["completed"] is True
    assert find_item(window.contentItem(), "subtaskInput", visible=True) is not None

    checkbox = find_item(window.contentItem(), "subtaskCompletion")
    assert checkbox is not None
    click(window, checkbox)
    assert repo.get_all()[0]["completed"] is False
    delete = find_item(window.contentItem(), "deleteSubtaskButton")
    assert delete is not None
    click(window, delete)
    assert repo.get_all()[0]["subtasks"] == []
    assert not warnings, "\n".join(warnings)


def test_calendar_navigation_and_event_creation(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    sessions = sessionmaker(bind=database)
    monkeypatch.setattr(repository, "SessionLocal", sessions)
    monkeypatch.setattr(calendar_module, "SessionLocal", sessions)
    repo = repository.TaskRepository()
    repo.add("Due today", "", date.today(), 3)
    tasks = RealTaskViewModel()
    calendar = calendar_module.CalendarViewModel()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    engine.setInitialProperties({"taskViewModel": tasks, "calendarViewModel": calendar})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    navigation = find_item(window.contentItem(), "navigationCalendar")
    assert navigation is not None
    click(window, navigation)
    assert window.property("currentPage") == "Calendar"
    assert navigation.property("checked") is True
    QTest.qWait(150)
    page = window.findChild(QObject, "calendarPage")
    assert page is not None, "\n".join(warnings)
    entries = window.findChild(QObject, "calendarEntries")
    assert entries is not None and entries.property("count") == 1
    month = find_item(window.contentItem(), "monthGrid", visible=True)
    assert month.height() > month.width() * 0.8
    assert month.height() > month.parentItem().height() * 0.8
    assert entries.mapToScene(QPointF()).x() >= month.mapToScene(QPointF()).x() + month.width()
    assert find_items(window.contentItem(), "calendarEntryDot")
    click(window, find_item(window.contentItem(), "manageCalendarsButton"))
    toggle = find_item(window.contentItem(), "calendarVisibilitytasks", visible=True)
    assert toggle is not None and toggle.property("checked")
    click(window, toggle)
    assert entries.property("count") == 0
    assert not find_items(window.contentItem(), "calendarEntryDot")
    assert find_item(window.contentItem(), "calendarName", visible=True).property("text") == ""
    manager = window.findChild(QObject, "calendarManager")
    assert QMetaObject.invokeMethod(manager, "close")
    for mode in ("Day", "Week", "Month"):
        click(window, find_item(window.contentItem(), "calendar" + mode + "Button"))
        assert entries.property("count") == 0
    window.setProperty("currentPage", "Dashboard")
    window.setProperty("currentPage", "Calendar")
    QTest.qWait(100)
    page = window.findChild(QObject, "calendarPage")
    entries = window.findChild(QObject, "calendarEntries")
    assert entries.property("count") == 0
    click(window, find_item(window.contentItem(), "manageCalendarsButton"))
    toggle = find_item(window.contentItem(), "calendarVisibilitytasks", visible=True)
    assert not toggle.property("checked")
    click(window, toggle)
    assert entries.property("count") == 1
    manager = window.findChild(QObject, "calendarManager")
    assert QMetaObject.invokeMethod(manager, "close")
    button = find_item(window.contentItem(), "newEventButton")
    assert button is not None
    click(window, button)
    title = find_item(window.contentItem(), "eventTitle")
    assert title is not None
    title.setProperty("text", "Meeting")
    save = find_item(window.contentItem(), "saveEventButton")
    assert save is not None
    click(window, save)
    assert len(calendar.events) == 1
    assert entries.property("count") == 2
    click(window, find_item(window.contentItem(), "manageCalendarsButton"))
    toggle = find_item(window.contentItem(), "calendarVisibilitydefault", visible=True)
    click(window, toggle)
    assert entries.property("count") == 1
    toggle = find_item(window.contentItem(), "calendarVisibilitydefault", visible=True)
    click(window, toggle)
    assert entries.property("count") == 2
    assert QMetaObject.invokeMethod(window.findChild(QObject, "calendarManager"), "close")
    task = repo.get_all()[0]
    repo.update(task["id"], "Moved task", "", date.today() + timedelta(days=1), 3)
    tasks._refresh_tasks()
    QTest.qWait(50)
    assert entries.property("count") == 1

    entry = find_item(window.contentItem(), "calendarEntry", visible=True)
    assert entry is not None
    click(window, entry)
    title = find_item(window.contentItem(), "eventTitle")
    assert title is not None and title.property("text") == "Meeting"
    title.setProperty("text", "Updated meeting")
    save = find_item(window.contentItem(), "saveEventButton")
    click(window, save)
    assert calendar.events[0]["title"] == "Updated meeting"

    tomorrow = date.today() + timedelta(days=1)
    page.setProperty("selectedDate", QDateTime(tomorrow.year, tomorrow.month, tomorrow.day, 12, 0, 0))
    QTest.qWait(50)
    assert entries.property("count") == 1
    for mode in ("Day", "Week", "Month"):
        button = find_item(window.contentItem(), "calendar" + mode + "Button")
        assert button is not None
        click(window, button)
        assert page.property("viewMode") == mode
        assert entries.property("count") == 1
        if mode == "Month":
            month = find_item(window.contentItem(), "monthGrid", visible=True)
            assert entries.mapToScene(QPointF()).x() >= month.mapToScene(QPointF()).x() + month.width()
        else:
            heading = find_item(window.contentItem(), "calendarSelectedDate", visible=True)
            assert abs(entries.mapToScene(QPointF()).x() - heading.mapToScene(QPointF()).x()) < 1

    start = date.today()
    end = start + timedelta(days=2)
    assert calendar.saveEvent(
        "", "Overnight", start.isoformat(), end.isoformat(), "23:00", "00:00", False,
        "default", "none", "", "series", "", False
    ) == ""
    QTest.qWait(50)
    assert entries.property("count") == 2
    page.setProperty("selectedDate", QDateTime(end.year, end.month, end.day, 12, 0, 0))
    QTest.qWait(50)
    assert entries.property("count") == 0
    assert calendar.saveEvent(
        "", "Holiday", start.isoformat(), end.isoformat(), "", "", True,
        "default", "none", "", "series", "", False
    ) == ""
    QTest.qWait(50)
    assert entries.property("count") == 1
    entry = find_item(window.contentItem(), "calendarEntry", visible=True)
    click(window, entry)
    delete = find_item(window.contentItem(), "deleteEventButton", visible=True)
    assert delete is not None
    click(window, delete)
    confirm = window.findChild(QObject, "confirmDeleteEvent")
    assert confirm is not None and confirm.property("visible")
    assert QMetaObject.invokeMethod(confirm, "accept")
    QTest.qWait(50)
    assert entries.property("count") == 0
    assert len(calendar.events) == 2
    assert not warnings, "\n".join(warnings)


def test_calendar_management_and_recurrence_ui(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    database = create_engine("sqlite://")
    Base.metadata.create_all(database)
    sessions = sessionmaker(bind=database)
    monkeypatch.setattr(repository, "SessionLocal", sessions)
    monkeypatch.setattr(calendar_module, "SessionLocal", sessions)
    tasks = RealTaskViewModel()
    calendar = calendar_module.CalendarViewModel()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    engine.setInitialProperties({"taskViewModel": tasks, "calendarViewModel": calendar})
    qml_file = Path(__file__).parents[2] / "src" / "finance_app" / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    assert engine.rootObjects(), "\n".join(warnings)
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    window.resize(1000, 720)
    window.setProperty("currentPage", "Calendar")
    QTest.qWait(150)

    click(window, find_item(window.contentItem(), "manageCalendarsButton"))
    row = find_item(window.contentItem(), "calendarRowdefault", visible=True)
    assert row is not None
    click(window, row)
    assert find_item(window.contentItem(), "calendarName", visible=True).property("text") == "Personal"
    click(window, row)
    assert find_item(window.contentItem(), "calendarName", visible=True).property("text") == ""
    find_item(window.contentItem(), "calendarName", visible=True).setProperty("text", "Birthdays")
    click(window, find_item(window.contentItem(), "chooseCalendarColor", visible=True))
    picker = window.findChild(QObject, "calendarColorPicker")
    assert picker is not None
    picker.setProperty("selectedColor", QColor("#AA33CC"))
    assert QMetaObject.invokeMethod(picker, "accept")
    QTest.qWait(50)
    assert find_item(window.contentItem(), "calendarColor", visible=True).property("text") == "#AA33CC"
    click(window, find_item(window.contentItem(), "saveCalendarButton", visible=True))
    assert any(item["name"] == "Birthdays" and item["color"] == "#AA33CC" for item in calendar.calendars)
    manager = window.findChild(QObject, "calendarManager")
    assert QMetaObject.invokeMethod(manager, "close")
    QTest.qWait(50)

    click(window, find_item(window.contentItem(), "newEventButton"))
    find_item(window.contentItem(), "eventTitle", visible=True).setProperty("text", "Birthday")
    all_day = find_item(window.contentItem(), "eventAllDay", visible=True)
    indicator = find_item(all_day, "checkIndicator")
    assert indicator is not None and indicator.property("radius") == indicator.width() / 2
    click(window, all_day)
    assert all_day.property("checked") is True
    click(window, all_day)
    combo = find_item(window.contentItem(), "eventCalendar", visible=True)
    click(window, combo)
    options = find_items(window.contentItem(), "comboOptionText")
    assert [option.property("text") for option in options] == ["Birthdays", "Personal"]
    click(window, options[0].parentItem())
    QTest.qWait(100)
    repeat = find_item(window.contentItem(), "eventRepeat", visible=True)
    click(window, repeat)
    options = find_items(window.contentItem(), "comboOptionText")
    assert [option.property("text") for option in options] == [
        "Does not repeat", "Daily", "Weekly", "Monthly", "Yearly"
    ]
    click(window, options[-1].parentItem())
    click(window, find_item(window.contentItem(), "saveEventButton", visible=True))
    assert calendar.events[0]["recurrence"] == "yearly"
    assert calendar.occurrencesForDate(date.today().isoformat())[0]["color"] == "#AA33CC"

    click(window, find_item(window.contentItem(), "calendarEntry", visible=True))
    click(window, find_item(window.contentItem(), "editOccurrenceButton", visible=True))
    title = find_item(window.contentItem(), "eventTitle", visible=True)
    title.setProperty("text", "This birthday")
    click(window, find_item(window.contentItem(), "saveEventButton", visible=True))
    assert calendar.occurrencesForDate(date.today().isoformat())[0]["title"] == "This birthday"

    click(window, find_item(window.contentItem(), "calendarEntry", visible=True))
    click(window, find_item(window.contentItem(), "editSeriesButton", visible=True))
    find_item(window.contentItem(), "eventRepeat", visible=True).setProperty("currentIndex", 3)
    click(window, find_item(window.contentItem(), "saveEventButton", visible=True))
    confirm = window.findChild(QObject, "confirmResetOccurrences")
    assert confirm is not None and confirm.property("visible")
    assert QMetaObject.invokeMethod(confirm, "accept")
    QTest.qWait(50)
    assert calendar.events[0]["recurrence"] == "monthly"
    assert calendar.occurrencesForDate(date.today().isoformat())[0]["title"] == "Birthday"
    # The offscreen Qt platform uses a fallback color dialog with native-style warnings.
    unexpected = [
        warning for warning in warnings
        if not (
            warning.startswith("qrc:/qt-project.org/imports/QtQuick/Dialogs/quickimpl/qml/ColorDialog.qml:")
            and "The current style does not support customization of this control" in warning
        )
    ]
    assert not unexpected, "\n".join(unexpected)
