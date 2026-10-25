"""Separate ticket-photo and work-order-proof metadata."""
from alembic import op
import sqlalchemy as sa
revision='0008_attachments'
down_revision='0007_audit_context'
branch_labels=depends_on=None

def upgrade():
    for table, owner, parent in [('ticket_attachments','ticket_id','maintenance_tickets'),('work_order_attachments','work_order_id','work_orders')]:
        op.create_table(table,
            sa.Column('id',sa.Uuid(),server_default=sa.text('gen_random_uuid()'),nullable=False),
            sa.Column(owner,sa.Uuid(),nullable=False),
            sa.Column('uploaded_by_id',sa.Uuid(),nullable=False),
            sa.Column('storage_key',sa.String(32),nullable=False),
            sa.Column('filename',sa.String(200),nullable=False),
            sa.Column('content_type',sa.String(100),nullable=False),
            sa.Column('size',sa.Integer(),nullable=False),
            sa.Column('sha256',sa.String(64),nullable=False),
            sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('CURRENT_TIMESTAMP'),nullable=False),
            sa.PrimaryKeyConstraint('id',name='pk_'+table),
            sa.UniqueConstraint('storage_key',name='uq_'+table+'_storage_key'),
            sa.CheckConstraint('size > 0 AND size <= 1048576',name='ck_'+table+'_size'),
            sa.ForeignKeyConstraint([owner],[parent+'.id'],name=f'fk_{table}_{owner}_{parent}',ondelete='RESTRICT',onupdate='RESTRICT'),
            sa.ForeignKeyConstraint(['uploaded_by_id'],['users.id'],name=f'fk_{table}_uploaded_by_id_users',ondelete='RESTRICT',onupdate='RESTRICT'))
        for column in (owner,'uploaded_by_id'): op.create_index(f'ix_{table}_{column}',table,[column])

def downgrade():
    op.drop_table('work_order_attachments'); op.drop_table('ticket_attachments')
