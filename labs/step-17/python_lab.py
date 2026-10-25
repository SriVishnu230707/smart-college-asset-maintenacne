"""Separate Python annotations, ORM mapping, and installed database constraints."""

import re
import sys
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import get_args, get_origin, get_type_hints
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import CheckConstraint, UniqueConstraint, event, func, insert, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.schema import CreateSchema, CreateTable

from labs.shared.column_models import Asset, AssetCategory, Base, Department, MaintenanceTicket, User
from college_maintenance.database import engine

SCHEMA = "college_step17"
MODELS = (Department, AssetCategory, Asset, User, MaintenanceTicket)
EXPECTED_COLUMNS = {
    "departments": "id code name is_archived",
    "asset_categories": "id code name is_archived",
    "assets": "id asset_code name department_id category_id status location",
    "users": "id email display_name password_hash role department_id is_active",
    "maintenance_tickets": "id asset_id reported_by_id assigned_to_id department_id title description priority status created_at assigned_at rejected_at closed_at rejection_reason",
}
# Earlier reference-policy names and targets, independent of mapper inspection.
EXPECTED_LINKS = {
    "fk_users_department": ("users", "department_id", "departments"),
    "fk_assets_department": ("assets", "department_id", "departments"),
    "fk_assets_category": ("assets", "category_id", "asset_categories"),
    "fk_tickets_asset": ("maintenance_tickets", "asset_id", "assets"),
    "fk_tickets_reporter": ("maintenance_tickets", "reported_by_id", "users"),
    "fk_tickets_assignee": ("maintenance_tickets", "assigned_to_id", "users"),
    "fk_tickets_department": ("maintenance_tickets", "department_id", "departments"),
}


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def default_sql(value):
    return str(value).replace("::text", "").strip().lower() if value is not None else None


def type_sql(column_type):
    return str(column_type.compile(dialect=engine.dialect))


def reject_sql(connection, sql, parameters, state, table, message, constraint=None, column=None):
    # Savepoints isolate expected raw-SQL failures; Session persistence is Step 18.
    try:
        with connection.begin_nested():
            connection.execute(text(sql), parameters)
    except IntegrityError as exc:
        original = exc.orig
        check(original.sqlstate == state and original.diag.table_name == table
              and (constraint is None or original.diag.constraint_name == constraint)
              and (column is None or original.diag.column_name == column), message)
        print(f"Expected PostgreSQL rejection: SQLSTATE={state}; table={table}; diagnostic={constraint or column}")
    else:
        raise AssertionError(f"PostgreSQL accepted invalid raw SQL: {message}")


