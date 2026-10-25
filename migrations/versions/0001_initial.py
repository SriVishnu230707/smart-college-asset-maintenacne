"""Initial reviewed application schema: explicit, frozen DDL operations."""
from alembic import op
import sqlalchemy as sa

revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('asset_categories',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('is_archived', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'", name=op.f('ck_asset_categories_code')),
    sa.CheckConstraint("name !~ '^[[:space:]]*$'", name=op.f('ck_asset_categories_name')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_asset_categories')),
    sa.UniqueConstraint('code', name=op.f('uq_asset_categories_code'))
    )
    op.create_table('departments',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('is_archived', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'", name=op.f('ck_departments_code')),
    sa.CheckConstraint("name !~ '^[[:space:]]*$'", name=op.f('ck_departments_name')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
    sa.UniqueConstraint('code', name=op.f('uq_departments_code'))
    )
    op.create_table('spare_parts',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('sku', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('stock_quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('reorder_level', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('current_unit_cost', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('is_archived', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("name !~ '^[[:space:]]*$'", name=op.f('ck_spare_parts_name')),
    sa.CheckConstraint("sku = upper(btrim(sku)) AND sku <> ''", name=op.f('ck_spare_parts_sku')),
    sa.CheckConstraint('current_unit_cost >= 0', name=op.f('ck_spare_parts_cost')),
    sa.CheckConstraint('stock_quantity >= 0 AND reorder_level >= 0', name=op.f('ck_spare_parts_stock')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_spare_parts')),
    sa.UniqueConstraint('sku', name=op.f('uq_spare_parts_sku'))
    )
    op.create_table('assets',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('asset_code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('department_id', sa.Uuid(), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=True),
    sa.CheckConstraint("asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'", name=op.f('ck_assets_asset_code')),
    sa.CheckConstraint("name !~ '^[[:space:]]*$'", name=op.f('ck_assets_name')),
    sa.CheckConstraint("status IN ('active', 'under_maintenance', 'retired')", name=op.f('ck_assets_status')),
    sa.ForeignKeyConstraint(['category_id'], ['asset_categories.id'], name='fk_assets_category', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name='fk_assets_department', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assets')),
    sa.UniqueConstraint('asset_code', name=op.f('uq_assets_asset_code'))
    )
    op.create_index(op.f('ix_assets_category_id'), 'assets', ['category_id'], unique=False)
    op.create_index(op.f('ix_assets_department_id'), 'assets', ['department_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('display_name', sa.String(length=150), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('department_id', sa.Uuid(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.CheckConstraint("display_name !~ '^[[:space:]]*$'", name=op.f('ck_users_display_name')),
    sa.CheckConstraint("email = lower(btrim(email)) AND email <> '' AND email !~ '[[:space:]]'", name=op.f('ck_users_email')),
    sa.CheckConstraint("password_hash !~ '^[[:space:]]*$'", name=op.f('ck_users_password_hash')),
    sa.CheckConstraint("role = 'super_admin' OR department_id IS NOT NULL", name=op.f('ck_users_department')),
    sa.CheckConstraint("role IN ('student', 'technician', 'department_admin', 'super_admin')", name=op.f('ck_users_role')),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name='fk_users_department', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_index(op.f('ix_users_department_id'), 'users', ['department_id'], unique=False)
    op.create_table('maintenance_tickets',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('asset_id', sa.Uuid(), nullable=False),
    sa.Column('reported_by_id', sa.Uuid(), nullable=False),
    sa.Column('assigned_to_id', sa.Uuid(), nullable=True),
    sa.Column('department_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('priority', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'open'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("description !~ '^[[:space:]]*$'", name=op.f('ck_maintenance_tickets_description')),
    sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name=op.f('ck_maintenance_tickets_priority')),
    sa.CheckConstraint("status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected')", name=op.f('ck_maintenance_tickets_status')),
    sa.CheckConstraint("title !~ '^[[:space:]]*$'", name=op.f('ck_maintenance_tickets_title')),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name='fk_tickets_asset', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], name='fk_tickets_assignee', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name='fk_tickets_department', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], name='fk_tickets_reporter', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_maintenance_tickets'))
    )
    op.create_index(op.f('ix_maintenance_tickets_asset_id'), 'maintenance_tickets', ['asset_id'], unique=False)
    op.create_index(op.f('ix_maintenance_tickets_assigned_to_id'), 'maintenance_tickets', ['assigned_to_id'], unique=False)
    op.create_index(op.f('ix_maintenance_tickets_department_id'), 'maintenance_tickets', ['department_id'], unique=False)
    op.create_index(op.f('ix_maintenance_tickets_reported_by_id'), 'maintenance_tickets', ['reported_by_id'], unique=False)
    op.create_table('work_orders',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('ticket_id', sa.Uuid(), nullable=False),
    sa.Column('technician_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('labor_cost', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('completion_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('draft','in_progress','completed')", name=op.f('ck_work_orders_status')),
    sa.CheckConstraint('labor_cost >= 0', name=op.f('ck_work_orders_labor_cost')),
    sa.ForeignKeyConstraint(['technician_id'], ['users.id'], name=op.f('fk_work_orders_technician_id_users'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['ticket_id'], ['maintenance_tickets.id'], name=op.f('fk_work_orders_ticket_id_maintenance_tickets'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_work_orders'))
    )
    op.create_index(op.f('ix_work_orders_technician_id'), 'work_orders', ['technician_id'], unique=False)
    op.create_index(op.f('ix_work_orders_ticket_id'), 'work_orders', ['ticket_id'], unique=False)
    op.create_index('uq_work_orders_active_ticket', 'work_orders', ['ticket_id'], unique=True, postgresql_where=sa.text("status IN ('draft','in_progress')"))
    op.create_table('work_order_parts',
    sa.Column('work_order_id', sa.Uuid(), nullable=False),
    sa.Column('spare_part_id', sa.Uuid(), nullable=False),
    sa.Column('quantity_used', sa.Integer(), nullable=False),
    sa.Column('unit_cost_at_use', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.CheckConstraint('quantity_used > 0', name=op.f('ck_work_order_parts_quantity')),
    sa.CheckConstraint('unit_cost_at_use >= 0', name=op.f('ck_work_order_parts_unit_cost')),
    sa.ForeignKeyConstraint(['spare_part_id'], ['spare_parts.id'], name=op.f('fk_work_order_parts_spare_part_id_spare_parts'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], name=op.f('fk_work_order_parts_work_order_id_work_orders'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('work_order_id', 'spare_part_id', name=op.f('pk_work_order_parts'))
    )
    op.create_index(op.f('ix_work_order_parts_spare_part_id'), 'work_order_parts', ['spare_part_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_work_order_parts_spare_part_id'), table_name='work_order_parts')
    op.drop_table('work_order_parts')
    op.drop_index('uq_work_orders_active_ticket', table_name='work_orders', postgresql_where=sa.text("status IN ('draft','in_progress')"))
    op.drop_index(op.f('ix_work_orders_ticket_id'), table_name='work_orders')
    op.drop_index(op.f('ix_work_orders_technician_id'), table_name='work_orders')
    op.drop_table('work_orders')
    op.drop_index(op.f('ix_maintenance_tickets_reported_by_id'), table_name='maintenance_tickets')
    op.drop_index(op.f('ix_maintenance_tickets_department_id'), table_name='maintenance_tickets')
    op.drop_index(op.f('ix_maintenance_tickets_assigned_to_id'), table_name='maintenance_tickets')
    op.drop_index(op.f('ix_maintenance_tickets_asset_id'), table_name='maintenance_tickets')
    op.drop_table('maintenance_tickets')
    op.drop_index(op.f('ix_users_department_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_assets_department_id'), table_name='assets')
    op.drop_index(op.f('ix_assets_category_id'), table_name='assets')
    op.drop_table('assets')
    op.drop_table('spare_parts')
    op.drop_table('departments')
    op.drop_table('asset_categories')
