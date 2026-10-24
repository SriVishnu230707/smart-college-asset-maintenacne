# Step 12: ask existence questions

The [Step 12 lab](../labs/step-12/notes.md) finds unused assets and technicians with assigned tickets. It compares subqueries, joins, and set operations against handwritten expected rows. These are read queries over disposable projections of the [relational model](RELATIONAL_MODEL.md).

## Correlate the question with the outer row

```sql
SELECT a.asset_code
FROM assets AS a
WHERE NOT EXISTS (
    SELECT 1 FROM maintenance_tickets AS t
    WHERE t.asset_id = a.id
)
ORDER BY a.asset_code COLLATE "C";
```

The reference to `a.id` correlates the subquery with the current asset. The fixture returns PC-003: every other asset has at least one ticket, including terminal history. Omitting that reference asks whether any ticket exists anywhere; because six do, the incorrect NOT EXISTS query returns no assets.

EXISTS tests whether a subquery returns any row; NOT EXISTS tests that it returns none. It does not multiply outer rows when several matches exist. A selected NULL still constitutes a row. See [subquery expressions](https://www.postgresql.org/docs/18/functions-subquery.html).

Two alternatives return the same PC-003:

```sql
SELECT a.asset_code
FROM assets AS a
LEFT JOIN maintenance_tickets AS t ON t.asset_id = a.id
WHERE t.id IS NULL
ORDER BY a.asset_code COLLATE "C";
```

```sql
SELECT asset_code
FROM (
    SELECT asset_code FROM assets
    EXCEPT
    SELECT a.asset_code
    FROM assets AS a JOIN maintenance_tickets AS t ON t.asset_id = a.id
) AS unused
ORDER BY asset_code COLLATE "C";
```

The anti-join checks the child's nonnullable primary key. Checking nullable `t.assigned_to_id` would also select a real unassigned ticket. The EXCEPT query projects unique asset codes, preserving this project's independent business identities. Compare the results without assuming one formulation is universally faster; query-plan analysis comes later.

## Distinguish a scalar value from a row-existence test

A scalar subquery supplies one column from at most one returned row. An empty result becomes NULL; multiple returned rows are an error. It may also refer to the outer row. See [scalar subqueries](https://www.postgresql.org/docs/18/sql-expressions.html#SQL-SYNTAX-SCALAR-SUBQUERIES).

```sql
SELECT a.asset_code,
       (SELECT count(*) FROM maintenance_tickets AS t
        WHERE t.asset_id = a.id) AS tickets
FROM assets AS a
ORDER BY a.asset_code COLLATE "C";
```

| Asset | Hand-counted tickets |
|---|---|
| PC-001 | 1 |
| PC-002 | 2 |
| PC-003 | 0 |
| PRJ-001 | 2 |
| PRJ-002 | 1 |

The ungrouped COUNT produces one scalar row even for no matches. Filtering that count to zero finds PC-003 too. Conversely, `EXISTS (SELECT count(*) FROM maintenance_tickets WHERE false)` is TRUE because the aggregate still returns its one row. Use `EXISTS (SELECT 1 ... WHERE ...)` to ask about matching tickets. This connects to [Step 11 empty-input aggregates](SQL_AGGREGATION.md).

A unique department-code lookup returns CSE; an UNKNOWN-code lookup returns NULL. A scalar lookup of all CSE user emails fails with `21000`, rather than choosing one arbitrarily. Adding an arbitrary LIMIT would change the question instead of establishing uniqueness.

## Define what assigned work means

```sql
SELECT u.email
FROM users AS u
WHERE u.role = 'technician' AND u.is_active
  AND EXISTS (
      SELECT 1 FROM maintenance_tickets AS t
      WHERE t.assigned_to_id = u.id
        AND t.status IN ('assigned', 'in_progress', 'awaiting_verification')
  )
ORDER BY u.id;
```

This report means nonterminal assigned tickets, including those awaiting verification. It returns Ravi and Nila once each. A raw matching inner join returns Ravi twice; DISTINCT on the joined user identity restores one row per technician.

Retained assignment history also includes inactive Mira and active Leela, whose only tickets are closed. Active technicians with no current assigned tickets are Omar and Leela; only Omar has never had an assignment. The distinction follows the [history and lifecycle contract](PROJECT_CONTRACT.md). These reports do not implement the later authorized assignment operation or prove a technician is eligible for a particular department's ticket.

## Reproduce the nullable NOT IN trap

For the question of no assignment ever, this query is incorrect on the fixture:

```sql
SELECT u.email
FROM users AS u
WHERE u.role = 'technician' AND u.is_active
  AND u.id NOT IN (SELECT t.assigned_to_id FROM maintenance_tickets AS t)
ORDER BY u.id;
```

T1 supplies a NULL assignee. Ravi has an equal match, so his predicate is FALSE. Omar has no equal match but encounters NULL, so his result is UNKNOWN; WHERE does not retain it. The query returns nobody. See [NOT IN semantics](https://www.postgresql.org/docs/18/functions-subquery.html#FUNCTIONS-SUBQUERY-NOTIN).

The direct correction returns Omar:

```sql
SELECT u.email
FROM users AS u
WHERE u.role = 'technician' AND u.is_active
  AND NOT EXISTS (
      SELECT 1 FROM maintenance_tickets AS t
      WHERE t.assigned_to_id = u.id
  )
ORDER BY u.id;
```

Filtering `assigned_to_id IS NOT NULL` inside NOT IN also agrees here because the outer `u.id` is a nonnullable primary key. This is a qualified equivalence, not a rule about arbitrary nullable expressions. The lab separately observes NULL on the left against nonempty values as UNKNOWN, but NOT IN against an empty result as TRUE. An empty assignment result includes all four active technicians.

## Combine complete result rows

Let O be assets with an open ticket: PRJ-001. Let C be assets with a nonterminal assigned ticket: PC-001, PC-002, PRJ-001. Each input uses EXISTS, so each asset appears once before combination.

| Operation | Hand-predicted asset codes in final C order |
|---|---|
| O UNION C | PC-001, PC-002, PRJ-001 |
| O UNION ALL C | PC-001, PC-002, PRJ-001, PRJ-001 |
| O INTERSECT C | PRJ-001 |
| All ticketed assets EXCEPT C | PRJ-002 |

UNION removes duplicate projected rows; UNION ALL preserves them. INTERSECT selects common rows and EXCEPT selects left-only rows. Inputs must have the same column count and compatible corresponding types. Use parentheses when mixing operations, and apply explicit ORDER BY to the final result. See [combining queries](https://www.postgresql.org/docs/18/queries-union.html).

PRJ-002 has historical tickets only; PC-003 has never had a ticket. Those are different sets. The SQL wraps combined rows in a derived table so the final `ORDER BY asset_code COLLATE "C"` sorts the complete result. Set operations compare all projected columns; using unrelated display names alone could collapse distinct identities.

The [executed evidence](../labs/step-12/evidence.txt) records 31 passing checks: twenty-five exact row comparisons, three expected scalar/set errors, one fixture assertion, and two cleanup assertions. All study objects are rolled back, and another connection confirms absence. Python database layers and SQLAlchemy begin with Step 13.
