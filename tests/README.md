# Run all implemented labs

With Docker Desktop running, install the pinned [root requirements](../requirements.txt) into the ignored `.venv`, then run from PowerShell 7 or Windows PowerShell 5.1:

```powershell
.\tests\run.ps1 -WriteEvidence
```

The suite runs **Steps 2-50 sequentially: 49 labs, 1224 lab assertions, and fourteen runner regression checks (1238 checks)**. Step 1 contains written business proofs. It does not advance the learning checklist. Individual lessons use their own `labs/step-NN/verify.ps1`; run suites sequentially because they share study namespace names.

Steps 5 and 13-50 require Python. The shared resolver tries the project virtual environment, PATH, and an existing bundled interpreter, skips Store aliases, and respects an explicit `-PythonExecutable C:\path\to\python.exe`. It checks pinned dependencies before connecting. No interpreter or package is installed automatically. SQLAlchemy 2.1.6, psycopg 3.3.6, Alembic 1.20.1, FastAPI 0.162.0, and resolved HTTP dependencies are pinned through the root requirements.

## Verification coverage

SQL and ORM proofs cover constraints, exact money/time, SQL queries, Core DML, object lifecycle, flush/commit recovery, relationships, migrations, scoped projections and pagination. [Steps 31-50](../docs/WORKFLOW_PHASE_31_50.md) add measured loaders, real HTTP requests, resource permissions, lifecycle transitions, audit rollback, attachment compensation, stock reconciliation, immutable history, completion failure injection, MVCC/isolation, real backend contention/deadlocks, bounded retries, durable idempotency, optimistic edits, and fan-out-safe advanced reports.

Fourteen runner regressions retain database readiness, syntax/include checks, nonzero assertion exits, native stderr, explicit Python preflight, fresh-schema cleanup, current failure logs, and preservation of primary/observer/cleanup errors. The [maintenance review](../docs/MAINTENANCE_REVIEW.md) explains those fixes; [runner-regressions.ps1](runner-regressions.ps1) can run independently. Deliberately rejected SQLSTATEs and business conflicts are expected assertions; unexpected exits, assertion failures, missing cleanup, or changed check counts fail the suite.

Every committed lab has an independent SQL observer and exact-run cleanup guard. Historical Steps 17-20 use frozen column-only mappings so current model growth does not rewrite their original learning experiment. Concurrency proofs use distinct PostgreSQL backends with explicit coordination and observed blocking; the one-slot application learning pool cannot serialize those tests invisibly. There is no SQLite substitute.

## Evidence and database scope

- [PowerShell 7 complete-suite evidence](evidence-powershell7.txt)
- [Windows PowerShell 5.1 complete-suite evidence](evidence-powershell5.txt)
- Per-step notes and evidence under `labs/step-NN/`

Full process output, including failed children, is saved under ignored `.local/test-results/`. `-WriteEvidence` saves a UTF-8 summary; failed runs report FAILED and exit nonzero. Private credentials, opaque bearer digests, local uploaded bytes and the virtual environment remain outside Git.

Application migrations execute as college_learner and advance the local application database to the reviewed head. Exact CHECK names are verified separately because normal metadata autogenerate does not compare them. Fresh/populated chain proofs create and drop only strictly generated scratch database names, using the ignored admin credential for database creation/removal. Credentials and Docker volumes are preserved; there is no reset or force-drop.

These results were exercised on Windows in both installed PowerShell versions against PostgreSQL 18 with the pinned Python environment. They cover the local backend and learning labs. The [API guide](../docs/API.md) documents opaque local authentication, private file storage, exact decimal strings, versioned edit inputs and report limits. Frontend, external identity-provider integration, production role separation, deployment/recovery procedures and later performance lessons remain outside this result.
