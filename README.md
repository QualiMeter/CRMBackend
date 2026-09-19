# RTK IT School CRM Backend

FastAPI backend для уже существующей PostgreSQL базы `crm`.

## Локальный запуск

Создай `.env` из `.env.example` и укажи данные PostgreSQL:

```env
APP_NAME=RTK IT School CRM API
APP_VERSION=2.0.0
API_PREFIX=/api/v1
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/crm
CORS_ORIGINS=*
```

Установи зависимости:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Запуск только через Uvicorn:

```powershell
python -m uvicorn app.main:app --reload
```

## Railway

Проект содержит `Dockerfile`. Railway автоматически собирает контейнер и запускает его. Порт берётся из переменной окружения `PORT`, которую предоставляет Railway.

Для подключения PostgreSQL укажи `DATABASE_URL` в Variables. Формат:

```text
postgresql+asyncpg://USERNAME:PASSWORD@SERVER:PORT/crm
```

Если PostgreSQL Railway предоставляет URL с `postgresql://` или `postgres://`, его необходимо привести к формату `postgresql+asyncpg://`.

SQL-файлов и Docker Compose в проекте нет. База `crm` должна уже содержать актуальную схему.

## Документация

- Swagger: `/docs`
- Scalar: `/scalar`
- Health: `/health`

## Заполнение БД

Для обычного заполнения можно использовать CRUD-роуты, например:

```http
POST /api/v1/data/universities
Content-Type: application/json

{
  "name": "Московский технический университет",
  "short_name": "МТУ",
  "city": "Москва",
  "status": "communication"
}
```

Полный пример данных находится в `examples/database-snapshot.json`.

## Синхронизация всей БД с фронтендом

Фронтенд может отправлять текущий снимок данных одним запросом:

```http
POST /api/v1/sync/database
Content-Type: application/json
```

Тело:

```json
{
  "tables": {
    "universities": [
      {
        "id": 1,
        "name": "Московский технический университет",
        "short_name": "МТУ",
        "city": "Москва"
      }
    ]
  },
  "deleted": {
    "universities": [5]
  },
  "replace": false
}
```

Существующие строки обновляются по primary key, новые создаются, а ключи из `deleted` удаляются. Операция выполняется в одной транзакции.

`replace: true` предназначен только для полного snapshot: отсутствующие строки переданных таблиц будут удалены.

Список таблиц:

```http
GET /api/v1/sync/database/tables
```
