"""Add claim/citation snapshots; intentionally no update/backfill of answer_runs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0005_citations'
down_revision='0004_answers'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('answer_claims',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('run_id',sa.Uuid(),sa.ForeignKey('answer_runs.id',ondelete='CASCADE'),nullable=False),
        sa.Column('position',sa.Integer(),nullable=False),sa.Column('text',sa.Text(),nullable=False),
        sa.Column('retained',sa.Boolean(),nullable=False),sa.Column('assessment',JSONB(),nullable=False),
        sa.Column('snapshot',JSONB(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),
        sa.UniqueConstraint('run_id','position'),sa.CheckConstraint('position >= 1',name='ck_claim_position'))
    op.create_index('ix_answer_claims_run_id','answer_claims',['run_id'])
    op.create_table('claim_citations',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('claim_id',sa.Uuid(),sa.ForeignKey('answer_claims.id',ondelete='CASCADE'),nullable=False),
        sa.Column('position',sa.Integer(),nullable=False),
        sa.Column('version_id',sa.Uuid(),sa.ForeignKey('document_versions.id'),nullable=False),
        sa.Column('passage_id',sa.Uuid(),sa.ForeignKey('index_passages.id'),nullable=False),
        sa.Column('page_id',sa.Uuid(),sa.ForeignKey('extracted_pages.id'),nullable=False),
        sa.Column('quote',sa.Text(),nullable=False),sa.Column('start_offset',sa.Integer(),nullable=False),sa.Column('end_offset',sa.Integer(),nullable=False),
        sa.Column('metadata_snapshot',JSONB(),nullable=False),sa.Column('provenance',JSONB(),nullable=False),
        sa.UniqueConstraint('claim_id','position'),sa.CheckConstraint('start_offset >= 0 AND end_offset > start_offset',name='ck_citation_span'))
    op.create_index('ix_claim_citations_claim_id','claim_citations',['claim_id'])


def downgrade():
    op.drop_table('claim_citations');op.drop_table('answer_claims')
