# Step 9: filter and order rows deliberately

Read the [filtering and ordering guide](../../docs/FILTERING_AND_ORDERING.md), then predict each query's returned keys before reading its expected array in the SQL.

## Run the proof

Use the [Step 2 environment](../step-02/notes.md). With Docker Desktop running, execute from PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-09\verify.ps1 -WriteEvidence
```

The [verifier](verify.ps1) runs [query.sql](query.sql) and [reconnect.sql](reconnect.sql) in separate authenticated psql connections. It needs no Python or new package. It replaces [evidence.txt](evidence.txt) only after both scripts succeed. Omit `-WriteEvidence` to print the run without replacing the saved transcript.

For interactive SQL study:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```sql
\i /labs/step-09/query.sql
\i /labs/step-09/reconnect.sql
\quit
```

The script refuses an existing `college_step09` schema. It creates three reduced project read-model tables plus one text comparison table inside a transaction, fixes the session timezone locally to UTC, and rolls everything back. Department IDs are synthetic fixture labels; omitted entity columns, full parent graphs, and authorization remain covered by the project model and later application work.

## Know the fixture before predicting results

| Asset | Display name | Department | Status |
|---|---|---|---|
| PRJ-001 | Lab Projector | CSE | active |
| PC-001 | lab computer | CSE | active |
| PC-002 | LAB Computer | CSE | under_maintenance |
| PC-003 | Library Computer | ECE | retired |
| PRJ-002 | Projector 100% | ECE | active |
| PC-004 | Computer_Stand | ECE | active |

| Ticket label | Department | Assignee | Status / priority | Created at, UTC |
|---|---|---|---|---|
| T1 | CSE | NULL | open / high | Oct 22, 09:00 |
| T2 | CSE | NULL | open / low | Oct 22, 09:00 |
| T3 | CSE | CSE technician | assigned / high | Oct 22, 09:00 |
| T4 | ECE | NULL | open / critical | Oct 22, 09:00 |
| T5 | ECE | NULL | rejected / low | Oct 21, 08:00 |
| T6 | ECE | ECE technician | in_progress / medium | Oct 22, 08:30 |

All dates are in 2026. T1-T6 label full UUIDs ending in 001-006. They are explanatory labels, not an added ticket-code column. Two fixture technicians supply the optional assignee references.

The separate text table contains NULL, empty text, three spaces, padded/case-varied Lab strings, percent/underscore strings, numeric text 2/10, and invalid numeric text two. `quote_nullable` and `char_length` make its distinctions visible. Required asset names/ticket titles are never weakened to store these comparison values.

## Predict the important outputs

| Query choice | Expected keys in order |
|---|---|
| All active assets | PC-001, PC-004, PRJ-001, PRJ-002 |
| Active CSE assets | PC-001, PRJ-001 |
| All unassigned tickets | T1, T2, T4, T5 |
| CSE, unassigned, open, newest first, ID ASC, LIMIT 2 | T1, T2 |
| `assigned_to_id = NULL` | No rows |
| CSE AND (high OR critical) | T1, T3 |
| CSE AND high OR critical, without parentheses | T1, T3, T4 |
| Case-sensitive Lab prefix under C collation | PRJ-001 |
| Case-insensitive lab prefix under C collation | PC-001, PC-002, PRJ-001 |
| Literal percent; literal underscore | PRJ-002; PC-004 |
| Newest timestamps then ID ASC, LIMIT 2 | T1, T2 |
| Newest timestamps then ID DESC, LIMIT 2 | T4, T3 |
| Assignee ASC, default NULLS LAST, then ID ASC | T3, T6, T1, T2, T4, T5 |
| Assignee ASC NULLS FIRST, then ID ASC | T1, T2, T4, T5, T3, T6 |
| Assignee DESC, default NULLS FIRST, then ID ASC | T1, T2, T4, T5, T6, T3 |
| LIMIT 0 | No rows |
| LIMIT NULL with the full newest/ID ASC order | T1, T2, T3, T4, T6, T5 |

The same-timestamp example demonstrates an incomplete primary sort key. It does not claim to observe random order changes from repeated execution. The two explicit ID policies show why the tie decision matters. Stable selection here assumes unchanged input; concurrent pagination is later work.

Other assertions check empty versus NULL/space-only values, deliberate NULLIF grouping, lower/btrim behavior, text versus integer ordering, a typed UUID predicate, and an explicitly zoned date cast. Every returned-key assertion checks both membership and order, not just a count.

## Read the proof machinery and invalid cases

`assert_keys` executes only literal one-column queries written in this lab and compares their ordered result arrays against handwritten predictions. Its PASS output includes observed keys. `assert_true` checks scalar/fixture facts. Arrays, counts, and verification subqueries are scaffolding; aggregation and existence-query lessons follow later.

`expect_error` executes each invalid SELECT in a nested exception block, verifies its SQLSTATE, and leaves the outer transaction usable. An accepted bad value or unexpected error fails the script:

| Invalid input | Expected SQLSTATE |
|---|---|
| Malformed UUID cast | `22P02` |
| Cast nonnumeric two to integer | `22P02` |
| Negative LIMIT | `2201W` |

See [official error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html). [fail.sql](fail.sql) uses a real SQL exception for top-level assertion failures, making psql return a nonzero exit status under ON_ERROR_STOP.

## Recorded outcome and learning gate

The live run passed on 22 October 2026: **37 PostgreSQL checks** comprising 28 exact ordered-key checks, four scalar/fixture assertions, three expected invalid-input rejections, and two cleanup assertions. See [original evidence](evidence.txt). All study tables, values, and helper functions were rolled back; a fresh connection confirmed the schema was absent.

Explain why unassigned differs from actionable, why parentheses change scope, how NULL differs from empty text, what a wildcard matches, why the lab pins case collation, why casts can fail, and how a unique final sort key determines LIMIT results. Explain what LIMIT NULL means and why the UUID tie order does not imply event chronology.

Continue with Step 10 in the [learning path](../../docs/LEARNING_PATH.md) when you can reproduce those predictions without copying the expected arrays.
