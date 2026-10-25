# Step 25: Ownership and deletion policies

Application references preserve ticket and work-order history for loaded, unloaded, and direct SQL deletion paths; delete-orphan and CASCADE are demonstrated only on disposable owned children.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-25\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Removing an owned demo child deletes its row.
- Loaded ORM children are deleted explicitly.
- Unloaded children use database CASCADE without a SELECT.
- Referenced domain rows always reject physical deletion with 23001.

The 25 October 2026 verification passed **23 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
