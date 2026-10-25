# Step 29: Explicit authorized ORM reads

Explicit asset/ticket DTO projections compose server-derived actor scope with department, status, priority, and assignment filters; SQL and ORM outputs agree for missing and nullable rows.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-29\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Missing and unauthorized asset details return None.
- Student own, technician assigned-or-own, and admin scopes cannot be widened by filters.
- Unassigned tickets retain NULL assignee names.
- Own ticket history survives department changes; inactive actors are rejected.

The 25 October 2026 verification passed **24 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
