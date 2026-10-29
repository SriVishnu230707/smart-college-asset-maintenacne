# Campus Care dashboard

Run the existing local startup commands in the [README](../README.md#run-locally), then open <http://127.0.0.1:8000/>. Static HTML, CSS, and JavaScript are served by the same FastAPI process; no Node build or external fonts/CDNs are needed. The Docker image already copies these files with the Python package.

## Connect an account

Choose **Connect account** and enter the bearer token provisioned using the [API guide](API.md). There is no public signup or password login. The server determines your identity, department, and permissions. Tokens stay in tab memory and are cleared on disconnect, reload, or an authenticated 401 response. A top-bar account control remains available on small screens.

## Everyday tasks

| View | Available behavior |
|---|---|
| Overview | Counts across every accessible ticket, recent tickets, and a description of the repair workflow. Active counts exclude closed/rejected tickets; urgent counts include active high/critical tickets. |
| Maintenance tickets | Status and priority filters, cursor pagination, ticket descriptions, and discussion. Finalized discussions are read-only. Administrators can assign, reject, verify, or request rework when the ticket state permits it. |
| Asset directory | Search by asset code or name and page through department-scoped assets. Search treats `%` and `_` as literal characters. |
| Report an issue | Search/select an asset, enter title, priority, and description, and submit through the existing audited API. Retired assets are excluded from the selection. Search can narrow results beyond the first 100 matches. |
| Spare parts | Staff can inspect up to 100 campus catalog records, stock balances, reorder thresholds, and unit costs. Archived records are identified. |
| Reports | Administrators can inspect completed maintenance costs and frequently reported assets within their authorized department scope. Each list is capped at 100 results. |

Technicians see their reported/assigned tickets; students see their own reports. Department administrators see their department's tickets plus their own reports, consistent with the existing API. Asset visibility follows the asset's current department. Financial reports retain the department recorded when the issue was reported.

The interface supports desktop and narrow screens, keyboard focus indicators, native labeled dialogs, a skip link, live status messages, horizontal table scrolling, and reduced-motion preferences. It escapes server-provided text before rendering it and serves the shell with a same-origin Content Security Policy.

## Current scope

Work-order editing, spare-part consumption, completion-proof uploads, stock administration, and audit inspection remain available through the [API](API.md). This dashboard does not introduce new authentication rules, public signup, asset administration, or an identity provider.

## Verification

```powershell
.\tests\dashboard.ps1 -WriteEvidence
powershell.exe -NoProfile -File tests/dashboard.ps1 -WriteEvidence
node --check college_maintenance/static/app.js
.\.venv\Scripts\python.exe tools\build_reference.py --check
.\.venv\Scripts\python.exe tools\check_docs.py
```

The dashboard acceptance tests use real PostgreSQL with a uniquely generated schema and remove only that schema afterward. They verify authentication, field exposure, department boundaries, all-page totals, wildcard search, stable asset paging, bounded input, descriptions, comments, and assignment. They do not mutate the application's public schema or reuse production credentials.

Evidence: [PowerShell 7](../tests/dashboard-evidence-powershell7.txt), [Windows PowerShell 5.1](../tests/dashboard-evidence-powershell5.txt). See [UI verification](UI_VERIFICATION.md) for browser checks and the regression checkpoint.
