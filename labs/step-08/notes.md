# Step 8: manipulate the first dataset in SQL

Read the [CRUD and transaction guide](../../docs/SQL_CRUD_AND_TRANSACTIONS.md) first. This lab uses real COMMIT/ROLLBACK boundaries and checks the result from an independent PostgreSQL connection.

## Run the complete proof

Use the [Step 2 environment](../step-02/notes.md). With Docker Desktop running, execute from PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-08\verify.ps1 -WriteEvidence
```

No Python or additional package is needed. The [verifier](verify.ps1) generates a synthetic run UUID, then performs five psql invocations:

1. [query.sql](query.sql) commits a baseline and performs the two rollback experiments.
2. [cleanup.sql](cleanup.sql), with a different UUID, proves cleanup refuses another run.
3. [reconnect.sql](reconnect.sql) reads the original baseline in an independent backend.
4. [cleanup.sql](cleanup.sql), with the correct UUID, commits removal of the study objects.
5. [cleanup-check.sql](cleanup-check.sql) verifies absence from another connection.

The baseline consists of two departments, two categories, three assets, and one metadata row identifying its run and writer backend. It exists temporarily in `college_step08`. The script refuses an existing schema, and cleanup requires matching metadata and schema ownership. The verifier attempts correct cleanup in `finally`, including after a failed proof; a machine/process interruption can still require manual cleanup using the retained run ID.

[guard.sql](guard.sql) checks the expected connection and required run ID. [fail.sql](fail.sql) turns an assertion failure into a real SQL error and nonzero psql exit. Saved [evidence.txt](evidence.txt) is replaced only after the proof and cleanup both succeed. Without `-WriteEvidence`, output is printed without replacing that file.

## Trace the baseline and rollback

| Asset | Committed location/status | Change inside the CRUD transaction | After ROLLBACK, including independent observation |
|---|---|---|---|
| PRJ-001 | Lecture Hall A / active | Room 204 / under_maintenance | Lecture Hall A / active, same UUID |
| PC-001 | Computer Lab 1 / active | Unchanged in this experiment | Original row remains |
| PC-002 | Electronics Lab / active | Deleted with RETURNING | Original row restored, same UUID |
| ROLLBACK-ONLY | Absent | Inserted and visible to the writer | Absent |

The writer also creates MECH and LAB-TEMP, then deletes the temporary asset before its department. Returned IDs and affected-row counts identify the exact removed rows. These fixtures have no historical tickets. They teach DELETE without replacing the application's retirement policy.

RETURNING exposes generated/default INSERT values, old/new UPDATE values, and removed DELETE values. The writer reads its pending changes before ROLLBACK. Zero-match UPDATE/DELETE statements return no rows and report success with a count of zero; they are not treated as one-row changes.

The second transaction successfully changes PC-001 to Change Before Error, then triggers a duplicate asset-code failure. Its following SELECT cannot run until ROLLBACK. Both the writer and observer confirm PC-001 remains at Computer Lab 1 afterward.

## Explain the three deliberate errors

| Operation | Expected SQLSTATE | Proof |
|---|---|---|
| Insert PRJ-001 a second time | `23505` | Duplicate business identifier is rejected |
| SELECT after that transaction error | `25P02` | The aborted transaction rejects further statements until rollback |
| Cleanup using a different run UUID | `22023` | The lab-defined run-ID guard refuses cleanup before any DROP |

These exact errors are expected in the transcript. The two statement failures are captured and asserted after ROLLBACK; the cleanup refusal must exit psql with code 3 and the expected run-ID marker/SQLSTATE. Other failures stop verification. psql result and error streams can interleave, so an error line may appear after a PASS that checks its captured SQLSTATE.

The live run passed on 22 October 2026: **23 verification checks across PostgreSQL/psql and the PowerShell runner**. See [original evidence](evidence.txt) for RETURNING values, error codes, different writer/observer backend PIDs, restored rows, the wrong-run refusal, and final schema absence.

## Explore the SQL manually

The verifier handles cleanup automatically. For manual study, retain the same run ID until cleanup finishes:

```powershell
$step8RunId = [guid]::NewGuid().ToString('D')
docker compose exec postgres sh /labs/step-02/psql.sh "--set=lab_run_id=$step8RunId"
```

Inside that psql session:

```sql
\i /labs/step-08/query.sql
\quit
```

Back in the same PowerShell window, use separate connections for observation and cleanup:

```powershell
docker compose exec -T postgres sh /labs/step-02/psql.sh "--set=lab_run_id=$step8RunId" --file /labs/step-08/reconnect.sql
docker compose exec -T postgres sh /labs/step-02/psql.sh "--set=lab_run_id=$step8RunId" --file /labs/step-08/cleanup.sql
docker compose exec -T postgres sh /labs/step-02/psql.sh "--set=lab_run_id=$step8RunId" --file /labs/step-08/cleanup-check.sql
```

Complete cleanup even if a manual exercise fails. If ownership/run metadata does not match, inspect the schema instead of bypassing the guard. The UUID is a lab ownership marker, not a credential or an application authorization mechanism.

During this machine's verification, Docker startup hit the previously observed stale runtime-socket error. With Docker stopped, its runtime directory was moved to the recoverable backup `%LOCALAPPDATA%\Docker\run.stale-step08-20261022-205335` and recreated. The existing PostgreSQL volume and local credentials were preserved.

## Explain before advancing

1. How do explicit INSERT column lists and RETURNING connect new assets to generated parent IDs?
2. What does the affected-row count tell you when UPDATE or DELETE matches nothing?
3. Why can RETURNING and a subsequent SELECT succeed before the change is committed?
4. Which inserted, updated, and deleted rows does the first ROLLBACK restore or remove?
5. Why does that rollback leave the earlier committed baseline intact?
6. What happens after error 23505, and why does SELECT then report 25P02?
7. Why does rollback undo the successful update that preceded the duplicate error?
8. What proves that the observer is an independent connection, and which original values does it verify?
9. Why is committed fixture cleanup a separate transaction with an exact run-ID guard?
10. Which deletion, authorization, audit, and concurrency policies still belong to later application steps?

Continue with Step 9 in the [learning path](../../docs/LEARNING_PATH.md) when you can reproduce and explain the observations.
