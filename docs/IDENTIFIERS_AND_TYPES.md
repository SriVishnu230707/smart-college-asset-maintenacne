# Step 4: identifiers and ordinary types

This decision record turns the [relational model](RELATIONAL_MODEL.md) into choices for identifiers and ordinary column types. The [Step 4 lab](../labs/step-04/notes.md) verifies them in a disposable PostgreSQL schema. Money/timestamps, complete row validation, and referential/deletion policies are Steps 5-7.

## 1. Give technical and business identity separate jobs

| Identity | Project choice | Purpose |
|---|---|---|
| Entity primary key | PostgreSQL `uuid` | Stable internal identity for references |
| Department code | `varchar(20) NOT NULL UNIQUE` | College-facing identity such as `CSE` |
| Category code | `varchar(30) NOT NULL UNIQUE` | Shared catalog identity such as `PROJECTOR` |
| Asset code | `varchar(50) NOT NULL UNIQUE` | Inventory label such as `PRJ-001` |
| Part SKU | `varchar(50) NOT NULL UNIQUE` | Part catalog identity such as `LAMP-001` |
| User email | Normalized `text NOT NULL UNIQUE` | Account identity independent of display name |
| Work-order/part link | Composite key `(work_order_id, spare_part_id)`, both UUIDs | One consolidated use of each part per work order |

A **surrogate key** is an identifier with no business meaning. A **natural/business key** identifies the subject in its business context; its value may be assigned by the college rather than supplied by nature. A UUID primary key and an asset code answer different questions.

For example, these two attempted rows still describe the same business asset:

```text
id = UUID-A, asset_code = PRJ-001
id = UUID-B, asset_code = PRJ-001
```

Distinct UUIDs satisfy neither the business uniqueness rule nor the requirement to reject duplicate inventory labels. Keep both `PRIMARY KEY (id)` and `UNIQUE (asset_code)`. Conversely, a new asset code cannot make a duplicate UUID primary key acceptable. UUID generation makes accidental collisions unlikely; the primary key remains the database guarantee for stored rows.

The initial code convention is trimmed uppercase for department/category/asset codes and SKUs. Normalize input before checking/inserting it. Plain `varchar` and `UNIQUE` do not themselves convert `" prj-001 "` to `PRJ-001`; Step 6 will define the database validity checks. The lab normalizes its duplicate-code input explicitly.

Retirement/archive preserves the original record and its business code. The contract forbids assigning a historical asset code or SKU to another entity. A future code-correction feature must also preserve/reserve the old label; a simple update that frees it for reuse would be insufficient. The UUID remains independent of that business-label policy.

## 2. Choose UUID generation, and document the alternative

