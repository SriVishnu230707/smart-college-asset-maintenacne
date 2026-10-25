"""Canonicalize CHECK names expanded twice by earlier operation conventions.

Existing revisions remain reproducible. This reviewed forward rename fixes the
installed catalog; ordinary autogenerate does not check these names.
"""
from alembic import op
revision='0012_names'
down_revision='0011_version'
branch_labels=depends_on=None

NAMES=[('ticket_comments','body'),('ticket_attachments','size'),('work_order_attachments','size'),
       ('suppliers','details'),('inventory_movements','context'),('inventory_movements','actor'),('maintenance_tickets','version')]

def upgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    for table,suffix in NAMES:
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT ck_{table}_ck_{table}_{suffix} TO ck_{table}_{suffix}')

def downgrade():
    op.execute("SET LOCAL lock_timeout='5s'")
    for table,suffix in reversed(NAMES):
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT ck_{table}_{suffix} TO ck_{table}_ck_{table}_{suffix}')
