"""Add request/entity/department context to successful business history."""
from alembic import op
import sqlalchemy as sa
revision = '0007_audit_context'
down_revision = '0006_resolution'
branch_labels = depends_on = None

def upgrade():
    op.add_column('audit_events', sa.Column('department_id', sa.Uuid(), nullable=True))
    op.add_column('audit_events', sa.Column('request_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.add_column('audit_events', sa.Column('target_type', sa.Text(), server_default=sa.text("'legacy'"), nullable=False))
    op.add_column('audit_events', sa.Column('target_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_audit_events_department_id_departments','audit_events','departments',['department_id'],['id'],ondelete='RESTRICT',onupdate='RESTRICT')
    op.create_index('ix_audit_events_department_id','audit_events',['department_id'])
    op.execute('UPDATE audit_events a SET department_id=t.department_id, target_id=t.id, target_type=\'ticket\' FROM maintenance_tickets t WHERE a.ticket_id=t.id')

def downgrade():
    op.drop_index('ix_audit_events_department_id', table_name='audit_events')
    op.drop_constraint('fk_audit_events_department_id_departments','audit_events',type_='foreignkey')
    for name in ('target_id','target_type','request_id','department_id'): op.drop_column('audit_events',name)
