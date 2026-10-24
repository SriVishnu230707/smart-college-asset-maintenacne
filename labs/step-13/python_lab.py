"""Trace a read-only Core probe through the Engine to a real psycopg cursor."""

import io
import logging
import platform
import sys
from importlib.metadata import version
from pathlib import Path

# Direct execution from labs/step-13 must also work outside the project cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg
from sqlalchemy import event, func, literal, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DataError
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from college_maintenance.database import engine


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> None:
    print(f"Python {platform.python_version()}; SQLAlchemy {version('SQLAlchemy')}; "
          f"psycopg {version('psycopg')}; psycopg-binary {version('psycopg-binary')}")
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6"
          and version("psycopg-binary") == "3.3.6", "The SQLAlchemy and psycopg versions match the pinned requirements.")
    check(isinstance(engine, Engine) and not isinstance(engine, Session),
          "The application object is an Engine, not an ORM Session.")
    check(engine.dialect.name == "postgresql" and engine.dialect.driver == "psycopg"
          and engine.dialect.dbapi is psycopg, "The PostgreSQL dialect selects the psycopg 3 DBAPI module explicitly.")
    check(isinstance(engine.pool, QueuePool) and engine.pool.size() == 1
          and engine.pool.checkedin() == 0 and engine.pool.checkedout() == 0,
          "Engine construction is lazy: its one-slot QueuePool contains no physical connection yet.")
    print("URL (password hidden):", engine.url.render_as_string(hide_password=True))

    engine.echo = True  # Enable SQL logging only for this local learning probe.
    counts = {"connect": 0, "checkout": 0, "checkin": 0}
    trace = []
    replies = []

    def connected(dbapi_connection, connection_record):
        counts["connect"] += 1

    def checked_out(dbapi_connection, connection_record, connection_proxy):
        counts["checkout"] += 1

    def checked_in(dbapi_connection, connection_record):
        counts["checkin"] += 1

    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        if "/* step13_trace */" in statement:
            trace.append((statement, dict(parameters), cursor, cursor.connection.info.backend_pid))
            print(f"TRACE driver cursor: {type(cursor).__module__}.{type(cursor).__name__}")
            print("TRACE statement:", statement)
            print("TRACE synthetic probe parameters:", dict(parameters))

    def after_cursor(connection, cursor, statement, parameters, context, executemany):
        if "/* step13_trace */" in statement:
            replies.append([column.name for column in cursor.description])

    event.listen(engine, "connect", connected)
    event.listen(engine, "checkout", checked_out)
    event.listen(engine, "checkin", checked_in)
    event.listen(engine, "before_cursor_execute", before_cursor)
    event.listen(engine, "after_cursor_execute", after_cursor)
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    logger = logging.getLogger("sqlalchemy.engine.Engine")
    logger.addHandler(handler)
    driver_connection = None

    try:
        statement = select(
            literal("step-13").label("lesson"),
            func.current_database().label("database_name"),
            func.current_user().label("role_name"),
            func.pg_backend_pid().label("backend_pid"),
            func.current_setting("application_name").label("application_name"),
            func.current_setting("TimeZone").label("timezone"),
            func.current_setting("server_version_num").label("server_version_num"),
        ).prefix_with("/* step13_trace */")
        compiled = statement.compile(dialect=engine.dialect)
        print("TRACE Core expression compiled for PostgreSQL:", str(compiled))
        check("step-13" not in str(compiled) and "step-13" in compiled.params.values()
              and counts["connect"] == 0,
              "Compiling the Core expression creates bound SQL without opening a database connection.")

        with engine.connect() as first:
            check(isinstance(first, Connection) and not isinstance(first, Session)
                  and first.engine is engine and engine.pool.checkedout() == 1,
                  "Engine.connect borrows a SQLAlchemy Connection from the same Engine.")
            driver_connection = first.connection.driver_connection
            check(isinstance(driver_connection, psycopg.Connection) and not driver_connection.closed,
                  "The SQLAlchemy Connection wraps a live psycopg physical connection.")
            row = first.execute(statement).one()._mapping
            print("TRACE PostgreSQL result:", dict(row))
            print(f"engine_backend_pid={row['backend_pid']}")
            check(row["database_name"] == "college_learning" and row["role_name"] == "college_learner"
                  and row["application_name"] == "college_step13" and row["timezone"] == "UTC"
                  and 180000 <= int(row["server_version_num"]) < 190000,
                  "The server confirms PostgreSQL 18, the learner identity, application name, and UTC configuration.")
            check(row["lesson"] == "step-13" and row["backend_pid"] == driver_connection.info.backend_pid,
                  "The server-returned probe and backend PID match the actual driver connection.")
            check(len(trace) == 1 and trace[0][0] == str(compiled) and trace[0][1] == compiled.params
                  and isinstance(trace[0][2], psycopg.Cursor) and trace[0][3] == row["backend_pid"],
                  "The cursor event observes the compiled SQL and parameters at the psycopg execution boundary.")
            check(replies == [list(row.keys())],
                  "The after-cursor event observes the server result columns before SQLAlchemy exposes the row.")

            try:
                first.execute(text("SELECT 1 / 0"))
            except DataError as exc:
                check(isinstance(exc.orig, psycopg.errors.DivisionByZero) and exc.orig.sqlstate == "22012"
                      and not exc.connection_invalidated,
                      "A server error reaches SQLAlchemy as DataError with the original psycopg SQLSTATE 22012.")
                print("Expected error path: PostgreSQL 22012 -> psycopg DivisionByZero -> SQLAlchemy DataError")
            else:
                raise AssertionError("The invalid division query was accepted")
            first.rollback()
            check(first.execute(select(literal("recovered"))).scalar_one() == "recovered",
                  "Explicit rollback recovers the connection after the deliberate server error.")

        check(first.closed and not driver_connection.closed and engine.pool.checkedout() == 0
              and engine.pool.checkedin() == 1,
              "Closing the SQLAlchemy wrapper returns the physical connection to the pool instead of closing it.")
        with engine.connect() as second:
            check(second is not first and second.engine is engine,
                  "A second checkout has a new Connection wrapper but still uses the one application Engine.")
            check(second.connection.driver_connection is driver_connection
                  and second.execute(select(func.pg_backend_pid())).scalar_one() == row["backend_pid"]
                  and counts["connect"] == 1,
                  "Sequential checkouts reuse the same psycopg connection and PostgreSQL backend.")
        check(counts == {"connect": 1, "checkout": 2, "checkin": 2} and engine.pool.checkedout() == 0,
              "Pool events record one physical connection and two balanced checkout/checkin pairs.")
        logs = log_buffer.getvalue()
        check("SELECT /* step13_trace */" in logs and "BEGIN (implicit)" in logs and "ROLLBACK" in logs,
              "Local Engine logging records real SQL and transaction boundaries.")
        check(engine.echo and engine.hide_parameters and "SQL parameters hidden due to hide_parameters=True" in logs,
              "SQL logging is enabled for the lab while automatic parameter-value logging stays hidden.")
        check(engine.url.password not in logs and engine.url.password not in str(engine.url)
              and "***" in engine.url.render_as_string(hide_password=True),
              "The connection password is absent from the captured SQL log and rendered URL.")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)
        event.remove(engine, "after_cursor_execute", after_cursor)
        event.remove(engine, "connect", connected)
        event.remove(engine, "checkout", checked_out)
        event.remove(engine, "checkin", checked_in)
        engine.dispose()
        logger.removeHandler(handler)
        handler.close()
    check(driver_connection is not None and driver_connection.closed and engine.pool.checkedout() == 0,
          "Engine.dispose closes the returned physical connection after the lab.")


if __name__ == "__main__":
    main()
