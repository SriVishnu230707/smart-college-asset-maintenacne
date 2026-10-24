# Flush, commit, autoflush, and recovery

Step 20 tests ticket writes against a simultaneous independent reader. The [lab](../labs/step-20/notes.md) and [saved evidence](../labs/step-20/evidence.txt) contain 35 checks: 29 Python assertions and six wrapper/psql assertions.

## Observe visibility before assuming durability

| Observed COMMIT-TICKET checkpoint | Writer | Independent reader |
|---|---|---|
| Add to Session | Pending object; no INSERT | No row |
| Explicit flush | UUID, open status, aware creation time; SELECT finds row | No row |
| Commit | Transaction ends | Row visible |

ROLLBACK-TICKET receives a UUID and is selectable by its writer after flush too. The observer sees no row before rollback, and neither a new writer query nor the observer finds it afterward. These observations prove that successful flush and generated IDs alone do not make the change durable. This experiment tests commit visibility and rollback, not recovery from hardware failure.

The observer uses an additional psycopg connection, not a second Engine or checkout from the application's one-slot pool. It verifies a different backend PID, read-only mode, and READ COMMITTED. Its autocommit setting makes each SELECT independent of a long-lived transaction. Observer autocommit never commits the writer's work. [psycopg transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

Under READ COMMITTED, a statement does not see another transaction's uncommitted writes; later statements can see changes committed in between. The lab checks the isolation setting explicitly rather than depending on a server default. [PostgreSQL transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED).

## Compare flush triggers

Flush sends pending work within the current transaction. ORM queries normally autoflush first. The no_autoflush context temporarily suppresses automatic query flushing; explicit flush still works. Commit flushes pending work even when Session autoflush is disabled. [SQLAlchemy flushing](https://docs.sqlalchemy.org/en/21/orm/session_basics.html#flushing).

| Measured operation | Ticket SQL observed | Result |
|---|---|---|
| Explicit flush, writer query, commit | INSERT, SELECT | COMMIT-TICKET persists |
| Explicit flush, writer query, rollback, missing get | INSERT, SELECT, SELECT | ROLLBACK-TICKET absent |
| Default ORM query with a pending ticket | INSERT, SELECT | AUTO-TICKET rolls back |
| Query then explicit flush inside no_autoflush | SELECT, INSERT | CONTROLLED-TICKET rolls back |
| Query then commit with autoflush=False | SELECT, INSERT | COMMIT-NOAUTO persists |
| Failed transaction | SELECT, UPDATE, INSERT, INSERT attempted | All changes in that transaction roll back |
| Same Session after explicit rollback | SELECT, SELECT, INSERT | RECOVERED persists |

The failed INSERT is included as an attempted cursor statement, not a successful database change. Queries suppressed by the failed Session produce no cursor event at all.

## Recover the logical Session transaction

The failure experiment first changes COMMIT-TICKET's description and flushes an additional BEFORE-ERROR ticket successfully. It then flushes INVALID-PRIORITY with priority urgent. PostgreSQL returns SQLSTATE 23514 and ck_maintenance_tickets_priority. The observer confirms that both preceding writes disappeared and the original description remains.

The Session remains inactive with a logical transaction after the database rollback. A query before explicit Session.rollback raises PendingRollbackError without sending SQL. Calling rollback completes that failed transaction; the same Session then reads original values and commits a newly constructed valid RECOVERED ticket. This deliberately demonstrates recovery within one Session, unlike Step 18's use of a fresh Session after an error. [SQLAlchemy failed-flush FAQ](https://docs.sqlalchemy.org/en/21/faq/sessions.html#this-session-s-transaction-has-been-rolled-back-due-to-a-previous-exception-during-flush).

Application operations should still own a clear transaction boundary and let unexpected errors propagate. The lab catches its exact deliberate CHECK failure, resets the Session explicitly, and creates valid new work. It does not blindly retry invalid data or provide a production ticket workflow. [Session transaction framing](https://docs.sqlalchemy.org/en/21/orm/session_basics.html#framing-out-a-begin-commit-rollback-block).

## Verify the whole result

Only COMMIT-TICKET, COMMIT-NOAUTO, and RECOVERED survive, with exact recorded UUIDs, open status, original descriptions, and expected priorities. The simultaneous driver reader, a fresh ORM Session, and independent psql after Python exits all agree. psql verifies defaults, unchanged parent references, absence of every rollback/error fixture, and disappearance of both Python backends.

Session contexts and the Python finally block return pool resources and close both physical connections. The committed study fixture is isolated in college_step20. PowerShell finally performs ownership/run-UUID guarded cleanup, refuses a mismatched UUID, drops only known objects without CASCADE, and checks committed removal from another connection. Credentials remain in ignored `.local/`; connection arguments are never printed.

Explain why the writer can read a flushed row that the observer cannot, which operations trigger flush, why disabling autoflush does not suppress commit's flush, and why the failed Session needs explicit rollback. Identity freshness and relationships remain later lessons.
