"""Nullable versioned evidence snapshot; no backfill, rejudgment or changed answers."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0007_evidence_quality'
down_revision = '0006_language_ocr'
branch_labels = depends_on = None


def upgrade():
    op.add_column('answer_runs', sa.Column('evidence_quality', JSONB(), nullable=True))


def downgrade():
    op.drop_column('answer_runs', 'evidence_quality')
