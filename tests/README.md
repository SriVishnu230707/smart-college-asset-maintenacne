# Run all implemented labs

With Docker Desktop running, install the [root requirements](../requirements.txt) into an ignored Python 3.10+ virtual environment once, then execute the suite from the project root in PowerShell 7 or Windows PowerShell 5.1. See the [Step 13 setup](../labs/step-13/notes.md) for the complete commands:

```powershell
.\tests\run.ps1 -WriteEvidence
```

The suite starts the existing Compose database, preserves its credentials and volume, and runs Steps 2-19 sequentially. Step 1 contains written business proofs. Run an individual lesson using its own `labs/step-NN/verify.ps1` command. The suite does not advance the learning checklist.

Steps 5 and 13-19 need Python 3.10+. The root requirements include Step 5 timezone data and Step 13 SQLAlchemy 2.1.6 with psycopg 3.3.6, reused by Steps 14-19. The shared interpreter resolver tries a project virtual environment, normal PATH interpreters, then an existing bundled interpreter. Windows Store aliases are skipped during automatic selection. Each lab checks its required packages/imports before connecting: Step 5 requires tzdata and Asia/Kolkata, while Steps 13-19 require their pinned SQLAlchemy/psycopg versions. An explicit interpreter is respected by all eight labs:

```powershell
.\tests\run.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

No interpreter or package is installed automatically. Python JSON input uses UTF-8. The [ZoneInfo documentation](https://docs.python.org/3/library/zoneinfo.html#data-sources) explains its timezone-data dependency.

## What is verified

The suite requires all **547 checks across eighteen labs** to pass. This includes thirteen Python checks in Step 5, twenty-one in Step 13, twenty-five in Step 14, twenty-nine in Step 15, thirty-eight in Step 16, forty-six in Step 17, twenty-five in Step 18, and thirty-three in Step 19. Each lab runs in a child process using the current PowerShell executable, from an unrelated working directory. Absolute Compose paths and argument arrays handle this project's spaces and ampersand.

Seven additional regression checks verify:

1. Database startup and Compose readiness.
2. PowerShell syntax, existing relative SQL include targets, and absence of invalid numeric quit commands.
3. A missing required Step 4 UUID returns psql exit 3 with SQLSTATE P0001.
4. The shared runner throws for an unexpected nonzero SQL exit.
5. Native stderr is captured while a zero-exit process still succeeds.
6. An unavailable explicit Python fails clearly before the SQL exercise starts.
7. A fresh connection finds no Step 2-19 study schemas after the suite.

Steps deliberately reject invalid values. In particular, Step 8 expects SQL errors 23505 and 25P02 while recovering its transaction, plus a guarded cleanup refusal with exit 3 and SQLSTATE 22023. Step 14 asserts a duplicate-code 23505, application-error rollback, client-side binding/transaction errors, and the same guarded cleanup refusal. Step 18 asserts application-error rollback, ORM duplicate-code 23505, referenced-delete restriction 23001, and cleanup refusal 22023. These remain asserted behavior. Actual unexpected process exits fail the suite. See [psql exit status](https://www.postgresql.org/docs/18/app-psql.html#APP-PSQL-EXIT-STATUS).

## Fixes and simpler runner logic

Earlier Steps 2-7 used `\quit 1` for failed assertions. Reproducing Step 4 without its UUID printed FAIL but returned exit 0, because psql ignores the extra argument. Their guards now include [one shared SQL failure handler](../labs/shared/fail.sql), which raises a real error under ON_ERROR_STOP. An open transaction then rolls back when the failed client closes.

Step 8 also failed on Windows PowerShell 5.1 before the fix: native stderr interrupted the wrapper before its expected-error logic could run. The [shared PowerShell helper](../labs/shared/verify.ps1) captures native output, restores the caller's error preference, and compares the real exit code with the expected value. That helper replaces repeated process invocation and evidence-writing logic across the lab verifiers and database startup.

The executable lookup selects one resolved application path, and Step 5 validates Python candidates instead of choosing the first unverified installation. Existing lesson queries and expected business results are preserved.

## Evidence and scope

The original per-step evidence remains alongside each lesson. The current suite, including Step 19, has separate summaries:

- [PowerShell 7 evidence](evidence-powershell7.txt)
- [Windows PowerShell 5.1 evidence](evidence-powershell5.txt)

Full current lab output is saved locally under ignored `.local/test-results/powershell-<version>/`. `-WriteEvidence` saves the suite summary here as UTF-8 without a BOM. A failed run reports FAILED and exits nonzero. Run suites sequentially because they use the same study namespaces.

Compatibility was exercised on Windows with both installed PowerShell versions and the existing PostgreSQL 18 Docker image. These checks cover the implemented SQL/Python learning labs, typed ORM column mappings, and short-lived Session CRUD with SQL logging and error cleanup, plus observed object lifecycle and unit-of-work behavior. Failed-flush recovery, relationship behavior, API, frontend, other operating systems, and older PostgreSQL versions are outside this test result.
