# Step 12 lab: ask existence questions

Read the [existence/subquery guide](../../docs/SQL_EXISTENCE_AND_SUBQUERIES.md), then predict [query.sql](query.sql) before running it. This implements only Step 12 of the [learning path](../../docs/LEARNING_PATH.md): scalar/correlated subqueries, EXISTS/NOT EXISTS, the nullable NOT IN trap, and set operations.

## Run the proof

With Docker Desktop running, use PowerShell from the project root:

```powershell
.\labs\step-02\start.ps1
.\labs\step-12\verify.ps1 -WriteEvidence
```

The [verifier](verify.ps1) reuses the [shared runner](../shared/verify.ps1), runs as `college_learner`, and starts a separate psql process for [reconnect.sql](reconnect.sql). No Python dependency is added. Local credentials remain in ignored `.local/`. An existing `college_step12` schema causes a refusal before any fixture is created.

For interactive study:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```text
\i /labs/step-12/query.sql
\i /labs/step-12/reconnect.sql
\quit
```

## Hand-count the fixture

Three departments exist: CSE, ECE, MECH. The seven users are Ravi, Nila, Omar, Mira, Alex, Campus Admin, and Leela. Ravi/Nila/Omar/Leela are active technicians; Mira is an inactive technician with retained terminal history; Alex is a student. Campus Admin is a Super Admin with NULL department. MECH has no users/assets/tickets.

Five assets exist: PRJ-001 and PC-001 in CSE, plus PRJ-002, PC-002, and unused PC-003 now in ECE. T1-T6 abbreviate UUID endings, not new ticket-code columns.

| Ticket | Asset | Recorded department | Status | Assignee |
|---|---|---|---|---|
| T1 | PRJ-001 | CSE | open | NULL |
| T2 | PRJ-001 | CSE | assigned | Ravi |
| T3 | PC-001 | CSE | in_progress | Ravi |
| T4 | PRJ-002 | CSE | closed | Mira |
| T5 | PC-002 | ECE | assigned | Nila |
| T6 | PC-002 | ECE | closed | Leela |

T4 represents history before transfer/deactivation. Leela's retained T6 assignment does not give her a current ticket. These four tables are reduced query projections; category/reporter/completion/audit facts and full workflow enforcement are omitted. They are not production migrations.

## Predict the returned rows

| Query | Expected result |
|---|---|
| Correlated NOT EXISTS for no ticket | PC-003 |
| LEFT JOIN then child primary key IS NULL | PC-003 |
| All asset codes EXCEPT ticketed codes | PC-003 |
| Correlated EXISTS for any ticket | PC-001, PC-002, PRJ-001, PRJ-002 |
| NOT EXISTS without the asset correlation | No assets |
| Scalar department lookup CSE; UNKNOWN | CSE; NULL |
| Correlated counts, asset-code C order | PC-001 1; PC-002 2; PC-003 0; PRJ-001 2; PRJ-002 1 |
| Correlated scalar count = 0 | PC-003 |
| EXISTS(SELECT NULL); same SELECT with WHERE false | TRUE; FALSE |
| EXISTS(SELECT COUNT(*) ... WHERE false) | TRUE: the aggregate returns a row |
| Active technicians with nonterminal assigned tickets | Ravi, Nila |
| Raw inner join for that same question | Ravi, Ravi, Nila |
| DISTINCT on joined user identity | Ravi, Nila |
| Any assignment history, including inactive technicians | Ravi, Nila, Mira, Leela |
| Active technicians without current assigned tickets | Omar, Leela |
| Active technicians with no assignment ever, NOT EXISTS | Omar |
| Raw NOT IN over all nullable assignees | No rows: Omar's predicate is UNKNOWN |
| Raw predicate projected for Ravi; Omar | FALSE; NULL |
| NOT IN after removing right-side NULLs | Omar |
| NOT IN against an empty assignment result | Ravi, Nila, Omar, Leela |
| Nullable outer UUID against nonempty IDs; empty IDs | UNKNOWN; TRUE |
| Open assets UNION current-assigned assets | PC-001, PC-002, PRJ-001 |
| The same UNION ALL | PC-001, PC-002, PRJ-001, PRJ-001 |
| The same INTERSECT | PRJ-001 |
| Ticketed assets EXCEPT current-assigned assets | PRJ-002 |

Current assigned work means status assigned, in_progress, or awaiting_verification. It is a report definition, not a claim that every such ticket is ready for another repair action. All user results use UUID ordering; asset results use explicit C collation. Technician names above abbreviate the unique `.invalid` emails asserted in the SQL.

## Read the proof machinery

`assert_rows` compares complete ordered rows as JSON, preserving NULL, duplicate rows, and projected column names. Expected values are literal handwritten predictions. JSON is just the test comparison format. `assert_true` checks unchanged fixture counts.

`expect_error` runs each invalid SELECT in a nested exception block and requires its exact SQLSTATE. Unexpected errors or accepted invalid queries fail the lab:

| Invalid query | SQLSTATE |
|---|---|
| Multiple CSE user emails used as one scalar value | `21000` cardinality_violation |
| UNION inputs with different column counts | `42601` syntax_error |
| UNION of text asset codes and UUID ticket IDs | `42804` datatype_mismatch |

See [official error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html). Top-level guards include the [shared failure handler](../shared/fail.sql), which raises a real SQL error under ON_ERROR_STOP. Every failed assertion stops psql with a nonzero exit, and an open transaction rolls back on disconnect.

## Recorded result and learning gate

The live run on **24 October 2026** passed **31 PostgreSQL checks**: twenty-five exact row comparisons, three expected SQL errors, one fixture assertion, and two cleanup assertions. The [original evidence](evidence.txt) contains the actual rows and distinct exercise/cleanup backend PIDs. ROLLBACK removed the schema, fixtures, and helpers; another connection confirmed absence.

Explain the correlation reference, why EXISTS avoids join multiplication, how scalar zero/multiple rows differ, why COUNT inside EXISTS can ask the wrong question, and why NOT IN loses Omar. Reproduce the corrected NOT EXISTS and the qualified NULL-filtered NOT IN alternative. Distinguish current from historical assignments, and predict duplicate handling in the four set operations.

Continue with Step 13, Python database layers, when you can explain these results without copying their expected JSON.
