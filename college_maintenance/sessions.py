"""Shared Session configuration; create one short-lived Session per operation."""

from sqlalchemy.orm import sessionmaker

from college_maintenance.database import engine

SessionFactory = sessionmaker(bind=engine)
