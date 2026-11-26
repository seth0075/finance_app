"""Persist calendar visibility preferences."""

import sqlalchemy as sa
from alembic import op

revision = "f17a0cd82a50"
down_revision = "d8a4c0719c5e"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("hidden_calendars"):
        op.create_table(
            "hidden_calendars",
            sa.Column("calendar_id", sa.Text(), primary_key=True),
        )


def downgrade():
    op.drop_table("hidden_calendars")
