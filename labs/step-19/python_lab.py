"""Predict and assert ORM instance states and unit-of-work collections."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import event, insert, inspect, select, text
from sqlalchemy.schema import CreateSchema

from college_maintenance.database import engine
from labs.shared.column_models import Asset, AssetCategory, Base, Department
from college_maintenance.sessions import SessionFactory
from labs.shared.observations import statements_by_phase

SCHEMA = "college_step19"
STATES = ("transient", "pending", "persistent", "deleted", "detached")


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def observe(label, asset, session, expected, *, new=False, dirty=False, queued_delete=False):
    state = inspect(asset)
    snapshot = {name: getattr(state, name) for name in STATES}
    membership = {"new": asset in session.new, "dirty": asset in session.dirty,
                  "delete_queue": asset in session.deleted}
    print(f"State {label}: {snapshot}; collections={membership}; identity={state.identity}; was_deleted={state.was_deleted}")
    check(snapshot == {name: name == expected for name in STATES}
          and membership == {"new": new, "dirty": dirty, "delete_queue": queued_delete},
          f"{label}: state is {expected} and all three unit-of-work memberships match the prediction.")
    return state


def main(run_id):
    check(version("SQLAlchemy") == "2.1.6" and version("psycopg") == "3.3.6",
          "Lifecycle observations reuse the pinned SQLAlchemy and psycopg versions.")
    lab_engine = engine.execution_options(schema_translate_map={None: SCHEMA})
    sessions, trace = [], []
    counts = {"checkout": 0, "checkin": 0}
    phase = "setup"
    driver = None

    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        kind = statement.lstrip().split(None, 1)[0].upper()
        if kind in {"SELECT", "INSERT", "UPDATE", "DELETE"} and f"{SCHEMA}.assets" in statement:
            trace.append((phase, kind))

    def checkout(connection, record, proxy):
        counts["checkout"] += 1

    def checkin(connection, record):
        counts["checkin"] += 1

    def new_session():
        session = SessionFactory(bind=lab_engine)
        sessions.append(session)
        return session

    event.listen(engine, "before_cursor_execute", before_cursor)
    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)
    try:
        with new_session() as unused:
            check(unused.get_bind() is lab_engine and not unused.in_transaction() and engine.pool.checkedout() == 0,
                  "The lifecycle lab reuses the shared factory and pool without an unused Session checkout.")
        with lab_engine.begin() as connection:
            identity = connection.execute(text("""SELECT current_database(), current_user,
                current_setting('server_version_num')::integer, pg_backend_pid(),
                to_regnamespace('college_step19') IS NULL""")).one()
            check(identity[0:2] == ("college_learning", "college_learner") and 180000 <= identity[2] < 190000 and identity[4],
                  "The PostgreSQL 18 learner connection has a free Step 19 study namespace.")
            driver = connection.connection.driver_connection
            connection.execute(CreateSchema(SCHEMA))
            Base.metadata.create_all(connection)
            connection.execute(text("""CREATE TABLE college_step19.lab_run (
                run_id uuid PRIMARY KEY, writer_backend_pid integer NOT NULL, survivor_id uuid)"""))
            department_id = connection.execute(insert(Department.__table__).values(code="CSE", name="Computer Science").returning(Department.id)).scalar_one()
            category_id = connection.execute(insert(AssetCategory.__table__).values(code="COMPUTER", name="Computer").returning(AssetCategory.id)).scalar_one()
            connection.execute(text("INSERT INTO college_step19.lab_run VALUES (:run, :pid, NULL)"), {"run": run_id, "pid": identity[3]})
        print(f"writer_backend_pid={identity[3]}")

        def asset(code):
            return Asset(asset_code=code, name="Lifecycle Computer", department_id=department_id,
                         category_id=category_id, location="Original Lab")

        phase = "lifecycle"
        with new_session() as session:
            disposable = asset("LIFE-TEMP")
            state = observe("constructed", disposable, session, "transient")
            check(state.session is None and state.identity is None and disposable.id is None and not trace,
                  "Construction has no database identity, Session association, generated ID, or asset SQL.")
            session.add(disposable)
            state = observe("added", disposable, session, "pending", new=True)
            check(state.session is session and state.identity is None and not trace,
                  "Add queues the pending instance without issuing an asset INSERT.")
            session.flush()
            state = observe("insert flushed", disposable, session, "persistent")
            disposable_id = disposable.id
            check(isinstance(disposable_id, UUID) and state.identity == (disposable_id,)
                  and session.identity_map[state.key] is disposable and disposable.status == "active",
                  "The inserted object has its generated identity, server default, and identity-map entry.")
            disposable.location = "Changed Lab"
            state = observe("location assigned", disposable, session, "persistent", dirty=True)
            history = state.attrs.location.history
            check(list(history.added) == ["Changed Lab"] and list(history.deleted) == ["Original Lab"]
                  and session.is_modified(disposable),
                  "Attribute history records the original and new location before the unit of work writes it.")
            session.flush()
            observe("update flushed", disposable, session, "persistent")
            disposable.location = "Changed Lab"
            observe("same value assigned", disposable, session, "persistent", dirty=True)
            check(not session.is_modified(disposable), "Dirty membership can be optimistic even when there is no net column change.")
            before_noop = len(trace)
            session.flush()
            check(len(trace) == before_noop and disposable not in session.dirty,
                  "Flushing the same-value assignment clears dirty membership without another UPDATE.")
            session.delete(disposable)
            observe("delete requested", disposable, session, "persistent", queued_delete=True)
            session.flush()
            state = observe("delete flushed", disposable, session, "deleted")
            check(state.session is session and state.was_deleted and disposable not in session and state.key not in session.identity_map,
                  "A flushed deleted object retains its Session association but leaves Session membership and the identity map.")
            session.commit()
            state = observe("delete committed", disposable, session, "detached")
            check(state.session is None and state.identity == (disposable_id,) and state.was_deleted,
                  "Commit detaches the deleted object while retaining its identity and deletion history.")

        phase = "survivor"
        with new_session() as seed:
            survivor = asset("LIFE-KEEP")
            seed.add(survivor)
            seed.flush()
            survivor_id = survivor.id
            seed.execute(text("UPDATE college_step19.lab_run SET survivor_id = :id WHERE run_id = :run"), {"id": survivor_id, "run": run_id})
            seed.commit()
            observe("insert committed", survivor, seed, "persistent")
        state = observe("Session closed", survivor, seed, "detached")
        check(state.session is None and state.identity == (survivor_id,),
              "Closing detaches a surviving asset without deleting its committed row.")

        phase = "delete_rollback"
        with new_session() as undo:
            restored = undo.get(Asset, survivor_id)
            observe("existing row loaded", restored, undo, "persistent")
            undo.delete(restored)
            undo.flush()
            observe("existing delete flushed", restored, undo, "deleted")
            undo.rollback()
            state = observe("existing delete rolled back", restored, undo, "persistent")
            check(not state.was_deleted and state.session is undo and state.identity == (survivor_id,),
                  "Rollback restores a previously committed deleted object to persistent state and clears was_deleted.")

        phase = "pending_rollback"
        with new_session() as cancel:
            pending = asset("LIFE-CANCEL")
            cancel.add(pending)
            cancel.rollback()
            state = observe("pending insert rolled back", pending, cancel, "transient")
            check(state.session is None and state.identity is None and pending.id is None,
                  "Rolling back an unflushed new object returns it to transient state without a generated ID.")

        phase = "final_read"
        with new_session() as final:
            rows = [(item.id, item.asset_code, item.location) for item in final.scalars(select(Asset).order_by(Asset.asset_code))]
            check(rows == [(survivor_id, "LIFE-KEEP", "Original Lab")] and final.get(Asset, disposable_id) is None,
                  "Fresh ORM reads find only the original surviving asset; the disposable create/update/delete left no row.")
        print("Final lifecycle rows:", rows)
        expected = {"lifecycle": ["INSERT", "UPDATE", "DELETE"], "survivor": ["INSERT"],
                    "delete_rollback": ["SELECT", "DELETE"], "pending_rollback": [], "final_read": ["SELECT", "SELECT"]}
        actual = statements_by_phase(trace, expected)
        print("Observed asset SQL:", actual)
        check(actual == expected, "Observed SQL agrees with lifecycle predictions, including both branches that issue no write.")
        check(all(not item.in_transaction() and not item.identity_map and not item.new and not item.dirty and not item.deleted for item in sessions)
              and counts["checkout"] == counts["checkin"] and engine.pool.checkedout() == 0,
              "Every lifecycle Session releases its unit-of-work collections, transaction, and pool checkout.")
    finally:
        for session in sessions:
            session.close()
        event.remove(engine, "before_cursor_execute", before_cursor)
        event.remove(engine, "checkout", checkout)
        event.remove(engine, "checkin", checkin)
        engine.dispose()
    check(driver is not None and driver.closed and engine.pool.checkedout() == 0,
          "Engine disposal closes the physical lifecycle writer after all Session exits.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    main(parser.parse_args().run_id)
