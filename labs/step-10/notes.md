# Step 10 lab: join related data

Read the [join guide](../../docs/SQL_JOINS.md), then predict the results before running [query.sql](query.sql). This lab follows Step 9 and implements only Step 10 of the [learning path](../../docs/LEARNING_PATH.md).

## Run the proof

With Docker Desktop running, use PowerShell in the project root:

```powershell
.\labs\step-02\start.ps1
.\labs\step-10\verify.ps1 -WriteEvidence
```

The verifier uses the existing non-superuser `college_learner` connection, executes the lab, then starts a separate psql process for [reconnect.sql](reconnect.sql). Credentials stay under ignored `.local/`. No Python package is needed. Existing `college_step10` objects cause a refusal; inspect them before rerunning.

To inspect it interactively:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```text
\i /labs/step-10/query.sql
\i /labs/step-10/reconnect.sql
\quit
```

## Hand-predict the fixture

The SQL creates three departments, two categories, six users, five assets, and six tickets. MECH has no users/assets/tickets. T1-T6 below abbreviate UUID endings 001-006, not a new application ticket-code column.

| Ticket | Asset code | Recorded department | Reporter | Stored assignee | Status |
|---|---|---|---|---|---|
| T1 | PRJ-001 | CSE | Alex (CSE) | NULL | open |
| T2 | PC-001 | CSE | Alex (CSE) | Ravi | assigned |
| T3 | PC-002 | ECE | Alex (ECE) | NULL | open |
| T4 | PRJ-001 | CSE | Ravi | Ravi | in_progress |
| T5 | PRJ-002 | CSE | Alex (CSE) | Mira, now inactive | closed |
| T6 | PC-002 | ECE | Alex (ECE) | Nila | assigned |

PRJ-002 now belongs to ECE; T5 represents terminal history retained after transfer and deactivation. It does not demonstrate creating a new assignment to an inactive technician. PC-003 has no ticket. Both PC-001 and PC-002 are named Lab Computer, and the two Alex users have different UUIDs/emails.

| Query choice | Hand prediction |
|---|---|
| Ticket details with required asset/reporter and optional assignee | Six rows, correct names; T1/T3 assignee NULL; T5 Mira/false |
| INNER JOIN assignee | T2, T4, T5, T6 |
| Normal LEFT JOIN then WHERE active | T2, T4, T6 |
| LEFT JOIN with active in ON | All six; T1/T3/T5 have NULL joined profiles |
| Filtered ON then joined ID IS NULL | T1, T3, T5 |
| Filtered ON then stored assignee ID IS NULL | T1, T3 |
| Normal LEFT JOIN then WHERE active OR joined ID IS NULL | T1, T2, T3, T4, T6 |
| Normal LEFT JOIN then CSE ticket predicate | T1, T2, T4, T5 |
| T5 recorded and current asset departments | CSE and ECE |
| Asset INNER JOIN tickets; LEFT JOIN tickets | Six pairs; seven pairs including PC-003 with no ticket |
| Open-ticket predicate in WHERE; in ON | Two pairs; five pairs retaining all assets |
| Incorrect reporter join on department | Sixteen rows |
| Same-department self join with ID less-than | Four pairs, each unordered pair once |
| Same self join without ID restriction | Thirteen pairs including self and mirror pairs |

The expected ordered asset-ticket pairs and complete detail rows are literal predictions in the SQL. Checks compare actual values and multiplicity, not just total counts.

## Understand the proof machinery

`assert_keys` compares ordered one-column result arrays. `assert_rows` compares full ordered result rows serialized as JSON, retaining NULLs and projected column names. `assert_true` checks scalar and fixture facts. Their aggregate, JSON, and subquery internals are test scaffolding; they do not introduce production JSON storage or complete the later aggregation/existence lessons.

`expect_error` catches only the requested SQLSTATE inside a nested exception block. Unexpected errors or accepted bad queries fail the exercise:

| Invalid query | SQLSTATE |
|---|---|
| Ambiguous unqualified ID | `42702` |
| Same alias for both user references | `42712` |
| Original users qualifier after aliasing it as reporter | `42P01` |

See [PostgreSQL error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html). [fail.sql](fail.sql) raises a real exception for top-level assertion failures, so psql exits nonzero under ON_ERROR_STOP.

## Recorded result and learning gate

The live run on **22 October 2026** passed **26 PostgreSQL checks**: thirteen ordered-key checks, four full-row checks, four scalar/fixture checks, three expected query rejections, and two cleanup assertions. The [original evidence](evidence.txt) records separate backend PIDs for the exercise and fresh cleanup check. ROLLBACK removed every study object and row.

Explain why the required joins preserve the six tickets, how aliasing separates reporter/assignee, why WHERE active drops unmatched rows, why the ON form retains an inactive stored assignment with NULL joined columns, and why duplicate names cannot identify a parent. Predict the self-join and one-to-many row counts, and distinguish historical ticket department from current asset department.

Continue with Step 11 when you can explain those observations without copying the expected results.
