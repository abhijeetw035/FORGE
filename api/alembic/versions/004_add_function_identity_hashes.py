"""Add body_hash, signature_hash, canonical_id to functions table

Revision ID: 004
Revises: 003
Create Date: 2026-03-08

Problem solved
--------------
The old approach tracked functions by line-number ranges.  This breaks
silently on:
  - function moved to a different line or file
  - code reformatted / indentation changed
  - large refactor that shifts all line numbers

New approach
------------
Three 16-char hex fingerprints are stored per Function row:

  body_hash      SHA-256[:16] of the normalised function body.
                 "Normalised" means: comments stripped, whitespace
                 collapsed.  A pure move or reformat produces the
                 SAME hash.

  signature_hash SHA-256[:16] of "<lang>:<name>(<param1>,<param2>,…)".
                 Stable across body changes; changes on rename or
                 parameter edits.

  canonical_id   SHA-256[:16] of (signature_hash + ":" + body_hash).
                 The primary cross-commit identity key.  Two Function
                 rows in different commits share a canonical_id when
                 they represent the same logical function regardless of
                 where it lives in the file.

All three are indexed so the API can do O(log n) lookups when building
function-evolution timelines.
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {c['name'] for c in inspector.get_columns('functions')}

    if 'body_hash' not in existing_cols:
        op.add_column('functions', sa.Column('body_hash', sa.String(16), nullable=True))
        op.create_index('ix_functions_body_hash', 'functions', ['body_hash'])

    if 'signature_hash' not in existing_cols:
        op.add_column('functions', sa.Column('signature_hash', sa.String(16), nullable=True))
        op.create_index('ix_functions_signature_hash', 'functions', ['signature_hash'])

    if 'canonical_id' not in existing_cols:
        op.add_column('functions', sa.Column('canonical_id', sa.String(16), nullable=True))
        op.create_index('ix_functions_canonical_id', 'functions', ['canonical_id'])


def downgrade() -> None:
    op.drop_index('ix_functions_canonical_id',   table_name='functions')
    op.drop_index('ix_functions_signature_hash', table_name='functions')
    op.drop_index('ix_functions_body_hash',      table_name='functions')
    op.drop_column('functions', 'canonical_id')
    op.drop_column('functions', 'signature_hash')
    op.drop_column('functions', 'body_hash')
