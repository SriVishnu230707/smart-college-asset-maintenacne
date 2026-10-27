# Step 66: Full-text ticket search

Learn: Explore tsvector/tsquery, language configuration, ranking, and GIN. Prerequisites: 54–56.

  Apply: Build ranked ticket search and compare it with substring search on representative text.

  Prove: State language/tokenization behavior and measure the indexed search.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-66\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Ranked English full-text search preserves ticket visibility, tests actual dictionary stems versus substrings and stopwords, and measures matching GIN expression indexing.

See [captured evidence](evidence.txt).
