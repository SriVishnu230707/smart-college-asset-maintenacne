# Step 24: Part usage association objects

WorkOrderPart explicitly maps consolidated quantities and exact historical unit costs between work orders and catalog parts; duplicate lines and invalid values are rejected.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-24\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Two units at 12.50 total exactly 25.00.
- Catalog price changes leave the snapshot unchanged.
- Draft usage leaves stock at zero.
- Composite identity and the active-order index reject duplicates.

The 25 October 2026 verification passed **20 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
