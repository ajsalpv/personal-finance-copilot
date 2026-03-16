"""
Nova AI Life Assistant — Database Connection
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Async SQLAlchemy engine (for direct PostgreSQL queries)
# ---------------------------------------------------------------------------
# Convert postgres:// to postgresql+asyncpg://
_db_url = settings.DATABASE_URL.strip()
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, echo=False, pool_size=5, max_overflow=10)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Supabase client (for Storage, Auth helpers, Realtime)
# ---------------------------------------------------------------------------
def get_supabase_client() -> Client:
    """Returns a Supabase client using the service role key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def get_supabase_anon_client() -> Client:
    """Returns a Supabase client using the anon/public key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
