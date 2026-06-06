"""Add chat_messages and feedback tables

Revision ID: a1b2c3d4e5f6
Revises: 0a45e4524ff5
Create Date: 2026-06-06 05:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0a45e4524ff5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_session_id", "chat_messages", ["session_id"])
    op.create_index("idx_chat_created_at", "chat_messages", ["created_at"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String()),
        sa.Column("helpful", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String()),
        sa.Column("team_name", sa.String()),
        sa.Column("query_text", sa.String()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_feedback_session", "feedback", ["session_id"])


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("chat_messages")