def main():
    print(f"SQLAlchemy {version('SQLAlchemy')}; psycopg {version('psycopg')}")
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "The typed-mapping lab reuses the pinned SQLAlchemy and psycopg versions.")
    Base.registry.configure()
    check(set(Base.metadata.tables) == set(EXPECTED_COLUMNS)
          and {mapper.class_ for mapper in Base.registry.mappers} == set(MODELS)
          and Base.metadata.schema is None,
          "One DeclarativeBase registers exactly the five agreed mapped classes and their unqualified tables.")
    for model in MODELS:
        mapper = inspect(model)
        table = model.__table__
        hints = get_type_hints(model)
        check(mapper.class_ is model and mapper.local_table is table and table.metadata is Base.metadata
              and list(table.c.keys()) == EXPECTED_COLUMNS[table.name].split()
              and set(mapper.column_attrs.keys()) == set(table.c.keys())
              and all(get_origin(hints[column.name]) is Mapped for column in table.c),
              f"{model.__name__}: Mapped annotations, mapper properties, and registered Table columns agree.")
    check(isinstance(Asset.asset_code, InstrumentedAttribute)
          and str(select(Asset).compile(dialect=engine.dialect)) == str(select(Asset.__table__).compile(dialect=engine.dialect)),
          "Instrumented class attributes and the mapped class expose the same underlying Core table for SQL compilation.")
    check(not Asset.__table__.c.department_id.nullable and Asset.__table__.c.location.nullable
          and User.__table__.c.department_id.nullable and MaintenanceTicket.__table__.c.assigned_to_id.nullable
          and get_args(get_type_hints(User)["department_id"])[0] == UUID | None,
          "Mapped optional annotations infer nullable membership, location, and assignee while required references stay NOT NULL.")
    check(all(MaintenanceTicket.__table__.c[name].type.timezone for name in ("created_at", "assigned_at", "rejected_at", "closed_at"))
          and not MaintenanceTicket.__table__.c.created_at.nullable
          and all(MaintenanceTicket.__table__.c[name].nullable for name in ("assigned_at", "rejected_at", "closed_at")),
          "Lifecycle instants use timezone-aware SQL types with required creation and optional later events.")
    check(all(not inspect(model).relationships for model in MODELS),
          "The initial mapping contains columns and foreign keys; ORM navigation remains for the relationship lessons.")

    class AnnotatedOnly:
        name: str

    plain = AnnotatedOnly()
    plain.name = None  # type: ignore[assignment] -- deliberate runtime counterexample
    check(plain.name is None and inspect(AnnotatedOnly, raiseerr=False) is None,
          "A plain Python annotation neither creates a mapper nor validates a runtime assignment.")
    invalid = Department(code=" cse ", name=None)
    check(invalid.code == " cse " and invalid.name is None and invalid.id is None and invalid.is_archived is None,
          "The mapped keyword constructor accepts invalid field values and does not evaluate server defaults.")
    try:
        Department(unmapped_field="unexpected")
    except TypeError:
        check(True, "The ORM constructor rejects an unknown attribute even though it does not validate field values.")
    else:
        raise AssertionError("The mapped constructor accepted an unknown attribute")
    print("Compiled mapped Asset DDL:", CreateTable(Asset.__table__).compile(dialect=engine.dialect))
    check(engine.pool.checkedin() == 0 and engine.pool.checkedout() == 0,
          "Mapping, object construction, inspection, and DDL compilation open no physical database connection.")

    statements = []

    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor)
    driver_connection = None
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                identity = connection.execute(text("""SELECT current_database(), current_user,
                    current_setting('server_version_num')::integer, pg_backend_pid(),
                    to_regnamespace('college_step17') IS NULL""")).one()
                check(identity[0] == "college_learning" and identity[1] == "college_learner"
                      and 180000 <= identity[2] < 190000 and identity[4],
                      "The PostgreSQL 18 learner connection has a free disposable Step 17 namespace.")
                print(f"engine_backend_pid={identity[3]}")
                driver_connection = connection.connection.driver_connection
                connection.execute(CreateSchema(SCHEMA))
                connection = connection.execution_options(schema_translate_map={None: SCHEMA})
                Base.metadata.create_all(connection)
                created = [re.search(r"CREATE TABLE\s+(\S+)", sql).group(1)
                           for sql in statements if re.search(r"CREATE TABLE\s+", sql)]
                check(len(created) == 5 and set(created) == {f"{SCHEMA}.{name}" for name in EXPECTED_COLUMNS}
                      and all(created.index(f"{SCHEMA}.{parent}") < created.index(f"{SCHEMA}.{child}")
                              for child, column, parent in EXPECTED_LINKS.values()),
                      "Schema translation creates only five lab-qualified tables, ordered after their referenced parents.")
                inspector = inspect(connection)
                for model in MODELS:
                    table = model.__table__
                    actual_columns = [(c["name"], type_sql(c["type"]), c["nullable"], default_sql(c["default"]))
                                      for c in inspector.get_columns(table.name, schema=SCHEMA)]
                    declared_columns = [(c.name, type_sql(c.type), c.nullable,
                                         default_sql(c.server_default.arg) if c.server_default is not None else None) for c in table.c]
                    print(f"Installed {table.name} columns:", actual_columns)
                    check(actual_columns == declared_columns,
                          f"{table.name}: PostgreSQL column order, SQL types, lengths, nullability, and server defaults match the mapped table.")
                    pk = inspector.get_pk_constraint(table.name, schema=SCHEMA)
                    uniques = {(c["name"], tuple(c["column_names"])) for c in inspector.get_unique_constraints(table.name, schema=SCHEMA)}
                    checks = {c["name"] for c in inspector.get_check_constraints(table.name, schema=SCHEMA)}
                    check(pk["name"] == f"pk_{table.name}" and pk["constrained_columns"] == ["id"]
                          and uniques == {(str(c.name), tuple(col.name for col in c.columns)) for c in table.constraints if isinstance(c, UniqueConstraint)}
                          and checks == {str(c.name) for c in table.constraints if isinstance(c, CheckConstraint)},
                          f"{table.name}: PostgreSQL installed the declared primary key, business uniqueness, and named checks.")
                actual_links = {}
                actual_indexes = set()
                for table in Base.metadata.sorted_tables:
                    for link in inspector.get_foreign_keys(table.name, schema=SCHEMA):
                        actual_links[link["name"]] = (table.name, tuple(link["constrained_columns"]), link["referred_schema"],
                                                       link["referred_table"], tuple(link["referred_columns"]),
                                                       link["options"].get("ondelete"), link["options"].get("onupdate"))
                    actual_indexes.update((table.name, tuple(index["column_names"]))
                                          for index in inspector.get_indexes(table.name, schema=SCHEMA) if not index.get("duplicates_constraint"))
                check(actual_links == {name: (child, (column,), SCHEMA, parent, ("id",), "RESTRICT", "RESTRICT")
                                       for name, (child, column, parent) in EXPECTED_LINKS.items()},
                      "All seven installed foreign keys preserve their target identities and RESTRICT update/delete policies.")
                check(actual_indexes == {(child, (column,)) for child, column, parent in EXPECTED_LINKS.values()},
                      "Every referencing column has its declared supporting index without duplicating unique backing indexes.")

                department = connection.execute(insert(Department.__table__).values(code="CSE", name="Computer Science")
                                                .returning(Department.id, Department.is_archived)).one()
                category = connection.execute(insert(AssetCategory.__table__).values(code="PROJECTOR", name="Projector")
                                              .returning(AssetCategory.id, AssetCategory.is_archived)).one()
                user_ids = {}
                for role in ("student", "technician", "super_admin"):
                    user = connection.execute(insert(User.__table__).values(
                        email=f"{role}@example.test", display_name=f"Lab {role}", password_hash="synthetic_mapping_lab_hash",
                        role=role, department_id=None if role == "super_admin" else department.id
                    ).returning(User.id, User.is_active, User.department_id)).one()
                    user_ids[role] = user.id
                    if user.is_active is not True or (role == "super_admin" and user.department_id is not None):
                        raise AssertionError("User default or optional Super Admin membership differed")
                asset = connection.execute(insert(Asset.__table__).values(asset_code="PRJ-001", name="Classroom Projector",
                    department_id=department.id, category_id=category.id).returning(Asset.id, Asset.status, Asset.location)).one()
                check(all(isinstance(value, UUID) and value.version == 4 for value in (department.id, category.id, asset.id, *user_ids.values()))
                      and department.is_archived is False and category.is_archived is False
                      and asset.status == "active" and asset.location is None,
                      "Core inserts through mapped tables obtain server UUID/boolean/status defaults and allow a departmentless Super Admin.")
                ticket = connection.execute(insert(MaintenanceTicket.__table__).values(
                    asset_id=asset.id, reported_by_id=user_ids["student"], department_id=department.id,
                    title="Projector flickers", description="Image briefly disappears during use", priority="high"
                ).returning(MaintenanceTicket.id, MaintenanceTicket.status, MaintenanceTicket.created_at,
                            MaintenanceTicket.assigned_to_id, MaintenanceTicket.assigned_at, MaintenanceTicket.rejected_at,
                            MaintenanceTicket.closed_at, MaintenanceTicket.rejection_reason)).one()
                check(isinstance(ticket.id, UUID) and ticket.status == "open" and isinstance(ticket.created_at, datetime)
                      and ticket.created_at.utcoffset() == timedelta(0)
                      and all(value is None for value in tuple(ticket)[3:]),
                      "A new ticket receives an aware creation instant and open status while optional assignment/lifecycle fields remain NULL.")
                common = {"department_id": department.id, "category_id": category.id}
                reject_sql(connection, "INSERT INTO college_step17.departments (code) VALUES (:code)", {"code": "ECE"},
                           "23502", "departments", "Direct SQL cannot omit the required department name despite permissive Python construction.", column="name")
                reject_sql(connection, "INSERT INTO college_step17.departments (code, name) VALUES (:code, :name)",
                           {"code": " ece ", "name": "Electronics"}, "23514", "departments",
                           "Direct SQL rejects noncanonical department codes without relying on a Python type hint.", constraint="ck_departments_code")
                asset_insert = "INSERT INTO college_step17.assets (asset_code, name, department_id, category_id, status) VALUES (:code, :name, :department_id, :category_id, :status)"
                reject_sql(connection, asset_insert, {**common, "code": "PRJ-001", "name": "Duplicate Projector", "status": "active"},
                           "23505", "assets", "A newly generated UUID cannot bypass the installed unique asset-code constraint.", constraint="uq_assets_asset_code")
                reject_sql(connection, asset_insert, {**common, "code": "BAD-STATUS", "name": "Status Probe", "status": "broken"},
                           "23514", "assets", "The installed asset-status CHECK rejects an arbitrary string that Python str typing permits.", constraint="ck_assets_status")
                reject_sql(connection, asset_insert, {**common, "department_id": UUID("10000000-0000-4000-8000-999999999999"),
                           "code": "BAD-PARENT", "name": "Reference Probe", "status": "active"}, "23503", "assets",
                           "The installed asset department foreign key rejects an unknown UUID.", constraint="fk_assets_department")
                user_insert = "INSERT INTO college_step17.users (email, display_name, password_hash, role, department_id) VALUES (:email, :name, :hash, :role, :department_id)"
                user_values = {"email": "probe@example.test", "name": "Lab Probe", "hash": "synthetic_mapping_lab_hash", "role": "student", "department_id": department.id}
                reject_sql(connection, user_insert, {**user_values, "email": "Probe@EXAMPLE.TEST"}, "23514", "users",
                           "The installed email CHECK rejects noncanonical storage independently of the mapper.", constraint="ck_users_email")
                reject_sql(connection, user_insert, {**user_values, "role": "owner"}, "23514", "users",
                           "The installed user-role CHECK rejects a role outside the agreed set.", constraint="ck_users_role")
                reject_sql(connection, user_insert, {**user_values, "department_id": None}, "23514", "users",
                           "A nullable membership column still rejects a departmentless student through its same-row CHECK.", constraint="ck_users_department")
                ticket_insert = "INSERT INTO college_step17.maintenance_tickets (asset_id, reported_by_id, assigned_to_id, department_id, title, description, priority) VALUES (:asset_id, :reporter, :assignee, :department_id, :title, :description, :priority)"
                ticket_values = {"asset_id": asset.id, "reporter": user_ids["student"], "assignee": None,
                                 "department_id": department.id, "title": "Lab Report", "description": "Synthetic issue", "priority": "high"}
                reject_sql(connection, ticket_insert, {**ticket_values, "priority": "urgent"}, "23514", "maintenance_tickets",
                           "The installed ticket-priority CHECK rejects an unrecognized priority.", constraint="ck_maintenance_tickets_priority")
                reject_sql(connection, ticket_insert, {**ticket_values, "assignee": UUID("30000000-0000-4000-8000-999999999999")},
                           "23503", "maintenance_tickets", "An optional assignee must still reference an existing user when supplied.", constraint="fk_tickets_assignee")
                reject_sql(connection, ticket_insert, {**ticket_values, "title": "   "}, "23514", "maintenance_tickets",
                           "The installed ticket-title CHECK rejects whitespace-only text.", constraint="ck_maintenance_tickets_title")
                counts = {table.name: connection.execute(select(func.count()).select_from(table)).scalar_one() for table in Base.metadata.sorted_tables}
                check(counts == {"departments": 1, "asset_categories": 1, "users": 3, "assets": 1, "maintenance_tickets": 1},
                      "All direct-SQL rejections leave the valid five-entity fixture unchanged and the transaction usable.")
            finally:
                transaction.rollback()
            check(not connection.in_transaction(), "The mapping lab rolls back schema creation, valid inserts, and every failure probe.")
        with engine.connect() as observer:
            check(connection.closed and observer.execute(text("SELECT to_regnamespace('college_step17') IS NULL")).scalar_one()
                  and Base.metadata.schema is None and all(table.schema is None for table in Base.metadata.tables.values()),
                  "The lab schema is absent after rollback and application metadata retains its original schema ownership.")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)
        engine.dispose()
    check(driver_connection is not None and driver_connection.closed and engine.pool.checkedout() == 0,
          "All checkouts return before final Engine disposal closes the physical mapping-lab connection.")


if __name__ == "__main__":
    main()
