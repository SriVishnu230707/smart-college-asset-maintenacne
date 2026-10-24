"""Prove flush visibility, autoflush boundaries, and failed-Session recovery."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg
from sqlalchemy import event, insert, inspect, select, text
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.schema import CreateSchema

from college_maintenance.database import engine
from college_maintenance.models import Asset, AssetCategory, Base, Department, MaintenanceTicket, User
from college_maintenance.sessions import SessionFactory

SCHEMA = "college_step20"


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main(run_id):
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "Flush and recovery observations reuse the pinned SQLAlchemy and psycopg versions.")
    lab_engine = engine.execution_options(schema_translate_map={None: SCHEMA})
    sessions, trace = [], []
    counts = {"checkout": 0, "checkin": 0}
    phase = "setup"
    driver = observer = None

    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        kind = statement.lstrip().split(None, 1)[0].upper()
        if kind in {"SELECT", "INSERT", "UPDATE", "DELETE"} and f"{SCHEMA}.maintenance_tickets" in statement:
            trace.append((phase, kind))

    def checkout(connection, record, proxy):
        counts["checkout"] += 1

    def checkin(connection, record):
        counts["checkin"] += 1

    def new_session(**options):
        session = SessionFactory(bind=lab_engine, **options)
        sessions.append(session)
        return session

    def observer_rows(sql, parameters=()):
        with observer.cursor() as cursor:
            cursor.execute(sql, parameters)
            return cursor.fetchall()

    def count_title(title):
        return observer_rows("SELECT count(*) FROM college_step20.maintenance_tickets WHERE title = %s", (title,))[0][0]

    event.listen(engine, "before_cursor_execute", before_cursor)
    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)
    try:
        with lab_engine.begin() as connection:
            identity = connection.execute(text("""SELECT current_database(), current_user,
                current_setting('server_version_num')::integer, pg_backend_pid(),
                to_regnamespace('college_step20') IS NULL""")).one()
            check(identity[0:2] == ("college_learning", "college_learner") and 180000 <= identity[2] < 190000 and identity[4],
                  "The PostgreSQL 18 learner connection has a free Step 20 study namespace.")
            driver = connection.connection.driver_connection
            connection.execute(CreateSchema(SCHEMA))
            Base.metadata.create_all(connection)
            connection.execute(text("""CREATE TABLE college_step20.lab_run (
                run_id uuid PRIMARY KEY, writer_backend_pid integer NOT NULL, observer_backend_pid integer,
                committed_ticket_id uuid, noauto_ticket_id uuid, recovered_ticket_id uuid)"""))
            department_id = connection.execute(insert(Department.__table__).values(code="CSE", name="Computer Science").returning(Department.id)).scalar_one()
            category_id = connection.execute(insert(AssetCategory.__table__).values(code="COMPUTER", name="Computer").returning(AssetCategory.id)).scalar_one()
            reporter_id = connection.execute(insert(User.__table__).values(email="reporter@example.test", display_name="Flush Reporter",
                password_hash="synthetic_flush_lab_hash", role="student", department_id=department_id).returning(User.id)).scalar_one()
            asset_id = connection.execute(insert(Asset.__table__).values(asset_code="FLUSH-PC", name="Flush Computer",
                department_id=department_id, category_id=category_id, location="Original Lab").returning(Asset.id)).scalar_one()
            connection.execute(text("INSERT INTO college_step20.lab_run (run_id, writer_backend_pid) VALUES (:run, :pid)"),
                               {"run": run_id, "pid": identity[3]})
        print(f"writer_backend_pid={identity[3]}")

        # The shared pool has one slot. Use a separate driver connection for a
        # genuinely simultaneous observer, rather than checking it out twice.
        observer = psycopg.connect(**engine.url.translate_connect_args(username="user", database="dbname"),
            autocommit=True, connect_timeout=5, options="-c statement_timeout=5000 -c timezone=UTC",
            application_name="college_step20_observer")
        with observer.cursor() as cursor:
            cursor.execute("SET default_transaction_isolation TO 'read committed'")
            cursor.execute("SET default_transaction_read_only TO on")
        observed_identity = observer_rows("SELECT current_database(), current_user, pg_backend_pid(), current_setting('transaction_isolation'), current_setting('transaction_read_only')")[0]
        check(observed_identity[0:2] == ("college_learning", "college_learner") and observed_identity[2] != identity[3]
              and observed_identity[3:] == ("read committed", "on") and observer.autocommit,
              "A distinct read-only psycopg backend observes fresh READ COMMITTED statements without consuming the shared pool slot.")
        print(f"observer_backend_pid={observed_identity[2]}")

        def ticket(title, priority="high"):
            return MaintenanceTicket(asset_id=asset_id, reported_by_id=reporter_id, department_id=department_id,
                                     title=title, description="Original description", priority=priority)

        phase = "explicit_commit"
        with new_session() as writer:
            committed = ticket("COMMIT-TICKET")
            writer.add(committed)
            check(committed in writer.new and committed.id is None and not trace and count_title("COMMIT-TICKET") == 0,
                  "Adding a ticket queues it in memory; neither INSERT nor independent visibility occurs yet.")
            writer.flush()
            committed_id = committed.id
            check(isinstance(committed_id, UUID) and inspect(committed).persistent and committed.status == "open"
                  and committed.created_at.utcoffset() is not None and writer.in_transaction(),
                  "Explicit flush inserts the ticket and obtains UUID/defaults while its transaction remains open.")
            check(writer.scalar(select(MaintenanceTicket.id).where(MaintenanceTicket.id == committed_id)) == committed_id,
                  "The writing Session can select its own flushed ticket before commit.")
            check(count_title("COMMIT-TICKET") == 0, "The independent backend cannot see the successfully flushed ticket before commit.")
            writer.execute(text("""UPDATE college_step20.lab_run SET observer_backend_pid = :pid,
                committed_ticket_id = :id WHERE run_id = :run"""), {"pid": observed_identity[2], "id": committed_id, "run": run_id})
            writer.commit()
            check(not writer.in_transaction() and count_title("COMMIT-TICKET") == 1,
                  "Commit releases the write transaction and makes its ticket independently visible.")
        print("Visibility COMMIT-TICKET: after add=0; after flush=0; after commit=1")

        phase = "explicit_rollback"
        with new_session() as writer:
            rolled_back = ticket("ROLLBACK-TICKET")
            writer.add(rolled_back)
            writer.flush()
            rolled_back_id = rolled_back.id
            check(writer.scalar(select(MaintenanceTicket.id).where(MaintenanceTicket.id == rolled_back_id)) == rolled_back_id
                  and count_title("ROLLBACK-TICKET") == 0,
                  "A second flushed ticket exists for its writer while remaining hidden from the independent reader.")
            writer.rollback()
            check(count_title("ROLLBACK-TICKET") == 0 and writer.get(MaintenanceTicket, rolled_back_id) is None,
                  "Rollback removes the successfully flushed ticket; its generated ID did not make the insert durable.")
        print("Visibility ROLLBACK-TICKET: writer after flush=1; observer after flush=0; observer after rollback=0")

        phase = "autoflush"
        with new_session() as writer:
            automatic = ticket("AUTO-TICKET")
            writer.add(automatic)
            check(automatic in writer.new, "Default autoflush begins with the new ticket still pending.")
            check(writer.scalars(select(MaintenanceTicket).where(MaintenanceTicket.title == "AUTO-TICKET")).one() is automatic
                  and inspect(automatic).persistent and count_title("AUTO-TICKET") == 0,
                  "An ORM SELECT autoflushes INSERT first, but that query does not commit the ticket.")
            writer.rollback()
        check(count_title("AUTO-TICKET") == 0, "The autoflushed ticket also disappears on rollback.")

        phase = "no_autoflush"
        with new_session() as writer:
            controlled = ticket("CONTROLLED-TICKET")
            writer.add(controlled)
            with writer.no_autoflush:
                check(writer.scalar(select(MaintenanceTicket.id).where(MaintenanceTicket.title == "CONTROLLED-TICKET")) is None
                      and controlled in writer.new and controlled.id is None,
                      "The no_autoflush block suppresses query-triggered INSERT and leaves the ticket pending.")
                writer.flush()
                check(inspect(controlled).persistent and count_title("CONTROLLED-TICKET") == 0,
                      "Explicit flush still writes inside no_autoflush without making the row independently visible.")
            writer.rollback()

        phase = "commit_autoflush_disabled"
        with new_session(autoflush=False) as writer:
            noauto = ticket("COMMIT-NOAUTO")
            writer.add(noauto)
            check(writer.scalar(select(MaintenanceTicket.id).where(MaintenanceTicket.title == "COMMIT-NOAUTO")) is None
                  and noauto in writer.new,
                  "Disabling Session autoflush suppresses the automatic flush before an ORM query.")
            writer.commit()
            noauto_id = inspect(noauto).identity[0]
            check(isinstance(noauto_id, UUID) and count_title("COMMIT-NOAUTO") == 1,
                  "Commit flushes pending work even with autoflush disabled and the observer sees the committed ticket.")
        with lab_engine.begin() as connection:
            connection.execute(text("UPDATE college_step20.lab_run SET noauto_ticket_id = :id WHERE run_id = :run"),
                               {"id": noauto_id, "run": run_id})

        phase = "failed_flush"
        with new_session() as recovery_session:
            original = recovery_session.get(MaintenanceTicket, committed_id)
            original.description = "Must roll back"
            recovery_session.flush()
            earlier = ticket("BEFORE-ERROR")
            recovery_session.add(earlier)
            recovery_session.flush()
            invalid = ticket("INVALID-PRIORITY", "urgent")
            recovery_session.add(invalid)
            try:
                recovery_session.flush()
            except IntegrityError as exc:
                check(exc.orig.sqlstate == "23514" and exc.orig.diag.constraint_name == "ck_maintenance_tickets_priority",
                      "The deliberate invalid priority fails flush with SQLSTATE 23514 and the named ticket CHECK.")
                print("Expected ORM database error: SQLSTATE=23514; constraint=ck_maintenance_tickets_priority")
            else:
                raise AssertionError("Invalid priority was accepted")
            check(not recovery_session.is_active and recovery_session.in_transaction(),
                  "After failed flush the Session is inactive and still requires its logical transaction to be rolled back.")
            check(count_title("BEFORE-ERROR") == count_title("INVALID-PRIORITY") == 0
                  and observer_rows("SELECT description FROM college_step20.maintenance_tickets WHERE id = %s", (committed_id,)) == [("Original description",)],
                  "The failed flush undoes both the earlier successful INSERT and UPDATE in that transaction.")
            before_blocked = len(trace)
            try:
                recovery_session.scalar(select(MaintenanceTicket.id))
            except PendingRollbackError:
                check(len(trace) == before_blocked, "Reusing the failed Session before rollback raises PendingRollbackError without sending SQL.")
                print("Expected Session error: PendingRollbackError before explicit rollback")
            else:
                raise AssertionError("The failed Session accepted a query without rollback")
            recovery_session.rollback()
            check(recovery_session.is_active and not recovery_session.in_transaction()
                  and not recovery_session.new and not recovery_session.dirty and not recovery_session.deleted,
                  "Explicit Session.rollback resets the failed logical transaction and its pending work.")
            phase = "recovery"
            check(recovery_session.get(MaintenanceTicket, committed_id).description == "Original description"
                  and recovery_session.scalar(select(MaintenanceTicket.id).where(MaintenanceTicket.title == "BEFORE-ERROR")) is None,
                  "The same recovered Session reads the original committed values and no aborted ticket.")
            recovered = ticket("RECOVERED", "medium")
            recovery_session.add(recovered)
            recovery_session.flush()
            recovered_id = recovered.id
            recovery_session.execute(text("UPDATE college_step20.lab_run SET recovered_ticket_id = :id WHERE run_id = :run"),
                                     {"id": recovered_id, "run": run_id})
            recovery_session.commit()
            check(count_title("RECOVERED") == 1, "That same Session successfully commits a valid recovery ticket after rollback.")

        phase = "final_read"
        with new_session() as final:
            rows = [(item.id, item.title, item.priority, item.status, item.description)
                    for item in final.scalars(select(MaintenanceTicket).order_by(MaintenanceTicket.title))]
            expected_rows = [(noauto_id, "COMMIT-NOAUTO", "high", "open", "Original description"),
                             (committed_id, "COMMIT-TICKET", "high", "open", "Original description"),
                             (recovered_id, "RECOVERED", "medium", "open", "Original description")]
            check(rows == expected_rows, "A fresh ORM Session finds exactly the three committed tickets with their expected IDs and values.")
        check(observer_rows("SELECT id, title, priority, status, description FROM college_step20.maintenance_tickets ORDER BY title") == rows,
              "The independent driver observer agrees with every final ORM ticket value.")
        print("Final committed tickets:", rows)
        expected_sql = {"explicit_commit": ["INSERT", "SELECT"], "explicit_rollback": ["INSERT", "SELECT", "SELECT"],
                        "autoflush": ["INSERT", "SELECT"], "no_autoflush": ["SELECT", "INSERT"],
                        "commit_autoflush_disabled": ["SELECT", "INSERT"], "failed_flush": ["SELECT", "UPDATE", "INSERT", "INSERT"],
                        "recovery": ["SELECT", "SELECT", "INSERT"], "final_read": ["SELECT"]}
        actual = {label: [kind for recorded, kind in trace if recorded == label] for label in expected_sql}
        print("Observed ticket SQL:", actual)
        check(actual == expected_sql, "Cursor observations prove explicit, automatic, suppressed, failed, and recovered flush statement ordering.")
        check(all(not item.in_transaction() and not item.identity_map and not item.new and not item.dirty and not item.deleted for item in sessions)
              and counts["checkout"] == counts["checkin"] and engine.pool.checkedout() == 0,
              "All write, read, rollback, and recovered Sessions return their transactions and pool resources.")
    finally:
        for session in sessions:
            session.close()
        if observer is not None:
            observer.close()
        event.remove(engine, "before_cursor_execute", before_cursor)
        event.remove(engine, "checkout", checkout)
        event.remove(engine, "checkin", checkin)
        engine.dispose()
    check(driver is not None and driver.closed and observer is not None and observer.closed and engine.pool.checkedout() == 0,
          "The independent observer and physical writer are both closed after all Session exits.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    main(parser.parse_args().run_id)