Use a database default of `gen_random_uuid()` for entity IDs. PostgreSQL generates a version 4 UUID when an insert omits the ID or requests `DEFAULT`. This keeps ordinary SQL clients working as well as future application clients. No extension is required for this built-in function in PostgreSQL 18. See [UUID functions](https://www.postgresql.org/docs/18/functions-uuid.html).

An application may generate its UUID before insertion and provide it explicitly. The column's ordinary default permits that supplied value. Step 4 generates a real client-side UUID using PowerShell's `[guid]::NewGuid()` and verifies that PostgreSQL preserves it. The equivalent Python idea is `uuid.uuid4()`; the lab does not require a Python installation. References: [Guid.NewGuid](https://learn.microsoft.com/en-us/dotnet/api/system.guid.newguid), [Python uuid](https://docs.python.org/3/library/uuid.html).

A PostgreSQL UUID column stores a UUID value, not a 36-character string. Its type accepts UUID versions beyond v4; the default chooses a generator, not a version-validation constraint. References: [UUID type](https://www.postgresql.org/docs/18/datatype-uuid.html).

| Option | Benefits for this project | Costs / limitations | Decision |
|---|---|---|---|
| UUIDv4 with a database default and optional client-supplied value | Same ID format across clients; a client can know an ID before writing; no central numeric allocation needed for client generation | Larger values than integer keys; random key distribution; randomness is not a uniqueness constraint | Initial entity-key choice |
| UUIDv7 | PostgreSQL 18 offers time-ordered UUID generation | Encodes time information; generator and ordering behavior must be understood; not an authoritative business-event timestamp | Compare in the lab; retain v4 initially |
| `bigint GENERATED ALWAYS AS IDENTITY` plus a primary key | Compact numeric IDs allocated by the database; simple for a single database | Explicit IDs require a special override; allocated values can have gaps; independent databases can allocate overlapping numbers | Valid alternative, not the selected entity-ID policy |
| Business code as the primary key | Directly meaningful reference | Couples references to business formatting/correction policies | Keep as an independent unique key |

The lab measures UUID, bigint, and integer value sizes, not total row or index size. It is not a performance benchmark. UUIDv7's time ordering is documented behavior; no workload speed claim is made here.

## 3. Distinguish application values from server defaults

```text
Application generation:
    client creates UUID -> sends INSERT with that UUID -> PostgreSQL stores it

Server generation:
    client sends INSERT without ID -> PostgreSQL evaluates its DEFAULT -> returns UUID
```

A future ORM-side callable default only runs through the relevant application path. It does not automatically install a database default for `psql` or another client. Later SQLAlchemy mapping must represent the chosen server default explicitly. Defaults versus explicit `NULL` are explored in Step 6. Reference: [SQLAlchemy client and server defaults](https://docs.sqlalchemy.org/en/21/core/defaults.html).

For the initial database definition, the pattern is:

```sql
id uuid DEFAULT gen_random_uuid() PRIMARY KEY
```

UUID generation does not authorize a caller to read or change the identified record. Access still follows the resource permissions in the [project contract](PROJECT_CONTRACT.md).

## 4. Understand identity integers before rejecting or choosing them

An identity column draws values from an implicit sequence:

```sql
id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY
```

`ALWAYS` rejects ordinary explicit-value insertion; `OVERRIDING SYSTEM VALUE` is an intentional escape hatch. `BY DEFAULT` permits an explicit value. Providing an explicit value does not advance the underlying sequence to that number, so mixing manual and generated values requires care.

Identity generation does not itself guarantee uniqueness; retain the primary key. Sequence allocations are not undone when an insert fails or its transaction aborts. In the lab, a failed duplicate-label insert consumes value 2, leaving successful IDs 1 and 3. Do not treat an identity as a gapless invoice number or derive row counts from its maximum. References: [identity columns](https://www.postgresql.org/docs/18/ddl-identity-columns.html), [sequence behavior](https://www.postgresql.org/docs/18/functions-sequence.html).

## 5. Choose ordinary text and boolean types

These limits are initial project decisions, not limits required by PostgreSQL or proof that a value is meaningful.

| Field group | Chosen type | Reason |
|---|---|---|
| Department name | `varchar(150)` | A bounded display label |
| Category name | `varchar(100)` | A bounded catalog label |
| User display name, asset name, supplier name, part name | `varchar(150)` | Bounded display labels; names need not be unique |
| Asset location | `varchar(200)` | A bounded human-readable location |
| Ticket title | `varchar(200)` | A bounded summary |
| Ticket descriptions, comments, completion/rejection/rework notes | `text` | Free-form content without an arbitrary small database limit |
| Normalized email and encoded password hash | `text` | No arbitrary display-label cap; separate validation/storage rules apply |
| Role, status, and priority names | `text` | Value sets will be constrained in Step 6; native enums are a later comparison |
| User activation | `boolean NOT NULL DEFAULT true` | New users are active unless explicitly set otherwise |
| Catalog archival flags | `boolean NOT NULL DEFAULT false` | New records begin unarchived |
| Stock, reorder levels, and part quantities | `integer` | Whole units; nonnegative/positive conditions belong to Step 6 |

Use `varchar(n)` to express a chosen length restriction, not as a speed optimization over `text`. Avoid fixed-width `char(n)` for these labels; its space padding is not useful here. [PostgreSQL character types](https://www.postgresql.org/docs/18/datatype-character.html).

Length is measured in characters, not UTF-8 bytes. The lab stores four `é` characters in `varchar(4)` and observes four characters but eight bytes. A normal insert of five non-space characters fails with SQLSTATE `22001`. An explicit cast such as `'ABCDE'::varchar(4)` instead truncates to `ABCD`; do not use that cast as input validation. PostgreSQL also permits truncation when excess assignment characters are spaces, so validate the original business input deliberately.

Use actual boolean values in application data. `psql` normally displays stored booleans as `t` and `f`. Omission invokes a default; supplying `false` remains false even when the default is true. PostgreSQL also has boolean `NULL`, which the chosen required flags reject; fuller NULL semantics are Step 6. Reference: [boolean type](https://www.postgresql.org/docs/18/datatype-boolean.html).

## 6. Verification boundary

The [executed lab](../labs/step-04/notes.md) tests server/client UUID generation, duplicate business keys with fresh IDs, duplicate UUIDs with different codes, identity alternatives and gaps, malformed UUID rejection, string length behavior, and boolean defaults. It uses reduced department/asset/part tables and comparison tables, then rolls them all back.

These decisions do not install the complete application schema or replace later migration ownership. The [Step 5 decisions](MONEY_AND_TIME.md) add exact money and timezone-aware timestamps; Steps 6-7 cover the remaining validity/reference rules.
