
"""Add family budget incomes.

Revision ID: e14000000001
Revises: 20194f42fa83
"""

from alembic import op
import sqlalchemy as sa

revision = "e14000000001"
down_revision = "20194f42fa83"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "budget_id", sa.Integer(),
            sa.ForeignKey("budgets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "telegram_user_id", sa.BigInteger(), nullable=False,
        ),
        sa.Column(
            "telegram_chat_id", sa.BigInteger(), nullable=False,
        ),
        sa.Column("message_thread_id", sa.BigInteger()),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("income_date", sa.Date(), nullable=False),
        sa.Column("comment", sa.String(500)),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
    )

    for column in (
        "budget_id",
        "telegram_user_id",
        "income_date",
    ):
        op.create_index(
            f"ix_incomes_{column}", "incomes", [column],
        )


def downgrade():
    op.drop_table("incomes")
