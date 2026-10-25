# Step 21: Identity and freshness

Identity-map reuse, expire/refresh, commit expiration, detached access, and merge are verified against independent committed writes. A deterministic merge race proves it is not atomic upsert.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-21\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Repeated get: one SELECT and the same object.
- External writes remain stale until explicit reload.
- Commit expiration plus close prevents unloaded access.
- Merge returns a different managed object and can lose an insert race.

The 25 October 2026 verification passed **22 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
