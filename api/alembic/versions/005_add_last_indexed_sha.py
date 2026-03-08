"""Add last_indexed_sha to repositories table

Revision ID: 005
Revises: 004
Create Date: 2026-03-08

Stores the HEAD SHA of the most recently fully-indexed commit so that
re-analysis of the same repository only needs to process the delta
(git log <last_indexed_sha>..HEAD) instead of the entire history.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_cols = [c['name'] for c in inspector.get_columns('repositories')]

    if 'last_indexed_sha' not in existing_cols:
        op.add_column(
            'repositories',
            sa.Column('last_indexed_sha', sa.String(), nullable=True)
        )


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_cols = [c['name'] for c in inspector.get_columns('repositories')]

    if 'last_indexed_sha' in existing_cols:
        op.drop_column('repositories', 'last_indexed_sha')
