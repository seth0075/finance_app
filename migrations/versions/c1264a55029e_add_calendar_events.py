"""Add independent calendar events."""

import sqlalchemy as sa
from alembic import context, op

revision = "c1264a55029e"
down_revision = "e029df3e0652"
branch_labels = None
depends_on = None


def upgrade():
    if not context.is_offline_mode():
        inspector = sa.inspect(op.get_bind())
        if inspector.has_table("calendar_events"):
            columns = {
                column["name"] for column in inspector.get_columns("calendar_events")
            }
            if not {"id", "title", "starts_at", "ends_at", "all_day", "color"}.issubset(columns):
                raise RuntimeError(
                    "Existing calendar_events table has an unexpected schema."
                )
            return
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
    )


def downgrade():
    op.drop_table("calendar_events")
