"""Isolated mapping laboratories leave application metadata/migrations unchanged."""
from contextlib import contextmanager

@contextmanager
def extra_tables(lab,metadata):
    with lab.engine.begin() as connection:metadata.create_all(connection)
    try:yield
    finally:
        with lab.engine.begin() as connection:metadata.drop_all(connection)
