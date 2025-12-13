"""Async database connection using SQLAlchemy 2.0 + asyncpg.

Provides connection pooling and session management for PostgreSQL.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════
# Async Engine Configuration
# ═══════════════════════════════════════════════════════════════
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=not settings.is_production,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# ═══════════════════════════════════════════════════════════════
# Session Factory
# ═══════════════════════════════════════════════════════════════
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions.

    Yields:
        AsyncSession: Database session that auto-closes on completion

    Example:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and verify connectivity.

    Raises:
        Exception: If database connection fails
    """
    async with engine.begin() as conn:
        # Test connection
        await conn.execute("SELECT 1")
