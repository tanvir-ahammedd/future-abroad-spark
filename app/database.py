from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine with future=True and pooling settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# Async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for all ORM models
Base = declarative_base()

async def create_all_tables():
    """
    Creates all tables registered on the Base metadata.
    Typically used for local testing and initial environment setup before migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
