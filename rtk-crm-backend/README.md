# RTK CRM Backend

FastAPI + PostgreSQL backend for the RTK IT School CRM.

## Authentication

Authentication is fully local. No external identity provider or admin service is required.

The API uses:
- PBKDF2-HMAC-SHA256 password hashes;
- signed JWT access tokens;
- database-backed, rotating refresh tokens;
- PostgreSQL roles `user`, `manager`, `admin`.

### Auth endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/me`
- `GET /api/v1/me/roles`

## Configuration

Copy `.env.example` to `.env` and set `DATABASE_URL` and a strong `JWT_SECRET`.

PowerShell:

```powershell
Copy-Item .env.example .env
```

CMD:

```cmd
copy .env.example .env
```

## Local run

```bash
python -m uvicorn app.main:app --reload
```

## Railway

The Dockerfile listens on Railway's `PORT` environment variable and binds to `0.0.0.0`.

## API documentation

- Swagger UI: `/docs`
- Scalar: `/scalar`

## Error format

Errors use HTTP status codes `401`, `403`, `404`, `409`, `422`, and `500` with a JSON body containing `detail`, `code`, and `request_id`. Validation errors additionally include `details` with the invalid fields.

## Database

The project does not contain SQL seed/schema files. At startup it reflects the existing CRM schema and creates only the two authentication support tables if they do not already exist:
- `auth_credentials`
- `auth_sessions`
