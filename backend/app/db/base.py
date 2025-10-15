from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from typing import TypeVar, Type

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False,  # Disable SQL logging for performance
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False,  # CRITICAL: Prevent objects from expiring after commit to avoid lazy loading
)

Base = declarative_base()

ModelType = TypeVar("ModelType")

async def fully_detach(db: AsyncSession, obj: ModelType) -> ModelType:
    """
    Fully detach an object from the session to prevent lazy loading issues.
    
    This forcefully makes all attributes concrete values, avoiding any future DB queries.
    Use this when you need to access object attributes after the session is closed
    or after commits that might expire the object.
    
    Args:
        db: The database session
        obj: The SQLAlchemy model instance
        
    Returns:
        The same object with all relationships eagerly loaded
    """
    # Make the object expire so it will be reloaded
    await db.refresh(obj)
    # Now it's detached with all current attributes
    db.expunge(obj)
    return obj
