"""Track transactions imported from Plaid."""

import sqlalchemy as sa
from alembic import op

revision = "af17de081539"
down_revision = "c49f3bd4580e"
branch_labels = None
depends_on = None


def upgrade():
    if "plaid_imported_transactions" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "plaid_imported_transactions",
            sa.Column("source_id", sa.String(256), primary_key=True),
            sa.Column("transaction_id", sa.String(36), nullable=False),
        )


def downgrade():
    op.drop_table("plaid_imported_transactions")
