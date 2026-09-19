from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_auth_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS auth_credentials (
            user_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            username varchar(100) NOT NULL UNIQUE,
            password_hash text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """)
        await conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id uuid PRIMARY KEY,
            user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            refresh_token_hash varchar(128) NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz
        )
        """)
        await conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id
        ON auth_sessions(user_id)
        """)
        await conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS user_invitations (
            id uuid PRIMARY KEY,
            user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash varchar(128) NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            accepted_at timestamptz,
            revoked_at timestamptz
        )
        """)
        await conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS ix_user_invitations_user_id
        ON user_invitations(user_id)
        """)

        # The main schema contains the roles table, but role seed data may not
        # have been applied yet. Local registration must work on a fresh DB, so
        # bootstrap the three built-in application roles idempotently.
        await conn.exec_driver_sql("""
        INSERT INTO roles (code, name, description) VALUES
            ('user', 'User', 'Default authenticated application user'),
            ('manager', 'Manager', 'CRM manager'),
            ('admin', 'Administrator', 'CRM administrator')
        ON CONFLICT (code) DO NOTHING
        """)
