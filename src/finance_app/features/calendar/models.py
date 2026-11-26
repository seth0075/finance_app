from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from finance_app.core.database import Base


class Calendar(Base):
    __tablename__ = "calendars"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False)


class HiddenCalendar(Base):
    __tablename__ = "hidden_calendars"

    calendar_id: Mapped[str] = mapped_column(Text, primary_key=True)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    calendar_id: Mapped[str] = mapped_column(
        ForeignKey("calendars.id", name="fk_event_calendar"), nullable=False
    )
    recurrence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="none", server_default="none"
    )
    recurrence_until: Mapped[date | None] = mapped_column(Date, nullable=True)


class EventException(Base):
    __tablename__ = "calendar_event_exceptions"
    __table_args__ = (UniqueConstraint("event_id", "occurrence_date"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False
    )
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    all_day: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    calendar_id: Mapped[str | None] = mapped_column(
        ForeignKey("calendars.id"), nullable=True
    )
