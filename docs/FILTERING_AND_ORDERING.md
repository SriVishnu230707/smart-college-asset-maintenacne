# Step 9: filter and order rows deliberately

The [Step 9 lab](../labs/step-09/notes.md) turns query intent into explicit predicates, search patterns, typed expressions, and a complete row order. Its fixtures are disposable projections of assets, technicians, and tickets, plus a separate text comparison table. Full application columns and department reference graphs remain defined by the earlier model; this lab does not install permanent tables or authorization.

## State the intended list before writing its predicate

| Intended result | Predicate or rule | Executed result |
|---|---|---|
| All active study assets | `status = 'active'` | PC-001, PC-004, PRJ-001, PRJ-002 |
| Active CSE assets | Department equality AND active status | PC-001, PRJ-001 |
| Active or maintenance assets | `status IN ('active', 'under_maintenance')` | All except retired PC-003 |
| Every unassigned ticket | `assigned_to_id IS NULL` | T1, T2, T4, T5, including rejected T5 |
| CSE's actionable unassigned queue | CSE AND unassigned AND open | T1, T2 |

T1-T6 are teaching labels for UUIDs ending in 001-006, not new application business keys. The raw queries return full IDs.

WHERE keeps rows for which the predicate is TRUE. Use `IS NULL` for an absent assignee: `assigned_to_id = NULL` is UNKNOWN and returns no rows. See [WHERE](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-WHERE) and [NULL comparisons](https://www.postgresql.org/docs/18/functions-comparison.html).

The queue query is:

```sql
SELECT id, title, priority, created_at
FROM maintenance_tickets
WHERE department_id = '10000000-0000-4000-8000-000000000001'::uuid
  AND assigned_to_id IS NULL
  AND status = 'open'
ORDER BY created_at DESC, id ASC
LIMIT 2;
```

Unassigned does not itself mean open or actionable. Department scope is also a distinct predicate. The example expresses a selected department; later authenticated use cases must establish which scope the actor may request.

Parenthesize mixed AND/OR intent. The lab's CSE filter with `(priority = 'high' OR priority = 'critical')` returns T1 and T3. Removing the parentheses makes the OR's critical branch independent of the department condition and also returns ECE's T4. Parentheses or a scoped IN predicate preserve the department condition. See [operator precedence](https://www.postgresql.org/docs/18/sql-syntax-lexical.html#SQL-PRECEDENCE).

## Decide whether the search is case-sensitive or literal

| Search under the lab's explicit C collation | Expected matches |
|---|---|
| `name LIKE 'Lab%'` | PRJ-001: Lab Projector |
| `name ILIKE 'lab%'` | PC-001, PC-002, PRJ-001: lab/LAB/Lab prefixes |
| `name LIKE '%!%%' ESCAPE '!'` | PRJ-002: Projector 100% |
| `name LIKE '%!_%' ESCAPE '!'` | PC-004: Computer_Stand |

`%` matches any sequence and `_` one character. Escaping them requests a literal character. The probe shows unescaped `Lab_01` matches both Lab_01 and LabX01. ILIKE uses locale-aware case matching; the lab uses C collation and ASCII examples for reproducible case expectations. This does not choose a global application collation or establish Unicode search behavior. See [LIKE, ILIKE, and ESCAPE](https://www.postgresql.org/docs/18/functions-matching.html#FUNCTIONS-LIKE).

Names retain display case. Canonical business codes and allowed status values still follow the earlier [row-validity policy](ROW_VALIDITY.md); a search expression does not change stored values or uniqueness policy.

## Distinguish missing, empty, and space-only text

Required project names/titles remain nonblank. These cases are confined to `text_filter_probe`:

| Expression | Probe labels selected |
|---|---|
| `value = ''` | empty |
| `btrim(value) = ''` | empty, spaces |
| `nullif(btrim(value), '') IS NULL` | empty, null, spaces |
| `lower(btrim(value) COLLATE "C") = 'lab'` | lower, mixed, upper |

The label `null` identifies the row whose value is SQL NULL. It is not the string value `'null'`. `char_length('')` is zero, while length/trim/lower on NULL remain NULL. Grouping missing and blank values through NULLIF is an explicit query choice. Here btrim removes ordinary surrounding spaces; it is not a universal whitespace-normalization rule. See [string functions](https://www.postgresql.org/docs/18/functions-string.html) and [NULLIF](https://www.postgresql.org/docs/18/functions-conditional.html#FUNCTIONS-NULLIF).

## Use casts to express a real type

The known text values `'10'` and `'2'` sort in that lexical order under C collation. Sorting their integer casts yields 2 before 10. A UUID cast selects the intended technician assignment. An explicit `(created_at AT TIME ZONE 'UTC')::date` expression selects the five October 22 ticket instants without depending on the session's display zone.

A cast requires data the target type accepts: `'two'::integer` and `'not-a-uuid'::uuid` fail with SQLSTATE `22P02`. The numeric comparison selects only two known fixture values. SQL does not promise left-to-right AND evaluation, so a separate predicate must not be assumed to shield an unsafe cast on arbitrary text. See [casts and expression evaluation](https://www.postgresql.org/docs/18/sql-expressions.html) and the [money/time policy](MONEY_AND_TIME.md).

## Finish the order before applying LIMIT

Four ticket IDs share the newest creation timestamp. `ORDER BY created_at DESC` leaves their internal order unspecified. Adding unique `id ASC` defines T1, T2, T3, T4 within that tie, so LIMIT 2 selects T1 and T2. Choosing `id DESC` instead defines T4, T3, T2, T1. Both respect the same timestamp ordering; the ID direction is the deliberate tie policy. A UUIDv4 tie order is deterministic, not evidence of creation chronology.

The lab does not try to force an optimizer to return unstable rows. It demonstrates the tied input and asserts two explicit complete orders. Without ORDER BY there is no promised row order at all. See [sorting rows](https://www.postgresql.org/docs/18/queries-order.html).

Each sort key has its own direction/NULL policy. PostgreSQL defaults to NULLS LAST for ASC and NULLS FIRST for DESC. The assignee examples add `id ASC` to order equal/NULL assignees and demonstrate an explicit NULLS FIRST choice.

LIMIT applies to the ordered result: zero returns no rows, NULL removes the limit, and -1 fails with `2201W`. Validate the intended page size in later input handling. A complete order is necessary for predictable selection; it does not by itself freeze data between requests or implement concurrent pagination. See [LIMIT](https://www.postgresql.org/docs/18/queries-limit.html) and [error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html).

The [captured evidence](../labs/step-09/evidence.txt) records 37 successful PostgreSQL checks, including three expected invalid-input rejections and fresh-connection cleanup. All tables, fixtures, and helpers are rolled back. SQLAlchemy translation starts later; Step 10 next introduces joins and user aliases.
