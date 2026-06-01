from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session.
    Guarantees the session is closed after completion, even on exceptions.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
