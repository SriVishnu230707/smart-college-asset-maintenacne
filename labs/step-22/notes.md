# Step 22: Bidirectional department and asset relationships

Department.assets and Asset.department synchronize in Python and persist their foreign key, while direct SQL independently enforces parent existence.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-22\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Scalar assignment updates the collection immediately.
- Flush supplies parent UUIDs and child FK values.
- Reassignment updates both collections.
- Direct SQL rejects absent parent UUIDs with 23503.

The 25 October 2026 verification passed **19 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
