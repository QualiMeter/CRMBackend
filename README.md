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

## Platform features

The backend includes local authentication and invitations, password change/reset, email verification, refresh-session management, RBAC foundations, audit logging, notifications and notification preferences, global search, webhooks with queued deliveries, background-job storage, soft-delete fields for users, metrics, health checks and a WebSocket endpoint.

### Authentication flow

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/request-password-reset`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/resend-verification`
- `GET /api/v1/auth/sessions`
- `DELETE /api/v1/auth/sessions/{id}`

### Invitations

An administrator creates a user with `invited` status and calls `POST /api/v1/users/{id}/invite`. The invitation is one-time, hashed in the database and expires according to `INVITATION_EXPIRE_HOURS`. The invited user validates it with `GET /api/v1/auth/invitations/{token}` and accepts it with `POST /api/v1/auth/invitations/accept`.

### Notifications

- `GET /api/v1/notifications`
- `GET /api/v1/notifications/unread-count`
- `POST /api/v1/notifications/{id}/read`
- `POST /api/v1/notifications/read-all`
- `GET/PUT /api/v1/notifications/preferences`

### Operations

- `GET /api/v1/search?q=...`
- `GET /api/v1/audit-log`
- `GET/POST/DELETE /api/v1/webhooks`
- `GET /api/v1/metrics`
- `WS /api/v1/ws`

All platform support tables are created idempotently at startup; no SQL files are required in the backend archive.


## Тесты и Test UI

Установите зависимости из `requirements.txt`, затем запускайте:

```bash
python -m pytest -q -rA
```

Каталоги тестов:
- `tests/unit` — быстрые unit/contract тесты;
- `tests/api` — API/integration-контракт тесты;
- `tests/integration` — тесты, требующие PostgreSQL через `TEST_DATABASE_URL`.

Для запуска тестов кнопками откройте `http://localhost:8000/api/v1/tests/ui`. В `.env` включите `TEST_UI_ENABLED=true`. UI запускает pytest отдельным процессом и показывает текущий stdout в реальном времени через опрос статуса. На публичном production-сервере этот флаг следует отключить.

## Логирование

Приложение пишет логи одновременно в stdout и `storage/logs/app.log`, с ротацией файлов. Настройки: `LOG_LEVEL` и `LOG_DIR`. Каждый HTTP-запрос получает `X-Request-ID`; в логах фиксируются метод, путь, статус и длительность.

## Production test console

The project contains two complementary test layers:

1. `pytest` tests for automated regression testing.
2. Live diagnostic checks for a running production instance. These checks are read-only or contract checks and are intended to verify the live database/schema/storage/configuration without creating test data.

Enable the console with:

```env
TEST_UI_ENABLED=true
TEST_UI_REQUIRE_ADMIN=true
```

Open `/api/v1/tests/ui` and enter an administrator access token. The console provides a separate button for database, authentication, sessions, notifications, notification write contract, search, files, tasks, workflow, reports, imports, webhooks, email/SMTP and WebSocket checks, plus the full pytest suites.

The production console is admin-protected. Do not expose it publicly without authentication.

## Students and teachers

The CRM supports two education-specific account roles in addition to the existing `user`, `manager`, and `admin` roles:

- `student` — student account;
- `teacher` — teacher account.

Startup creates the `student_profiles` and `teacher_profiles` tables idempotently and seeds these two roles. A profile is linked to the existing `users` account, so authentication remains unified.

Education API:

- `GET /api/v1/students` — list student profiles for admin/manager/teacher;
- `GET /api/v1/students/me` — current student's profile;
- `PUT /api/v1/students/me` — create/update current student's profile;
- `GET /api/v1/teachers` — list teacher profiles for admin/manager/teacher;
- `GET /api/v1/teachers/me` — current teacher's profile;
- `PUT /api/v1/teachers/me` — create/update current teacher's profile.

Student profile stores student number, university, educational program, course/year, group and enrollment/graduation years. Teacher profile stores employee number, university, department, academic title and specialization.

## Обновление по ТЗ CRM ИТ Школы Ростелекома

