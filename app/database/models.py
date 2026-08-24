from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    message_thread_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    dashboard_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    members: Mapped[list["BudgetMember"]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
    )

    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="budget",
    )

    archives: Mapped[list["ArchiveMonth"]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
    )


class BudgetMember(Base):
    __tablename__ = "budget_members"

    __table_args__ = (
        UniqueConstraint(
            "budget_id",
            "telegram_user_id",
            name="uq_budget_member",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    budget_id: Mapped[int] = mapped_column(
        ForeignKey(
            "budgets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    budget: Mapped["Budget"] = relationship(
        back_populates="members",
    )


class ArchiveMonth(Base):
    __tablename__ = "archive_months"

    __table_args__ = (
        UniqueConstraint(
            "budget_id",
            "year",
            "month",
            name="uq_archive_month",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    budget_id: Mapped[int] = mapped_column(
        ForeignKey(
            "budgets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    year: Mapped[int] = mapped_column(
        nullable=False,
    )

    month: Mapped[int] = mapped_column(
        nullable=False,
    )

    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    budget: Mapped["Budget"] = relationship(
        back_populates="archives",
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    message_thread_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
    )

    budget_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "budgets.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    expense_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    budget: Mapped["Budget | None"] = relationship(
        back_populates="expenses",
    )
