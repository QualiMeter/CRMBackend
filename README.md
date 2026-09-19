# RTK CRM Backend

FastAPI + PostgreSQL backend for RTK IT School CRM.

## Stack
- FastAPI
- SQLAlchemy async + asyncpg
- PostgreSQL 15+
- Pydantic v2 request/response schemas
- Multipart file uploads
- CSV / JSON / JSONL / XLSX imports
- XLS / XLSX / PDF / JSON / PNG reports
- Scalar: `/scalar`
- Swagger: `/docs`

## Local start
1. Copy `.env.example` to `.env`:
   - PowerShell: `Copy-Item .env.example .env`
   - cmd: `copy .env.example .env`
3. Run exactly:

```bash
python -m uvicorn app.main:app --reload
```

The database schema is expected to already be applied. SQL files are intentionally not included in this backend package.

## Railway
The Dockerfile listens on Railway's `PORT` and binds to `0.0.0.0`.

If PostgreSQL is a separate Railway service, set the API service variable to a Railway reference such as:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Replace `Postgres` with the actual PostgreSQL service name. Do not use `localhost` for a database in another Railway service.

Set:

```text
AUTH_REQUIRED=true
AUTH_AUTO_PROVISION=true
```



Send:

```http
Authorization: Bearer <access-token>
```

## API groups

### Current user
- `GET /api/v1/me`
- `GET /api/v1/me/roles`

### Users
- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`
- `PUT /api/v1/users/{user_id}/roles`

### Files
- `POST /api/v1/files/upload` — `multipart/form-data`, field `file`
- `GET /api/v1/files/{file_id}`
- `GET /api/v1/files/{file_id}/download`
- `POST /api/v1/documents/{document_id}/versions/upload` — multipart upload for document versions

### Comments
- `GET /api/v1/comments/stage/{stage_instance_id}`
- `POST /api/v1/comments/stage/{stage_instance_id}`
- `PATCH /api/v1/comments/{comment_id}`
- `DELETE /api/v1/comments/{comment_id}` — soft delete

### Imports
- `POST /api/v1/imports/upload` — multipart file + JSON fields
- `GET /api/v1/imports/{job_id}`
- `GET /api/v1/imports/{job_id}/rows`
- `POST /api/v1/imports/{job_id}/execute`

### Reports
- `POST /api/v1/reports`
- `GET /api/v1/reports`
- `GET /api/v1/reports/{job_id}`

### Named CRUD resources
There is no `/api/v1/data/{table}` frontend endpoint anymore. Every database table has its own named resource path, for example:

- `/api/v1/universities`
- `/api/v1/university-contacts`
- `/api/v1/it-directions`
- `/api/v1/vendors`
- `/api/v1/it-products`
- `/api/v1/programs`
- `/api/v1/contracts`
- `/api/v1/licenses`
- `/api/v1/workflow-templates`
- `/api/v1/workflow-template-stages`
- `/api/v1/interactions`
- `/api/v1/workflow-stage-instances`
- `/api/v1/stage-transitions`
- `/api/v1/tasks`
- `/api/v1/documents`
- `/api/v1/document-versions`
- `/api/v1/activities`
- `/api/v1/user-drafts`
- and the remaining schema tables using kebab-case paths.

Single-key resources use `GET/POST/PATCH/DELETE`; composite-key resources use key segments, e.g. `/api/v1/role-permissions/{role_id}/{permission_id}`.

## Pydantic schemas
`app/schemas/crud.py` contains named `CreateRequest`, `UpdateRequest`, and `Response` Pydantic models for every table in the authoritative CRM schema. Specialized request/response models are in `app/schemas/requests.py` and `app/schemas/schemas.py`.

## Standard errors
All OpenAPI operations document these responses:

| Status | Meaning |
|---|---|
| `401` | Missing/invalid/expired Bearer JWT |
| `403` | Valid JWT, but the user lacks the required role/access |
| `404` | Resource does not exist |
| `409` | Unique, foreign-key, or other database constraint conflict |
| `422` | Pydantic/request validation error |
| `500` | Unexpected server-side error |

Error body shape:

```json
{
  "detail": "Human-readable message",
  "code": "ERROR_CODE",
  "request_id": "uuid"
}
```

Every response also includes `X-Request-ID`.

## Security model
- `user`: normal CRM operations
- `manager`: normal operations + imports and broader management
- `admin`: user/role/security/integration/audit administration


## Authentication


Endpoints:

- `POST /api/v1/auth/refresh` — rotates/refreshes the access token using a refresh token.
- `GET /api/v1/me` — compatibility alias for `/auth/me`.
- `GET /api/v1/me/roles` — compatibility role endpoint.


For login/register through this API, the client must allow Direct Access Grants (password flow).



## Auth setup — important


Recommended production setup:

2. Enable **Service accounts** for that client.
4. Put its client ID and secret into:

```env
```



## Auth request examples

Registration accepts both snake_case and the usual frontend camelCase aliases for names and refresh tokens:

```json
{
  "username": "ivan",
  "email": "ivan@example.com",
  "password": "StrongPassword123!",
  "firstName": "Ivan",
  "lastName": "Ivanov"
}
```

Login accepts `username`, `login`, or `email` as the identifier:

```json
{
  "username": "ivan",
  "password": "StrongPassword123!"
}
```

Refresh:

```json
{
}
```

All unknown request fields are rejected with HTTP 422, while the supported aliases are normalized by Pydantic before the endpoint is called.

## Auth error format

Validation errors include field-level details:

```json
{
  "detail": "Request validation failed",
  "code": "VALIDATION_ERROR",
  "request_id": "6f4b0d0a-3d5b-4fb2-9e12-2f5f7d9e7e21",
  "details": [
    {
      "field": "body.email",
      "message": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

Authentication and authorization errors use the same envelope. The API also returns the request ID in the `X-Request-ID` response header.

## Recommended frontend flow

```text
register -> receive access/refresh tokens -> store them securely
login    -> receive access/refresh tokens
refresh  -> replace the access token when it expires
logout   -> invalidate the refresh token
me       -> restore the CRM user and roles after application startup
```

For browser applications, keep refresh tokens in a secure mechanism appropriate to the application's threat model; do not put long-lived credentials into URLs.

## Authentication

Authentication is handled by the API itself; Keycloak is not required.

Endpoints:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Passwords are stored as PBKDF2-HMAC-SHA256 hashes. Access/refresh sessions are managed by the API.
