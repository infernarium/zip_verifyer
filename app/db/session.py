import redis.asyncio as redis_async
import redis as redis_sync
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.config import db_settings, redis_settings

# Асинхронный движок для FastAPI
async_engine = create_async_engine(db_settings.DATABASE_URL)
async_session_maker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# Синхронный движок для Celery
sync_engine = create_engine(db_settings.DATABASE_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=sync_engine)

# Подключение к Redis
redis_client_async = redis_async.Redis.from_url(
    redis_settings.REDIS_URL, decode_responses=True
)
redis_client_sync = redis_sync.Redis.from_url(
    redis_settings.REDIS_URL, decode_responses=True
)


async def get_db():
    """Функция получения асинхронной сессии (используется в FastAPI)"""
    async with async_session_maker() as session:
        yield session
