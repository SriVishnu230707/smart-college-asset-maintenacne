# Step 5: money and time

This record defines monetary precision, Python representations, event timestamps, and reporting dates for the [project contract](PROJECT_CONTRACT.md). The [Step 5 lab](../labs/step-05/notes.md) verifies the decisions in PostgreSQL and Python. It leaves no permanent application schema behind.

## 1. Choose exact monetary values

The first version uses INR only. Use PostgreSQL `NUMERIC(12,2)` for standard part unit prices, completed part-price snapshots, and labor costs. Precision 12 includes two fractional digits, leaving ten integer digits. The chosen nonnegative range is `0.00` through `9999999999.99`; an individual repair total must also fit that range.

Use Python `Decimal` created from decimal strings or another `Decimal`. Avoid binary floating-point money and `Decimal(float_value)`, which carries the float's approximation into the decimal value. Exact multiplication by integer quantities and addition of validated two-place amounts need no rounding in this workflow. Reference: [Python Decimal](https://docs.python.org/3/library/decimal.html).

```text
labor:                100.00
2 lamps * 250.10:      500.20
3 fuses *   0.10:        0.30
repair total:         600.50 INR
```

Prices are frozen at completion. Historical totals use `unit_cost_at_use`, not the current catalog price. The lab changes the lamp catalog price to 300.00 and confirms the old repair remains 600.50. Full immutability and atomic completion are implemented in later workflow lessons.

Report aggregates can exceed the individual-repair range. Keep `SUM` results as wider `numeric`/`Decimal` values rather than casting a college-wide total back to `NUMERIC(12,2)`. The lab sums two maximum-size amounts to `19999999999.98` exactly. [PostgreSQL numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html).

## 2. Reject excess precision before storage

The contract's policy is **reject, rather than round, monetary input with more than two fractional places**. This includes trailing third-place zeros: `1.230` is rejected. Inputs with fewer places, such as `0` or `1.2`, are accepted and formatted as `0.00` or `1.20` without changing value. Reject negative, nonfinite, missing, malformed, and out-of-range values too.

`NUMERIC(12,2)` alone does not enforce that input policy: PostgreSQL converts `1.005` to `1.01`. A Python half-even quantization can produce `1.00` for the same decimal. Neither is the accepted business outcome; the original input must fail validation.

Validate the original unconstrained decimal **before** assignment or casting to the scaled storage column. A `CHECK` on an already coerced `NUMERIC(12,2)` value cannot recover the discarded input digits. Step 5's SQL helper takes unconstrained `numeric`; its Python counterpart checks the original Decimal exponent before quantizing an accepted value.

All application input, completion, and future import paths must apply that raw-input policy. The helper is an executable lab example, not a trigger securing arbitrary direct inserts. If every SQL writer must reject original scale at the database boundary, later schema/interface work must use an appropriate raw-numeric validation boundary, such as a restricted write function or an unconstrained numeric/domain with checks before scaled conversion. Row constraints and database privileges are examined in later steps.

## 3. Match Python and future ORM representations

| Meaning | PostgreSQL | Python | Intended later SQLAlchemy mapping |
|---|---|---|---|
| Unit/labor cost | `NUMERIC(12,2)` | `Decimal` | `Numeric(12, 2, asdecimal=True)` |
| Report aggregate | Wider `numeric` expression | `Decimal` with sufficient arithmetic precision | Numeric result projection |
| Event instant | `timestamptz` / `timestamp with time zone` | Aware `datetime` | `DateTime(timezone=True)` |
| Calendar-only fact | `date` | `date` | `Date()` |

