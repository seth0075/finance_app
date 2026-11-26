from datetime import date, datetime
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from finance_app.core.database import Base
from finance_app.features.calendar import viewmodel
from finance_app.integrations.google_calendar import sync as google_sync
from finance_app.integrations.google_calendar import viewmodel as google_viewmodel
from finance_app.integrations.google_calendar.models import (
    GoogleCache,
    GoogleCalendar,
    GoogleEvent,
)


class Request:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class Resource:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return Request(self.pages[0])

    def list_next(self, request, response):
        index = self.pages.index(response) + 1
        return Request(self.pages[index]) if index < len(self.pages) else None


def test_fetch_paginates_and_expands_google_events(monkeypatch):
    calendars = Resource(
        [
            {
                "items": [
                    {
                        "id": "cal",
                        "summary": "Work",
                        "backgroundColor": "#123456",
                        "timeZone": "UTC",
                    }
                ]
            },
            {"items": []},
        ]
    )
    events = Resource(
        [
            {
                "items": [
                    {
                        "id": "instance-1",
                        "summary": "Holiday",
                        "start": {"date": "2025-01-01"},
                        "end": {"date": "2025-01-03"},
                    },
                ]
            },
            {
                "items": [
                    {
                        "id": "instance-2",
                        "summary": "Meeting",
                        "start": {"dateTime": "2025-01-02T09:00:00+00:00"},
                        "end": {"dateTime": "2025-01-02T10:00:00+00:00"},
                    },
                    {"id": "cancelled", "status": "cancelled"},
                ]
            },
        ]
    )
    service = SimpleNamespace(calendarList=lambda: calendars, events=lambda: events)
    monkeypatch.setattr(google_sync, "build", lambda *args, **kwargs: service)
    credentials = SimpleNamespace(expired=False)

    calendar_rows, event_rows, start, end = google_sync.fetch(
        credentials, date(2025, 1, 1)
    )

    assert (start, end) == (date(2024, 1, 2), date(2026, 1, 1))
    assert [(row.name, row.color) for row in calendar_rows] == [("Work", "#123456")]
    assert [(row.title, row.all_day) for row in event_rows] == [
        ("Holiday", True),
        ("Meeting", False),
    ]
    assert event_rows[0].ends_at == datetime(2025, 1, 2)
    assert event_rows[1].starts_at == datetime.fromisoformat(
        "2025-01-02T09:00:00+00:00"
    ).astimezone().replace(tzinfo=None)
    assert events.calls[0]["singleEvents"] is True
    assert events.calls[0]["showDeleted"] is False
    assert len(calendars.calls) == 1


def test_cache_is_read_only_persistent_and_atomically_replaced(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessions)
    start, end = date(2025, 1, 1), date(2025, 12, 31)
    with sessions() as session:
        google_sync.replace_cache(
            session,
            (
                [GoogleCalendar(id="remote", name="Personal", color="#123456")],
                [
                    GoogleEvent(
                        id="e",
                        calendar_id="remote",
                        title="Holiday",
                        starts_at=datetime(2025, 1, 1),
                        ends_at=datetime(2025, 1, 2),
                        all_day=True,
                    )
                ],
                start,
                end,
            ),
        )
    vm = viewmodel.CalendarViewModel()
    remote = next(item for item in vm.calendars if item["id"] == "google:remote")
    assert remote["readOnly"]
    event = vm.occurrencesForDate("2025-01-02")[0]
    assert (
        event["title"] == "Holiday"
        and event["readOnly"]
        and event["color"] == "#123456"
    )
    assert vm.saveCalendar(remote["id"], "Changed", "#123456")
    assert vm.deleteCalendar(remote["id"])
    assert vm.deleteEvent(event["id"], "series", "")
    assert vm.saveEvent(
        "", "New event", "2025-01-02", "2025-01-02", "", "", True,
        remote["id"], "none", "", "series", "", False,
    )

    assert vm.setCalendarVisible(remote["id"], False) == ""
    with sessions() as session:
        google_sync.replace_cache(
            session,
            (
                [GoogleCalendar(id="remote", name="Personal", color="#123456")],
                [GoogleEvent(id="e", calendar_id="remote", title="Holiday",
                             starts_at=datetime(2025, 1, 1), ends_at=datetime(2025, 1, 2),
                             all_day=True)],
                start, end,
            ),
        )
    vm = viewmodel.CalendarViewModel()
    assert not next(item for item in vm.calendars if item["id"] == remote["id"])["visible"]
    assert vm.occurrencesForDate("2025-01-02") == []
    assert vm.setCalendarVisible(remote["id"], True) == ""
    assert vm.occurrencesForDate("2025-01-02")[0]["title"] == "Holiday"
    assert vm.setCalendarVisible(remote["id"], False) == ""
    with sessions() as session:
        with pytest.raises(IntegrityError):
            google_sync.replace_cache(
                session,
                (
                    [
                        GoogleCalendar(id="duplicate", name="a", color="#123456"),
                        GoogleCalendar(id="duplicate", name="b", color="#123456"),
                    ],
                    [],
                    start,
                    end,
                ),
            )
        session.rollback()
        assert session.get(GoogleCalendar, "remote") is not None
        assert session.scalar(select(GoogleEvent)).title == "Holiday"
        assert session.get(GoogleCache, 1).starts_on == start
        google_sync.clear_cache(session)
    assert viewmodel.CalendarViewModel().occurrencesForDate("2025-01-02") == []
    with sessions() as session:
        from finance_app.features.calendar.models import HiddenCalendar
        assert session.get(HiddenCalendar, remote["id"]) is None


