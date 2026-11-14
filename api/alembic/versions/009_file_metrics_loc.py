"""Add loc to file_metrics

Revision ID: 009
Revises: 008
Create Date: 2026-11-15

loc = non-blank lines of the file at HEAD. The heatmap used to sum function
line spans across every commit and label that "LOC"; it now reads this.
Filled by the miner on the next (re-)analysis.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = Inspector.from_engine(op.get_bind())
    if 'loc' not in {c['name'] for c in insp.get_columns('file_metrics')}:
        op.add_column('file_metrics', sa.Column(
            'loc', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    insp = Inspector.from_engine(op.get_bind())
    if 'loc' in {c['name'] for c in insp.get_columns('file_metrics')}:
        op.drop_column('file_metrics', 'loc')
