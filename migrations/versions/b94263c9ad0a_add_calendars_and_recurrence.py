"""Add calendars and recurring-event exceptions."""

import sqlalchemy as sa
from alembic import context, op

revision = "b94263c9ad0a"
down_revision = "c1264a55029e"
branch_labels = None
depends_on = None


def upgrade():
    if context.is_offline_mode():
        raise RuntimeError("Calendar migration requires an online database connection.")
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("calendars"):
        op.create_table(
            "calendars",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("color", sa.String(7), nullable=False),
        )
    bind.execute(
        sa.text(
            "INSERT INTO calendars (id, name, color) SELECT :id, :name, :color WHERE NOT EXISTS (SELECT 1 FROM calendars WHERE id = :id)"
        ),
        [
            {"id": "default", "name": "Personal", "color": "#7395F5"},
            {"id": "tasks", "name": "Tasks", "color": "#62C6A0"},
        ],
    )
    columns = {column["name"] for column in inspector.get_columns("calendar_events")}
    if "calendar_id" not in columns:
        with op.batch_alter_table("calendar_events") as batch:
            batch.add_column(
                sa.Column(
                    "calendar_id",
                    sa.String(36),
                    nullable=False,
                    server_default="default",
                )
            )
            batch.add_column(
                sa.Column(
                    "recurrence", sa.String(10), nullable=False, server_default="none"
                )
            )
            batch.add_column(sa.Column("recurrence_until", sa.Date(), nullable=True))
            batch.create_foreign_key(
                "fk_event_calendar", "calendars", ["calendar_id"], ["id"]
            )
    elif not {"recurrence", "recurrence_until"}.issubset(columns):
        raise RuntimeError("Existing calendar event schema is incomplete.")
    if not sa.inspect(bind).has_table("calendar_event_exceptions"):
        op.create_table(
            "calendar_event_exceptions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "event_id",
                sa.String(36),
                sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("occurrence_date", sa.Date(), nullable=False),
            sa.Column("cancelled", sa.Boolean(), nullable=False),
            sa.Column("title", sa.String(500)),
            sa.Column("starts_at", sa.DateTime()),
            sa.Column("ends_at", sa.DateTime()),
            sa.Column("all_day", sa.Boolean()),
            sa.Column("calendar_id", sa.String(36), sa.ForeignKey("calendars.id")),
            sa.UniqueConstraint("event_id", "occurrence_date"),
        )


def downgrade():
    op.drop_table("calendar_event_exceptions")
    with op.batch_alter_table("calendar_events") as batch:
        batch.drop_constraint("fk_event_calendar", type_="foreignkey")
        batch.drop_column("recurrence_until")
        batch.drop_column("recurrence")
        batch.drop_column("calendar_id")
    op.drop_table("calendars")
