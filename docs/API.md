# Local maintenance API

Install the root requirements into the ignored `.venv`, start the PostgreSQL lab, and run migrations before starting the API:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn college_maintenance.api:app --host 127.0.0.1 --port 8000
```

The OpenAPI page is at http://127.0.0.1:8000/docs. Each database operation owns one explicit transaction; its request Session closes on every outcome. Routes return primitive values, never lazy ORM objects or password hashes. Validated HTTP input and authenticated actor identity are separate inputs to the service layer.

Authentication uses opaque bearer credentials provisioned out of band. `.local/api-tokens.json` (or `COLLEGE_API_TOKENS_FILE`) maps SHA-256 token digests to records with `actor_id` and an aware ISO `expires_at`. Use a randomly generated secret of at least 32 bytes, store only its digest in this file, and provide the secret to the intended local caller. The actor must exist and remain active in PostgreSQL. Missing, expired, removed, or malformed credentials fail closed. File contents and bearer secrets stay outside Git. A caller supplies `Authorization: Bearer <secret>`; request roles or actor IDs have no authority. This local example has no public login or token issuance endpoint; external identity-provider integration remains a separate deployment choice.

Read routes: `GET /assets/{id}`, `GET /tickets`, `GET /tickets/{id}`. The feed supports bounded `limit`, `cursor`, `department_id`, `status`, and `priority`; newest timestamp/UUID ordering is fixed. Each request constructs fresh scope from its actor's current database record. An inaccessible detail uses the same 404 response as an absent resource. HTTP-level tests use the real ASGI routes and PostgreSQL with a synthetic trusted credential verifier.

Errors: 401 requires valid authentication, 403 denies an actor/action, 404 conceals missing or inaccessible resources, 422 rejects transport input, 400 rejects domain input, and 409 reports state/integrity conflicts. SQL parameters and driver exception messages are not returned. OpenAPI documents transport validation. Database roles and application roles remain separate; runtime-role privilege separation belongs to Step 58.
