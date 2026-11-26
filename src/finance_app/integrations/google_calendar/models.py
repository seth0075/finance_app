from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from finance_app.core.database import Base


class GoogleCalendar(Base):
    __tablename__ = "google_calendars"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)


class GoogleEvent(Base):
    __tablename__ = "google_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    calendar_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GoogleCache(Base):
    __tablename__ = "google_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
