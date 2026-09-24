from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_education_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            user_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            student_number varchar(80) UNIQUE,
            university_id bigint REFERENCES universities(id) ON DELETE SET NULL,
            program_id bigint REFERENCES programs(id) ON DELETE SET NULL,
            course_year smallint CHECK (course_year IS NULL OR course_year BETWEEN 1 AND 12),
            group_name varchar(100),
            enrollment_year smallint CHECK (enrollment_year IS NULL OR enrollment_year BETWEEN 1900 AND 2200),
            graduation_year smallint CHECK (graduation_year IS NULL OR graduation_year BETWEEN 1900 AND 2200),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """)
        await conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS teacher_profiles (
            user_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            employee_number varchar(80) UNIQUE,
            university_id bigint REFERENCES universities(id) ON DELETE SET NULL,
            department varchar(200),
            academic_title varchar(200),
            specialization varchar(300),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """)
        await conn.exec_driver_sql("""
        INSERT INTO roles (code, name, description) VALUES
            ('student', 'Student', 'Student account with access to educational CRM features'),
            ('teacher', 'Teacher', 'Teacher account with access to educational CRM features')
        ON CONFLICT (code) DO NOTHING
        """)
        await conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS ix_student_profiles_university_id
        ON student_profiles(university_id)
        """)
        await conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS ix_student_profiles_program_id
        ON student_profiles(program_id)
        """)
        await conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS ix_teacher_profiles_university_id
        ON teacher_profiles(university_id)
        """)
