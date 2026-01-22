"""Add users table and repository owner_id

Revision ID: 002
Revises: 001
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if users table exists, create only if it doesn't
    # (it may have been auto-created by SQLAlchemy)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'users' not in inspector.get_table_names():
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('password_hash', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Add owner_id column to repositories table (this is always needed)
    op.add_column('repositories', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_repositories_owner_id', 'repositories', 'users', ['owner_id'], ['id'])

def downgrade() -> None:
    # Remove foreign key and column from repositories
    op.drop_constraint('fk_repositories_owner_id', 'repositories', type_='foreignkey')
    op.drop_column('repositories', 'owner_id')
    
    # Only drop users table if we want to completely rollback
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
