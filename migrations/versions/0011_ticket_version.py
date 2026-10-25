"""Backfill a required optimistic version counter for existing tickets."""
from alembic import op
import sqlalchemy as sa
revision='0011_version'
down_revision='0010_history'
branch_labels=depends_on=None

def upgrade():
    op.add_column('maintenance_tickets',sa.Column('version',sa.Integer(),server_default=sa.text('1'),nullable=False))
    op.create_check_constraint('ck_maintenance_tickets_version','maintenance_tickets','version > 0')

def downgrade():
    op.drop_constraint('ck_maintenance_tickets_version','maintenance_tickets',type_='check')
    op.drop_column('maintenance_tickets','version')
