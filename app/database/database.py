import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Sequence
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, desc

from app.config import settings
from app.database.models import (
    Base,
    User,
    Job,
    JobMatch,
    DEFAULT_SKILLS,
    DEFAULT_ROLES,
    DEFAULT_LOCATION_TIERS,
)

logger = logging.getLogger(__name__)

# Create async engine and session factory
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database tables and run automatic migrations for SQLite schema updates."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # SQLite automatic schema migration for added columns
        def migrate_columns(sync_conn):
            from sqlalchemy import text
            cursor = sync_conn.connection.cursor()
            cursor.execute("PRAGMA table_info(users)")
            existing_cols = [row[1] for row in cursor.fetchall()]
            
            if "location_tiers" not in existing_cols:
                cursor.execute(f"ALTER TABLE users ADD COLUMN location_tiers TEXT DEFAULT '{DEFAULT_LOCATION_TIERS}'")
                logger.info("Migrated users table: added location_tiers column.")
            if "work_mode" not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN work_mode VARCHAR(100) DEFAULT 'Any (Remote, Hybrid, On-site)'")
                logger.info("Migrated users table: added work_mode column.")

        await conn.run_sync(migrate_columns)
    logger.info("Database schema initialized and migrated successfully.")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async transactional database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Repository helper functions
async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> User:
    """Retrieve existing user or create a new user profile."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            skills=DEFAULT_SKILLS,
            preferred_roles=DEFAULT_ROLES,
            location_tiers=DEFAULT_LOCATION_TIERS,
            location_preference="Ahmedabad / Gujarat / Remote India",
            work_mode="Any (Remote, Hybrid, On-site)",
            experience_years=0,
            is_subscribed=True,
        )
        session.add(user)
        await session.flush()
        logger.info(f"Created personalized user profile for telegram_id={telegram_id}")
    else:
        # Update username/first_name if changed
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name

    return user


async def get_active_subscribers(session: AsyncSession) -> Sequence[User]:
    """Retrieve all users with active job digest subscriptions."""
    result = await session.execute(select(User).where(User.is_subscribed == True))
    return result.scalars().all()


async def get_recent_jobs(session: AsyncSession, limit: int = 50) -> Sequence[Job]:
    """Retrieve active jobs ordered by latest posted date."""
    result = await session.execute(
        select(Job).where(Job.is_active == True).order_by(desc(Job.posted_at)).limit(limit)
    )
    return result.scalars().all()
