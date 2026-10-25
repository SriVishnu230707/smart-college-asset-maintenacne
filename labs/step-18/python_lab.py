"""Prove short-lived ORM Session CRUD, emitted SQL, and cleanup on every exit."""

import argparse
import io
import logging
import sys
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import event, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema

from college_maintenance.database import engine
from labs.shared.column_models import Asset, AssetCategory, Base, Department, MaintenanceTicket, User
from college_maintenance.sessions import SessionFactory
from labs.shared.observations import statements_by_phase
from asset_crud import create_asset, delete_fixture_asset, get_asset, list_assets, update_asset_location

SCHEMA = "college_step18"
MISSING_ID = UUID("40000000-0000-4000-8000-999999999999")


class InjectedFailure(RuntimeError):
    """Deliberate application error after successful ORM writes."""


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def released(session):
    # Session.close resets by default; there is no public Session.closed flag.
    return not session.in_transaction() and not session.identity_map and engine.pool.checkedout() == 0


def main(run_id):
    print(f"SQLAlchemy {version('SQLAlchemy')}; psycopg {version('psycopg')}; run_id={run_id}")
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "The ORM persistence lab reuses the pinned SQLAlchemy and psycopg versions.")
    with SessionFactory() as probe:
        check(isinstance(probe, Session) and probe.get_bind() is engine and not probe.in_transaction()
              and probe.autoflush and probe.expire_on_commit and engine.pool.checkedin() == 0,
              "The shared sessionmaker creates a lazy Session bound to the one application Engine with standard defaults.")

    previous_echo = engine.echo
    engine.echo = True
    lab_engine = engine.execution_options(schema_translate_map={None: SCHEMA})
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    logger = logging.getLogger("sqlalchemy.engine.Engine")
    logger.addHandler(handler)
    phase = "setup"
    sql_trace = []
    pool_counts = {"checkout": 0, "checkin": 0}
    used_sessions = []
    driver_connection = None

    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        kind = statement.lstrip().split(None, 1)[0].upper()
        if kind in {"SELECT", "INSERT", "UPDATE", "DELETE"} and f"{SCHEMA}.assets" in statement:
            sql_trace.append((phase, kind))

    def checkout(dbapi_connection, record, proxy):
        pool_counts["checkout"] += 1

    def checkin(dbapi_connection, record):
        pool_counts["checkin"] += 1

    def new_session():
        session = SessionFactory(bind=lab_engine)
        used_sessions.append(session)
        return session

    event.listen(engine, "before_cursor_execute", before_cursor)
    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)
    try:
        with lab_engine.begin() as setup:
            identity = setup.execute(text("""SELECT current_database(), current_user,
                current_setting('server_version_num')::integer, pg_backend_pid(),
                to_regnamespace('college_step18') IS NULL""")).one()
            check(identity[0] == "college_learning" and identity[1] == "college_learner"
                  and 180000 <= identity[2] < 190000 and identity[4],
                  "The PostgreSQL 18 learner connection has a free disposable Step 18 namespace.")
            driver_connection = setup.connection.driver_connection
            setup.execute(CreateSchema(SCHEMA))
            Base.metadata.create_all(setup)
            setup.execute(text("""CREATE TABLE college_step18.lab_run (
                run_id uuid PRIMARY KEY, writer_backend_pid integer NOT NULL,
                protected_asset_id uuid NOT NULL, created_asset_id uuid)"""))
            department_ids = {}
            for code, name in (("CSE", "Computer Science"), ("ECE", "Electronics")):
                department_ids[code] = setup.execute(insert(Department.__table__).values(code=code, name=name).returning(Department.id)).scalar_one()
            category_id = setup.execute(insert(AssetCategory.__table__).values(code="COMPUTER", name="Computer").returning(AssetCategory.id)).scalar_one()
            reporter_id = setup.execute(insert(User.__table__).values(email="reporter@example.test", display_name="Lab Reporter",
                password_hash="synthetic_session_lab_hash", role="student", department_id=department_ids["ECE"]).returning(User.id)).scalar_one()
            protected_id = setup.execute(insert(Asset.__table__).values(asset_code="KEEP-001", name="Referenced Computer",
                department_id=department_ids["ECE"], category_id=category_id, location="Electronics Lab").returning(Asset.id)).scalar_one()
            setup.execute(insert(MaintenanceTicket.__table__).values(asset_id=protected_id, reported_by_id=reporter_id,
                department_id=department_ids["ECE"], title="Computer issue", description="Synthetic reference protection fixture", priority="high"))
            setup.execute(text("INSERT INTO college_step18.lab_run VALUES (:run, :pid, :protected, NULL)"),
                          {"run": run_id, "pid": identity[3], "protected": protected_id})
        print(f"writer_backend_pid={identity[3]}")

        phase = "create"
        with new_session() as created_session, created_session.begin():
            created = create_asset(created_session, asset_code="PC-001", name="Lab Computer",
                                   department_id=department_ids["CSE"], category_id=category_id, location="Computer Lab 1")
            temporary = create_asset(created_session, asset_code="LAB-TEMP", name="Temporary Computer",
                                     department_id=department_ids["CSE"], category_id=category_id)
            created_id, temporary_id = created.id, temporary.id
            check(isinstance(created_id, UUID) and created_id.version == 4 and temporary_id != created_id
                  and created.status == temporary.status == "active",
                  "Session.add and the create helper obtain generated UUIDs and server defaults on real Asset instances.")
            created_session.execute(text("UPDATE college_step18.lab_run SET created_asset_id = :id WHERE run_id = :run"),
                                    {"id": created_id, "run": run_id})
        check(released(created_session), "The successful write context commits and closes its Session, returning the pool checkout.")

        phase = "get"
        with new_session() as read_session:
            loaded = get_asset(read_session, created_id)
            check(isinstance(loaded, Asset) and loaded.id == created_id and loaded.asset_code == "PC-001"
                  and loaded.location == "Computer Lab 1",
                  "A fresh Session.get loads the committed row as an Asset, rather than a Core Row.")
        check(released(read_session), "The read-only Session context closes and releases its implicit transaction.")

        phase = "list"
        with new_session() as list_session:
            all_codes = [asset.asset_code for asset in list_assets(list_session)]
            department_codes = [asset.asset_code for asset in list_assets(list_session, department_ids["CSE"])]
            check(all_codes == ["KEEP-001", "LAB-TEMP", "PC-001"] and department_codes == ["LAB-TEMP", "PC-001"],
                  "Session.scalars(select(Asset)) returns ordered mapped objects and applies the requested department filter.")

        phase = "update"
        with new_session() as update_session, update_session.begin():
            updated = update_asset_location(update_session, created_id, "Computer Lab 2")
            check(updated is not None and updated.id == created_id and updated.location == "Computer Lab 2",
                  "Assigning a mapped location and flushing emits the ORM asset update.")

        phase = "delete"
        with new_session() as delete_session, delete_session.begin():
            check(delete_fixture_asset(delete_session, temporary_id),
                  "Session.delete removes the disposable temporary asset inside the caller's transaction.")

        phase = "missing"
        with new_session() as missing_session, missing_session.begin():
            check(get_asset(missing_session, MISSING_ID) is None
                  and update_asset_location(missing_session, MISSING_ID, "Nowhere") is None
                  and not delete_fixture_asset(missing_session, temporary_id),
                  "Missing gets and updates return None, and deleting an absent fixture returns False without a write.")

        phase = "no_commit"
        with new_session() as uncommitted_session:
            uncommitted = create_asset(uncommitted_session, asset_code="NO-COMMIT", name="Uncommitted Computer",
                                       department_id=department_ids["CSE"], category_id=category_id)
            check(isinstance(uncommitted.id, UUID), "A Session context can execute an INSERT before any explicit commit.")
        phase = "verify_no_commit"
        with new_session() as no_commit_observer:
            check(no_commit_observer.scalar(select(Asset.id).where(Asset.asset_code == "NO-COMMIT")) is None,
                  "Closing a Session context alone rolls back its pending write; it does not commit automatically.")

        phase = "application_failure"
        try:
            with new_session() as aborted_session, aborted_session.begin():
                update_asset_location(aborted_session, created_id, "Must Roll Back")
                create_asset(aborted_session, asset_code="APP-ROLLBACK", name="Aborted Computer",
                             department_id=department_ids["CSE"], category_id=category_id)
                raise InjectedFailure("Abort the operation after successful ORM writes")
        except InjectedFailure:
            check(released(aborted_session), "A propagated application error rolls back and closes the write Session.")
        else:
            raise AssertionError("The deliberate application error did not propagate")
        phase = "verify_application_failure"
        with new_session() as application_observer:
            check(get_asset(application_observer, created_id).location == "Computer Lab 2"
                  and application_observer.scalar(select(Asset.id).where(Asset.asset_code == "APP-ROLLBACK")) is None,
                  "A fresh Session finds neither the aborted location change nor the aborted inserted asset.")

        phase = "database_failure"
        try:
            with new_session() as rejected_session, rejected_session.begin():
                update_asset_location(rejected_session, created_id, "Before Duplicate Error")
                create_asset(rejected_session, asset_code="PC-001", name="Duplicate Computer",
                             department_id=department_ids["CSE"], category_id=category_id)
        except IntegrityError as exc:
            check(exc.orig.sqlstate == "23505" and exc.orig.diag.constraint_name == "uq_assets_asset_code"
                  and released(rejected_session),
                  "The duplicate-code 23505 escapes the operation after rollback and Session cleanup.")
            print("Expected ORM database error: SQLSTATE=23505; constraint=uq_assets_asset_code")
        else:
            raise AssertionError("The duplicate asset code was accepted")
        phase = "verify_database_failure"
        with new_session() as database_observer:
            check(get_asset(database_observer, created_id).location == "Computer Lab 2"
                  and database_observer.scalars(select(Asset).where(Asset.asset_code == "PC-001")).one().id == created_id,
                  "A new Session confirms the failed INSERT also rolled back its preceding successful UPDATE.")

        phase = "reference_failure"
        try:
            with new_session() as protected_session, protected_session.begin():
                delete_fixture_asset(protected_session, protected_id)
        except IntegrityError as exc:
            check(exc.orig.sqlstate == "23001" and exc.orig.diag.constraint_name == "fk_tickets_asset"
                  and released(protected_session),
                  "A referenced-asset delete raises 23001 while still rolling back and closing the Session.")
            print("Expected ORM database error: SQLSTATE=23001; constraint=fk_tickets_asset")
        else:
            raise AssertionError("A ticket-referenced asset was deleted")
        phase = "final_read"
        with new_session() as final_session:
            final_rows = [(asset.id, asset.asset_code, asset.name, asset.location, asset.status) for asset in list_assets(final_session)]
            check(final_rows == [(protected_id, "KEEP-001", "Referenced Computer", "Electronics Lab", "active"),
                                 (created_id, "PC-001", "Lab Computer", "Computer Lab 2", "active")]
                  and final_session.scalars(select(MaintenanceTicket)).one().asset_id == protected_id,
                  "Fresh ORM reads show the exact committed create/update/delete results and the preserved ticket reference.")
        print("Final committed ORM rows:", final_rows)
        phase = "raw_sql_observer"
        with lab_engine.connect() as observer:
            sql_rows = observer.execute(text("SELECT id, asset_code, name, location, status FROM college_step18.assets ORDER BY asset_code")).all()
            check(sql_rows == final_rows, "Independent Core SQL agrees with the final ORM object values after all Session exits.")

        expected_sql = {
            "create": ["INSERT", "INSERT"], "get": ["SELECT"], "list": ["SELECT", "SELECT"],
            "update": ["SELECT", "UPDATE"], "delete": ["SELECT", "DELETE"],
            "missing": ["SELECT", "SELECT", "SELECT"], "no_commit": ["INSERT"],
            "application_failure": ["SELECT", "UPDATE", "INSERT"],
            "database_failure": ["SELECT", "UPDATE", "INSERT"], "reference_failure": ["SELECT", "DELETE"],
        }
        actual_sql = statements_by_phase(sql_trace, expected_sql)
        print("Observed asset SQL by operation:", actual_sql)
        check(actual_sql == expected_sql, "Cursor observations identify the exact asset statements attempted by each ORM operation.")
        check(len({id(session) for session in used_sessions}) == len(used_sessions)
              and all(released(session) for session in used_sessions)
              and pool_counts["checkout"] == pool_counts["checkin"] and pool_counts["checkout"] > 1,
              "Every operation uses its own closed Session, with empty identity maps and balanced returned checkouts.")
        logged = log_buffer.getvalue()
        check(all(token in logged for token in ("BEGIN", "COMMIT", "ROLLBACK", "SELECT college_step18.assets", "INSERT INTO college_step18.assets",
                                                "UPDATE college_step18.assets", "DELETE FROM college_step18.assets")),
              "Local SQL logging includes ORM INSERT/SELECT/UPDATE/DELETE activity and transaction completion.")
        check(engine.hide_parameters and "SQL parameters hidden" in logged and engine.url.password not in logged
              and "synthetic_session_lab_hash" not in logged,
              "Automatic parameter logging stays hidden and the captured SQL log contains no learner credential or fixture hash.")
    finally:
        # Resource cleanup still runs when an assertion or unexpected error fails.
        for session in used_sessions:
            session.close()
        event.remove(engine, "before_cursor_execute", before_cursor)
        event.remove(engine, "checkout", checkout)
        event.remove(engine, "checkin", checkin)
        engine.dispose()
        engine.echo = previous_echo
        logger.removeHandler(handler)
    check(driver_connection is not None and driver_connection.closed and engine.pool.checkedout() == 0,
          "All Sessions return their resources before Engine disposal closes the physical writer connection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    main(parser.parse_args().run_id)
