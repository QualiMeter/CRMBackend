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

- `POST /api/v1/auth/register` — самостоятельная регистрация нового пользователя.
- `POST /api/v1/auth/login` — вход по username или email.
- `POST /api/v1/auth/refresh` — ротация refresh token.
- `POST /api/v1/auth/logout` — отзыв refresh token.
- `GET /api/v1/auth/me` — текущий пользователь.
- `GET /api/v1/me` — совместимый alias.
- `GET /api/v1/me/roles` — роли текущего пользователя.
- `GET /api/v1/auth/invitations/{token}` — публичная проверка приглашения.
- `POST /api/v1/auth/invitations/accept` — принять приглашение, создать пароль и получить токены.

### User invitations

Администратор сначала создаёт пользователя со статусом `invited`, затем вызывает:

- `POST /api/v1/users/{user_id}/invite` — создать одноразовую ссылку-приглашение.
- `POST /api/v1/users/{user_id}/invite/revoke` — отозвать активное приглашение.

Токен приглашения хранится в базе только в виде SHA-256 хеша. Ссылка действует `INVITATION_EXPIRE_HOURS` часов (по умолчанию 48). URL формируется относительно `FRONTEND_BASE_URL`. После принятия пользователь переводится из `invited` в `active`, для существующей записи пользователя создаются локальные credentials, а роли сохраняются.

Обычный `/auth/register` не используется для приглашённых пользователей: он создаёт новую запись пользователя.

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

The project does not contain SQL seed/schema files. At startup it reflects the existing CRM schema and creates authentication support tables if they do not already exist:
- `auth_credentials`
- `auth_sessions`
- `user_invitations`
