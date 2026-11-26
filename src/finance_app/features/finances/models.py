from datetime import date
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from finance_app.core.database import Base


def new_id():
    return str(uuid4())


class FinanceAccount(Base):
    __tablename__ = "finance_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    opened_on: Mapped[date] = mapped_column(Date, nullable=False)
    opening_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    credit_limit_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class FinanceCategory(Base):
    __tablename__ = "finance_categories"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("finance_accounts.id"), nullable=False
    )
    destination_id: Mapped[str | None] = mapped_column(
        ForeignKey("finance_accounts.id"), nullable=True
    )
    category: Mapped[str | None] = mapped_column(
        ForeignKey("finance_categories.name"), nullable=True
    )
    recurrence: Mapped[str] = mapped_column(String(10), nullable=False, default="none")
    subscription_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )


class PlaidImportedTransaction(Base):
    __tablename__ = "plaid_imported_transactions"

    source_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False)
