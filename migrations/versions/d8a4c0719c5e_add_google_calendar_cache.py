"""Add the read-only Google Calendar cache."""

import sqlalchemy as sa
from alembic import op

revision = "d8a4c0719c5e"
down_revision = "b94263c9ad0a"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "google_calendars" not in existing:
        op.create_table(
            "google_calendars",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("color", sa.String(7), nullable=False),
        )
    if "google_events" not in existing:
        op.create_table(
            "google_events",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("calendar_id", sa.Text(), primary_key=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("ends_at", sa.DateTime(), nullable=False),
            sa.Column("all_day", sa.Boolean(), nullable=False),
        )
    if "google_cache" not in existing:
        op.create_table(
            "google_cache",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("starts_on", sa.Date(), nullable=False),
            sa.Column("ends_on", sa.Date(), nullable=False),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
        )


def downgrade():
    op.drop_table("google_cache")
    op.drop_table("google_events")
    op.drop_table("google_calendars")