def test_sync_failure_keeps_cache_and_reports_error(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(google_viewmodel, "SessionLocal", sessions)
    monkeypatch.setattr(google_sync, "load_credentials", lambda: None)
    vm = google_viewmodel.GoogleCalendarViewModel()
    with sessions() as session:
        google_sync.replace_cache(
            session,
            (
                [GoogleCalendar(id="remote", name="Work", color="#123456")],
                [],
                date(2025, 1, 1),
                date(2025, 12, 31),
            ),
        )
    monkeypatch.setattr(google_sync, "load_credentials", lambda: object())

    def fail(_credentials):
        raise RuntimeError("Network unavailable")

    monkeypatch.setattr(google_sync, "fetch", fail)
    vm._run("refresh", "")
    assert vm.connected
    assert "Network unavailable" in vm.status
    assert "2025-01-01" in vm.cacheCoverage
    with sessions() as session:
        assert session.get(GoogleCalendar, "remote") is not None


def test_connect_and_disconnect_credential_store(monkeypatch):
    stored = {}
    monkeypatch.setattr(
        google_sync.keyring,
        "get_password",
        lambda service, account: stored.get((service, account)),
    )
    monkeypatch.setattr(
        google_sync.keyring,
        "set_password",
        lambda service, account, value: stored.update({(service, account): value}),
    )
    monkeypatch.setattr(
        google_sync.keyring,
        "delete_password",
        lambda service, account: stored.pop((service, account)),
    )
    credentials = SimpleNamespace(
        to_json=lambda: (
            '{"token": "test-token", "client_id": "client", "client_secret": "secret", "refresh_token": "refresh"}'
        )
    )
    flow = SimpleNamespace(run_local_server=lambda **kwargs: credentials)
    monkeypatch.setattr(
        google_sync.InstalledAppFlow,
        "from_client_secrets_file",
        lambda *args, **kwargs: flow,
    )
    assert google_sync.connect("client.json") is credentials
    assert google_sync.load_credentials().token == "test-token"
    google_sync.forget_credentials()
    assert google_sync.load_credentials() is None


def test_disconnect_removes_cache_and_credentials(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(google_viewmodel, "SessionLocal", sessions)
    monkeypatch.setattr(google_sync, "load_credentials", lambda: None)
    vm = google_viewmodel.GoogleCalendarViewModel()
    with sessions() as session:
        google_sync.replace_cache(
            session,
            (
                [GoogleCalendar(id="remote", name="Work", color="#123456")],
                [],
                date(2025, 1, 1),
                date(2025, 12, 31),
            ),
        )
    forgotten = []
    monkeypatch.setattr(
        google_sync, "forget_credentials", lambda: forgotten.append(True)
    )
    vm.disconnectAccount()
    assert forgotten == [True]
    assert not vm.connected and not vm.hasCache
    with sessions() as session:
        assert session.get(GoogleCalendar, "remote") is None


def test_background_connect_updates_calendar_view(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _app = QGuiApplication.instance() or QGuiApplication([])
    engine = create_engine(f"sqlite:///{(tmp_path / 'cache.db').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(google_viewmodel, "SessionLocal", sessions)
    monkeypatch.setattr(viewmodel, "SessionLocal", sessions)
    credential = object()
    stored = []
    monkeypatch.setattr(google_sync, "load_credentials", lambda: stored[0] if stored else None)

    def connect(_path):
        stored.append(credential)
        return credential

    monkeypatch.setattr(google_sync, "connect", connect)
    monkeypatch.setattr(google_sync, "fetch", lambda _credentials: (
        [GoogleCalendar(id="remote", name="Work", color="#123456")],
        [GoogleEvent(id="e", calendar_id="remote", title="Imported",
                     starts_at=datetime(2025, 1, 1), ends_at=datetime(2025, 1, 1), all_day=True)],
        date(2025, 1, 1), date(2025, 12, 31),
    ))
    calendar = viewmodel.CalendarViewModel()
    google = google_viewmodel.GoogleCalendarViewModel()
    google.cacheChanged.connect(calendar._refresh)
    google.connectAccount(QUrl.fromLocalFile(str(tmp_path / "client.json")))
    for _ in range(100):
        if not google.busy:
            break
        QTest.qWait(20)
    assert not google.busy and google.connected
    assert calendar.occurrencesForDate("2025-01-01")[0]["title"] == "Imported"
