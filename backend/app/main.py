from fastapi import FastAPI
from app.api.endpoints import (
    favorites, sync, dashboard, collections, tags, workshops, results, tasks, search, llm, settings
)
from app.api.endpoints import streams
from app.services.stream_manager import stream_manager
from app.services import workshop_service
from app.db.models import FavoriteItem
from app.core.runtime_config import runtime_config
from app.db.base import Base, engine
from app.core.logging_config import LogConfig
from sqlalchemy import select
from app.db.models import AppSetting, Workshop as WorkshopModel

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
    # Register auto-task handler: map stream events to workshops and trigger tasks
    async def _handle_stream_event(event: dict):
        # Expected event example (from plugin stream):
        # {"type": "favorite_added", "platform": "bilibili", "collection_id": "...", "item": {"bvid": "...", "category": "...", ...}}
        try:
            if not isinstance(event, dict):
                return
            etype = event.get("type")
            if etype != "favorite_added":
                return
            item = (event.get("item") or {})
            bvid = item.get("bvid") or item.get("platform_item_id")
            if not bvid:
                return
            # Find the corresponding FavoriteItem (assumes prior sync created it)
            # Minimal query via sessionmaker is in deps; here we use engine-bound session
            from app.db.base import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                # naive lookup by platform_item_id
                from sqlalchemy import select
                result = await db.execute(select(FavoriteItem).where(FavoriteItem.platform_item_id == bvid))
                db_item = result.scalars().first()
                if not db_item:
                    return
                # Map category -> workshop_id via runtime-configurable mapping
                category = item.get("category") or event.get("category")
                mapping = runtime_config.get_category_map()
                workshop_id = mapping.get(category or "", "summary-01")
                task = await workshop_service.start_workshop_task(db, workshop_id=workshop_id, collection_id=db_item.id)
                # Fire and forget run
                import asyncio as _asyncio
                _asyncio.create_task(workshop_service.run_workshop_task(db, task_id=task.id))
        except Exception:
            # best-effort; avoid crashing startup handler
            import logging
            logging.getLogger(__name__).exception("auto-task handler error")

    stream_manager.register_event_handler(_handle_stream_event)

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
app.include_router(streams.router, prefix="/api/v1", tags=["Streams"])

@app.on_event("shutdown")
async def shutdown_event():
    await stream_manager.stop()
