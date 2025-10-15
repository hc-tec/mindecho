from fastapi import FastAPI
from app.api.endpoints import (
    favorites, sync, dashboard, collections, tags, workshops, results, tasks, search, llm, settings as settings_endpoint
)
from app.api.endpoints import streams
from app.services.stream_manager import stream_manager
from app.services.listener_service import handle_stream_event, start_enabled_workshop_streams
from app.core.config import settings
from app.services import workshop_service
from app.db.models import FavoriteItem
from app.core.runtime_config import runtime_config
from app.db.base import Base, engine
from app.core.logging_config import LogConfig
from sqlalchemy import select
from app.db.models import AppSetting, Workshop as WorkshopModel, Collection
from app.core.websocket_manager import manager as websocket_manager

# Apply logging configuration at the earliest point
LogConfig.setup_logging()


app = FastAPI(
    title="MindEcho Backend",
    description="Backend service for MindEcho to manage and process favorites from various platforms.",
    version="0.1.0",
)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3001",
    "http://localhost:3000",
    "http://localhost:3002",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    # start rpc client
    await stream_manager.start()
    # seed default workshops if empty
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(WorkshopModel))).scalars().all()
        if not rows:
            defaults = [
                ("summary-01", "精华摘要", "请对以下内容进行精简摘要，保留要点与行动项。\n\n{source}", None, "llm_chat"),
                ("snapshot-insight", "快照洞察", "请输出该内容的关键洞察与三个重点问题。\n\n{source}", None, "llm_chat"),
                ("information-alchemy", "信息炼金术", "请将材料转化为结构化知识要点（主题-要点-例证）。\n\n{source}", None, "llm_chat"),
                ("point-counterpoint", "观点对撞", "从正反两方进行论证并得出结论。\n\n{source}", None, "llm_chat"),
                ("learning-tasks", "学习任务", "请为学习该材料生成分层学习任务与测验题。\n\n{source}", None, "llm_chat"),
            ]
            for wid, name, dp, dm, et in defaults:
                db.add(WorkshopModel(workshop_id=wid, name=name, default_prompt=dp, default_model=dm, executor_type=et))
            await db.commit()
        # load category map from settings if exists
        mapping_row = (await db.execute(select(AppSetting).where(AppSetting.key == "category_to_workshop"))).scalars().first()
        if mapping_row and mapping_row.value:
            try:
                import json
                runtime_config.set_category_map(json.loads(mapping_row.value))
            except Exception:
                pass
    # Initialize notification system
    from app.services.notifications.notification_service import notification_service
    notification_service.initialize()

    # Register stream handler and start enabled listeners
    stream_manager.register_event_handler(handle_stream_event)
    await start_enabled_workshop_streams()

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
app.include_router(settings_endpoint.router, prefix="/api/v1", tags=["Settings"])
app.include_router(favorites.router, prefix="/api/v1", tags=["Favorites"])
app.include_router(sync.router, prefix="/api/v1", tags=["Synchronization"])
app.include_router(streams.router, prefix="/api/v1", tags=["Streams"])

@app.on_event("shutdown")
async def shutdown_event():
    await stream_manager.stop()
