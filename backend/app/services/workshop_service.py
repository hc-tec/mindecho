import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select

from app.db.models import Task, FavoriteItem, Result, TaskStatus, Workshop as WorkshopModel
from app.schemas.unified import TaskCreate
from app.crud import crud_favorites
from app.core.websocket_manager import manager
from app.services.executors import executor_registry, ExecutionContext

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
    db_task = Task(**task_in.dict())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def run_workshop_task(
    db: AsyncSession, *, task_id: int, result_to_update_id: Optional[int] = None
):
    """
    Runs the actual AI workshop task in the background.
    Can either create a new result or update an existing one.
    """
    task = await db.get(Task, task_id)
    if not task:
        print(f"Task with id {task_id} not found.")
        return

    try:
        # 1. Set status to in_progress and notify client
        task.status = TaskStatus.IN_PROGRESS
        db.add(task)
        await db.commit()
        await manager.send_json(str(task_id), {"status": "in_progress", "message": "Starting AI task..."})
        
        # 2. Execute via pluggable executor
        await manager.send_json(str(task_id), {"status": "in_progress", "message": "Processing task..."})
        ws = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == task.workshop_id))).scalars().first()
        executor_type = ws.executor_type if ws else "llm_chat"
        prompt_text = task.prompt or (ws.default_prompt if ws else None)
        model_name = task.llm_model or (ws.default_model if ws else None)
        ctx = ExecutionContext(db=db, task_id=task.id, favorite_item_id=task.favorite_item_id)
        executor = executor_registry.get(executor_type)
        ai_result_text = await executor(ctx, prompt_template=prompt_text or "请对以下内容进行分析并给出结论与摘要。\n\n{source}", model=model_name)
        await manager.send_json(str(task_id), {"status": "in_progress", "type": "token", "data": ai_result_text})

        # 3. Save or Update the result
        if result_to_update_id:
            result_to_update = await db.get(Result, result_to_update_id)
            if result_to_update:
                result_to_update.content = ai_result_text
                result_to_update.task_id = task.id
                db.add(result_to_update)
            else:
                # Fallback to creating a new one if the old one is gone
                new_result = Result(
                    workshop_id=task.workshop_id,
                    content=ai_result_text,
                    task_id=task.id,
                    favorite_item_id=task.favorite_item_id # We'll need to add this to the Task model
                )
                db.add(new_result)
        else:
             new_result = Result(
                workshop_id=task.workshop_id,
                content=ai_result_text,
                task_id=task.id,
                favorite_item_id=task.favorite_item_id # We'll need to add this to the Task model
            )
             db.add(new_result)
        
        # 4. Set status to success and notify client
        task.status = TaskStatus.SUCCESS
        db.add(task)
        await db.commit()
        await manager.send_json(str(task_id), {"status": "success", "message": "Task completed.", "result": ai_result_text})

    except Exception as e:
        task.status = TaskStatus.FAILURE
        db.add(task)
        await db.commit()
        await manager.send_json(str(task_id), {"status": "failure", "message": str(e)})
    finally:
        # Disconnect the websocket after the task is done
        manager.disconnect(str(task_id))
