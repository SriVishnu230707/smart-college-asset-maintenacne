# Local maintenance API

Use Python 3.11+ for the pinned Starlette and HTTPX 2 dependencies; the full suite was verified with Python 3.12.14. Install the root requirements into the ignored `.venv`, start the PostgreSQL lab, and run migrations before starting the API:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn college_maintenance.api:app --host 127.0.0.1 --port 8000
```

The [OpenAPI page](http://127.0.0.1:8000/docs) describes the HTTP routes. Each database operation owns one explicit transaction; its request Session closes on every outcome. Routes return primitive values, never lazy ORM objects or password hashes. Validated HTTP input and authenticated actor identity are separate inputs to the service layer.

Authentication uses opaque bearer credentials provisioned out of band. `.local/api-tokens.json` (or `COLLEGE_API_TOKENS_FILE`) maps SHA-256 token digests to records with `actor_id` and an aware ISO `expires_at`. Use a randomly generated secret of at least 32 bytes, store only its digest in this file, and provide the secret to the intended local caller. The actor must exist and remain active in PostgreSQL. Missing, expired, removed, or malformed credentials fail closed. File contents and bearer secrets stay outside Git. A caller supplies `Authorization: Bearer <secret>`; request roles or actor IDs have no authority. This local example has no public login or token issuance endpoint; external identity-provider integration remains a separate deployment choice.

Read routes: `GET /assets/{id}`, `GET /tickets`, `GET /tickets/{id}`. The feed supports bounded `limit`, `cursor`, `department_id`, `status`, and `priority`; newest timestamp/UUID ordering is fixed. Each request constructs fresh scope from its actor's current database record. An inaccessible detail uses the same 404 response as an absent resource. HTTP-level tests use the real ASGI routes and PostgreSQL with a synthetic trusted credential verifier.

Errors: 401 requires valid authentication, 403 denies an actor/action, 404 conceals missing or inaccessible resources, 422 rejects transport input, 400 rejects domain input, and 409 reports state/integrity conflicts. SQL parameters and driver exception messages are not returned. OpenAPI documents transport validation. Database roles and application roles remain separate; runtime-role privilege separation belongs to Step 58.

Workflow routes now include ticket creation, original-report editing, priority triage, explicit transitions and scoped audit reads. Comments use `/tickets/{id}/comments`. Attachment uploads use `/ticket/{id}/attachments` or `/work_order/{id}/attachments` with bounded base64 JSON; downloads use `/attachments/{kind}/{id}`. Bytes remain private and failed metadata commits compensate their own staged object. Age-gated garbage collection runs separately with uploads paused.

Assigned technicians create `/tickets/{id}/work-orders`, start or edit `/work-orders/{id}`, and PUT/DELETE consolidated `/work-orders/{id}/parts/{part_id}`. Draft deletion records audit and leaves removed proof objects for orphan collection. POST `/work-orders/{id}/complete` accepts no editable fields and atomically verifies proof, locks stock, snapshots current prices, consumes stock, appends ledger/audit, and moves the ticket to verification. Monetary JSON values are exact decimal strings. Administrators verify or request rework through ticket transitions. Completion retry/concurrency behavior is expanded and tested in Steps 41-48.

Central inventory creation, supplier creation, receipts and reasoned adjustments require Super Admin. Staff may read the parts catalog; students cannot. `/inventory/reconciliation` is restricted to Super Admin. There is no direct stock overwrite or history-edit route.

Completion uses its work-order UUID as the durable operation identity. Authorized duplicate or simultaneous requests return the existing frozen result, including after later verification or rework. The current ticket status and catalog prices are excluded from that stable result. Authorization runs before result disclosure. A scoped administrator may retrieve completed work but cannot initiate an unfinished completion. Unique consumption identity and protected immutable work prevent duplicate business effects. Deadlock/serialization retries run the entire transaction up to three times; exhaustion returns 503.

Original-report and priority PATCH requests require a positive `expected_version` from ticket detail or the latest mutation result. A stale version returns 409 and records no success audit event; omitting it returns 422. ORM flushes automatically check and advance the ticket version. Bulk/Core writers must deliberately include an expected-version predicate and increment, because mapper versioning does not cover those paths.

Administrative reports use `/reports/costs`, `/reports/failures`, and `/reports/latest-comments`; all enforce recorded department scope. Costs pre-aggregate parts per completed order and exclude unfinished estimates. Latest comments use timestamp/UUID ties and retain tickets with no comments. The reviewed SQL strategies produce the same response grain. Report list limits are bounded at 100. Plan/index measurements and large streaming exports are demonstrated in the specialist labs; the core HTTP reports retain their explicit limits.

## Verified continuation

`GET /health/ready` performs a database readiness query without exposing rows. `GET /reports/ranked-failures` accepts `top`, `include_ties` and a validated `limit` up to 100; a response cap can cut a tied rank group, while the query-layer function retains its explicit tie policy. `GET /reports/monthly-costs` accepts increasing month-start dates `start`/`end` (end-exclusive), at most 120 months, and UTC or Asia/Kolkata. It fills missing department/month buckets and returns exact decimal strings for cost/change; the first change is null. `GET /tickets/search` precedes the UUID detail route, accepts bounded `q`/`limit`, and retains the ordinary ticket visibility rules with explicit English lexeme matching and ranking. Whitespace-only queries are domain errors; stopword-only queries return no matches.

The function-layer full-text expression is implemented in the application. Its GIN candidate is measured in the isolated Step 66 fixture; installing a production index requires a reviewed migration and workload decision. Optional materialized views, RLS, inheritance, async and outbox implementations use isolated specialist schemas. The core API remains synchronous. The optional booking prototype and its boundaries are described in [reference coverage](REFERENCE_COVERAGE.md).

Runtime-role separation is verified in Step 58 and installed by the fresh Step 62 deployment. The default learning connection is the learner/owner account. `COLLEGE_DATABASE_URL_FILE` selects an ignored or mounted psycopg URL secret; pool size/overflow/timeout settings have finite validated bounds. Preserve credentials and uploads outside Git.
