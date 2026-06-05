"""Initial schema with all tables

Revision ID: 0a45e4524ff5
Revises: 
Create Date: 2026-06-05 23:14:39.373674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a45e4524ff5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all tables."""
    # Tickets table
    op.create_table(
        'tickets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('assignee_team', sa.String(), nullable=False),
        sa.Column('priority', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tickets_team', 'tickets', ['assignee_team'])
    op.create_index('idx_tickets_status', 'tickets', ['status'])
    op.create_index('idx_tickets_created_at', 'tickets', ['created_at'], mysql_length={'created_at': None})

    # Reminders table
    op.create_table(
        'reminders',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('due_in_hours', sa.Integer(), nullable=False),
        sa.Column('scheduled_for', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reminders_recipient', 'reminders', ['recipient'])
    op.create_index('idx_reminders_status', 'reminders', ['status'])
    op.create_index('idx_reminders_created_at', 'reminders', ['created_at'], mysql_length={'created_at': None})

    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_name', sa.String()),
        sa.Column('team_name', sa.String()),
        sa.Column('role_title', sa.String()),
        sa.Column('employment_type', sa.String()),
        sa.Column('auth_subject', sa.String()),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('last_seen_at', sa.String(), nullable=False),
        sa.Column('metadata_json', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sessions_team_name', 'sessions', ['team_name'])
    op.create_index('idx_sessions_created_at', 'sessions', ['created_at'], mysql_length={'created_at': None})
    op.create_index('idx_sessions_employment_type', 'sessions', ['employment_type'])

    # Audit events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('actor', sa.String()),
        sa.Column('session_id', sa.String()),
        sa.Column('request_id', sa.String()),
        sa.Column('payload_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_event_type', 'audit_events', ['event_type'])
    op.create_index('idx_audit_session_id', 'audit_events', ['session_id'])
    op.create_index('idx_audit_created_at', 'audit_events', ['created_at'], mysql_length={'created_at': None})

    # Memory metadata table
    op.create_table(
        'memory_metadata',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('namespace', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('level', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('tags_json', sa.String(), nullable=False),
        sa.Column('metadata_json', sa.String(), nullable=False),
        sa.Column('backend_kind', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_hash', 'namespace')
    )
    op.create_index('idx_memory_namespace', 'memory_metadata', ['namespace'])
    op.create_index('idx_memory_level', 'memory_metadata', ['level'])
    op.create_index('idx_memory_source', 'memory_metadata', ['source'])
    op.create_index('idx_memory_created_at', 'memory_metadata', ['created_at'], mysql_length={'created_at': None})


def downgrade() -> None:
    """Downgrade schema - drop all tables."""
    op.drop_table('memory_metadata')
    op.drop_table('audit_events')
    op.drop_table('sessions')
    op.drop_table('reminders')
    op.drop_table('tickets')
