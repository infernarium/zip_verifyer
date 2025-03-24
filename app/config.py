from pydantic_settings import BaseSettings, SettingsConfigDict


class MinioSettings(BaseSettings):
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadminpassword"
    MINIO_BUCKET_NAME: str = "zip-archives"

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="allow"
    )


class CelerySettings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="allow"
    )


class DBSettings(BaseSettings):
    POSTGRES_DB: str = "zip_verifier"
    POSTGRES_USER: str = "zip_admin"
    POSTGRES_PASSWORD: str = "supersecurepassword"
    DATABASE_URL: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}"
    )

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="allow"
    )


class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="allow"
    )


minio_settings = MinioSettings()
celery_settings = CelerySettings()
db_settings = DBSettings()
redis_settings = RedisSettings()
