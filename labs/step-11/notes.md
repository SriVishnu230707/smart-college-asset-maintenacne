# Step 11 lab: aggregate data

Read the [aggregation guide](../../docs/SQL_AGGREGATION.md), then predict each report in [query.sql](query.sql). This lab implements Step 11 of the [learning path](../../docs/LEARNING_PATH.md): COUNT, SUM, AVG, GROUP BY, HAVING, CASE, COALESCE, and FILTER.

## Run the proof

With Docker Desktop running, use PowerShell from the project root:

```powershell
.\labs\step-02\start.ps1
.\labs\step-11\verify.ps1 -WriteEvidence
```

The [verifier](verify.ps1) runs the SQL as the existing non-superuser `college_learner`, then opens another psql process for [reconnect.sql](reconnect.sql). No Python package is required. Local credentials remain in ignored `.local/`. An existing `college_step11` namespace causes a refusal rather than replacing prior objects.

For interactive inspection:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```text
\i /labs/step-11/query.sql
\i /labs/step-11/reconnect.sql
\quit
```

## Count the fixture by hand

Three departments exist: CSE, ECE, MECH. The two users represent active departmental technicians Ravi and Nila. The four study tables are reduced report projections, omitting asset/reporter references, proof, audit, ledger, and other workflow facts. This is not the permanent application schema. T1-T6 and W1-W5 abbreviate UUID endings, not new business-code columns.

| Ticket | Recorded department | Priority | Status | Assignee |
|---|---|---|---|---|
| T1 | CSE | high | open | NULL |
| T2 | CSE | high | in_progress | Ravi |
| T3 | ECE | medium | open | NULL |
| T4 | CSE | critical | in_progress | Ravi |
| T5 | CSE | low | closed | Ravi |
| T6 | ECE | high | awaiting_verification | Nila |

| Work order | Ticket | Status | Labor cost, INR |
|---|---|---|---|
| W1 | T4 | completed | 600.50 |
| W2 | T5 | completed | 0.00 |
| W3 | T6 | completed | 75.50 |
| W4 | T2 | in_progress | 1000.00 |
| W5 | T4 | draft | 2000.00 |

T4 represents rework after W1, with a new draft W5. Completed W1 stays in historical labor costs. W3 counts before ticket verification. Monetary values are already validated two-place literals; the lab does not install a new raw-input validator or complete the repair workflow. Parts are not projected, so labor totals do not claim to be whole repair costs.

| Department | low | medium | high | critical | Tickets | Assignments | Distinct assignees |
|---|---|---|---|---|---|---|---|
| CSE | 1 | 0 | 2 | 1 | 4 | 3 | 1 |
| ECE | 0 | 1 | 1 | 0 | 2 | 1 | 1 |
| MECH | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The SQL compares all twelve department/priority output rows, including zeros. A simpler observed-priority grouping has six rows: CSE critical/high/low, ECE high/medium, and MECH with NULL priority and zero tickets. The explicit four-priority reporting axis supplies absent combinations.

## Predict the differences

| Query choice | Hand prediction |
|---|---|
| COUNT(*) over department LEFT JOIN tickets | CSE 4, ECE 2, MECH 1 |
| COUNT(t.id) over the same join | CSE 4, ECE 2, MECH 0 |
| Open FILTER; SUM CASE 1/0; COUNT CASE 1/NULL | Each gives CSE 1, ECE 1, MECH 0 |
| COUNT(status = open) | 4, 2, 0: false also counts |
| COUNT(CASE open THEN 1 ELSE 0 END) | 4, 2, 1: zero also counts |
| COUNT(*) FILTER (WHERE assignee IS NULL) | 1, 1, 1: MECH's placeholder is not a ticket |
| Open predicate in WHERE; in ON | CSE/ECE only; all three departments with MECH zero |
| HAVING ticket count >= 3 | CSE with 4 |
| HAVING urgent count >= 2, where urgent means high/critical | CSE with total 4 and urgent 3 |
| Urgent predicate in WHERE, HAVING count >= 2 | CSE with total 3 |
| HAVING ticket count = 0 | MECH with 0 |
| Completed labor sum and average | CSE 600.50 / 300.25; ECE 75.50 / 75.50; MECH NULL / NULL |
| COALESCE completed labor sum to zero | MECH sum becomes 0.00; its mean remains NULL |
| AVG(CASE completed THEN labor ELSE 0 END) | CSE 120.10, ECE 37.75, MECH 0: wrong denominator |
| Isolated values 6.00, NULL, 0.00 | Three rows, two known values, sum 6.00, mean 3.00; zero-filled mean 2.00 |
| Ungrouped aggregate over no rows | One row: COUNT 0, SUM NULL, AVG NULL |
| Grouped aggregate over no rows, even with COALESCE | No rows |
| CSE ticket IDs counted after joining work orders | Five repeated IDs versus four distinct tickets |
| Sum of two 9999999999.99 NUMERIC(12,2) values | Exact 19999999999.98; narrowing back overflows |

All multirow predictions use explicit department/priority ordering. Numeric comparisons preserve mathematical values without treating PostgreSQL's extra displayed trailing zeros as a different mean.

## Inspect assertions and invalid queries

`assert_rows` compares entire returned row arrays, including NULLs, zeros, column names, order, and multiplicity. It serializes ordered literal SELECTs to JSON only for verification; JSON storage and subquery design remain later lessons. `assert_true` verifies that all fixture row counts are unchanged.

`expect_error` catches a requested SQLSTATE inside a nested exception block, leaving the outer transaction usable. An accepted invalid query or unexpected error fails the run:

| Invalid query | Expected SQLSTATE |
|---|---|
| Aggregate in WHERE selecting its own inputs | `42803` grouping_error |
| Varying ticket priority projected without grouping or aggregation | `42803` grouping_error |
| Report total forced into NUMERIC(12,2) | `22003` numeric_value_out_of_range |

See [official error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html). [fail.sql](fail.sql) raises a real exception under ON_ERROR_STOP for top-level assertion failures, making psql return nonzero.

## Recorded result and learning gate

The live run on **24 October 2026** passed **25 PostgreSQL checks**: nineteen complete report-row comparisons, one fixture assertion, three expected SQL rejections, and two cleanup assertions. The [original evidence](evidence.txt) includes actual report rows and distinct exercise/cleanup backend PIDs. ROLLBACK removed all study tables, functions, and data; a fresh connection confirmed absence.

Explain COUNT(*) versus COUNT(column), how the twelve zero-filled buckets arise, which stage each condition filters, why false counts in COUNT(boolean), why absent and zero averages differ, and why joining work orders changes the ticket-count grain. Recalculate the labor means and explain the wider numeric report total.

Continue with Step 12, existence questions, when you can reproduce and explain these results without copying the expected JSON.
