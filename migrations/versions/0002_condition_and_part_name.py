"""Backfill a required condition note and preserve part names with a real rename."""
from alembic import op
import sqlalchemy as sa
revision='0002_condition'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column('assets',sa.Column('condition_note',sa.Text(),nullable=True))
    op.execute("UPDATE assets SET condition_note=CASE WHEN status='retired' THEN 'Retired inventory' ELSE 'Not assessed' END WHERE condition_note IS NULL")
    op.alter_column('assets','condition_note',nullable=False,server_default=sa.text("'Not assessed'"))
    op.create_check_constraint(op.f('ck_assets_condition_note'),'assets',"condition_note !~ '^[[:space:]]*$'")
    op.alter_column('spare_parts','name',new_column_name='display_name')

def downgrade():
    # Only an isolated rollback exercise should discard condition-note content.
    op.alter_column('spare_parts','display_name',new_column_name='name')
    op.drop_constraint(op.f('ck_assets_condition_note'),'assets',type_='check')
    op.drop_column('assets','condition_note')
