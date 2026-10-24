# Step 5: represent money and time correctly

Read the [money/time decision record](../../docs/MONEY_AND_TIME.md) first. This step calculates an exact repair cost, explains the no-rounding input policy, and groups event instants around midnight in `Asia/Kolkata`.

## Run the lab

Use the [Step 2 PostgreSQL environment](../step-02/notes.md), Python 3.10+, and the pinned timezone data in [requirements.txt](requirements.txt). From PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-05\verify.ps1 -WriteEvidence
```

The verifier tries a project virtual environment, normal Python executables on PATH (skipping Windows Store aliases), then an existing bundled interpreter. It checks Python 3.10+, the tzdata package, and Asia/Kolkata availability before running SQL. Supply an explicit interpreter with `-PythonExecutable` when needed; that choice is checked without silently substituting another interpreter. No packages are installed automatically. For a separate Python installation, install the lab requirements into that interpreter:

```powershell
python -m pip install -r labs/step-05/requirements.txt
.\labs\step-05\verify.ps1 -PythonExecutable python -WriteEvidence
```

The verified machine used Python 3.12.14 and tzdata 2026.5. Windows Python commonly needs the `tzdata` package for IANA zone names; the pinned requirement also makes the lab's timezone-data dependency explicit. Reference: [ZoneInfo data sources](https://docs.python.org/3/library/zoneinfo.html#data-sources).

[query.sql](query.sql) uses a disposable `college_step05` schema and refuses to touch one that already exists. It creates four study tables for prices, repair costs, part lines, and cost events, plus a raw-money validation helper. Everything is rolled back, and [reconnect.sql](reconnect.sql) checks cleanup from a new connection.

[python_lab.py](python_lab.py) receives a JSON payload containing actual PostgreSQL result values on stdin. Money travels as decimal strings, events as offset-aware ISO strings, and quantities/counts as integers. Python explicitly reconstructs `Decimal` and aware `datetime` values and verifies the same cost and daily groups. This transport does not require a database driver; driver/ORM integration remains for later lessons.

For SQL-only exploration:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```sql
\i /labs/step-05/query.sql
\quit
```

Use `verify.ps1` for the complete SQL/Python proof and saved evidence.

## Trace the monetary proof

The repair uses labor 100.00, two lamps at 250.10, and three fuses at 0.10:

```text
100.00 + (2 * 250.10) + (3 * 0.10) = 600.50 INR
```

Both PostgreSQL numeric arithmetic and Python Decimal return this exact result. Updating the current lamp catalog price to 300.00 leaves the copied historical unit cost and repair total unchanged. The lab demonstrates snapshot calculation; later completion lessons enforce immutability and transaction ownership.

The monetary input guard runs before a scaled conversion. It rejects `1.005`, `1.230`, and `0.001`, including excess trailing precision; nonfinite, negative, missing, malformed, and oversized inputs are also rejected in the appropriate SQL/Python exercises. Valid `0` and `1.2` normalize to `0.00` and `1.20`.

A bare `NUMERIC(12,2)` conversion rounds `1.005` to `1.01`, while Python half-even quantization gives `1.00`. This is why the contract rejects the original excess-scale input instead of accepting either rounded result. A check on the already converted value cannot inspect the original precision.

The individual repair cap is 9999999999.99. An individual repair exceeding it fails validation. An aggregate report may legitimately exceed it and uses a wider numeric/Decimal result: two maximum-size amounts sum to 19999999999.98 exactly.

## Trace the timestamp proof

`2026-10-21T18:30:00+00:00` and `2026-10-22T00:00:00+05:30` are the same instant. The SQL exercise changes the session timezone, prints both displays, and verifies the same epoch. Python converts the aware instant with `astimezone(ZoneInfo('Asia/Kolkata'))` and confirms equality.

Four events straddle two local midnight boundaries. Reporting on October 22 must include exactly `REPAIR-EXACT` and `LAST-SECOND`, for a total of 600.70. The event at the next midnight belongs to October 23. Explicit reporting-zone grouping produces the same results in both UTC and Kolkata sessions, and Python matches every daily count and sum.

Counterexamples show that an offset-free event string depends on the session timezone and that a timestamp-without-time-zone literal can discard its offset. The Python event helper rejects naive datetimes and date-only values instead of inventing an event instant for them.

## Read the implementation boundary

The SQL `require_money` helper and Python helpers are inspectable lab examples. They do not install production write protection. The small SQL `DO` blocks catch expected error codes so negative experiments can continue inside the transaction. The study fixture keys are readable labels, not a replacement for the application's UUID identifier policy.

Later work must apply the raw-money policy to all application/import inputs before scaled storage, enforce lifecycle/amount validity and protected history, and use the actual driver/ORM types. Step 6 studies those row-validity and NULL/default constraints next.

## Recorded outcome

The live exercise passed on 22 October 2026: 21 PostgreSQL checks and 13 Python checks. See [evidence.txt](evidence.txt) for original output, expected rejections, exact cost calculations, timezone displays, matching local-day groups, and successful cleanup. No permanent application table or helper was left behind.

## Explain before advancing

1. What do precision 12 and scale 2 mean? What is the chosen maximum nonnegative individual cost?
2. Why must Decimal start from a string rather than a binary float?
3. Why does a scaled numeric column not by itself implement the no-rounding input policy?
4. What happens to `1.230`, and what happens to a valid `1.2`?
5. Why can an aggregate report exceed the per-repair storage range?
6. Which price should a historical repair use after a catalog price change?
7. Why can an instant have different UTC and reporting dates without changing its epoch?
8. What does PostgreSQL preserve in timestamptz, and which original timezone information does it omit?
9. Why convert to the reporting zone before deriving the calendar date?
10. Why use an exclusive next-midnight boundary, and why reject naive event datetimes?

Continue with Step 6 in the [learning path](../../docs/LEARNING_PATH.md) when you can explain the observations without copying them.
