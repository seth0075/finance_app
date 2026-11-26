import logging
from threading import Thread

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from finance_app.core.database import SessionLocal
from finance_app.integrations.google_calendar import sync as google_sync
from finance_app.integrations.google_calendar.models import GoogleCache

logger = logging.getLogger(__name__)


class GoogleCalendarViewModel(QObject):
    changed = Signal()
    cacheChanged = Signal()
    _finished = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._connected = False
        self._status = "Connect a Google account to view its calendars."
        self._finished.connect(self._complete)
        try:
            self._connected = google_sync.load_credentials() is not None
        except Exception:
            logger.exception("Could not read Google Calendar credentials")
            self._status = (
                "Could not read Google credentials from the system credential store."
            )
        if self._connected:
            self.refresh()

    @Property(bool, notify=changed)
    def connected(self):
        return self._connected

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(str, notify=changed)
    def cacheCoverage(self):
        with SessionLocal() as session:
            cache = session.get(GoogleCache, 1)
            if cache is None:
                return "No Google events cached."
            return f"Cached {cache.starts_on.isoformat()} through {cache.ends_on.isoformat()} (last synced {cache.synced_at:%Y-%m-%d %H:%M})."

    @Property(bool, notify=changed)
    def hasCache(self):
        with SessionLocal() as session:
            return session.get(GoogleCache, 1) is not None

    def _start(self, operation, client_file=""):
        if self._busy:
            return
        self._busy = True
        self._status = (
            "Complete sign-in in your browser, then return here."
            if operation == "connect"
            else "Refreshing Google calendars..."
        )
        self.changed.emit()
        Thread(target=self._run, args=(operation, client_file), daemon=True).start()

    def _run(self, operation, client_file):
        try:
            credentials = (
                google_sync.connect(client_file)
                if operation == "connect"
                else google_sync.load_credentials()
            )
            if credentials is None:
                raise ValueError(
                    "Google credentials are missing. Connect your account again."
                )
            snapshot = google_sync.fetch(credentials)
            with SessionLocal() as session:
                google_sync.replace_cache(session, snapshot)
            self._finished.emit("success", "")
        except Exception as exc:
            logger.exception("Google Calendar %s failed", operation)
            self._finished.emit("error", str(exc))

    @Slot(str, str)
    def _complete(self, result, detail):
        self._busy = False
        if result == "success":
            self.cacheChanged.emit()
        try:
            self._connected = google_sync.load_credentials() is not None
        except Exception:
            logger.exception("Could not read Google Calendar credentials")
            self._connected = False
            detail = "Could not read credentials from the system credential store."
            result = "error"
        if result == "success":
            self._status = "Google calendars updated. Events are read-only."
        else:
            self._status = f"Google Calendar sync failed: {detail}"
        self.changed.emit()

    @Slot(QUrl)
    def connectAccount(self, file_url):
        path = file_url.toLocalFile()
        if not path:
            self._status = "Choose a Google desktop OAuth client JSON file."
            self.changed.emit()
            return
        self._start("connect", path)

    @Slot()
    def refresh(self):
        if self._connected:
            self._start("refresh")

    @Slot()
    def disconnectAccount(self):
        if self._busy:
            return
        try:
            with SessionLocal() as session:
                google_sync.clear_cache(session)
            self.cacheChanged.emit()
            google_sync.forget_credentials()
        except Exception as exc:
            logger.exception("Could not disconnect Google Calendar")
            self._status = f"Could not disconnect Google Calendar: {exc}"
        else:
            self._connected = False
            self._status = "Disconnected and removed cached Google data."
        self.changed.emit()
