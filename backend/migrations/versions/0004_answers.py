"""Owned answer jobs and worker availability; additive only."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0004_answers'
down_revision='0003_retrieval'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('answer_runs',
        sa.Column('id',sa.Uuid(),nullable=False),sa.Column('user_id',sa.Uuid(),nullable=False),
        sa.Column('question',sa.Text(),nullable=False),sa.Column('language',sa.String(2),nullable=False),
        sa.Column('filters',postgresql.JSONB(),nullable=False),sa.Column('state',sa.String(16),nullable=False),
        sa.Column('cancel_requested',sa.Boolean(),nullable=False),sa.Column('result',postgresql.JSONB(),nullable=True),
        sa.Column('sources',postgresql.JSONB(),nullable=False),sa.Column('model',postgresql.JSONB(),nullable=False),
        sa.Column('timings',postgresql.JSONB(),nullable=False),sa.Column('error_code',sa.String(60),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),
        sa.Column('finished_at',sa.DateTime(timezone=True),nullable=True),
        sa.ForeignKeyConstraint(['user_id'],['users.id']),sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("state IN ('queued','processing','done','error','cancelled') AND language IN ('en','hi')",name='ck_answer_state'))
    op.create_index('ix_answer_runs_user_id','answer_runs',['user_id'])
    op.create_index('ix_answer_runs_created_at','answer_runs',['created_at'])
    op.create_index('ix_single_pending_answer','answer_runs',[sa.text('(1)')],unique=True,postgresql_where=sa.text("state IN ('queued','processing')"))
    op.create_table('answer_worker',sa.Column('id',sa.Integer(),nullable=False),
        sa.Column('heartbeat',sa.DateTime(timezone=True),nullable=False),sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('id=1',name='ck_answer_worker_single'))

def downgrade():
    op.drop_table('answer_worker');op.drop_table('answer_runs')
