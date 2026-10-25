"""Retain verification and rework reasons."""
from alembic import op
import sqlalchemy as sa
revision = '0006_resolution'
down_revision = '0005_comments'
branch_labels = depends_on = None

def upgrade():
    for name in ('verification_note','rework_reason'):
        op.add_column('maintenance_tickets', sa.Column(name, sa.Text(), nullable=True))

def downgrade():
    for name in ('rework_reason','verification_note'):
        op.drop_column('maintenance_tickets', name)
