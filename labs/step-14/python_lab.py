"""Prove Core value binding and caller-owned transactions on a disposable fixture."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError, StatementError

from college_maintenance.database import engine

D1, D2, D3, D4, D5 = [UUID(f"10000000-0000-4000-8000-{n:012d}") for n in range(1, 6)]
A1, A2, A3, A4, A5, A6 = [UUID(f"40000000-0000-4000-8000-{n:012d}") for n in range(1, 7)]
CATEGORY = UUID("20000000-0000-4000-8000-000000000001")
PAYLOAD_NAME = "O'Brien'); DROP TABLE college_step14.assets; --"
LOOKUP = text("SELECT /* step14_lookup */ asset_code, name FROM college_step14.assets WHERE asset_code = :asset_code")
DEPARTMENT_INSERT = text("INSERT INTO college_step14.departments (id, code, name) VALUES (:id, :code, :name)")
ASSET_INSERT = text("""INSERT INTO college_step14.assets (id, asset_code, name, department_id, category_id)
                       VALUES (:id, :asset_code, :name, :department_id, :category_id)""")
SORT_COLUMNS = {"code": "asset_code", "name": "name"}


class InjectedFailure(RuntimeError):
    """A deliberate application failure after both related writes succeeded."""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def register_pair(connection, department_id, asset_id, department_code, asset_code, name):
    """Borrow the caller's Connection; never begin, commit, or close it here."""
    connection.execute(DEPARTMENT_INSERT, {"id": department_id, "code": department_code,
                                           "name": "Department " + department_code})
    connection.execute(ASSET_INSERT, {"id": asset_id, "asset_code": asset_code, "name": name,
                                     "department_id": department_id, "category_id": CATEGORY})


def pair_counts(connection, department_id, asset_id):
    return tuple(connection.execute(text(sql), {"id": identity}).scalar_one() for sql, identity in (
        ("SELECT count(*) FROM college_step14.departments WHERE id = :id", department_id),
        ("SELECT count(*) FROM college_step14.assets WHERE id = :id", asset_id),
    ))


def list_asset_codes(connection, sort_key):
    try:
        column = SORT_COLUMNS[sort_key]
    except KeyError:
        raise ValueError("Unsupported asset sort key") from None
    # Only trusted dictionary values enter SQL structure. User text never does.
    return connection.execute(text(
        f'SELECT asset_code FROM college_step14.assets ORDER BY {column} COLLATE "C", id'
    )).scalars().all()


