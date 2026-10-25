"""Persist successful audit events in the same transaction as their changes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0003_audit'
down_revision='0002_condition'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('audit_events',
        sa.Column('id',sa.Uuid(),server_default=sa.text('gen_random_uuid()'),nullable=False),
        sa.Column('actor_id',sa.Uuid(),nullable=False),sa.Column('asset_id',sa.Uuid(),nullable=True),
        sa.Column('ticket_id',sa.Uuid(),nullable=True),sa.Column('action',sa.Text(),nullable=False),
        sa.Column('payload',postgresql.JSONB(),server_default=sa.text("'{}'::jsonb"),nullable=False),
        sa.Column('occurred_at',sa.DateTime(timezone=True),server_default=sa.text('CURRENT_TIMESTAMP'),nullable=False),
        sa.PrimaryKeyConstraint('id',name=op.f('pk_audit_events')),
        sa.CheckConstraint("action !~ '^[[:space:]]*$'",name=op.f('ck_audit_events_action')),
        sa.ForeignKeyConstraint(['actor_id'],['users.id'],name=op.f('fk_audit_events_actor_id_users'),ondelete='RESTRICT',onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['asset_id'],['assets.id'],name=op.f('fk_audit_events_asset_id_assets'),ondelete='RESTRICT',onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['ticket_id'],['maintenance_tickets.id'],name=op.f('fk_audit_events_ticket_id_maintenance_tickets'),ondelete='RESTRICT',onupdate='RESTRICT'))
    for name in ('actor_id','asset_id','ticket_id'):op.create_index(f'ix_audit_events_{name}','audit_events',[name])

def downgrade():
    op.drop_table('audit_events')
