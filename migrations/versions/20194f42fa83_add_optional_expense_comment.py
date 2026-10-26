"""add optional expense comment

Revision ID: 20194f42fa83
Revises: f907c88ef0b3
Create Date: 2026-10-26 19:30:26.206548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20194f42fa83'
down_revision: Union[str, Sequence[str], None] = 'f907c88ef0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    connection = op.get_bind()
    inspector = sa.inspect(connection)

    columns = {
        column["name"]
        for column in inspector.get_columns("expenses")
    }

    if "comment" not in columns:
        op.add_column(
            "expenses",
            sa.Column("comment", sa.String(500), nullable=True),
        )


def downgrade() -> None:
    from alembic import op

    op.drop_column("expenses", "comment")
