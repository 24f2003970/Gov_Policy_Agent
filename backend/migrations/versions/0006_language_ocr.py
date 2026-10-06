"""Append-only extraction pages/reviews; no digital text or answer backfill."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0006_language_ocr'
down_revision = '0005_citations'
branch_labels = depends_on = None


def upgrade():
    op.create_table('extraction_revisions',
        sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('version_id',sa.Uuid(),sa.ForeignKey('document_versions.id'),nullable=False),
        sa.Column('creator_id',sa.Uuid(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('state',sa.String(20),nullable=False),sa.Column('attempts',sa.Integer(),nullable=False),
        sa.Column('spec',JSONB(),nullable=False),sa.Column('processed',sa.Integer(),nullable=False),sa.Column('total',sa.Integer(),nullable=False),
        sa.Column('lease_owner',sa.Uuid()),sa.Column('lease_until',sa.DateTime(timezone=True)),sa.Column('error_code',sa.String(60)),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),
        sa.CheckConstraint("state IN ('queued','processing','pending_review','completed','partial','failed','cancelled') AND attempts BETWEEN 0 AND 3 AND processed >= 0 AND total > 0",name='ck_ocr_job'))
    op.create_index('ix_extraction_revisions_version_id','extraction_revisions',['version_id'])
    op.create_index('ix_ocr_pending_version','extraction_revisions',['version_id'],unique=True,postgresql_where=sa.text("state IN ('queued','processing','pending_review')"))
    op.create_table('extraction_pages',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('revision_id',sa.Uuid(),sa.ForeignKey('extraction_revisions.id'),nullable=False),
        sa.Column('page_id',sa.Uuid(),sa.ForeignKey('extracted_pages.id'),nullable=False),sa.Column('attempt',sa.Integer(),nullable=False),
        sa.Column('text',sa.Text(),nullable=False),sa.Column('paragraphs',JSONB(),nullable=False),sa.Column('method',sa.String(20),nullable=False),
        sa.Column('quality_flags',JSONB(),nullable=False),sa.Column('signals',JSONB(),nullable=False),sa.Column('boxes',JSONB(),nullable=False),
        sa.UniqueConstraint('revision_id','page_id','attempt'),sa.CheckConstraint("method IN ('digital','ocr','failed') AND attempt BETWEEN 0 AND 3",name='ck_ocr_page'))
    op.create_index('ix_extraction_pages_revision_id','extraction_pages',['revision_id'])
    op.create_table('extraction_reviews',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('page_id',sa.Uuid(),sa.ForeignKey('extraction_pages.id'),nullable=False),
        sa.Column('reviewer_id',sa.Uuid(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('decision',sa.String(10),nullable=False),sa.Column('reason',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),
        sa.CheckConstraint("decision IN ('accepted','rejected')",name='ck_ocr_review'))
    op.create_index('ix_extraction_reviews_page_id','extraction_reviews',['page_id'])
    op.create_table('extraction_state',sa.Column('version_id',sa.Uuid(),sa.ForeignKey('document_versions.id'),primary_key=True),
        sa.Column('ready_id',sa.Uuid(),sa.ForeignKey('extraction_revisions.id'),nullable=False))
    op.add_column('index_passages',sa.Column('extraction_page_id',sa.Uuid(),sa.ForeignKey('extraction_pages.id'),nullable=True))
    op.add_column('answer_runs',sa.Column('retrieval_question',sa.Text(),nullable=True))
    op.add_column('answer_runs',sa.Column('query_normalization',JSONB(),server_default=sa.text("'{}'::jsonb"),nullable=False))
    op.execute("""CREATE FUNCTION protect_extraction_artifact() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Extraction text and reviews are append-only'; END $$""")
    for table in ('extraction_pages','extraction_reviews'):
        op.execute(f'CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_extraction_artifact()')


def downgrade():
    op.drop_column('answer_runs','query_normalization');op.drop_column('answer_runs','retrieval_question')
    op.drop_column('index_passages','extraction_page_id')
    for table in ('extraction_state','extraction_reviews','extraction_pages','extraction_revisions'):op.drop_table(table)
    op.execute('DROP FUNCTION protect_extraction_artifact()')
