# Step 4: choose identifiers and ordinary types

Deliverable: [identifier and type decisions](../../docs/IDENTIFIERS_AND_TYPES.md). This lesson keeps the UUID identity of an entity separate from its business code, then compares identifier generators and ordinary column types.

## Start with the required proof

Suppose `PRJ-001` is already recorded. A second insert supplies a freshly generated UUID and tries to use `PRJ-001` again. The new UUID is different, but the unique asset-code constraint must still reject the insert.

The reverse is also true: changing the asset code does not allow a duplicate UUID primary key. Technical identity and business identity each have an independent database rule.

## Run the lab

Using the [Step 2 PostgreSQL environment](../step-02/notes.md), run from PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-04\verify.ps1 -WriteEvidence
```

[verify.ps1](verify.ps1) generates a UUID in the PowerShell client, passes it as a `psql` variable, executes [query.sql](query.sql), then runs [reconnect.sql](reconnect.sql) through a separate connection. Successful output is saved to `evidence.txt`.

For an interactive replay:

```powershell
$applicationUuid = [guid]::NewGuid().ToString('D')
docker compose exec postgres sh /labs/step-02/psql.sh "--set=application_uuid=$applicationUuid"
```

```sql
\i /labs/step-04/query.sql
\quit
```

The `college_step04` schema contains reduced department/asset/part tables and three comparison tables for identity integers and ordinary types. It is created inside one transaction and rolled back. A pre-existing schema of that name is left untouched. No permanent application schema is installed.

## Read the experiments

| Experiment | Observation / rule |
|---|---|
| Omit an asset's UUID | The database default supplies a UUIDv4 |
| Supply the client's UUID | PostgreSQL keeps the same value |
| Supply a new UUID and duplicate canonical asset code | Reject with `23505` on `uq_assets_asset_code` |
| Repeat a department code or part SKU | Reject with `23505` on the relevant business-key constraint |
| Reuse a UUID with a different asset code | Reject with `23505` on `pk_assets` |
| Cast malformed identifier text to UUID | Reject with `22P02` |
| Measure identifier values | UUID uses 16 bytes; bigint uses 8; integer uses 4; these are value sizes, not table/index sizes |
| Compare UUID generators | `gen_random_uuid()` generates version 4; PostgreSQL 18's `uuidv7()` generates version 7 |
| Explicit insert into an ALWAYS identity | Reject with `428C9` unless an intentional override is used |
| Fail an insert after allocating an identity | The next successful row has ID 3 rather than reclaiming ID 2 |
| Explicit ID 42 in a BY DEFAULT identity | Accept 42; the first sequence-generated value is still 1 |
| Store four Unicode `é` characters | `varchar(4)` accepts four characters although their UTF-8 representation uses eight bytes |
| Store a long description | `text` preserves it without the short label's limit |
| Insert five non-space characters into `varchar(4)` | Reject with `22001` |
| Explicitly cast five characters to `varchar(4)` | Truncate to four: a cast is not length validation |
| Omit a boolean flag versus supply false | Defaults apply to omitted values; explicit false stays false |
| Reconnect after rollback | All Step 4 comparison objects are absent |

The expected failures are caught inside small `DO`/`EXCEPTION` blocks so that one rejected insert does not abort the whole exercise. The harness checks the SQLSTATE and, for duplicate-key tests, the exact constraint name. It raises an error if bad input is accepted or another constraint fails. You do not need to master PL/pgSQL now; it is verification plumbing, with procedural database programming examined in Step 73. Reference: [PostgreSQL error handling](https://www.postgresql.org/docs/18/plpgsql-control-structures.html#PLPGSQL-ERROR-TRAPPING).

## Trace the project decisions

- **Primary IDs:** native UUID, with `gen_random_uuid()` as the server default. Client-generated UUIDv4 values are supported too.
- **Business identities:** independently unique department/category codes, asset codes, part SKUs, and normalized user emails.
- **Short labels:** explicit `varchar(n)` limits chosen for the business, not a presumed speed advantage.
- **Free-form text:** `text` for descriptions, comments, and notes.
- **Flags:** required booleans, default true for activation and false for archival; asset lifecycle still uses its status field.
- **Whole units:** integer quantities, with valid ranges/positivity rules studied in Step 6.

The [decision record](../../docs/IDENTIFIERS_AND_TYPES.md) contains the complete initial type table and alternatives. None of these choices substitutes for authorization or makes a UUID a secret.

## Recorded outcome

The live exercise passed on 22 October 2026 with 19 successful verification checks. See [evidence.txt](evidence.txt) for the original output, including the client-generated UUID, the server-generated UUID, expected SQLSTATE/constraint diagnostics, the identity gap, Unicode measurements, boolean values, and cleanup through a fresh connection. All six demonstration tables were rolled back; the shared learning environment remains available.

## Explain before advancing

1. Which constraint rejects a fresh UUID with a duplicate `asset_code`, and why does the primary key not solve that problem?
2. Which path generates the UUID before sending SQL? Which path generates it in PostgreSQL?
3. Why should a future ORM-only default not be assumed to work for a direct `psql` insert?
4. Does a UUID column restrict values to the generator's version?
5. Why do two successful identity rows have IDs 1 and 3? Why is the maximum ID not a row count?
6. How do `GENERATED ALWAYS` and `BY DEFAULT` differ when given an explicit value?
7. Why can four characters occupy eight bytes? What does `varchar(4)` actually limit?
8. Why can an explicit varchar cast conceal an input-length problem?
9. Why does an explicit false value remain false even when the default is true?

Next: Step 5 in the [learning path](../../docs/LEARNING_PATH.md) covers exact monetary values and timezone-aware timestamps. Step 6 then expands NULL/default/constraint rules beyond this identifier-focused exercise.
