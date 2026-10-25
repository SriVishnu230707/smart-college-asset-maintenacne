# Step 28: One transaction owner

One use-case owner commits asset, ticket, and audit together; composable helpers only flush, and existing autobegun reads must be resolved explicitly.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-28\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Successful composition commits exactly once.
- Error after all three flushes rolls all of them back.
- Invalid final audit FK undoes earlier writes.
- A second owner refuses an already active transaction.

The 25 October 2026 verification passed **20 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
