# Dashboard debugging and verification

## Async debugging follow-up — 30 October 2026

- [x] Reproduced six failing cases before editing the shipped JavaScript: stale asset search results, asset responses after dialog closure, misleading retired-only results, responses from a previous connection using the same token, cancelled sign-in, and comments reopening a closed ticket.
- [x] Added connection and asset-request generations so earlier responses cannot overwrite the current state. Closing a dialog invalidates its pending submissions and releases its submit control for a new attempt.
- [x] Guarded sign-in, comment refresh, administrator refresh, and report completion callbacks so cancelled or replaced dialogs are not reopened, closed, or reset by older work.
- [x] Added two additional cases proving that an old sign-in cannot clear a newer successful connection and an old report cannot reset a reopened draft. All eight controlled-network cases pass in both shells: [PowerShell 7](../tests/dashboard-async-evidence-powershell7.txt) · [PowerShell 5.1](../tests/dashboard-async-evidence-powershell5.txt).
- [x] Reran the eleven real-PostgreSQL dashboard acceptance cases in both shells and refreshed their evidence; all passed. JavaScript syntax, documentation checks, and Git whitespace checks passed too.

These tests execute the actual JavaScript using Node's VM and a deliberately small DOM fixture. They verify response timing and state transitions; they do not claim a fresh browser-layout test or full 80-step regression. The earlier browser and API checkpoint evidence below remains the baseline.

## Original dashboard verification

Verified on 29 October 2026. This change adds the Campus Care browser interface to the existing FastAPI application. No numbered learning step or database migration is added.

## Acceptance checklist

- [x] Real PostgreSQL acceptance cases cover identity, authorization, cross-department visibility, bounded asset search, literal wildcard matching, stable pages, and summary totals beyond the first ticket page.
- [x] Rejected urgent tickets are excluded from active/urgent counts.
- [x] Ticket details return their description without bypassing existing ticket visibility.
- [x] Administrator technician choices can be narrowed to the ticket's department; a department administrator cannot broaden scope with that filter.
- [x] Report, comment, and assignment writes use the existing transactional/audited API services.
- [x] Eleven dashboard acceptance cases pass in both installed PowerShell versions. [PowerShell 7 evidence](../tests/dashboard-evidence-powershell7.txt) · [PowerShell 5.1 evidence](../tests/dashboard-evidence-powershell5.txt).
- [x] Browser checks exercise an invalid-token retry, administrator sign-in, required technician selection, successful assignment, a posted comment containing literal HTML, student issue submission, inventory balances/reorder labels, and administrator cost/failure reports.
- [x] Browser checks exercise narrow-screen filters, empty results, asset search, and disconnect. The measured narrow layout has equal document width and scroll width (375 CSS pixels), so the document does not overflow horizontally. Wide tables scroll inside their panel.
- [x] The responsive viewport override was reset. Browser diagnostics contained no error or warning entries during the completed checks.
- [x] JavaScript syntax, Python compilation, generated references, and documentation link checks pass.
- [x] The Steps 31–40 regression checkpoint passes in each shell: 218 lab checks plus 14 runner checks, for 232 checks per shell. [PowerShell 7](../tests/dashboard-regression-powershell7.txt) · [PowerShell 5.1](../tests/dashboard-regression-powershell5.txt).
- [x] Preview servers were stopped. The interrupted test fixture and synthetic browser fixture were removed by their exact generated schema names after checking their test identities; an independent connection confirms no dashboard test namespaces remain.

## Bugs resolved during review

1. Ticket details omitted the description needed to understand the issue. The existing scoped detail projection now includes it.
2. A narrow-screen sidebar would hide the account controls. A top-bar connect/disconnect control remains available.
3. Invalid credentials initially closed the dialog. Initial sign-in errors now remain inside the form so users can retry; expiry of an existing session clears protected content.
4. Verification actions need a reason under the existing workflow rules. The form now explains and validates that requirement for verification, rejection, and rework.
5. Finalized tickets must not invite comment submissions. Their discussion is read-only in the interface.
6. Account changes must not retain another user's filters or asset choices. Disconnect clears those values along with content, ticket details, and credentials. View revisions discard responses from earlier navigation requests.
7. Windows PowerShell interprets native stderr as an error under strict error handling, while `unittest` writes its successful progress to stderr. The new dashboard runner captures both process streams directly and checks the exit code.

## Browser evidence

These captures use an isolated synthetic PostgreSQL fixture, not the application's public records. The temporary preview uses the production HTML/CSS/JavaScript and existing services with test-only authentication injection. Test authentication is not enabled by the normal application.

![Campus Care desktop overview with synthetic test records](images/dashboard-desktop.png)

[Narrow-screen overview](images/dashboard-mobile.png)

## Existing API regression

The existing Steps 31–40 checkpoint covers API boundaries, error handling, authorization, ticket transitions, audit, and comments. It is invoked with:

```powershell
.\tests\run.ps1 -FromStep 31 -ThroughStep 40
powershell.exe -NoProfile -File tests/run.ps1 -FromStep 31 -ThroughStep 40
```

The saved full 80-step baseline remains historical evidence. New dashboard checks and the targeted regression are recorded separately rather than relabeling that baseline as a fresh full-suite run.

The checkpoint transcripts record the actual range invocation in their footer. The existing runner emits a generic full-suite command template even for a range run; the original raw output remains in ignored `.local/` logs.

## Local environment recovery

Docker initially failed on an inaccessible `dockerInference` runtime socket. The exact runtime directory was preserved under a new name and Docker restarted; application database volumes and credentials were retained. A subsequent Docker restart temporarily interrupted database connectivity. PostgreSQL readiness was established before the successful verification runs; connection failures were not counted as application test passes.
