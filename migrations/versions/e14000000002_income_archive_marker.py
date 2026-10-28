"""Track successful income archiving.

Revision ID: e14000000002
Revises: e14000000001
"""

from alembic import op
import sqlalchemy as sa

revision = "e14000000002"
down_revision = "e14000000001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "archive_months",
        sa.Column(
            "incomes_archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("archive_months", "incomes_archived_at")
