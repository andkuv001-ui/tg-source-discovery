from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False, pool_size=20, max_overflow=10)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


class LazySessionFactory:
    def __getattr__(self, name):
        return getattr(_get_session_factory(), name)

    def __call__(self, *args, **kwargs):
        return _get_session_factory()(*args, **kwargs)


async_session_factory = LazySessionFactory()


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
