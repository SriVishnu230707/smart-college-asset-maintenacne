# Step 6: enforce row-level validity

The [project contract](PROJECT_CONTRACT.md) defines the rules. This step implements their smallest useful constraint examples in the [disposable SQL lab](../labs/step-06/notes.md). It extends the [identifier decisions](IDENTIFIERS_AND_TYPES.md) with required values, valid ranges, allowed states, and business-key guards. Permanent application tables still belong to later migration work.

## Understand NULL before writing a rule

`NULL` means missing or unknown; it differs from zero, false, and an empty string. Ordinary comparisons with NULL yield UNKNOWN. Use `IS NULL` to find missing values and `IS [NOT] DISTINCT FROM` for a comparison that treats NULL as comparable. `WHERE` keeps only TRUE. See [comparison predicates](https://www.postgresql.org/docs/18/functions-comparison.html).

| Expression | Result |
|---|---|
| `NULL::integer >= 0` | UNKNOWN |
| `TRUE AND NULL::boolean` | UNKNOWN |
| `FALSE AND NULL::boolean` | FALSE |
| `TRUE OR NULL::boolean` | TRUE |
| `NOT NULL::boolean` | UNKNOWN |

These are SQL's three-valued logical operations. The lab evaluates and asserts every result. See [logical operators](https://www.postgresql.org/docs/18/functions-logical.html).

A CHECK rejects FALSE and accepts UNKNOWN, so pair required-value checks with NOT NULL. The deliberate `nullable_stock_probe` accepts a NULL balance under `CHECK (stock_quantity >= 0)`; the project example rejects it. See [check constraints](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS).

## Give each project rule an explicit mechanism

| Project field or rule | Chosen guard in the lab |
|---|---|
| Part stock and reorder level | `integer NOT NULL DEFAULT 0`, separate named `CHECK (value >= 0)` constraints |
| Part quantity used | `integer NOT NULL`, `CHECK (quantity_used > 0)` |
| Asset status | Required; default `active`; allow `active`, `under_maintenance`, `retired` |
| Ticket status | Required; default `open`; allow `open`, `assigned`, `in_progress`, `awaiting_verification`, `closed`, `rejected` |
| Ticket priority | Required, deliberately no default; allow `low`, `medium`, `high`, `critical` |
| User role | Required, no default; allow `student`, `technician`, `department_admin`, `super_admin` |
| Department membership | Nullable UUID plus `CHECK (role = 'super_admin' OR department_id IS NOT NULL)` |
| User activation / part archival | Required booleans with defaults `true` / `false` |
| Department name; ticket title and description | Required and not entirely whitespace |
| Department/category/asset codes and part SKUs | Required, nonblank, canonical uppercase, independent UNIQUE constraints |
| Normalized user email | Required, lowercase, no whitespace, independent UNIQUE constraint |
| One consolidated part line per work order | Composite primary key `(work_order_id, spare_part_id)`; both required |

Role plus department presence is a same-row condition: a Super Admin may omit the department; the other roles cannot. Whether a supplied department exists is a Step 7 foreign-key question. Whether a technician is active and eligible for a particular ticket is a later authorization/transaction question.

The existing work-order states remain `draft`, `in_progress`, and `completed`. When the permanent work-order table is built, apply the same required status/allowed-value pattern, with `draft` as the initial default. This reduced lab uses assets and tickets to demonstrate status constraints.

For example, stock needs all three independent choices:

```sql
stock_quantity integer
    CONSTRAINT nn_spare_parts_stock NOT NULL DEFAULT 0,
CONSTRAINT ck_spare_parts_stock CHECK (stock_quantity >= 0)
```

Zero is a valid starting balance. NULL is unknown stock, which the contract disallows. Negative is a known invalid balance. A positive requested quantity does not establish that stock is available for completion.

## Compare a default with a requirement

A default supplies an omitted value or an explicit SQL `DEFAULT`; it does not replace explicit NULL. Constraints still validate supplied/defaulted values. See [default values](https://www.postgresql.org/docs/18/ddl-default.html).

| Input | Nullable comparison balance, `DEFAULT 0` | Project balance, `NOT NULL DEFAULT 0` |
|---|---|---|
| Omit the field | 0 | 0 |
| Send `DEFAULT` | 0 | 0 |
| Send NULL | NULL | Reject, SQLSTATE `23502` |
| Send -1 | Reject by CHECK | Reject by CHECK |

The lab also proves explicit `false` user activation remains false. Mandatory priority and department name have no default: omission fails instead of silently choosing business information. Defaults establish initial values; they do not enforce state transitions or maintain later values automatically.

## Protect business identity and composite identity

The chosen code normalization remains trim surrounding spaces and uppercase. Writers normalize first; database CHECKs reject noncanonical or blank stored values. They do not transform input. All five business identities have independent uniqueness guards, so generating another UUID cannot bypass a duplicate code, SKU, or normalized email.

The email guard checks canonical storage form, not full email-address syntax or ownership. The code guards establish the current format, not a complete college labeling grammar. Full uniqueness on retained records includes archived/retired records. Preserving old labels after a future code correction still needs the historical-label policy described in Step 4.

A composite primary key prevents the same work-order/part pair twice. Reusing the part on another order, or adding a different part to the same order, is valid. Ordinary UNIQUE permits multiple NULLs; `UNIQUE NULLS NOT DISTINCT` changes that treatment in PostgreSQL. These are separate comparison tables; business identifiers remain NOT NULL. See [unique constraints and primary keys](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS).

## Read a rejection precisely

Use `nn_`, `ck_`, `uq_`, and `pk_` prefixes for required-value, CHECK, UNIQUE, and primary-key names. Names support inspection and later migration/error mapping; they do not imply a constraint evaluation order.

| SQLSTATE | Meaning | Lab diagnostic assertion |
|---|---|---|
| `23502` | NOT NULL violation | Expected column name |
| `23514` | CHECK violation | Expected named CHECK |
| `23505` | Uniqueness violation | Expected UNIQUE or primary-key name |

See [PostgreSQL error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html). The lab submits one targeted violation at a time and asserts structured diagnostics rather than parsing English messages.

Observed on PostgreSQL 18.6: NOT NULL errors leave `CONSTRAINT_NAME` empty and identify `COLUMN_NAME`, even when explicitly named. The catalog still exposes those names with `contype = 'n'`; the lab inspects this alongside `c`, `u`, and `p`. See [pg_constraint](https://www.postgresql.org/docs/18/catalog-pg-constraint.html) and the [actual evidence](../labs/step-06/evidence.txt).

## Keep the enforcement boundary clear

CHECKs validate current row values on writes. They cannot by themselves enforce transition history, completed-record immutability, ledger equality, stock allocation across concurrent repairs, or eligibility based on other records. The negative UPDATE experiment proves the stock guard applies after insertion too; successful row validation alone does not authorize a stock change. See [CHECK limitations](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS).

The [Step 5 raw-money policy](MONEY_AND_TIME.md) also remains unchanged: a CHECK on an already scaled `NUMERIC(12,2)` cannot recover excess original precision that conversion rounded away. Every application/import path must validate raw money before scaled storage. This lab does not add production monetary-write protection.

The [Step 6 lab](../labs/step-06/notes.md) records 48 successful PostgreSQL checks, including 37 expected rejections, and rolls all objects back. The [Step 7 decisions](REFERENTIAL_INTEGRITY.md) and [lab](../labs/step-07/notes.md) now add referential integrity and deletion policies.
