# Step 27: Safe evolution of populated data

A reviewed migration backfills a required condition note and truly renames a populated part-name column; original identities and data survive, and downgrade information loss is demonstrated only in a scratch database.

Run from the project root with Docker Desktop running and the ignored Python environment installed from [requirements](../../requirements.txt):

```powershell
.\labs\step-27\verify.ps1 -WriteEvidence
```

An explicit interpreter can be passed with -PythonExecutable. Paths resolve independently of the caller's working directory. Credentials remain in ignored .local/.

Predict these outcomes before executing:

- Autogenerate reports add/drop, not a semantic rename.
- Active/retired assets receive deliberate backfills before NOT NULL.
- A true rename preserves part IDs and labels.
- Downgrade discards new notes, so re-upgrade cannot restore them.

The 25 October 2026 verification passed **22 checks in both PowerShell 7 and Windows PowerShell 5.1**. [Saved evidence](evidence.txt) records the assertions, independent observation, exact-run cleanup refusal, and committed removal of the study schema. The [phase guide](../../docs/ORM_PHASE_21_30.md) explains scope and limitations. No later learning step is marked complete by this verification.
