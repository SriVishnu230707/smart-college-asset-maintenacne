"""Compare Core declarations, PostgreSQL inspection, and isolated reflection."""

import re
import sys
from importlib.metadata import version
from pathlib import Path
from pprint import pprint

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import (
    CheckConstraint, Column, ForeignKey, MetaData, String, Table,
    UniqueConstraint, Uuid, event, inspect, text,
)
from sqlalchemy.exc import NoReferencedTableError, NoSuchTableError
from sqlalchemy.schema import CreateSchema, CreateTable

from college_maintenance.database import engine
from schema import SCHEMA, assets, metadata


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def normalize_sql(value):
    # Fixed fixture expressions only: PostgreSQL adds text casts, parentheses,
    # and whitespace. This is not a general SQL equivalence/diff algorithm.
    return re.sub(r"::text|[()\s]", "", str(value)) if value is not None else None


def type_sql(column_type):
    return str(column_type.compile(dialect=engine.dialect))


def declared_shape(table):
    return {
        "columns": [(c.name, type_sql(c.type), c.nullable,
                     normalize_sql(c.server_default.arg) if c.server_default is not None else None)
                    for c in table.columns],
        "primary_key": (str(table.primary_key.name), tuple(c.name for c in table.primary_key.columns)),
        "unique": sorted((str(c.name), tuple(col.name for col in c.columns)) for c in table.constraints if isinstance(c, UniqueConstraint)),
        "checks": sorted((str(c.name), normalize_sql(c.sqltext)) for c in table.constraints if isinstance(c, CheckConstraint)),
        "foreign_keys": sorted((str(c.name), tuple(e.parent.name for e in c.elements),
                                c.elements[0].column.table.schema, c.elements[0].column.table.name,
                                tuple(e.column.name for e in c.elements), c.ondelete, c.onupdate)
                               for c in table.foreign_key_constraints),
        "indexes": sorted((str(i.name), tuple(c.name for c in i.columns), bool(i.unique)) for i in table.indexes),
    }


def inspected_shape(inspector, name):
    primary = inspector.get_pk_constraint(name, schema=SCHEMA)
    return {
        "columns": [(c["name"], type_sql(c["type"]), c["nullable"], normalize_sql(c["default"]))
                    for c in inspector.get_columns(name, schema=SCHEMA)],
        "primary_key": (primary["name"], tuple(primary["constrained_columns"])),
        "unique": sorted((c["name"], tuple(c["column_names"])) for c in inspector.get_unique_constraints(name, schema=SCHEMA)),
        "checks": sorted((c["name"], normalize_sql(c["sqltext"])) for c in inspector.get_check_constraints(name, schema=SCHEMA)),
        "foreign_keys": sorted((c["name"], tuple(c["constrained_columns"]), c["referred_schema"], c["referred_table"],
                                tuple(c["referred_columns"]), c["options"].get("ondelete"), c["options"].get("onupdate"))
                               for c in inspector.get_foreign_keys(name, schema=SCHEMA)),
        # PostgreSQL reports the index backing a UNIQUE constraint too. Compare
        # that constraint above, and compare only separately declared indexes here.
        "indexes": sorted((i["name"], tuple(i["column_names"]), bool(i["unique"]))
                          for i in inspector.get_indexes(name, schema=SCHEMA) if not i.get("duplicates_constraint")),
    }


def differences(expected, actual):
    return {key: {"declared": expected[key], "database": actual[key]}
            for key in expected if expected[key] != actual[key]}


