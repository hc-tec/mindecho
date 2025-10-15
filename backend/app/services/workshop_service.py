import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.models import Task, FavoriteItem, Result, TaskStatus, Workshop as WorkshopModel
from app.schemas.unified import TaskCreate
from app.crud import crud_favorites, crud_workshops
from app.core.websocket_manager import manager
from app.services.executors import executor_registry, ExecutionContext

logger = logging.getLogger(__name__)

async def start_workshop_task(db: AsyncSession, *, workshop_id: str, collection_id: int, prompt: Optional[str] = None, llm_model: Optional[str] = None) -> Task:
    """
    Creates a new task record in the database for a workshop execution.
    """
    task_in = TaskCreate(
        workshop_id=workshop_id,
        status=TaskStatus.PENDING,
        favorite_item_id=collection_id,
        prompt=prompt,
        llm_model=llm_model,
    )
    from app.crud import task as crud_task

    db_task = await crud_task.create_task(db, task_in=task_in)
    # CRUDBase.create only flushes + refreshes; commit explicitly for durability
    await db.commit()
    return db_task

async def run_workshop_task(
    *, task_id: int, result_to_update_id: Optional[int] = None
):
    """
    Runs the actual AI workshop task in the background.
    Can either create a new result or update an existing one.

    NOTE: This function creates its own database session to avoid
    session conflicts when running in background tasks.
    """
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if not task:
            logger.warning(f"Task with id {task_id} not found.")
            return

        # Extract all needed attributes immediately to avoid lazy loading issues
        _task_id = task.id
        _workshop_id = task.workshop_id
        _favorite_item_id = task.favorite_item_id
        _prompt = task.prompt
        _llm_model = task.llm_model

        try:
            # 1. Set status to in_progress and notify client
            task.status = TaskStatus.IN_PROGRESS
            db.add(task)
            await db.commit()

            logger.info(f"Task {_task_id}: Started execution")

            # 2. Execute via pluggable executor
            ws = await crud_workshops.workshop.get_by_workshop_id(db, workshop_id=_workshop_id)
            executor_type = ws.executor_type if ws else "llm_chat"
            prompt_text = _prompt or (ws.default_prompt if ws else None)
            model_name = _llm_model or (ws.default_model if ws else None)
            ctx = ExecutionContext(db=db, task_id=_task_id, favorite_item_id=_favorite_item_id)
            executor = executor_registry.get(executor_type)
            ai_result_text = await executor(ctx, prompt_template=prompt_text or "请对以下内容进行分析并给出结论与摘要。\n\n{source}", model=model_name)

            # 3. Save or Update the result via CRUD
            from app.crud import result as crud_result

            logger.info(f"Task {_task_id}: Saving AI result (length: {len(ai_result_text) if ai_result_text else 0})")

            result_obj = await crud_result.create_or_update(
                db,
                workshop_id=_workshop_id,
                favorite_item_id=_favorite_item_id,
                task_id=_task_id,
                content=ai_result_text,
                existing_id=result_to_update_id,
            )

            logger.info(f"Task {_task_id}: Result saved with ID {result_obj.id}")

            # 3.5 Trigger notification (non-blocking)
            try:
                from app.services.notifications.notification_service import notification_service

                # Create a new task to avoid blocking
                asyncio.create_task(
                    notification_service.notify_result_created(db, result_obj.id, ws)
                )
                logger.debug(f"Task {_task_id}: Notification triggered for result {result_obj.id}")
            except Exception as notify_error:
                # Don't fail the whole task if notification fails
                logger.error(f"Task {_task_id}: Failed to trigger notification: {notify_error}")

            # 4. Set status to success and notify client
            task.status = TaskStatus.SUCCESS
            db.add(task)
            await db.commit()

            logger.info(f"Task {_task_id}: Completed successfully")

        except Exception as e:
            logger.error(f"Task {_task_id} failed: {e}", exc_info=True)
            task.status = TaskStatus.FAILURE
            db.add(task)
            await db.commit()
