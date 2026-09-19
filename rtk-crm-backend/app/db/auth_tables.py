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
