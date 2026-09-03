"""add customer access id

Revision ID: add_customer_access_id
Revises: c15b4f1a6064
Create Date: 2026-09-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_customer_access_id"
down_revision: Union[str, Sequence[str], None] = "c15b4f1a6064"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "customer_access_id",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_customers_customer_access_id",
        "customers",
        ["customer_access_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customers_customer_access_id",
        table_name="customers",
    )

    op.drop_column(
        "customers",
        "customer_access_id",
    )