# Step 30: Stable ticket feed pagination

Bounded offset and created_at/id keyset feeds preserve actor/filter scope, page tied timestamps without duplicates in a fixed dataset, and demonstrate concurrent-insert/update limitations.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-30\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Equal timestamps use UUID as the unique descending tie-breaker.
- Filter/scope changes invalidate cursors; all queries still enforce authorization.
- Newer inserts shift offsets but not the keyset boundary.
- Backdated inserts and ordering-key updates expose the lack of a cross-request snapshot.

The 25 October 2026 verification passed **23 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.

Reverified on 2026-10-25 before continuing Steps 31-50: all 23 checks passed in both shells.
