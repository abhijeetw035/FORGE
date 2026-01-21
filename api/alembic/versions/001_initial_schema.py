"""Initial schema with repositories, commits, and functions"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner', sa.String(), nullable=False),
        sa.Column('clone_path', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repositories_id'), 'repositories', ['id'], unique=False)
    op.create_index(op.f('ix_repositories_url'), 'repositories', ['url'], unique=True)

    op.create_table('commits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('sha', sa.String(), nullable=False),
        sa.Column('author', sa.String(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commits_id'), 'commits', ['id'], unique=False)
    op.create_index(op.f('ix_commits_sha'), 'commits', ['sha'], unique=False)

    op.create_table('functions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('commit_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=True),
        sa.Column('end_line', sa.Integer(), nullable=True),
        sa.Column('complexity', sa.Integer(), nullable=True),
        sa.Column('lines_of_code', sa.Integer(), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('return_type', sa.String(), nullable=True),
        sa.Column('ast_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['commit_id'], ['commits.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_functions_id'), 'functions', ['id'], unique=False)
    op.create_index(op.f('ix_functions_name'), 'functions', ['name'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_functions_name'), table_name='functions')
    op.drop_index(op.f('ix_functions_id'), table_name='functions')
    op.drop_table('functions')
    
    op.drop_index(op.f('ix_commits_sha'), table_name='commits')
    op.drop_index(op.f('ix_commits_id'), table_name='commits')
    op.drop_table('commits')
    
    op.drop_index(op.f('ix_repositories_url'), table_name='repositories')
    op.drop_index(op.f('ix_repositories_id'), table_name='repositories')
    op.drop_table('repositories')
