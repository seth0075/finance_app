import os
from importlib import import_module
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "PersonalDashboard"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "dashboard.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def initialize_database():
    from finance_app.features.calendar.models import CalendarEvent as CalendarEvent
    from finance_app.features.tasks.models import Task

    import_module("finance_app.integrations.google_calendar.models")
    import_module("finance_app.features.finances.models")
    inspector = inspect(engine)
    if inspector.has_table("calendar_events"):
        columns = {column["name"] for column in inspector.get_columns("calendar_events")}
        if not {"calendar_id", "recurrence", "recurrence_until"}.issubset(columns):
            raise RuntimeError(
                "Calendar database needs upgrading. Run: uv run python -m alembic upgrade head"
            )
    if inspector.has_table("finance_categories"):
        columns = {column["name"] for column in inspector.get_columns("finance_categories")}
        if "color" not in columns:
            raise RuntimeError(
                "Finance database needs upgrading. Run: uv run python -m alembic upgrade head"
            )
    Base.metadata.create_all(bind=engine)
