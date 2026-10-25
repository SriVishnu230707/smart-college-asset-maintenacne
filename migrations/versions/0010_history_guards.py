"""Immutable completed repair facts and append-only business history."""
import re
from alembic import op
from sqlalchemy import text
revision='0010_history'
down_revision='0009_inventory'
branch_labels=depends_on=None

def install(connection, schema='public'):
    if not re.fullmatch(r'public|college_step(2[1-9]|[34][0-9]|50)',schema):raise ValueError('Unexpected history schema')
    connection.execute(text(f'''CREATE FUNCTION {schema}.protect_history() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent_id uuid; parents uuid[]; state text;
    BEGIN
      IF TG_TABLE_NAME IN ('audit_events','inventory_movements','ticket_comments') THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='Business history is append-only';
      ELSIF TG_TABLE_NAME='work_orders' THEN
        IF OLD.status='completed' THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='Completed work is immutable'; END IF;
      ELSE
        IF TG_OP='INSERT' THEN parents=ARRAY[NEW.work_order_id];
        ELSIF TG_OP='DELETE' THEN parents=ARRAY[OLD.work_order_id];
        ELSE parents=ARRAY[OLD.work_order_id,NEW.work_order_id]; END IF;
        FOR parent_id IN SELECT DISTINCT value FROM unnest(parents) value ORDER BY value LOOP
          EXECUTE format('SELECT status FROM %I.work_orders WHERE id=$1 FOR UPDATE',TG_TABLE_SCHEMA) INTO state USING parent_id;
          IF state='completed' THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='Completed child facts are immutable'; END IF;
        END LOOP;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$'''))
    for table in ('audit_events','inventory_movements','ticket_comments','work_orders','work_order_parts','work_order_attachments'):
        events='UPDATE OR DELETE' if table in ('audit_events','inventory_movements','ticket_comments','work_orders') else 'INSERT OR UPDATE OR DELETE'
        connection.exec_driver_sql(f'CREATE TRIGGER protect_history BEFORE {events} ON {schema}.{table} FOR EACH ROW EXECUTE FUNCTION {schema}.protect_history()')

def upgrade():install(op.get_bind())

def downgrade():
    for table in ('audit_events','inventory_movements','ticket_comments','work_orders','work_order_parts','work_order_attachments'):
        op.execute(f'DROP TRIGGER protect_history ON {table}')
    op.execute('DROP FUNCTION protect_history()')
