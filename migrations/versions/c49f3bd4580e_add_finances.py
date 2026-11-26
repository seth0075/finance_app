"""Add manually maintained finance accounts and transactions."""

import sqlalchemy as sa
from alembic import op

revision = "c49f3bd4580e"
down_revision = "f17a0cd82a50"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "finance_accounts" not in existing:
        op.create_table(
            "finance_accounts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("kind", sa.String(10), nullable=False),
            sa.Column("opened_on", sa.Date(), nullable=False),
            sa.Column("opening_cents", sa.BigInteger(), nullable=False),
            sa.Column("credit_limit_cents", sa.BigInteger()),
        )
    if "finance_categories" not in existing:
        op.create_table(
            "finance_categories",
            sa.Column("name", sa.String(100), primary_key=True),
        )
    if "finance_transactions" not in existing:
        op.create_table(
            "finance_transactions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("kind", sa.String(10), nullable=False),
            sa.Column("amount_cents", sa.BigInteger(), nullable=False),
            sa.Column(
                "account_id",
                sa.String(36),
                sa.ForeignKey("finance_accounts.id"),
                nullable=False,
            ),
            sa.Column(
                "destination_id", sa.String(36), sa.ForeignKey("finance_accounts.id")
            ),
            sa.Column(
                "category", sa.String(100), sa.ForeignKey("finance_categories.name")
            ),
            sa.Column("recurrence", sa.String(10), nullable=False),
            sa.Column("subscription_active", sa.Boolean(), nullable=False),
        )


def downgrade():
    op.drop_table("finance_transactions")
    op.drop_table("finance_categories")
    op.drop_table("finance_accounts")
