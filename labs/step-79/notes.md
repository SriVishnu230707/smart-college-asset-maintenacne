# Step 79: Reliable external side effects

Learn: Study outbox transactions, retries, duplicate delivery, consumer idempotency, and file/object compensation. Prerequisites: 37, 47, 59.

  Apply: Record a repair-completed outbox event in the repair transaction and deliver it separately.

  Prove: A crash between database commit and delivery does not lose the event; duplicate delivery has a defined outcome.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-79\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 20 checks passed in both installed PowerShell versions. Atomic envelope production, SKIP LOCKED publishers, independent consumer commit, crash-before-ack redelivery and idempotent local effects are verified without external messages.

See [captured evidence](evidence.txt).
