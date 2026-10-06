"""Private current feedback; no historical assessment mutation or backfill."""
from alembic import op
import sqlalchemy as sa

revision='0009_answer_feedback'
down_revision='0008_saved_answers'
branch_labels=depends_on=None

def upgrade():
    op.create_table('answer_feedback',
        sa.Column('user_id',sa.Uuid(),primary_key=True),sa.Column('run_id',sa.Uuid(),primary_key=True),
        sa.Column('vote',sa.String(12),nullable=False),sa.Column('reason',sa.String(24)),sa.Column('comment',sa.String(500)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('now()')),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id','run_id'],['answer_runs.user_id','answer_runs.id'],ondelete='CASCADE'),
        sa.CheckConstraint("vote IN ('helpful','not_helpful')",name='ck_feedback_vote'),
        sa.CheckConstraint("reason IS NULL OR reason IN ('unclear_wording','incomplete_answer','citation_issue','language_issue','suspected_factual_error')",name='ck_feedback_reason'))

def downgrade():
    op.drop_table('answer_feedback')
