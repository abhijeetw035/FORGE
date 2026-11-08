"""Add qualified_name, change_type, similarity to functions table

Revision ID: 006
Revises: 005
Create Date: 2026-11-08

Adds stable function identity tracking support:
- qualified_name: includes enclosing class/receiver type
- change_type: one of 'new', 'unchanged', 'edit', 'move', 'rename', 'deleted'
- similarity: token similarity ratio when matched via difflib
- compound index on (file_path, qualified_name)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_cols = {c['name'] for c in inspector.get_columns('functions')}
    existing_indexes = {ix['name'] for ix in inspector.get_indexes('functions')}

    if 'qualified_name' not in existing_cols:
        op.add_column('functions', sa.Column('qualified_name', sa.String(), nullable=True))

    if 'change_type' not in existing_cols:
        op.add_column('functions', sa.Column('change_type', sa.String(16), nullable=True))

    if 'similarity' not in existing_cols:
        op.add_column('functions', sa.Column('similarity', sa.Float(), nullable=True))

    if 'ix_functions_file_path_qualified_name' not in existing_indexes:
        op.create_index(
            'ix_functions_file_path_qualified_name',
            'functions',
            ['file_path', 'qualified_name']
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_indexes = {ix['name'] for ix in inspector.get_indexes('functions')}
    existing_cols = {c['name'] for c in inspector.get_columns('functions')}

    if 'ix_functions_file_path_qualified_name' in existing_indexes:
        op.drop_index('ix_functions_file_path_qualified_name', table_name='functions')

    if 'similarity' in existing_cols:
        op.drop_column('functions', 'similarity')

    if 'change_type' in existing_cols:
        op.drop_column('functions', 'change_type')

    if 'qualified_name' in existing_cols:
        op.drop_column('functions', 'qualified_name')

