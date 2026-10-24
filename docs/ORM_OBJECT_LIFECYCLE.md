# ORM object lifecycle and the unit of work

Step 19 follows real [Asset instances](../college_maintenance/models.py) through 15 asserted checkpoints. Read the [predictions](../labs/step-19/notes.md), then compare them with the [executed state snapshots and SQL trace](../labs/step-19/evidence.txt).

`inspect(asset)` reports instance state. `session.new`, `session.dirty`, and `session.deleted` describe work queued in that Session; they are not additional lifecycle states. [SQLAlchemy state management](https://docs.sqlalchemy.org/en/21/orm/session_state_management.html).

| Observed checkpoint | State | new / dirty / deleted membership |
|---|---|---|
| Construct LIFE-TEMP | transient | false / false / false |
| Add | pending | true / false / false |
| Flush INSERT | persistent | false / false / false |
| Assign changed location | persistent | false / true / false |
| Flush UPDATE | persistent | false / false / false |
| Assign the same loaded location | persistent | false / true / false |
| Request delete | persistent | false / false / true |
| Flush DELETE | deleted | false / false / false |
| Commit DELETE | detached | false / false / false |
| Commit a separate LIFE-KEEP insertion | persistent | false / false / false |
| Close its Session | detached | false / false / false |
| Load LIFE-KEEP in another Session | persistent | false / false / false |
| Flush its DELETE | deleted | false / false / false |
| Roll back that DELETE | persistent | false / false / false |
| Roll back an unflushed new LIFE-CANCEL | transient | false / false / false |

These are observed fixture results, not predictions inferred from the row's primary-key attribute alone. The constructor and add issue no asset SQL. The flushed INSERT supplies the UUID/default and identity-map entry. A flushed deleted object retains its Session association temporarily, leaves Session membership and the identity map, and has was_deleted true. After its commit it is detached with its identity retained. The rollback branch uses a previously committed row, so the deleted object returns to persistent and was_deleted clears.

## Observe without changing the experiment

The lab reads inspection flags, Session collections, identity markers, and loaded location history. It does not query between prediction and flush or access expired attributes after commit/rollback. Such access can cause additional database work and obscure the checkpoint being measured. Detailed freshness/loading behavior is Step 21.

The changed location records Original Lab in history.deleted and Changed Lab in history.added. After flushing, the object is clean. Assigning Changed Lab again places it in session.dirty, but session.is_modified reports no net change; a further flush clears the membership without emitting another UPDATE. This is the difference between tracked assignment and necessary SQL. [Session dirty and is_modified APIs](https://docs.sqlalchemy.org/en/21/orm/session_api.html#sqlalchemy.orm.Session.is_modified).

The unit of work gathers tracked changes and writes them during flush. The measured LIFE-TEMP path emits exactly INSERT, UPDATE, DELETE. A separate committed LIFE-KEEP insertion emits INSERT; loading and temporarily deleting it emits SELECT, DELETE before rollback. Pending LIFE-CANCEL rollback emits no SQL. [Session basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html).

## Separate object state from row existence

Closing the survivor's Session detaches its Python object while the committed row remains. Committing the disposable deletion also detaches that object, but its row is absent. Detached therefore does not establish current row existence. The lab's fresh ORM reader and independent psql observer confirm exactly one remaining asset: LIFE-KEEP in Original Lab.

Only college_step19 contains study tables. The shared Engine, factory, mappings, and production retirement policy are unchanged. Deletes are disposable lifecycle experiments. Exact-run cleanup checks ownership and a recorded UUID, refuses another UUID, removes known objects without CASCADE in finally, and verifies committed removal from a new connection. All Sessions return their resources before Engine disposal.

The [39 checks](../labs/step-19/evidence.txt) comprise 33 Python assertions and six wrapper/psql assertions. Explain the checkpoints, the same-value assignment, delete queue versus deleted state, and both detached outcomes before continuing to Step 20's visibility and failed-flush recovery experiments.
