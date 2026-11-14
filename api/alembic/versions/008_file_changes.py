"""file_changes table + commits.changes_recorded

Revision ID: 008
Revises: 007
Create Date: 2026-11-15

file_changes stores raw per-commit, per-file facts (author email, timestamp,
lines added/deleted). file_metrics is recomputed from it with SQL on every
run, replacing the old "walk git, merge deltas" logic (which lost history on
crash/resume and merged entropy with max()).

commits.changes_recorded marks commits whose facts are stored; existing
commits default to false and are backfilled by the miner on the next run.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)

    cols = {c['name'] for c in insp.get_columns('commits')}
    if 'changes_recorded' not in cols:
        op.add_column('commits', sa.Column(
            'changes_recorded', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    if 'file_changes' not in insp.get_table_names():
        op.create_table(
            'file_changes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('repository_id', sa.Integer(),
                      sa.ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False),
            sa.Column('commit_id', sa.Integer(),
                      sa.ForeignKey('commits.id', ondelete='CASCADE'), nullable=False),
            sa.Column('file_path', sa.String(), nullable=False),
            sa.Column('author_email', sa.String(), nullable=False),
            sa.Column('committed_at', sa.DateTime(), nullable=False),
            sa.Column('lines_added', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('lines_deleted', sa.Integer(), nullable=False, server_default='0'),
            sa.UniqueConstraint('commit_id', 'file_path', name='uq_file_changes_commit_file'),
        )
        op.create_index('ix_file_changes_id', 'file_changes', ['id'])
        op.create_index('ix_file_changes_repo_file', 'file_changes', ['repository_id', 'file_path'])


def downgrade() -> None:
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    if 'file_changes' in insp.get_table_names():
        op.drop_table('file_changes')
    if 'changes_recorded' in {c['name'] for c in insp.get_columns('commits')}:
        op.drop_column('commits', 'changes_recorded')
