# Server (contracts-first scaffold)

This is the Python FastAPI server aligned with the contracts in `contracts/`.

## Run locally

- Start both backend and frontend with one command (uses Uvicorn for the backend):

```
make dev-up
```

Backend: http://localhost:8080 (health: `/api/health`)

Stop processes:

```
make dev-down
```

## Project layout

```
server/
  app/
    main.py            # ASGI app (FastAPI), CORS, router includes, /api/health
    routers/
      jd.py            # /api/jd/import, /api/jd/:id/extract
      generate.py      # /api/generate, /api/generate/stream (SSE)
      keywords.py      # /api/keywords
      ats.py           # /api/ats
      pipelines.py     # /api/pipelines
    utils/
      contracts.py     # JSON Schema loader/validator used at runtime (dev)

  pyproject.toml       # Dependencies (fastapi, uvicorn, pydantic, jsonschema)
```

## Contracts mapping

Authoritative contracts (OpenAPI + JSON Schemas) live under `contracts/`:

- OpenAPI: `contracts/openapi.yaml`
- Schemas: `contracts/schemas/*.json`

Routers use Pydantic models that mirror these schemas. Two sample runtime validations are wired to prove conformance:

- `generate.py`
  - Request model `GenerateRequest` matches `generate_request.json` (fields: `job`, `prompt?`, `resumeId?`, `jdId?`).
  - Response model `GenerateResponse` matches `generate_response.json` and is validated at runtime:
    - `app/utils/contracts.py::validate_against("generate_response.json", data)`

- `pipelines.py`
  - Creation response is validated against `pipeline.json` using the same helper.

You can add more validations per endpoint if desired. Pydantic already validates request bodies; JSON Schema checks mainly ensure we don't drift from the contract spec.

## How JSON Schemas are loaded in Python

File: `app/utils/contracts.py`

- Resolves repo root and loads schemas from `contracts/schemas`:
  - `SCHEMAS_DIR = <repo_root>/contracts/schemas`
- Creates a Draft 2020-12 validator with a base resolver so relative `$ref` paths work.
- Exposes `validate_against(schema_file, data)` which returns a list of error strings on failure (or `None` if valid).

Example usage in a router:

```python
from app.utils.contracts import validate_against

resp = GenerateResponse(...)
errors = validate_against("generate_response.json", resp.model_dump())
if errors:
    raise HTTPException(status_code=500, detail={"schema": "generate_response.json", "errors": errors})
return resp
```

## Notes

- Endpoints currently return mocked data that conforms to the contracts. Swap in real services/agents when ready.
- CORS is open for local development. Tighten for production.
- Consider adding a test suite (pytest) that loads example payloads from fixtures and validates them against both Pydantic and JSON Schemas.

## Turso (libsql) optional storage

The backend can use Turso (libsql) as a temporary store for pipelines.

Environment variables:

- TURSO_URL: e.g. `libsql://<host>.turso.io` (you may also omit the `libsql://` prefix)
- TURSO_TOKEN: auth token (optional if the DB is public or local)
- DATABASE_URL: alternative SQLAlchemy URL; used if TURSO_URL is not set

Fallback: if neither TURSO_URL nor DATABASE_URL is provided, the backend uses a local SQLite file at `.run/talentflow.sqlite`.
