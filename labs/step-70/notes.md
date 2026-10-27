# Step 70: Reusable mapping and relationship conveniences

Learn: Explore mixins, declarative dataclass integration, composite value objects, association_proxy, and viewonly relationships as separate experiments. Prerequisites: 24, 25.

  Apply: Try a timestamp mixin, a value object, and convenient read access through WorkOrderPart.

  Prove: Keep one authoritative writable association path and prove conveniences do not create duplicate persistence.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-70\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 18 checks passed in both installed PowerShell versions. Timestamp mixins, immutable composites, mapped dataclasses, association proxies and viewonly reload behavior preserve one authoritative writable link.

See [captured evidence](evidence.txt).
