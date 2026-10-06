"""Owned bookmarks reference existing snapshots and cascade on retention deletion."""
from alembic import op
import sqlalchemy as sa

revision = '0008_saved_answers'
down_revision = '0007_evidence_quality'
branch_labels = depends_on = None


def upgrade():
    op.create_unique_constraint('uq_answer_owner_id','answer_runs',['user_id','id'])
    op.create_table('saved_answers',sa.Column('user_id',sa.Uuid(),primary_key=True),
        sa.Column('run_id',sa.Uuid(),primary_key=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id','run_id'],['answer_runs.user_id','answer_runs.id'],ondelete='CASCADE'))


def downgrade():
    op.drop_table('saved_answers')
    op.drop_constraint('uq_answer_owner_id','answer_runs',type_='unique')
