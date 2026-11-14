"""Idempotent writes + failed_reason

Revision ID: 007
Revises: 006
Create Date: 2026-11-15

- repositories.failed_reason: why a job ended as "failed" (shown in the UI)
- unique (repository_id, sha) on commits
- unique (commit_id, file_path, qualified_name, start_line, body_hash) on functions.
  NOTE: (commit_id, file_path, qualified_name) alone is NOT a safe key: real data
  has thousands of distinct functions sharing a qualified_name in one file
  (minified JS, parser-derived names), and it would delete ~9k legitimate rows.

If two workers ever process the same repo, INSERT .. ON CONFLICT DO NOTHING
turns the duplicate write into a no-op instead of duplicate rows.
Existing duplicates are collapsed first so the constraints can be created.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    cols = {c['name'] for c in inspector.get_columns('repositories')}
    if 'failed_reason' not in cols:
        op.add_column('repositories', sa.Column('failed_reason', sa.Text(), nullable=True))

    commit_ucs = {u['name'] for u in inspector.get_unique_constraints('commits')}
    func_ucs = {u['name'] for u in inspector.get_unique_constraints('functions')}

    if 'uq_commits_repository_sha' not in commit_ucs:
        # 1. Re-point functions of duplicate commits to the surviving (lowest id) commit
        op.execute("""
            UPDATE functions f
            SET commit_id = k.keep_id
            FROM (
                SELECT c.id AS dup_id, m.keep_id
                FROM commits c
                JOIN (SELECT repository_id, sha, MIN(id) AS keep_id
                      FROM commits GROUP BY repository_id, sha) m
                  ON m.repository_id = c.repository_id AND m.sha = c.sha
                WHERE c.id <> m.keep_id
            ) k
            WHERE f.commit_id = k.dup_id
        """)
        # 2. Delete the now-empty duplicate commits
        op.execute("""
            DELETE FROM commits c
            USING (SELECT repository_id, sha, MIN(id) AS keep_id
                   FROM commits GROUP BY repository_id, sha) m
            WHERE c.repository_id = m.repository_id AND c.sha = m.sha AND c.id <> m.keep_id
        """)
        op.create_unique_constraint(
            'uq_commits_repository_sha', 'commits', ['repository_id', 'sha'])

    if 'uq_functions_identity' not in func_ucs:
        # Collapse true duplicate rows (NULLs never conflict, so they are left alone)
        op.execute("""
            DELETE FROM functions
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY commit_id, file_path, qualified_name, start_line, body_hash ORDER BY id
                    ) AS rn
                    FROM functions
                    WHERE qualified_name IS NOT NULL
                ) t WHERE t.rn > 1
            )
        """)
        op.create_unique_constraint(
            'uq_functions_identity', 'functions',
            ['commit_id', 'file_path', 'qualified_name', 'start_line', 'body_hash'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    func_ucs = {u['name'] for u in inspector.get_unique_constraints('functions')}
    commit_ucs = {u['name'] for u in inspector.get_unique_constraints('commits')}
    if 'uq_functions_identity' in func_ucs:
        op.drop_constraint('uq_functions_identity', 'functions', type_='unique')
    if 'uq_commits_repository_sha' in commit_ucs:
        op.drop_constraint('uq_commits_repository_sha', 'commits', type_='unique')
    cols = {c['name'] for c in inspector.get_columns('repositories')}
    if 'failed_reason' in cols:
        op.drop_column('repositories', 'failed_reason')
