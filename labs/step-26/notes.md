# Step 26: Alembic application schema ownership

A frozen initial Alembic revision creates a genuinely empty database, installs named constraints, and owns the application schema; the application database is upgraded to the reviewed head.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-26\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Empty database to eight application tables without create_all.
- Named PK/FK/check/index policies survive inspection.
- Invalid writes are rejected and repeated upgrade preserves data.
- No unversioned application tables are silently adopted.

The 25 October 2026 verification passed **25 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
