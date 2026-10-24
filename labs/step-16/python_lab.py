"""Execute Core asset CRUD and prove result shape/cardinality contracts."""

import sys
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import Row, RowMapping, bindparam, delete, event, func, insert, select, text, update
from sqlalchemy.exc import MultipleResultsFound, NoResultFound, ResourceClosedError
from sqlalchemy.schema import CreateSchema

from college_maintenance.database import engine
from schema import SCHEMA, asset_categories, assets, departments, metadata


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def expect_error(exception_type, operation, message):
    try:
        operation()
    except exception_type as exc:
        check(type(exc) is exception_type, message)
        print(f"Expected result error: {exception_type.__name__}")
    else:
        raise AssertionError(f"Expected {exception_type.__name__}: {message}")


def show_sql(label, statement):
    print(f"Compiled {label} SQL:", statement.compile(dialect=engine.dialect))


def main():
    print(f"SQLAlchemy {version('SQLAlchemy')}; psycopg {version('psycopg')}")
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "The Core DML lab reuses the pinned SQLAlchemy and psycopg versions.")
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
                    to_regnamespace('college_step16') IS NULL""")).one()
                check(identity[0] == "college_learning" and identity[1] == "college_learner"
                      and 180000 <= identity[2] < 190000 and identity[4],
                      "The PostgreSQL 18 learner connection has a free disposable Step 16 namespace.")
                print(f"engine_backend_pid={identity[3]}")
                driver_connection = connection.connection.driver_connection
                connection.execute(CreateSchema(SCHEMA))
                metadata.create_all(connection)
                department_rows = connection.execute(insert(departments).values([
                    {"code": "CSE", "name": "Computer Science"},
                    {"code": "ECE", "name": "Electronics"},
                ]).returning(departments.c.id, departments.c.code, departments.c.is_archived)).mappings().all()
                department_ids = {row["code"]: row["id"] for row in department_rows}
                category_rows = connection.execute(insert(asset_categories).values([
                    {"code": "COMPUTER", "name": "Computer"},
                    {"code": "PROJECTOR", "name": "Projector"},
                ]).returning(asset_categories.c.id, asset_categories.c.code)).mappings().all()
                category_ids = {row["code"]: row["id"] for row in category_rows}
                check(set(department_ids) == {"CSE", "ECE"} and set(category_ids) == {"COMPUTER", "PROJECTOR"}
                      and all(isinstance(value, UUID) and value.version == 4 for value in [*department_ids.values(), *category_ids.values()])
                      and all(row["is_archived"] is False for row in department_rows),
                      "Parent INSERT RETURNING exposes generated UUIDs and database defaults, correlated by business code.")
                seed = insert(assets).values([
                    {"asset_code": "PC-001", "name": "Lab Computer", "location": "Computer Lab 1",
                     "department_id": department_ids["CSE"], "category_id": category_ids["COMPUTER"]},
                    {"asset_code": "PC-002", "name": "Electronics Computer", "location": None,
                     "department_id": department_ids["ECE"], "category_id": category_ids["COMPUTER"]},
                    {"asset_code": "PRJ-001", "name": "Classroom Projector", "location": "Lecture Hall A",
                     "department_id": department_ids["CSE"], "category_id": category_ids["PROJECTOR"]},
                ]).returning(assets.c.id, assets.c.asset_code, assets.c.status)
                show_sql("INSERT RETURNING", seed)
                inserted = connection.execute(seed).mappings().all()
                asset_ids = {row["asset_code"]: row["id"] for row in inserted}
                check(set(asset_ids) == {"PC-001", "PC-002", "PRJ-001"} and len(set(asset_ids.values())) == 3
                      and all(isinstance(row["id"], UUID) and row["id"].version == 4 and row["status"] == "active" for row in inserted),
                      "Asset INSERT explicitly returns each generated UUID and status without assuming RETURNING row order.")
                print("Returned asset IDs:", asset_ids)

                projected = select(assets.c.asset_code, assets.c.name.label("asset_name"), assets.c.location).order_by(assets.c.asset_code)
                expected_rows = [("PC-001", "Lab Computer", "Computer Lab 1"),
                                 ("PC-002", "Electronics Computer", None),
                                 ("PRJ-001", "Classroom Projector", "Lecture Hall A")]
                with connection.execute(projected) as result:
                    rows = result.all()
                    check(rows == expected_rows and all(isinstance(row, Row) for row in rows),
                          "all returns every ordered projected Row with the original nullable value.")
                    check(result.all() == [], "A consumed result does not replay its rows on a second all call.")
                row = rows[0]
                check(tuple(row) == expected_rows[0] and row[0] == row.asset_code == "PC-001"
                      and row._mapping["asset_name"] == "Lab Computer" and row._mapping[assets.c.location] == "Computer Lab 1",
                      "Row supports tuple positions, labeled attributes, and explicit mapping access.")
                mappings = connection.execute(projected).mappings().all()
                check(all(isinstance(row, RowMapping) for row in mappings)
                      and [dict(row) for row in mappings] == [dict(zip(("asset_code", "asset_name", "location"), values)) for values in expected_rows],
                      "mappings returns named RowMapping values suitable for explicit dictionary conversion.")
                check(connection.execute(projected).scalars().all() == ["PC-001", "PC-002", "PRJ-001"],
                      "scalars filters a multi-column projection down to its first column without checking row count.")
                check(connection.execute(projected).scalars(index=1).all() == [values[1] for values in expected_rows],
                      "An explicit scalars index selects the intended alternate projected column.")

                lookup = projected.where(assets.c.asset_code == bindparam("lookup_code"))
                show_sql("bound SELECT", lookup)
                check(connection.execute(lookup, {"lookup_code": "PC-001"}).one() == expected_rows[0],
                      "one returns the required asset Row when the unique lookup matches exactly once.")
                check(connection.execute(lookup, {"lookup_code": "PC-002"}).one_or_none() == expected_rows[1]
                      and connection.execute(lookup, {"lookup_code": "MISSING"}).one_or_none() is None,
                      "one_or_none distinguishes a found asset Row from an absent optional lookup.")
                missing = projected.where(assets.c.asset_code == "MISSING")
                check(connection.execute(missing).all() == [] and connection.execute(missing).first() is None,
                      "Empty all and first results are an empty sequence and None respectively.")
                many = projected.where(assets.c.department_id == department_ids["CSE"])
                before = len(statements)
                first_result = connection.execute(many)
                check(first_result.first() == expected_rows[0] and first_result.closed
                      and len(statements) == before + 1 and "LIMIT" not in statements[-1].upper(),
                      "first accepts multiple matching rows, closes the result, and adds no SQL LIMIT.")
                expect_error(ResourceClosedError, first_result.all,
                             "Reading again after first raises ResourceClosedError because the remaining rows were discarded.")
                before = len(statements)
                check(connection.execute(many.limit(1)).first() == expected_rows[0]
                      and len(statements) == before + 1 and "LIMIT" in statements[-1].upper(),
                      "An explicit ordered limit bounds the SELECT in SQL when only the first asset is wanted.")
                expect_error(NoResultFound, lambda: connection.execute(missing).one(),
                             "one rejects zero matching assets with NoResultFound.")
                expect_error(MultipleResultsFound, lambda: connection.execute(many).one(),
                             "one rejects a department lookup that matches multiple assets.")
                expect_error(MultipleResultsFound, lambda: connection.execute(many).one_or_none(),
                             "one_or_none also rejects multiple rows instead of silently choosing an asset.")
                id_lookup = select(assets.c.id, assets.c.asset_code).where(assets.c.asset_code == "PC-001")
                check(connection.execute(id_lookup).scalar_one() == asset_ids["PC-001"],
                      "scalar_one checks exactly one row and returns its first column, not the entire Row.")
                expect_error(NoResultFound, lambda: connection.execute(select(assets.c.id).where(assets.c.asset_code == "MISSING")).scalar_one(),
                             "scalar_one rejects a missing required ID with NoResultFound.")
                expect_error(MultipleResultsFound, lambda: connection.execute(select(assets.c.id).where(assets.c.department_id == department_ids["CSE"])).scalar_one(),
                             "scalar_one rejects multiple IDs with MultipleResultsFound.")
                nullable = select(assets.c.location).where(assets.c.asset_code == "PC-002")
                check(connection.execute(nullable).scalar_one() is None
                      and connection.execute(nullable).one_or_none() == (None,)
                      and connection.execute(select(assets.c.location).where(assets.c.asset_code == "MISSING")).one_or_none() is None,
                      "A present SQL NULL is a one-column Row containing None, distinct from no row.")
                check(connection.execute(select(func.count()).select_from(assets)).scalar_one() == 3,
                      "Client-side result cardinality errors leave the database transaction usable.")

                temporary = connection.execute(insert(assets).values(
                    asset_code="LAB-TEMP", name="Temporary Computer", location="Store Room",
                    department_id=department_ids["CSE"], category_id=category_ids["COMPUTER"]
                ).returning(assets.c.id, assets.c.asset_code)).one()
                check(isinstance(temporary.id, UUID) and temporary.asset_code == "LAB-TEMP"
                      and connection.execute(select(assets.c.id).where(assets.c.asset_code == "LAB-TEMP")).scalar_one() == temporary.id,
                      "A single asset INSERT RETURNING provides the same generated ID seen by a later SELECT.")
                change = update(assets).where(assets.c.id == asset_ids["PRJ-001"]).values(
                    location="Room 204", status="under_maintenance"
                ).returning(assets.c.id, assets.c.asset_code, assets.c.location, assets.c.status)
                show_sql("UPDATE RETURNING", change)
                changed = connection.execute(change).mappings().one()
                check(dict(changed) == {"id": asset_ids["PRJ-001"], "asset_code": "PRJ-001", "location": "Room 204", "status": "under_maintenance"},
                      "UPDATE RETURNING exposes the exact changed asset ID and new field values.")
                check(connection.execute(update(assets).where(assets.c.asset_code == "MISSING").values(location="Nowhere")
                                         .returning(assets.c.id)).one_or_none() is None,
                      "A zero-match UPDATE RETURNING succeeds with no returned row.")
                no_change = connection.execute(update(assets).where(assets.c.asset_code == "PC-001").values(location="Computer Lab 1"))
                check(no_change.supports_sane_rowcount() and no_change.rowcount == 1 and not no_change.returns_rows,
                      "A non-returning UPDATE reports one matched row even when the stored value stays unchanged.")
                expect_error(ResourceClosedError, no_change.all,
                             "A statement without returned rows cannot be consumed as a row-producing result.")
                no_match = connection.execute(update(assets).where(assets.c.asset_code == "MISSING").values(location="Nowhere"))
                check(no_match.rowcount == 0 and not no_match.returns_rows,
                      "A non-returning zero-match UPDATE reports rowcount zero without a database error.")
                removal = delete(assets).where(assets.c.id == temporary.id).returning(assets.c.id, assets.c.asset_code)
                show_sql("DELETE RETURNING", removal)
                check(connection.execute(removal).one() == (temporary.id, "LAB-TEMP")
                      and connection.execute(select(assets.c.id).where(assets.c.id == temporary.id)).one_or_none() is None,
                      "DELETE RETURNING identifies the removed disposable asset and a later SELECT confirms absence.")
                check(connection.execute(removal).one_or_none() is None,
                      "Repeating the same DELETE RETURNING succeeds with no row instead of inventing a deletion.")
                bulk = connection.execute(update(assets).where(assets.c.department_id == department_ids["CSE"])
                                          .values(status="under_maintenance").returning(assets.c.id, assets.c.asset_code)).all()
                check({row.asset_code: row.id for row in bulk} == {code: asset_ids[code] for code in ("PC-001", "PRJ-001")}
                      and len(bulk) == 2,
                      "A multi-match UPDATE is verified by its two returned identities without relying on rowcount or row order.")
                removed = connection.execute(delete(assets).where(assets.c.id == asset_ids["PC-002"])
                                             .returning(assets.c.id, assets.c.asset_code)).one()
                check(removed == (asset_ids["PC-002"], "PC-002"),
                      "The Core delete operation returns the original ID of the removed Electronics asset.")
                final_query = select(assets.c.asset_code, assets.c.name, assets.c.location, assets.c.status).order_by(assets.c.asset_code)
                final_rows = connection.execute(final_query).all()
                sql_rows = connection.execute(text("""SELECT asset_code, name, location, status
                    FROM college_step16.assets ORDER BY asset_code""")).all()
                print("Final transaction rows:", final_rows)
                check(final_rows == sql_rows == [("PC-001", "Lab Computer", "Computer Lab 1", "under_maintenance"),
                                                 ("PRJ-001", "Classroom Projector", "Room 204", "under_maintenance")],
                      "Core and equivalent raw SQL agree on the exact rows after insert, update, and delete operations.")
            finally:
                transaction.rollback()
            check(not connection.in_transaction(), "The complete fixture and all Core writes roll back in one cleanup transaction.")
        with engine.connect() as observer:
            check(connection.closed and observer.execute(text("SELECT to_regnamespace('college_step16') IS NULL")).scalar_one(),
                  "A subsequent checkout confirms no Step 16 schema or fixture row persists.")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)
        engine.dispose()
    check(driver_connection is not None and driver_connection.closed and engine.pool.checkedout() == 0,
          "All result work and connection contexts finish before Engine disposal closes the physical backend.")


if __name__ == "__main__":
    main()
