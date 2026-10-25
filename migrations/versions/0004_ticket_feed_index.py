"""Support compound created_at/id ticket ordering (backward scan for newest)."""
from alembic import op
revision='0004_feed'
down_revision='0003_audit'
branch_labels=None
depends_on=None
def upgrade():op.create_index('ix_maintenance_tickets_created_at_id','maintenance_tickets',['created_at','id'])
def downgrade():op.drop_index('ix_maintenance_tickets_created_at_id',table_name='maintenance_tickets')