def main():
    print(f"SQLAlchemy {version('SQLAlchemy')}; psycopg {version('psycopg')}")
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "The metadata lab reuses the pinned SQLAlchemy and psycopg versions.")
    check(set(metadata.tables) == {f"{SCHEMA}.{name}" for name in ("departments", "asset_categories", "assets")}
          and all(t.schema == SCHEMA for t in metadata.tables.values()),
          "MetaData registers three schema-qualified Core tables without ORM mappings.")
    check(assets.c is assets.columns and assets.c.asset_code.type.length == 50
          and not assets.c.department_id.nullable and assets.c.location.nullable,
          "Column collections retain the chosen code length and required versus optional fields.")
    check(str(assets.primary_key.name) == "pk_assets"
          and {str(c.name) for c in assets.constraints} == {
              "pk_assets", "uq_assets_asset_code", "ck_assets_asset_code_canonical", "ck_assets_name_nonblank",
              "ck_assets_status_allowed", "fk_assets_department_id_departments", "fk_assets_category_id_asset_categories"}
          and {str(i.name) for i in assets.indexes} == {"ix_assets_department_id", "ix_assets_category_id"},
          "Naming conventions assign stable primary, unique, check, foreign-key, and index names.")
    ordered = list(metadata.sorted_tables)
    check(ordered[-1] is assets and {t.name for t in ordered[:-1]} == {"departments", "asset_categories"}
          and all(fk.column.table in ordered[:-1] for fk in assets.foreign_keys),
          "Resolved foreign keys put both parents before assets in dependency order.")
    ddl = str(CreateTable(assets).compile(dialect=engine.dialect))
    print("Compiled asset DDL:", ddl)
    check(f"CREATE TABLE {SCHEMA}.assets" in ddl and f"REFERENCES {SCHEMA}.departments" in ddl
          and "DEFAULT gen_random_uuid()" in ddl and "CONSTRAINT ck_assets_status_allowed" in ddl,
          "DDL compilation includes schema-qualified references, named constraints, and server defaults.")
    broken = Table("broken_reference", MetaData(schema=SCHEMA),
                   Column("department_id", Uuid, ForeignKey(f"{SCHEMA}.missing_parent.id")))
    try:
        str(CreateTable(broken).compile(dialect=engine.dialect))
    except NoReferencedTableError:
        check(engine.pool.checkedout() == 0 and engine.pool.checkedin() == 0,
              "An unresolved foreign key fails at compilation before any physical connection opens.")
    else:
        raise AssertionError("The unresolved foreign key compiled without error")

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
                    to_regnamespace('college_step15') IS NULL""")).one()
                check(identity[0] == "college_learning" and identity[1] == "college_learner"
                      and 180000 <= identity[2] < 190000 and identity[4],
                      "The PostgreSQL 18 learner connection has a free disposable Step 15 namespace.")
                print(f"engine_backend_pid={identity[3]}")
                driver_connection = connection.connection.driver_connection
                connection.execute(CreateSchema(SCHEMA))
                connection.execute(text("SET LOCAL search_path TO pg_catalog, public"))
                metadata.create_all(connection)
                created = [re.search(r"CREATE TABLE\s+(\S+)", sql).group(1)
                           for sql in statements if re.search(r"CREATE TABLE\s+", sql)]
                print("Observed CREATE TABLE order:", created)
                check(len(created) == 3 and set(created) == {t.fullname for t in ordered}
                      and created[-1] == assets.fullname,
                      "create_all creates exactly the three declared tables in dependency order.")
                inspector = inspect(connection)
                check(set(inspector.get_table_names(schema=SCHEMA)) == {t.name for t in ordered}
                      and inspector.has_table("assets", schema=SCHEMA)
                      and SCHEMA not in connection.execute(text("SELECT current_schemas(false)")).scalar_one(),
                      "Explicit schema inspection finds the tables even though their schema is outside search_path.")
                expected = {t.name: declared_shape(t) for t in ordered}
                for table in ordered:
                    actual = inspected_shape(inspector, table.name)
                    print(f"Inspected {table.fullname}:")
                    pprint(actual, sort_dicts=False)
                    check(actual["columns"] == expected[table.name]["columns"],
                          f"{table.name}: inspected column order, PostgreSQL types, lengths, nullability, and server defaults match declarations.")
                    check(not differences({k: v for k, v in expected[table.name].items() if k != "columns"}, actual),
                          f"{table.name}: inspected primary, unique, check, foreign-key policies, and explicit indexes match declarations.")

                before = len([s for s in statements if s.lstrip().startswith("CREATE ")])
                metadata.create_all(connection)
                check(len([s for s in statements if s.lstrip().startswith("CREATE ")]) == before,
                      "Repeating create_all with checkfirst emits no additional CREATE statements.")
                reflected = MetaData()
                reflected.reflect(bind=connection, schema=SCHEMA)
                check(set(reflected.tables) == set(metadata.tables)
                      and all(reflected.tables[key] is not table for key, table in metadata.tables.items()),
                      "Reflection fills a separate MetaData registry with distinct schema-qualified Table objects.")
                check(all(declared_shape(reflected.tables[t.key]) == expected[t.name] for t in ordered),
                      "Reflected columns, server defaults, constraints, reference actions, and indexes match the declared database shape.")
                reflected_assets = reflected.tables[assets.key]
                check(all(fk.column.table is reflected.tables[fk.column.table.key] for fk in reflected_assets.foreign_keys)
                      and Table("assets", reflected, schema=SCHEMA, autoload_with=connection) is reflected_assets,
                      "Reflected foreign keys resolve within their own registry and table lookup reuses that registry's object.")
                check(assets.c.status.default.arg == "active" and reflected_assets.c.status.default is None
                      and assets.info and not reflected_assets.info
                      and normalize_sql(reflected_assets.c.status.server_default.arg) == normalize_sql(assets.c.status.server_default.arg),
                      "Reflection preserves the server default but cannot recover Python defaults or Table.info.")
                try:
                    Table("missing_assets", MetaData(), schema=SCHEMA, autoload_with=connection)
                except NoSuchTableError:
                    check(not inspector.has_table("missing_assets", schema=SCHEMA),
                          "Reflecting an absent table raises NoSuchTableError instead of creating it.")
                else:
                    raise AssertionError("Reflection accepted an absent table")

                # Deliberate drift exists only inside this disposable transaction.
                connection.execute(text("ALTER TABLE college_step15.assets ADD COLUMN audit_note text"))
                connection.execute(text("ALTER TABLE college_step15.assets DROP CONSTRAINT ck_assets_status_allowed"))
                # Caching varies by dialect/method. Refresh explicitly rather
                # than relying on a previously populated Inspector after DDL.
                inspector.clear_cache()
                drifted = inspected_shape(inspector, "assets")
                drift = differences(expected["assets"], drifted)
                print("Deliberate drift:")
                pprint(drift, sort_dicts=False)
                check(set(drift) == {"columns", "checks"}
                      and drifted["columns"] == expected["assets"]["columns"] + [("audit_note", "TEXT", True, None)]
                      and {name for name, sql in drifted["checks"]} == {"ck_assets_asset_code_canonical", "ck_assets_name_nonblank"},
                      "After clearing the cache, inspection detects exactly the extra column and removed status constraint.")
                proposal = MetaData()
                for table in ordered:
                    table.to_metadata(proposal)
                proposal.tables[assets.key].append_column(Column("planned_label", String(40)))
                before = len([s for s in statements if s.lstrip().startswith(("CREATE ", "ALTER "))])
                proposal.create_all(connection)
                inspector.clear_cache()
                check(inspected_shape(inspector, "assets") == drifted
                      and len([s for s in statements if s.lstrip().startswith(("CREATE ", "ALTER "))]) == before,
                      "create_all neither adds a newly declared column nor removes extra columns or restores a dropped constraint.")
                check(declared_shape(assets) == expected["assets"] and declared_shape(reflected_assets) == expected["assets"]
                      and "planned_label" in proposal.tables[assets.key].c,
                      "Declared, reflected, and proposed metadata remain separate Python descriptions after database drift.")
                refreshed = MetaData()
                refreshed.reflect(bind=connection, schema=SCHEMA)
                check(declared_shape(refreshed.tables[assets.key]) == drifted
                      and refreshed.tables[assets.key] is not reflected_assets,
                      "A fresh reflection observes the altered database without changing the original declarations or earlier snapshot.")
            finally:
                transaction.rollback()
            check(not connection.in_transaction(), "The lab rolls back its entire schema-creation and drift transaction.")
        with engine.connect() as observer:
            check(connection.closed and observer.execute(text("SELECT to_regnamespace('college_step15') IS NULL")).scalar_one(),
                  "A subsequent checkout confirms rollback removed the Step 15 schema and every study object.")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)
        engine.dispose()
    check(driver_connection is not None and driver_connection.closed and engine.pool.checkedout() == 0,
          "All checkouts return before Engine disposal closes the physical connection.")


if __name__ == "__main__":
    main()
