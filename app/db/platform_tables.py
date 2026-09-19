from sqlalchemy.ext.asyncio import AsyncEngine

async def ensure_platform_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        stmts = [
        """CREATE TABLE IF NOT EXISTS auth_email_verifications (
            id uuid PRIMARY KEY, user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash varchar(128) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL, verified_at timestamptz, revoked_at timestamptz)""",
        """CREATE INDEX IF NOT EXISTS ix_auth_email_verifications_user ON auth_email_verifications(user_id)""",
        """CREATE TABLE IF NOT EXISTS auth_password_resets (
            id uuid PRIMARY KEY, user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash varchar(128) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL, used_at timestamptz, revoked_at timestamptz)""",
        """CREATE INDEX IF NOT EXISTS ix_auth_password_resets_user ON auth_password_resets(user_id)""",
        """CREATE TABLE IF NOT EXISTS audit_log (
            id bigserial PRIMARY KEY, user_id bigint REFERENCES users(id) ON DELETE SET NULL,
            action varchar(150) NOT NULL, entity_type varchar(100), entity_id varchar(100),
            old_value jsonb, new_value jsonb, ip_address inet, user_agent text,
            request_id uuid, created_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log(created_at DESC)""",
        """CREATE INDEX IF NOT EXISTS ix_audit_log_entity ON audit_log(entity_type, entity_id)""",
        """CREATE TABLE IF NOT EXISTS notifications (
            id bigserial PRIMARY KEY, user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type varchar(100) NOT NULL, title varchar(255) NOT NULL, message text NOT NULL,
            data jsonb NOT NULL DEFAULT '{}'::jsonb, read_at timestamptz, created_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE INDEX IF NOT EXISTS ix_notifications_user_unread ON notifications(user_id, read_at, created_at DESC)""",
        """CREATE TABLE IF NOT EXISTS notification_preferences (
            user_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            email_enabled boolean NOT NULL DEFAULT true, in_app_enabled boolean NOT NULL DEFAULT true,
            workflow_enabled boolean NOT NULL DEFAULT true, task_enabled boolean NOT NULL DEFAULT true,
            document_enabled boolean NOT NULL DEFAULT true, updated_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS webhooks (
            id bigserial PRIMARY KEY, name varchar(150) NOT NULL, url text NOT NULL,
            secret text, events jsonb NOT NULL DEFAULT '[]'::jsonb, active boolean NOT NULL DEFAULT true,
            created_by bigint REFERENCES users(id) ON DELETE SET NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id bigserial PRIMARY KEY, webhook_id bigint NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
            event varchar(150) NOT NULL, payload jsonb NOT NULL, status_code integer,
            response_body text, attempt integer NOT NULL DEFAULT 1, delivered_at timestamptz,
            next_attempt_at timestamptz, created_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS background_jobs (
            id uuid PRIMARY KEY, kind varchar(120) NOT NULL, payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            status varchar(30) NOT NULL DEFAULT 'queued', attempts integer NOT NULL DEFAULT 0,
            error text, run_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz,
            finished_at timestamptz, created_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE INDEX IF NOT EXISTS ix_background_jobs_queue ON background_jobs(status, run_at)""",
        ]
        for stmt in stmts:
            await conn.exec_driver_sql(stmt)
        await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at timestamptz")
        # Soft-delete support for users without requiring a schema migration file.
        await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at timestamptz")
        await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_by bigint REFERENCES users(id) ON DELETE SET NULL")
