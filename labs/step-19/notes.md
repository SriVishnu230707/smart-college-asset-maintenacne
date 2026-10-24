# Step 19 lab: inspect object lifecycle states

Use the [lifecycle guide](../../docs/ORM_OBJECT_LIFECYCLE.md) to predict the 15 checkpoints in [python_lab.py](python_lab.py) before running it. This step uses the existing shared Engine, Session factory, and typed Asset mapping.

## Run

With Docker Desktop running and the existing ignored Python environment installed from [requirements.txt](../../requirements.txt):

```powershell
.\labs\step-02\start.ps1
.\labs\step-19\verify.ps1 -WriteEvidence
```

The verifier supports PowerShell 7 and Windows PowerShell 5.1, resolves paths independently of the caller's directory, and checks Python 3.10+, SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6 before connecting. An explicit interpreter is supported:

```powershell
.\labs\step-19\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

Reuse the ignored learner credential and consistent COLLEGE_POSTGRES_PORT setting. All fixture data and run UUIDs are synthetic.

## Predict and compare

The guide's table lists every predicted state and collection membership. Before each observe call, name the single true inspection state, membership in session.new/dirty/deleted, and whether asset SQL has occurred.

- LIFE-TEMP starts transient, becomes pending on add, then persistent on INSERT flush. Assigning location preserves persistent state while adding dirty membership. Its attribute history captures the two locations.
- A same-value assignment is dirty but has no net modification. Flushing it emits no UPDATE.
- Session.delete first queues a persistent object. Only the DELETE flush produces deleted state; commit then produces detached state.
- LIFE-KEEP is committed separately. Commit leaves it persistent; closing detaches it without removing its row. A new Session loads it, flushes deletion, and rolls back to persistent state.
- Rolling back pending LIFE-CANCEL returns it to transient, with no identity, generated UUID, or INSERT.

Inspection avoids loading expired values so it cannot change the measured SQL sequence. Detailed commit expiration, refresh, and identity freshness belong to Step 21. Detailed flush durability and failed-Session recovery belong to Step 20.

## Evidence

The run on **24 October 2026** passed **39 checks**: 33 Python assertions and six wrapper/psql assertions. [Saved evidence](evidence.txt) records all 15 state dictionaries, collection memberships, identity tuples, was_deleted values, attribute-history checks, and exact asset statement sequences.

The final ORM reader finds only LIFE-KEEP with its original location. [reconnect.sql](reconnect.sql) independently confirms that row and the absent writer backend. LIFE-TEMP and LIFE-CANCEL are absent; the single department/category and empty user/ticket tables remain exact.

The fixture is committed for independent observation. [verify.ps1](verify.ps1) always attempts guarded cleanup in finally. Cleanup first refuses a different run UUID with exit 3 / SQLSTATE 22023, leaving the survivor available to the observer. Matching-run cleanup checks schema ownership, drops only known objects without CASCADE, and commits; another connection confirms schema absence. The Python finally block closes every Session and disposes the Engine on unexpected failure too.

No permanent application schema or retirement workflow is installed. Explain why detached can describe both an existing and a deleted row, why dirty does not guarantee UPDATE, and why a delete request differs from a flushed deletion. Then reproduce the checkpoints without copying their predictions.
