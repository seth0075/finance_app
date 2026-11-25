import calendar as calendar_dates
import re
from datetime import date, datetime, time, timedelta

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy import delete, select

from finance_app.core.database import SessionLocal
from finance_app.features.calendar.models import Calendar, CalendarEvent, EventException


def occurrence_start(start, recurrence, index):
    if recurrence in ("daily", "weekly"):
        try:
            return start + timedelta(days=index * (7 if recurrence == "weekly" else 1))
        except OverflowError:
            return None
    if recurrence in ("monthly", "yearly"):
        month_index = (
            start.year * 12
            + start.month
            - 1
            + index * (12 if recurrence == "yearly" else 1)
        )
        year, month = divmod(month_index, 12)
        month += 1
        if not 1 <= year <= 9999:
            return None
        return start.replace(
            year=year,
            month=month,
            day=min(start.day, calendar_dates.monthrange(year, month)[1]),
        )
    return start if index == 0 else None


def occurrences_on(event, day):
    start = datetime.fromisoformat(event["start"])
    end = datetime.fromisoformat(event["end"])
    duration = end - start
    earliest = max(
        date.min, day - timedelta(days=min(day.toordinal() - 1, duration.days + 1))
    )
    frequency = event["recurrence"]
    if frequency == "daily":
        index = max(0, (earliest - start.date()).days)
    elif frequency == "weekly":
        index = max(0, (earliest - start.date()).days // 7)
    elif frequency in ("monthly", "yearly"):
        months = (earliest.year - start.year) * 12 + earliest.month - start.month
        index = max(0, months // (12 if frequency == "yearly" else 1) - 1)
    else:
        index = 0
    until = date.fromisoformat(event["until"]) if event["until"] else None
    while True:
        occurrence = occurrence_start(start, frequency, index)
        if (
            occurrence is None
            or occurrence.date() > day
            or (until and occurrence.date() > until)
        ):
            break
        occurrence_end = min(occurrence, datetime.max - duration) + duration
        if spans_day(occurrence, occurrence_end, event["allDay"], day):
            yield occurrence, occurrence_end
        if frequency == "none":
            break
        index += 1


def spans_day(start, end, all_day, day):
    if all_day:
        return start.date() <= day <= end.date()
    return start.date() <= day and (
        end.date() > day or (end.date() == day and end.time() != time.min)
    )


def is_occurrence(event, day):
    start = event.starts_at
    if day < start.date() or (event.recurrence_until and day > event.recurrence_until):
        return False
    if event.recurrence in ("daily", "weekly"):
        days = (day - start.date()).days
        interval = 7 if event.recurrence == "weekly" else 1
        return days % interval == 0
    if event.recurrence in ("monthly", "yearly"):
        months = (day.year - start.year) * 12 + day.month - start.month
        interval = 12 if event.recurrence == "yearly" else 1
        candidate = occurrence_start(start, event.recurrence, months // interval)
        return (
            months % interval == 0 and candidate is not None and candidate.date() == day
        )
    return False


def event_values(title, start_date, end_date, start_time, end_time, all_day):
    title = title.strip()
    if not title or len(title) > 500:
        return None, "Enter a title of up to 500 characters."
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_date) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", end_date
        ):
            raise ValueError
        start_day, end_day = (
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
        )
        if all_day:
            start, end = (
                datetime.combine(start_day, time.min),
                datetime.combine(end_day, time.min),
            )
        else:
            if not re.fullmatch(r"\d{2}:\d{2}", start_time) or not re.fullmatch(
                r"\d{2}:\d{2}", end_time
            ):
                raise ValueError
            start = datetime.combine(start_day, time.fromisoformat(start_time))
            end = datetime.combine(end_day, time.fromisoformat(end_time))
    except ValueError:
        return None, "Enter valid dates (YYYY-MM-DD) and times (HH:MM)."
    if end < start or (not all_day and end == start):
        return (
            None,
            "End must be after start (or on the same day for an all-day event).",
        )
    return (title, start, end, all_day), ""


class CalendarViewModel(QObject):
    eventsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        with SessionLocal() as session:
            if session.get(Calendar, "tasks") is None:
                session.add(Calendar(id="tasks", name="Tasks", color="#62C6A0"))
            if (
                session.scalar(
                    select(Calendar.id).where(Calendar.id != "tasks").limit(1)
                )
                is None
            ):
                session.add(Calendar(id="default", name="Personal", color="#7395F5"))
            session.commit()
        self._refresh()

    def _refresh(self):
        with SessionLocal() as session:
            self._calendars = [
                {"id": item.id, "name": item.name, "color": item.color}
                for item in session.scalars(select(Calendar).order_by(Calendar.name))
            ]
            self._events = [
                {
                    "id": item.id,
                    "title": item.title,
                    "start": item.starts_at.isoformat(),
                    "end": item.ends_at.isoformat(),
                    "startDate": item.starts_at.date().isoformat(),
                    "endDate": item.ends_at.date().isoformat(),
                    "startTime": item.starts_at.strftime("%H:%M"),
                    "endTime": item.ends_at.strftime("%H:%M"),
                    "allDay": item.all_day,
                    "calendarId": item.calendar_id,
                    "recurrence": item.recurrence,
                    "until": item.recurrence_until.isoformat()
                    if item.recurrence_until
                    else "",
                }
                for item in session.scalars(
                    select(CalendarEvent).order_by(
                        CalendarEvent.starts_at, CalendarEvent.title
                    )
                )
            ]
            self._exceptions = [
                {
                    "eventId": item.event_id,
                    "occurrenceDate": item.occurrence_date.isoformat(),
                    "cancelled": item.cancelled,
                    "title": item.title,
                    "start": item.starts_at.isoformat() if item.starts_at else None,
                    "end": item.ends_at.isoformat() if item.ends_at else None,
                    "allDay": item.all_day,
                    "calendarId": item.calendar_id,
                }
                for item in session.scalars(select(EventException))
            ]
            changed_events = {item["eventId"] for item in self._exceptions}
            for item in self._events:
                item["hasExceptions"] = item["id"] in changed_events
        self.eventsChanged.emit()

    @Property("QVariantList", notify=eventsChanged)
    def events(self):
        return self._events

    @Property("QVariantList", notify=eventsChanged)
    def calendars(self):
        return self._calendars

    @Slot(str, result="QVariantList")
    def occurrencesForDate(self, day_string):
        day = date.fromisoformat(day_string)
        colors = {item["id"]: item["color"] for item in self._calendars}
        exceptions = {
            (item["eventId"], item["occurrenceDate"]): item for item in self._exceptions
        }
        results = []
        events = {item["id"]: item for item in self._events}
        for event in self._events:
            for start, end in occurrences_on(event, day):
                key = (event["id"], start.date().isoformat())
                if key not in exceptions:
                    results.append(
                        self._display(
                            event,
                            start,
                            end,
                            event["title"],
                            event["allDay"],
                            event["calendarId"],
                            key[1],
                            colors,
                        )
                    )
        for exception in self._exceptions:
            if exception["cancelled"]:
                continue
            start, end = (
                datetime.fromisoformat(exception["start"]),
                datetime.fromisoformat(exception["end"]),
            )
            if spans_day(start, end, exception["allDay"], day):
                results.append(
                    self._display(
                        events[exception["eventId"]],
                        start,
                        end,
                        exception["title"],
                        exception["allDay"],
                        exception["calendarId"],
                        exception["occurrenceDate"],
                        colors,
                    )
                )
        return sorted(
            results,
            key=lambda item: (
                not item["allDay"],
                item["startDate"],
                item["startTime"],
                item["title"].casefold(),
            ),
        )

    @staticmethod
    def _display(
        event, start, end, title, all_day, calendar_id, occurrence_date, colors
    ):
        return {
            **event,
            "series": event,
            "title": title,
            "startDate": start.date().isoformat(),
            "endDate": end.date().isoformat(),
            "startTime": start.strftime("%H:%M"),
            "endTime": end.strftime("%H:%M"),
            "allDay": all_day,
            "calendarId": calendar_id,
            "color": colors[calendar_id],
            "occurrenceDate": occurrence_date,
        }

    @Slot(str, str, str, result=str)
    def saveCalendar(self, calendar_id, name, color):
        name = name.strip()
        if not name or len(name) > 100:
            return "Enter a calendar name of up to 100 characters."
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            return "Enter a color in #RRGGBB format."
        with SessionLocal() as session:
            calendar = session.get(Calendar, calendar_id) if calendar_id else None
            if calendar_id and calendar is None:
                return "This calendar no longer exists."
            if calendar_id == "tasks" and name != "Tasks":
                return "The Tasks calendar cannot be renamed."
            if any(
                item.id != calendar_id and item.name.casefold() == name.casefold()
                for item in session.scalars(select(Calendar))
            ):
                return "A calendar with this name already exists."
            if calendar is None:
                calendar = Calendar()
                session.add(calendar)
            calendar.name, calendar.color = name, color.upper()
            session.commit()
        self._refresh()
        return ""

    @Slot(str, result=str)
    def deleteCalendar(self, calendar_id):
        if calendar_id == "tasks":
            return "The Tasks calendar cannot be deleted."
        with SessionLocal() as session:
            calendar = session.get(Calendar, calendar_id)
            if calendar is None:
                return "This calendar no longer exists."
            count = len(
                list(session.scalars(select(Calendar).where(Calendar.id != "tasks")))
            )
            if count <= 1:
                return "Keep at least one event calendar."
            ids = list(
                session.scalars(
                    select(CalendarEvent.id).where(
                        CalendarEvent.calendar_id == calendar_id
                    )
                )
            )
            if ids:
                session.execute(
                    delete(EventException).where(EventException.event_id.in_(ids))
                )
                session.execute(delete(CalendarEvent).where(CalendarEvent.id.in_(ids)))
            for item in session.scalars(
                select(EventException).where(EventException.calendar_id == calendar_id)
            ):
                item.cancelled, item.calendar_id = True, None
            session.delete(calendar)
            session.commit()
        self._refresh()
        return ""

    @Slot(str, str, str, str, str, str, bool, str, str, str, str, str, bool, result=str)
    def saveEvent(
        self,
        event_id,
        title,
        start_date,
        end_date,
        start_time,
        end_time,
        all_day,
        calendar_id,
        recurrence,
        until_string,
        scope,
        occurrence_date,
        reset_exceptions,
    ):
        values, error = event_values(
            title, start_date, end_date, start_time, end_time, all_day
        )
        if error:
            return error
        if recurrence not in ("none", "daily", "weekly", "monthly", "yearly"):
            return "Choose a valid repeat option."
        try:
            if until_string and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", until_string):
                raise ValueError
            until = date.fromisoformat(until_string) if until_string else None
            original_day = (
                date.fromisoformat(occurrence_date) if occurrence_date else None
            )
        except ValueError:
            return "Enter a valid repeat end date."
        title, start, end, all_day = values
        if until and (
            recurrence == "none" or (scope != "occurrence" and until < start.date())
        ):
            return "Repeat end must be on or after the start date."
        if scope not in ("series", "occurrence"):
            return "Choose whether to edit the occurrence or series."
        with SessionLocal() as session:
            calendar = session.get(Calendar, calendar_id)
            if calendar is None or calendar_id == "tasks":
                return "Choose an event calendar."
            event = session.get(CalendarEvent, event_id) if event_id else None
            if event_id and event is None:
                return "This event no longer exists."
            if scope == "occurrence":
                if (
                    event is None
                    or original_day is None
                    or not is_occurrence(event, original_day)
                ):
                    return "Choose a valid recurring occurrence."
                exception = session.scalar(
                    select(EventException).where(
                        EventException.event_id == event_id,
                        EventException.occurrence_date == original_day,
                    )
                )
                if exception is None:
                    exception = EventException(
                        event_id=event_id, occurrence_date=original_day
                    )
                    session.add(exception)
                exception.cancelled = False
                exception.title, exception.starts_at, exception.ends_at = (
                    title,
                    start,
                    end,
                )
                exception.all_day, exception.calendar_id = all_day, calendar_id
            else:
                if event is None:
                    event = CalendarEvent(color="#7395F5")
                    session.add(event)
                elif (
                    event.starts_at.date() != start.date()
                    or event.recurrence != recurrence
                    or event.recurrence_until != until
                ):
                    has_exceptions = (
                        session.scalar(
                            select(EventException.id)
                            .where(EventException.event_id == event_id)
                            .limit(1)
                        )
                        is not None
                    )
                    if has_exceptions and not reset_exceptions:
                        return "Confirm removing individual occurrence changes before changing the schedule."
                    if has_exceptions:
                        session.execute(
                            delete(EventException).where(
                                EventException.event_id == event_id
                            )
                        )
                event.title, event.starts_at, event.ends_at = title, start, end
                event.all_day, event.calendar_id = all_day, calendar_id
                event.recurrence, event.recurrence_until = recurrence, until
            session.commit()
        self._refresh()
        return ""

    @Slot(str, str, str, result=str)
    def deleteEvent(self, event_id, scope, occurrence_date):
        with SessionLocal() as session:
            event = session.get(CalendarEvent, event_id)
            if event is None:
                return "This event no longer exists."
            if scope == "series":
                session.execute(
                    delete(EventException).where(EventException.event_id == event_id)
                )
                session.delete(event)
            elif scope == "occurrence" and event.recurrence != "none":
                try:
                    day = date.fromisoformat(occurrence_date)
                except ValueError:
                    return "Choose a valid occurrence."
                if not is_occurrence(event, day):
                    return "Choose a valid occurrence."
                exception = session.scalar(
                    select(EventException).where(
                        EventException.event_id == event_id,
                        EventException.occurrence_date == day,
                    )
                )
                if exception is None:
                    exception = EventException(event_id=event_id, occurrence_date=day)
                    session.add(exception)
                exception.cancelled = True
            else:
                return "Choose whether to delete the occurrence or series."
            session.commit()
        self._refresh()
        return ""
