"""Reconcile opening stock and record every subsequent balance change."""
from alembic import op
import sqlalchemy as sa
revision='0009_inventory'
down_revision='0008_attachments'
branch_labels=depends_on=None

def upgrade():
    op.create_table('suppliers',sa.Column('id',sa.Uuid(),server_default=sa.text('gen_random_uuid()'),nullable=False),
        sa.Column('name',sa.String(150),nullable=False),sa.Column('contact',sa.Text(),nullable=False),
        sa.Column('is_archived',sa.Boolean(),server_default=sa.text('false'),nullable=False),
        sa.PrimaryKeyConstraint('id',name='pk_suppliers'),sa.CheckConstraint("name !~ '^[[:space:]]*$' AND contact !~ '^[[:space:]]*$'",name='ck_suppliers_details'))
    op.create_table('inventory_movements',
        sa.Column('id',sa.Uuid(),server_default=sa.text('gen_random_uuid()'),nullable=False),
        sa.Column('spare_part_id',sa.Uuid(),nullable=False),sa.Column('actor_id',sa.Uuid(),nullable=True),
        sa.Column('supplier_id',sa.Uuid(),nullable=True),sa.Column('work_order_id',sa.Uuid(),nullable=True),
        sa.Column('kind',sa.String(20),nullable=False),sa.Column('quantity_delta',sa.Integer(),nullable=False),sa.Column('reason',sa.Text(),nullable=True),
        sa.Column('is_legacy',sa.Boolean(),server_default=sa.text('false'),nullable=False),
        sa.Column('occurred_at',sa.DateTime(timezone=True),server_default=sa.text('CURRENT_TIMESTAMP'),nullable=False),
        sa.PrimaryKeyConstraint('id',name='pk_inventory_movements'),
        sa.CheckConstraint("(kind='opening' AND quantity_delta>0 AND supplier_id IS NULL AND work_order_id IS NULL) OR (kind='receipt' AND quantity_delta>0 AND supplier_id IS NOT NULL AND work_order_id IS NULL) OR (kind='consume' AND quantity_delta<0 AND work_order_id IS NOT NULL AND supplier_id IS NULL) OR (kind='adjustment' AND quantity_delta<>0 AND reason !~ '^[[:space:]]*$' AND reason IS NOT NULL AND supplier_id IS NULL AND work_order_id IS NULL)",name='ck_inventory_movements_context'),
        sa.CheckConstraint("actor_id IS NOT NULL OR (is_legacy AND kind='opening')",name='ck_inventory_movements_actor'),
        *[sa.ForeignKeyConstraint([column],[parent+'.id'],name=f'fk_inventory_movements_{column}_{parent}',ondelete='RESTRICT',onupdate='RESTRICT') for column,parent in [('spare_part_id','spare_parts'),('actor_id','users'),('supplier_id','suppliers'),('work_order_id','work_orders')]])
    for column in ('spare_part_id','actor_id','supplier_id','work_order_id'):op.create_index('ix_inventory_movements_'+column,'inventory_movements',[column])
    op.create_index('uq_inventory_movements_opening','inventory_movements',['spare_part_id'],unique=True,postgresql_where=sa.text("kind='opening'"))
    op.create_index('uq_inventory_movements_consume','inventory_movements',['work_order_id','spare_part_id'],unique=True,postgresql_where=sa.text("kind='consume'"))
    op.execute("INSERT INTO inventory_movements(spare_part_id,kind,quantity_delta,is_legacy,reason) SELECT id,'opening',stock_quantity,true,'Balance adopted by reviewed migration' FROM spare_parts WHERE stock_quantity>0")

def downgrade():
    op.drop_table('inventory_movements');op.drop_table('suppliers')
