"""Add optional colors to finance categories."""

import sqlalchemy as sa
from alembic import op

revision = "be49c337f201"
down_revision = "af17de081539"
branch_labels = None
depends_on = None


def upgrade():
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("finance_categories")
    }
    if "color" not in columns:
        op.add_column(
            "finance_categories", sa.Column("color", sa.String(7), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("finance_categories") as batch:
        batch.drop_column("color")
