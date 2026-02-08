"""Dependency injection for API service."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db

# Database session dependency
async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_db():
        yield session