The ORM type declaration does not replace input validation. In particular, require an aware datetime explicitly; a timezone-enabled column is not an application-level naive-input validator. Reference: [SQLAlchemy types](https://docs.sqlalchemy.org/en/21/core/type_basics.html).

For the future driver lesson, Psycopg documents Decimal/numeric and aware-datetime/timestamptz adaptation. This lab currently uses `psql` and an explicit JSON transport: PostgreSQL exports monetary and timestamp strings, and Python parses them into `Decimal` and aware `datetime`. Driver and ORM integration follow when those layers are introduced. Reference: [Psycopg adaptation](https://www.psycopg.org/psycopg3/docs/basic/adapt.html).

Serialize API money as fixed two-place strings, such as `"600.50"`, and event times as offset-aware ISO strings, preferably UTC with `Z`. Converting cost to a JSON floating-point number would undo the deliberate exact-decimal boundary.

## 4. Model events as instants

Use `timestamptz` for ticket creation/assignment/rejection/closure, work-order completion, inventory movement, and audit instants. An event that has not occurred has a nullable lifecycle timestamp, with the conditional rules explored in Step 6. Preserve the original completion instant on retries and rework history.

Store an instant and normally run application database sessions in UTC. PostgreSQL displays that instant using the session timezone; it does not preserve the caller's original timezone name. Keep an additional zone field only if a future requirement actually needs the original named zone. [PostgreSQL date/time types](https://www.postgresql.org/docs/18/datatype-datetime.html).

These inputs describe the same instant:

```text
2026-10-21T18:30:00+00:00
2026-10-22T00:00:00+05:30
```

Require an explicit offset/aware datetime at the event boundary. An offset-free timestamp converted to `timestamptz` is interpreted in the session timezone. A `timestamp without time zone` literal can discard a supplied offset; it is unsuitable for these event columns.

Use a `date` only for a genuine calendar fact, if introduced, or for a derived reporting day. A date has no clock time or offset; turning it into an event requires additional business information, not an automatic assumption of midnight.

Creation defaults may use `CURRENT_TIMESTAMP`, which represents transaction start. Do not assume it is a fresh wall-clock reading on every statement or an automatic `updated_at` mechanism. Event capture and update behavior must be defined in the relevant use case. Reference: [current date/time functions](https://www.postgresql.org/docs/18/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT).

## 5. Report in an explicit named timezone

The reporting timezone is `Asia/Kolkata`. Derive the local day deliberately:

```sql
(completed_at AT TIME ZONE 'Asia/Kolkata')::date
```

Casting `completed_at::date` instead depends on the session timezone. A user changing the display timezone must not silently reassign events to different reporting days. Keep department attribution from the ticket's recorded department, as established in [Step 3](RELATIONAL_MODEL.md).

| Event | UTC | Asia/Kolkata | Cost |
|---|---|---|---|
| BEFORE | 21 Oct 2026, 18:29:59 | 21 Oct 2026, 23:59:59 | 0.10 |
| REPAIR-EXACT | 21 Oct 2026, 18:30:00 | 22 Oct 2026, 00:00:00 | 600.50 |
| LAST-SECOND | 22 Oct 2026, 18:29:59 | 22 Oct 2026, 23:59:59 | 0.20 |
| NEXT-DAY | 22 Oct 2026, 18:30:00 | 23 Oct 2026, 00:00:00 | 0.30 |

The local totals are 0.10 on October 21, 600.70 on October 22, and 0.30 on October 23. The lab checks the same grouping before and after changing the session timezone and confirms the epoch of the stored repair instant is unchanged.

For one reporting day, interpret the start and the next day's start in the named zone, then use a half-open interval:

```sql
WHERE completed_at >= (timestamp '2026-10-22 00:00:00' AT TIME ZONE 'Asia/Kolkata')
  AND completed_at <  (timestamp '2026-10-23 00:00:00' AT TIME ZONE 'Asia/Kolkata')
```

The end boundary belongs to the following day. In Python, use `ZoneInfo('Asia/Kolkata')`, convert an instant with `astimezone()`, and derive its date after conversion. Construct each local-day boundary in the reporting zone before converting it to UTC. References: [AT TIME ZONE](https://www.postgresql.org/docs/18/functions-datetime.html#FUNCTIONS-DATETIME-ZONECONVERT), [Python aware datetimes](https://docs.python.org/3/library/datetime.html), [ZoneInfo](https://docs.python.org/3/library/zoneinfo.html).

## 6. Verification and next steps

The [Step 5 lab](../labs/step-05/notes.md) and [captured evidence](../labs/step-05/evidence.txt) contain the live SQL/Python proof, invalid-input cases, matching daily totals, and rollback/reconnection cleanup. The four study tables and SQL input helper are discarded afterward. Full application constraints, authorization, and immutable completion enforcement are later steps.
