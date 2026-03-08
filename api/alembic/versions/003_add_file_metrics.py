"""Add file_metrics table with rich per-file features

Revision ID: 003
Revises: 002
Create Date: 2026-03-07

New table: file_metrics
  Stores aggregated git-history and AST-derived features per (repository, file_path).
  Populated by the miner service; consumed by the API risk-prediction endpoint.

Features added vs the old 3-column approach:
  churn, lines_added, lines_deleted, file_age_days, commit_frequency,
  recent_churn, author_count, ownership_entropy, dependency_count, avg_complexity
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'file_metrics' not in inspector.get_table_names():
        op.create_table(
            'file_metrics',
            sa.Column('id',                sa.Integer(),  nullable=False),
            sa.Column('repository_id',     sa.Integer(),  nullable=False),
            sa.Column('file_path',         sa.String(),   nullable=False),

            # commit-history features
            sa.Column('churn',             sa.Integer(),  nullable=True, server_default='0'),
            sa.Column('lines_added',       sa.Integer(),  nullable=True, server_default='0'),
            sa.Column('lines_deleted',     sa.Integer(),  nullable=True, server_default='0'),
            sa.Column('file_age_days',     sa.Float(),    nullable=True, server_default='0'),
            sa.Column('commit_frequency',  sa.Float(),    nullable=True, server_default='0'),
            sa.Column('recent_churn',      sa.Integer(),  nullable=True, server_default='0'),
            sa.Column('author_count',      sa.Integer(),  nullable=True, server_default='1'),
            sa.Column('ownership_entropy', sa.Float(),    nullable=True, server_default='0'),
            sa.Column('dependency_count',  sa.Integer(),  nullable=True, server_default='0'),

            # AST-derived
            sa.Column('avg_complexity',    sa.Float(),    nullable=True, server_default='0'),

            sa.Column('updated_at',        sa.DateTime(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(
                ['repository_id'], ['repositories.id'],
                name='fk_file_metrics_repository_id',
                ondelete='CASCADE'
            ),
        )
        op.create_index(
            op.f('ix_file_metrics_id'),
            'file_metrics', ['id'], unique=False
        )
        op.create_index(
            op.f('ix_file_metrics_repository_id'),
            'file_metrics', ['repository_id'], unique=False
        )
        op.create_index(
            op.f('ix_file_metrics_file_path'),
            'file_metrics', ['file_path'], unique=False
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_file_metrics_file_path'),      table_name='file_metrics')
    op.drop_index(op.f('ix_file_metrics_repository_id'),  table_name='file_metrics')
    op.drop_index(op.f('ix_file_metrics_id'),             table_name='file_metrics')
    op.drop_table('file_metrics')
