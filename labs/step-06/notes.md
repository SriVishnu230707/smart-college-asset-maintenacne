# Step 6: enforce row-level validity

Read the [row-validity decisions](../../docs/ROW_VALIDITY.md) first. This lab proves the database rejects invalid values submitted directly through psql, including NULL cases that an ordinary CHECK would permit.

## Run the lab

Use the [Step 2 environment](../step-02/notes.md). With Docker Desktop running, execute from PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-06\verify.ps1 -WriteEvidence
```

No Python or additional package is needed. The [verifier](verify.ps1) runs [query.sql](query.sql) through authenticated psql, then [reconnect.sql](reconnect.sql) through a new connection. It saves [evidence.txt](evidence.txt) only after both succeed. Without `-WriteEvidence`, it prints the proof without replacing the saved transcript.

To study the same SQL interactively:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```sql
\i /labs/step-06/query.sql
\i /labs/step-06/reconnect.sql
\quit
```

The exercise refuses to touch an existing `college_step06` schema. It creates seven reduced project tables and three deliberately weaker/comparison tables inside one transaction. Its UUID links are illustrative values: foreign keys, full application columns, and permanent schema ownership are later lessons. Everything, including the verification helper, is rolled back.

## Trace the positive observations

1. The truth-table expressions return TRUE, FALSE, or UNKNOWN as expected. `WHERE balance = NULL` finds nothing; `IS NULL` finds the missing value.
2. A nullable `CHECK (stock_quantity >= 0)` accepts explicit NULL. Its default supplies zero only when omitted; the required project column rejects NULL.
3. Initial asset/ticket states, zero balances/reorder levels, and boolean defaults are accepted. Explicit boolean choices and explicit SQL `DEFAULT` behave as specified.
4. A student has a department; a Super Admin can omit it. This is a same-row presence rule.
5. Three part lines show both a shared order with different parts and a shared part across different orders. Only the pair must be unique.
6. Ordinary nullable UNIQUE accepts two NULL values. The `NULLS NOT DISTINCT` comparison accepts its first NULL and rejects the second.

## Explain every rejected input

The 37 negative attempts below use otherwise valid values to target the stated rule. SQLSTATE `23514` means CHECK, `23502` means NOT NULL, and `23505` means uniqueness. See [official error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html).

| Attempt(s) | Expected rejecting rule | SQLSTATE | Count |
|---|---|---|---|
| Negative stock; negative reorder level | `ck_spare_parts_stock`; `ck_spare_parts_reorder` | `23514` | 2 |
| Explicit NULL stock; NULL reorder level | Required `stock_quantity`; `reorder_level` | `23502` | 2 |
| Zero; negative quantity used | `ck_work_order_parts_quantity` | `23514` | 2 |
| NULL quantity used | Required `quantity_used` | `23502` | 1 |
| Asset status `broken` | `ck_assets_status` | `23514` | 1 |
| NULL asset status despite its default | Required `status` | `23502` | 1 |
| Ticket status `approved` | `ck_tickets_status` | `23514` | 1 |
| NULL ticket status | Required `status` | `23502` | 1 |
| Priority `urgent`; omitted priority | `ck_tickets_priority`; required `priority` | `23514`; `23502` | 2 |
| Whitespace-only title; empty description | `ck_tickets_title`; `ck_tickets_description` | `23514` | 2 |
| Repeated department/category/asset code, SKU, email | `uq_departments_code`, `uq_categories_code`, `uq_assets_asset_code`, `uq_spare_parts_sku`, `uq_users_email` | `23505` | 5 |
| Lowercase asset code; padded SKU; blank asset code | `ck_assets_asset_code`; `ck_spare_parts_sku`; `ck_assets_asset_code` | `23514` | 3 |
| NULL asset code | Required `asset_code` | `23502` | 1 |
| Noncanonical email; blank email | `ck_users_email` | `23514` | 2 |
| Unknown role; NULL role | `ck_users_role`; required `role` | `23514`; `23502` | 2 |
| Student with no department | `ck_users_department` | `23514` | 1 |
| NULL activation despite its default | Required `is_active` | `23502` | 1 |
| Omitted department name | Required `name` | `23502` | 1 |
| Repeated work-order/part pair; NULL order key | `pk_work_order_parts`; required `work_order_id` | `23505`; `23502` | 2 |
| Repeated non-NULL optional code | `uq_nullable_unique_probe` | `23505` | 1 |
| Second NULL with NULLS NOT DISTINCT | `uq_nulls_not_distinct_probe` | `23505` | 1 |
| Negative balance in the nullable comparison | `ck_nullable_stock_probe` | `23514` | 1 |
| UPDATE existing stock to -1 | `ck_spare_parts_stock` | `23514` | 1 |

The `expect_rejection` function is verification plumbing. Each call actually executes its literal INSERT or UPDATE in PostgreSQL. A nested PL/pgSQL exception block rolls back that statement, asserts the expected SQLSTATE and constraint/column, and returns one PASS. Unexpected rejection diagnostics or accepted bad data fail the exercise.

On this PostgreSQL 18.6 server, NOT NULL diagnostics identify the column and omit the constraint name. Those calls assert the column. CHECK and uniqueness calls assert the exact constraint name. The final catalog query independently displays the explicit NOT NULL name, plus named CHECK, UNIQUE, and composite primary-key definitions. Diagnostic notices and query results can interleave because psql uses separate stdout/stderr streams.

## Recorded outcome and limits

The live run passed on 22 October 2026: **48 PostgreSQL checks**, comprising 37 expected rejections and 11 successful assertions covering valid observations, metadata, unchanged fixtures, and cleanup. See [original output](evidence.txt). The rejected inserts created no extra rows, and the rejected UPDATE left both balances at zero. A new connection confirmed that the schema was absent.

This establishes executable row-validity examples. It does not establish stock/ledger equality, completion concurrency, valid workflow transitions, historical immutability, user authorization, or foreign-key enforcement. Draft part quantities do not reserve stock; the positive lines are valid even while the demonstrated balance is zero.

## Explain before advancing

1. Why does `CHECK (stock_quantity >= 0)` accept NULL, and which additional constraint rejects it?
2. Why do `WHERE quantity = NULL` and `WHERE quantity IS NULL` give different results?
3. How do omission, explicit `DEFAULT`, explicit NULL, and an explicit false value differ?
4. Why does mandatory priority have no default in this example?
5. Which constraint rejects each negative attempt above? Which diagnostic fields can this server provide?
6. Why do fresh UUIDs not permit duplicate business identifiers? Why reject noncanonical storage too?
7. Why can the same part appear on two different orders while the same pair cannot repeat?
8. How do ordinary UNIQUE, NULLS NOT DISTINCT, and a required composite primary key handle NULL?
9. Why does an allowed status value not establish that a transition to it was authorized?
10. Which rules still need foreign keys, transactions, or protected history instead of a same-row CHECK?

Continue with Step 7 in the [learning path](../../docs/LEARNING_PATH.md) when you can explain the evidence without copying it.
