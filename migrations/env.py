"""Reviewed revisions own the application schema; credentials stay outside Git."""
from alembic import context
from college_maintenance.database import engine
from college_maintenance.models import Base

def online(connection):
    context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True,compare_server_default=True)
    with context.begin_transaction():context.run_migrations()

supplied=context.config.attributes.get('connection')
if supplied is not None:
    online(supplied)
elif context.is_offline_mode():
    context.configure(url=engine.url,target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
else:
    with engine.connect() as connection:online(connection)
