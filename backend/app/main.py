from fastapi import FastAPI
from app.api.endpoints import (
    favorites, sync, dashboard, collections, tags, workshops, results, tasks, search, llm, settings
)
from app.db.base import Base, engine
from app.core.logging_config import LogConfig

# Apply logging configuration at the earliest point
LogConfig.setup_logging()

app = FastAPI(
    title="MindEcho Backend",
    description="Backend service for MindEcho to manage and process favorites from various platforms.",
    version="0.1.0",
)

@app.on_event("startup")
async def startup_event():
    """
    On startup, create database tables.
    In a production environment, you would use Alembic migrations for this.
    """
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Use this to reset DB
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def read_root():
    return {"message": "Welcome to MindEcho Backend"}

# Include routers for different endpoints
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["Collections"])
app.include_router(tags.router, prefix="/api/v1", tags=["Tags"])
app.include_router(workshops.router, prefix="/api/v1/workshops", tags=["Workshops"])
app.include_router(results.router, prefix="/api/v1/results", tags=["Results"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(llm.router, prefix="/api/v1", tags=["LLM"])
app.include_router(settings.router, prefix="/api/v1", tags=["Settings"])
app.include_router(favorites.router, prefix="/api/v1", tags=["Favorites"])
app.include_router(sync.router, prefix="/api/v1", tags=["Synchronization"])
