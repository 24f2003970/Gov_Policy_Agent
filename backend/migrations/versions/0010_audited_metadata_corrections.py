"""Append-only evidence-backed corrections for document dates."""
from alembic import op
import sqlalchemy as sa

revision = "0010_metadata_corrections"
down_revision = "0009_answer_feedback"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "document_metadata_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_url", sa.String(length=1500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_document_metadata_corrections_version_id", "document_metadata_corrections", ["version_id"])
    op.execute("""CREATE FUNCTION protect_metadata_correction() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'document metadata corrections are append-only'; END; $$""")
    op.execute("CREATE TRIGGER document_metadata_correction_immutable BEFORE UPDATE OR DELETE ON document_metadata_corrections FOR EACH ROW EXECUTE FUNCTION protect_metadata_correction()")


def downgrade():
    op.execute("DROP TRIGGER document_metadata_correction_immutable ON document_metadata_corrections")
    op.drop_table("document_metadata_corrections")
    op.execute("DROP FUNCTION protect_metadata_correction()")
