"""Create initial data map tables.

Revision ID: 8715065c7435
Revises:
Create Date: 2026-10-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision: str = "8715065c7435"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the initial Privora database tables."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", name="uq_services_name"),
    )
    op.create_index("ix_services_id", "services", ["id"], unique=False)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="UNKNOWN",
            nullable=False,
        ),
        sa.Column("retention_info", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
    )
    op.create_index("ix_accounts_id", "accounts", ["id"], unique=False)

    op.create_table(
        "data_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
    )
    op.create_index(
        "ix_data_records_id", "data_records", ["id"], unique=False
    )

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("policy_type", sa.String(length=50), nullable=False),
        sa.Column("policy_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_policies_id", "policies", ["id"], unique=False)


def downgrade() -> None:
    """Remove the initial Privora database tables."""

    op.drop_index("ix_policies_id", table_name="policies")
    op.drop_table("policies")

    op.drop_index("ix_data_records_id", table_name="data_records")
    op.drop_table("data_records")

    op.drop_index("ix_accounts_id", table_name="accounts")
    op.drop_table("accounts")

    op.drop_index("ix_services_id", table_name="services")
    op.drop_table("services")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")