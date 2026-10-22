# Step 8: manipulate the first dataset in SQL

The [Step 8 lab](../labs/step-08/notes.md) practices SQL writes against a small department/category/asset dataset. It combines the earlier [row-validity](ROW_VALIDITY.md) and [reference policies](REFERENTIAL_INTEGRITY.md) with explicit transaction boundaries. Its baseline is committed temporarily so another connection can inspect real committed data before guarded cleanup.

## Connect each SQL statement to its result

| Operation | Project example | What to inspect |
|---|---|---|
| INSERT | Seed two departments, two categories, and three assets | Explicit column lists, generated UUIDs, default status, inserted-row count |
| SELECT | Read asset code, name, location, status | Returned values and row count; order by unique asset code |
| UPDATE | Move PRJ-001 to Room 204 and mark it under maintenance | A WHERE clause selecting one row; returned old/new values and unchanged UUID |
| DELETE | Remove a temporary study asset, then its temporary department | Returned deleted identity and child-before-parent ordering |
| DELETE followed by ROLLBACK | Temporarily remove committed PC-002 | Deleted row disappears in the writer, then returns with its original identity |

Use an explicit INSERT column list to show which values are supplied and which defaults apply. The lab captures generated parent IDs with RETURNING and supplies those IDs to new asset rows. See [inserting data](https://www.postgresql.org/docs/18/dml-insert.html).

UPDATE changes the selected rows' specified columns. DELETE removes selected rows. A WHERE clause defines that selection; omitting it targets all rows. A statement matching no rows can still succeed. The lab deliberately gets `UPDATE 0` and `DELETE 0` and distinguishes these from its expected one-row changes. See [updating data](https://www.postgresql.org/docs/18/dml-update.html) and [deleting data](https://www.postgresql.org/docs/18/dml-delete.html).

The study fixture has no tickets or repair history. Its DELETE examples do not change the contract's retirement/history-preservation policy for application records.

## Read RETURNING without confusing it with COMMIT

RETURNING describes rows affected by a statement. INSERT can return a generated UUID/default, UPDATE returns modified values, and DELETE returns removed values. PostgreSQL 18 also supports explicit old/new row values. See [returning modified rows](https://www.postgresql.org/docs/18/dml-returning.html).

The executed update is:

```sql
UPDATE assets
SET location = 'Room 204', status = 'under_maintenance'
WHERE asset_code = 'PRJ-001'
RETURNING id,
          old.location AS old_location, new.location AS new_location,
          old.status AS old_status, new.status AS new_status;
```

It reports Lecture Hall A -> Room 204 and active -> under_maintenance. The writer can then SELECT those values inside its transaction. Later ROLLBACK restores Lecture Hall A and active. Receiving a successful RETURNING result did not commit the change.

psql's `\gset` stores a single returned row in client variables. `ROW_COUNT` reports the latest query's returned/affected count; `SQLSTATE` reports its result code. The lab copies these immediately before another SQL statement replaces them. Client variables themselves are not database rows and are not rolled back. See [psql variables and commands](https://www.postgresql.org/docs/18/app-psql.html).

## Make transaction ownership explicit

| Phase | SQL boundary | Verified outcome |
|---|---|---|
| Baseline | BEGIN, create/seed, COMMIT | The dataset remains readable from a separate backend |
| Successful CRUD experiment | BEGIN, several writes, ROLLBACK | Insert disappears; update reverts; deleted committed asset returns |
| Failed transaction experiment | BEGIN, valid update, duplicate insert, blocked SELECT, ROLLBACK | Neither the successful preceding update nor the invalid insert persists |
| Independent read | BEGIN READ ONLY, inspect, COMMIT | Original baseline is intact after both rollbacks |
| Cleanup | BEGIN, guarded known-object drops, COMMIT | Another connection confirms the schema is absent |

BEGIN groups statements. COMMIT saves successful transaction work; ROLLBACK discards the current transaction's work. Under psql's normal autocommit behavior, statements outside an explicit transaction are committed individually. The lab uses explicit boundaries for each intended unit. See [PostgreSQL transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html).

Rollback affects the current transaction, not an earlier committed baseline. It also does not remove data merely because a client connection closes after a successful COMMIT. This is why the observer can still examine the baseline and why cleanup needs a separate committed operation.

## Observe a real aborted transaction

The second experiment first updates PC-001 successfully, then tries to insert PRJ-001 again. It records the duplicate error `23505`. The next SELECT gets `25P02` because the transaction is aborted. ROLLBACK recovers the connection and also undoes the earlier successful update. See [PostgreSQL error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html).

The script disables `ON_ERROR_STOP` only around those two expected failures, captures each SQLSTATE, restores fail-fast behavior, rolls back, and asserts both codes and the restored row. `ON_ERROR_ROLLBACK` is explicitly off so psql does not conceal the aborted transaction with automatic savepoints.

Assertion failures use a real SQL exception under `ON_ERROR_STOP`, which yields psql exit 3. `\quit` has no exit-code argument. The cleanup guard likewise raises a deliberate `22023` on a run-ID mismatch; the verifier asserts that exact refusal. See [psql exit status](https://www.postgresql.org/docs/18/app-psql.html#APP-PSQL-EXIT-STATUS).

## Verify from another connection, then remove the fixture

The observer reads the committed run metadata and proves its backend PID differs from the writer's. It checks department/category values, all three original assets, the absence of ROLLBACK-ONLY/LAB-TEMP/MECH, and the restored values after both rolled-back transactions. This proves the stated post-rollback results across separate connections; it is not a concurrent isolation-level experiment or a crash-recovery test.

Cleanup requires the expected database/role, schema ownership, and the exact stored run UUID. A wrong-run attempt is actually executed and refused before the observer confirms the baseline is intact. Correct cleanup drops only the four known tables and the empty study schema, without CASCADE. The verifier attempts cleanup in `finally` even after a failed proof. A final connection verifies that cleanup was committed.

The [saved evidence](../labs/step-08/evidence.txt) records 23 successful verification checks, including the three deliberate SQL errors, RETURNING values, independent backend IDs, and committed cleanup. Permanent schema migrations, authorized application use cases, and concurrent workflows remain later lessons. Step 9 introduces more deliberate filtering and ordering next.