Реализованы изменения из обновленного backend-ТЗ:

- роль `leader` и `users.supervisor_id`;
- реестр `students` с необязательной связью с пользовательским аккаунтом;
- массовый импорт студентов из `.csv`, `.xls`, `.xlsx` через `POST /api/v1/students/import`;
- обязательный `direction_id` при `POST /api/v1/programs`;
- дополнительные поля Interaction: vendor, contract, license и transfer status;
- `workflow_instances`, сохранение версии шаблона и запрет смены шаблона уже запущенного workflow;
- `workflow_transition_requests` с `approve/reject`;
- возврат на предыдущий этап с причиной и `workflow_transition_history`;
- `workflow_template_transitions` для ветвлений;
- mock двусторонних интеграций LMS и сайта;
- `integration_runs` и история интеграций;
- ограничение видимости вузов/взаимодействий для менеджеров по `user_university_access`;
- локальный JWT сохранён как основной demo provider.

Существующие `student_profiles` и `teacher_profiles` сохранены: они предназначены для учебных кабинетов и не заменяют основной CRM-реестр студентов.

## Updated CRM workflow contract

The backend follows the current CRM frontend contract:

- `manager`, `leader`, `admin` are the primary CRM roles; `student` and `teacher` remain auxiliary educational roles.
- `users.supervisor_id` links a leader to their manager team. `user_university_access.is_manager` identifies the responsible KAM for a university.
- Managers are restricted to their assigned universities. Leaders see their own/team universities and can reassign a university to a manager from their team. Admins have full access.
- `Interaction` is the central CRM business object. Compatibility fields `owner_user_id`/`template_id` remain, while `responsible_user_id`/`workflow_template_id` are also exposed.
- Workflow stages are snapshots. The legacy interaction-created workflow trigger is disabled by the application migration. A workflow is started explicitly with `POST /api/v1/interactions/{id}/workflow/start`; the template version and stages are copied into a `workflow_instance`.
- Existing workflow stage instances are not rewritten when a template is edited. Direct CRUD modification/deletion of stage instances is blocked.
- Stage status changes use `workflow_transition_requests` and are applied only after leader/admin approval.
- Rollback and branch transitions are represented by approval requests and are applied atomically in the approval transaction.
- `workflow_transition_history` records start, approve/reject, forward/branch and rollback actions.
- Student registry records are independent from user accounts and supports CSV/XLS/XLSX import.
- LMS and site endpoints are mock bidirectional integrations and create `integration_runs` records.
- `AUTH_PROVIDER=local` is the current demo provider. A `KeycloakProvider` boundary is included for the future corporate OIDC deployment; no Keycloak dependency is required for the demo.

### Main new/updated endpoints

`/api/v1/users/team`

`PUT /api/v1/universities/{id}/manager`

`GET|POST|PATCH /api/v1/it-directions`

`GET|POST|PATCH /api/v1/it-products`

`GET|POST|PATCH|DELETE /api/v1/vendors`

`POST|PATCH /api/v1/programs`

`GET|POST|PATCH /api/v1/interactions`

`POST /api/v1/interactions/{id}/workflow/start`

`GET /api/v1/interactions/{id}/workflow`

`POST /api/v1/workflow-transition-requests`

`GET /api/v1/workflow-transition-requests?status=pending`

`POST /api/v1/workflow-transition-requests/{id}/approve`

`POST /api/v1/workflow-transition-requests/{id}/reject`

`POST /api/v1/interactions/{id}/workflow/rollback`

`POST /api/v1/interactions/{id}/workflow/transition`

`GET /api/v1/interactions/{id}/workflow/history`

`GET|POST /api/v1/workflow-templates/{id}/transitions`

`PATCH|DELETE /api/v1/workflow-template-transitions/{id}`

`GET|POST|PATCH|DELETE /api/v1/students`

`POST /api/v1/students/import`

`GET|POST /api/v1/integrations/lms/*`

`GET|POST /api/v1/integrations/site/*`

`GET /api/v1/integrations/history`

`GET /api/v1/integrations/history/{id}`
