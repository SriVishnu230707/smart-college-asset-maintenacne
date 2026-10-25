# Step 23: Separate reporter and assignee paths

Explicit foreign_keys map reporter and optional assignee separately; aliased projections correctly handle different users, the same user, and no assignee.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-23\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Reporter and assignee collections contain different ticket sets.
- Two explicit aliases retain unassigned tickets with LEFT JOIN.
- The same user may fill both roles without ambiguity.
- Raw SQL and ORM projections agree.

The 25 October 2026 verification passed **17 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
