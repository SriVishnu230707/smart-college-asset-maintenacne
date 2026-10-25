"""Programmatic migration entry point with an explicit caller-owned connection."""
from pathlib import Path
from alembic import command
from alembic.config import Config

def migration_config(connection=None):
    root=Path(__file__).resolve().parents[1]
    config=Config(str(root/'alembic.ini'))
    config.set_main_option('script_location',str(root/'migrations'))
    if connection is not None:config.attributes['connection']=connection
    return config

def upgrade(connection, revision='head'):
    command.upgrade(migration_config(connection),revision)