def main(run_id: UUID) -> None:
    print(f"SQLAlchemy {version('SQLAlchemy')}; psycopg {version('psycopg')}; run_id={run_id}")
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "The Core lab uses the existing pinned SQLAlchemy and psycopg versions.")
    sent = []

    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        sent.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", before_cursor)
    driver_connection = None
    try:
        with engine.begin() as setup:
            identity = setup.execute(text("""SELECT current_database(), current_user,
                current_setting('server_version_num')::integer,
                to_regnamespace('college_step14') IS NULL, pg_backend_pid()""")).one()
            check(identity[0] == "college_learning" and identity[1] == "college_learner"
                  and 180000 <= identity[2] < 190000 and identity[3],
                  "The expected PostgreSQL 18 learner connection has a free Step 14 namespace.")
            driver_connection = setup.connection.driver_connection
            for ddl in (
                "CREATE SCHEMA college_step14",
                "CREATE TABLE college_step14.lab_run (run_id uuid PRIMARY KEY, writer_backend_pid integer NOT NULL)",
                """CREATE TABLE college_step14.departments (
                    id uuid PRIMARY KEY, code text NOT NULL UNIQUE, name text NOT NULL,
                    CHECK (code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'),
                    CHECK (name !~ '^[[:space:]]*$'))""",
                "CREATE TABLE college_step14.asset_categories (id uuid PRIMARY KEY, code text NOT NULL UNIQUE)",
                """CREATE TABLE college_step14.assets (
                    id uuid PRIMARY KEY,
                    asset_code text NOT NULL CONSTRAINT uq_step14_assets_code UNIQUE,
                    name text NOT NULL CHECK (name !~ '^[[:space:]]*$'),
                    department_id uuid NOT NULL REFERENCES college_step14.departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
                    category_id uuid NOT NULL REFERENCES college_step14.asset_categories(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
                    CHECK (asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'))""",
            ):
                setup.execute(text(ddl))
            setup.execute(text("INSERT INTO college_step14.lab_run VALUES (:run_id, :pid)"),
                          {"run_id": run_id, "pid": identity[4]})
            setup.execute(DEPARTMENT_INSERT, {"id": D1, "code": "CSE", "name": "Computer Science"})
            setup.execute(text("INSERT INTO college_step14.asset_categories VALUES (:id, :code)"),
                          {"id": CATEGORY, "code": "COMPUTER"})
            setup.execute(ASSET_INSERT, [
                {"id": A1, "asset_code": "PC-001", "name": "Zebra Computer", "department_id": D1, "category_id": CATEGORY},
                {"id": A2, "asset_code": "PC-002", "name": "Alpha Computer", "department_id": D1, "category_id": CATEGORY},
            ])
        print(f"writer_backend_pid={identity[4]}")

        with engine.connect() as connection:
            check(not connection.in_transaction(), "A fresh Core Connection has no SQLAlchemy transaction before its first statement.")
            normal = connection.execute(LOOKUP, {"asset_code": "PC-001"}).all()
            check(normal == [("PC-001", "Zebra Computer")] and connection.in_transaction(),
                  "A bound lookup returns its one asset and the first SELECT autobegins a transaction.")
            tautology = "PC-001' OR '1'='1"
            stacked = "PC-001'; DROP TABLE college_step14.assets; --"
            check(connection.execute(LOOKUP, {"asset_code": tautology}).all() == [],
                  "A tautology-shaped input is treated as one unmatched asset-code value.")
            check(connection.execute(LOOKUP, {"asset_code": stacked}).all() == [],
                  "A stacked-statement-shaped input is also an unmatched value, not executed SQL.")
            lookups = [entry for entry in sent if "/* step14_lookup */" in entry[0]]
            print("TRACE bound SQL:", lookups[0][0])
            print("TRACE synthetic input values:", [entry[1]["asset_code"] for entry in lookups])
            check(len(lookups) == 3 and len({entry[0] for entry in lookups}) == 1
                  and [entry[1]["asset_code"] for entry in lookups] == ["PC-001", tautology, stacked]
                  and all(value not in lookups[0][0] for value in (tautology, stacked)),
                  "Cursor observations show unchanged SQL with three separately bound input values.")
            identifier_values = connection.execute(text(
                "SELECT :column_name AS requested_column FROM college_step14.assets ORDER BY asset_code"
            ), {"column_name": "asset_code"}).scalars().all()
            check(identifier_values == ["asset_code", "asset_code"],
                  "Binding a column name selects a repeated string value rather than that column.")
            check(list_asset_codes(connection, "code") == ["PC-001", "PC-002"]
                  and list_asset_codes(connection, "name") == ["PC-002", "PC-001"],
                  "A fixed identifier allowlist provides the two intended deterministic sort orders.")
            before = len(sent)
            try:
                list_asset_codes(connection, "asset_code; DROP TABLE college_step14.assets; --")
            except ValueError:
                check(len(sent) == before, "An unapproved identifier is rejected before any SQL reaches the cursor.")
            else:
                raise AssertionError("An unapproved sort key was accepted")
            before = len(sent)
            try:
                connection.execute(LOOKUP, {})
            except StatementError as exc:
                check(isinstance(exc.orig, InvalidRequestError) and len(sent) == before,
                      "A missing bound value raises a client-side error before cursor execution.")
            else:
                raise AssertionError("The required bound value was omitted without error")
            try:
                connection.begin()
            except InvalidRequestError:
                check(connection.in_transaction(), "Beginning again after autobegin is rejected without replacing the active transaction.")
            else:
                raise AssertionError("A second outer transaction was unexpectedly allowed")
            connection.rollback()
            check(not connection.in_transaction(), "Explicit rollback ends the autobegun transaction.")
        check(connection.closed and engine.pool.checkedout() == 0,
              "The connection context closes its wrapper and returns its checkout to the pool.")

        with engine.connect() as uncommitted:
            register_pair(uncommitted, D3, A4, "MECH", "NO-COMMIT", "Uncommitted Computer")
            check(pair_counts(uncommitted, D3, A4) == (1, 1),
                  "Both related writes are visible inside an uncommitted connection transaction.")
        with engine.connect() as observer:
            check(uncommitted.closed and pair_counts(observer, D3, A4) == (0, 0),
                  "Closing engine.connect without commit rolls back both related writes.")

        with engine.begin() as successful:
            register_pair(successful, D2, A3, "ECE", "PC-003", PAYLOAD_NAME)
            check(successful.in_transaction() and pair_counts(successful, D2, A3) == (1, 1),
                  "engine.begin provides one transaction for the department and its linked asset.")
        with engine.connect() as observer:
            check(successful.closed and pair_counts(observer, D2, A3) == (1, 1)
                  and observer.execute(LOOKUP, {"asset_code": "PC-003"}).one() == ("PC-003", PAYLOAD_NAME),
                  "Successful engine.begin exit commits both rows and preserves quoted input exactly as data.")

        try:
            with engine.begin() as aborted:
                register_pair(aborted, D4, A5, "CIVIL", "APP-ROLLBACK", "Aborted Computer")
                check(pair_counts(aborted, D4, A5) == (1, 1),
                      "Both inserts actually succeed before the deliberate application exception.")
                raise InjectedFailure("Stop after both related writes")
        except InjectedFailure:
            check(aborted.closed, "The application exception propagates outside engine.begin and closes its Connection.")
        else:
            raise AssertionError("The deliberate application exception did not propagate")
        with engine.connect() as observer:
            check(pair_counts(observer, D4, A5) == (0, 0),
                  "A propagated application exception rolls back both successful inserts.")

        try:
            with engine.begin() as rejected:
                register_pair(rejected, D5, A6, "EEE", "PC-001", "Duplicate Computer")
        except IntegrityError as exc:
            check(isinstance(exc.orig, psycopg.errors.UniqueViolation) and exc.orig.sqlstate == "23505"
                  and exc.orig.diag.constraint_name == "uq_step14_assets_code" and rejected.closed,
                  "A duplicate asset code propagates its PostgreSQL 23505 constraint error outside the transaction.")
            print("Expected database error: SQLSTATE=23505; constraint=uq_step14_assets_code")
        else:
            raise AssertionError("The duplicate business identifier was accepted")
        with engine.connect() as observer:
            check(pair_counts(observer, D5, A6) == (0, 0),
                  "When the second insert fails, the first department insert is rolled back too.")
            rows = observer.execute(text("""SELECT a.asset_code, a.name, d.code
                FROM college_step14.assets AS a JOIN college_step14.departments AS d ON d.id = a.department_id
                ORDER BY a.asset_code COLLATE "C"
                """)).all()
            print("Committed final rows:", rows)
            check(rows == [("PC-001", "Zebra Computer", "CSE"), ("PC-002", "Alpha Computer", "CSE"),
                           ("PC-003", PAYLOAD_NAME, "ECE")],
                  "Only the original two assets and the successfully committed linked asset remain.")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)
        engine.dispose()
    check(driver_connection is not None and driver_connection.closed and engine.pool.checkedout() == 0,
          "All Core contexts return their resources and final Engine disposal closes the physical connection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    main(parser.parse_args().run_id)
