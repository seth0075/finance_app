import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from finance_app.core import database
from finance_app.core.database import Base
from finance_app.features.calendar import viewmodel


@pytest.fixture
def vm(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=engine))
    return viewmodel.CalendarViewModel()


def save(
    vm,
    title="Event",
    start="2024-01-31",
    end="2024-01-31",
    recurrence="none",
    until="",
    event_id="",
    scope="series",
    occurrence="",
    calendar="default",
    all_day=True,
):
    return vm.saveEvent(
        event_id,
        title,
        start,
        end,
        "09:00",
        "10:00",
        all_day,
        calendar,
        recurrence,
        until,
        scope,
        occurrence,
        False,
    )


def test_calendar_management_and_colors(vm):
    assert vm.saveCalendar("", "Work", "#123456") == ""
    work = next(item for item in vm.calendars if item["name"] == "Work")
    assert vm.saveCalendar(work["id"], "Office", "#ABCDEF") == ""
    assert vm.saveCalendar("", "office", "#ABCDEF")
    assert vm.saveCalendar("tasks", "Renamed", "#123456")
    assert vm.saveCalendar("tasks", "Tasks", "#123456") == ""
    assert vm.deleteCalendar("tasks")
    assert save(vm, calendar=work["id"]) == ""
    assert vm.occurrencesForDate("2024-01-31")[0]["color"] == "#ABCDEF"
    assert vm.deleteCalendar(work["id"]) == ""
    assert not vm.events
    assert vm.deleteCalendar("default")

    assert vm.saveCalendar("", "Second", "#112233") == ""
    assert vm.deleteCalendar("default") == ""
    assert all(
        item["id"] != "default" for item in viewmodel.CalendarViewModel().calendars
    )


@pytest.mark.parametrize(
    ("frequency", "start", "present", "absent"),
    [
        ("daily", "2024-01-31", "2024-02-01", "2024-01-30"),
        ("weekly", "2024-01-31", "2024-02-07", "2024-02-08"),
        ("monthly", "2024-01-31", "2024-02-29", "2024-03-30"),
        ("yearly", "2024-02-29", "2025-02-28", "2025-03-01"),
    ],
)
def test_recurrence_and_end_date(vm, frequency, start, present, absent):
    assert save(vm, start=start, end=start, recurrence=frequency, until=present) == ""
    assert len(vm.occurrencesForDate(present)) == 1
    assert vm.occurrencesForDate(absent) == []
    assert vm.occurrencesForDate("2026-03-01") == []


def test_individual_occurrences_and_series(vm):
    assert save(vm, recurrence="monthly") == ""
    event_id = vm.events[0]["id"]
    assert (
        save(
            vm,
            title="Moved",
            start="2024-03-03",
            end="2024-03-03",
            recurrence="monthly",
            event_id=event_id,
            scope="occurrence",
            occurrence="2024-02-29",
        )
        == ""
    )
    assert vm.occurrencesForDate("2024-02-29") == []
    assert vm.occurrencesForDate("2024-03-03")[0]["title"] == "Moved"
    assert (
        viewmodel.CalendarViewModel().occurrencesForDate("2024-03-03")[0]["title"]
        == "Moved"
    )
    assert vm.deleteEvent(event_id, "occurrence", "2024-03-30")
    assert len(vm.occurrencesForDate("2024-03-31")) == 1
    assert vm.deleteEvent(event_id, "occurrence", "2024-03-31") == ""
    assert vm.occurrencesForDate("2024-03-31") == []
    assert save(vm, event_id=event_id, recurrence="yearly")
    assert len(vm.occurrencesForDate("2024-03-03")) == 1
    assert (
        vm.saveEvent(
            event_id,
            "Event",
            "2024-01-31",
            "2024-01-31",
            "",
            "",
            True,
            "default",
            "yearly",
            "",
            "series",
            "",
            True,
        )
        == ""
    )
    assert vm.occurrencesForDate("2024-03-03") == []
    assert vm.deleteEvent(event_id, "series", "") == ""
    assert vm.occurrencesForDate("2024-03-03") == []


def test_deleting_override_calendar_cancels_only_its_occurrence(vm):
    assert vm.saveCalendar("", "Work", "#123456") == ""
    work = next(item for item in vm.calendars if item["name"] == "Work")
    assert save(vm, recurrence="monthly") == ""
    event_id = vm.events[0]["id"]
    assert (
        save(
            vm,
            start="2024-02-29",
            end="2024-02-29",
            recurrence="monthly",
            event_id=event_id,
            scope="occurrence",
            occurrence="2024-02-29",
            calendar=work["id"],
        )
        == ""
    )
    assert vm.deleteCalendar(work["id"]) == ""
    assert vm.occurrencesForDate("2024-02-29") == []
    assert len(vm.occurrencesForDate("2024-03-31")) == 1


def test_overlapping_multiday_occurrences_and_validation(vm):
    assert save(vm, start="2024-01-01", end="2024-01-03", recurrence="daily") == ""
    assert len(vm.occurrencesForDate("2024-01-03")) == 3
    assert save(vm, title="") != ""
    assert save(vm, start="2024-02-30") != ""
    assert save(vm, recurrence="monthly", until="2024-01-01") != ""
    assert save(vm, calendar="tasks") != ""
    assert vm.saveCalendar("", "Bad", "red") != ""
    assert len(vm.occurrencesForDate("9999-12-31")) == 3


@pytest.mark.parametrize("initialize_first", [False, True])
def test_calendar_migration(monkeypatch, tmp_path, initialize_first):
    url = f"sqlite:///{(tmp_path / 'calendar.db').as_posix()}"
    monkeypatch.setattr(database, "DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "e029df3e0652")
    engine = create_engine(url)
    if initialize_first:
        Base.metadata.create_all(engine)
    command.upgrade(config, "head")
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=engine))
    assert save(viewmodel.CalendarViewModel()) == ""
    command.downgrade(config, "c1264a55029e")


def test_migration_preserves_existing_events(monkeypatch, tmp_path):
    url = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    monkeypatch.setattr(database, "DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "c1264a55029e")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO calendar_events VALUES ('old', 'Birthday', '2024-01-01 00:00:00', '2024-01-01 00:00:00', 1, '#F07878')"
            )
        )
    command.upgrade(config, "head")
    monkeypatch.setattr(viewmodel, "SessionLocal", sessionmaker(bind=engine))
    vm = viewmodel.CalendarViewModel()
    event = vm.occurrencesForDate("2024-01-01")[0]
    assert event["title"] == "Birthday"
    assert event["calendarId"] == "default"
    assert event["color"] == "#7395F5"


def test_stale_database_requires_migration(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE calendar_events (id VARCHAR(36) PRIMARY KEY)")
        )
    monkeypatch.setattr(database, "engine", engine)
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        database.initialize_database()
