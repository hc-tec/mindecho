from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.crud import crud_favorites
from app.schemas.unified import Result, Task
from app.db.models import Result as ResultModel
from app.services import workshop_service

router = APIRouter()

class ResultUpdate(BaseModel):
    content: str

@router.put("/{id}", response_model=Result)
async def update_result(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    result_in: ResultUpdate,
):
    """
    Update the content of an AI-generated result.
    """
    db_result = await db.get(ResultModel, id)
    if not db_result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    db_result.content = result_in.content
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)
    
    return db_result

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
):
    """
    Delete an AI-generated result.
    """
    db_result = await db.get(ResultModel, id)
    if not db_result:
        raise HTTPException(status_code=404, detail="Result not found")
        
    await db.delete(db_result)
    await db.commit()
    return

@router.post("/{id}/regenerate", response_model=Task, status_code=202)
async def regenerate_result(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    background_tasks: BackgroundTasks,
):
    """
    Regenerate an AI result by creating and running a new workshop task.
    """
    db_result = await db.get(ResultModel, id)
    if not db_result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    if not db_result.favorite_item_id:
        raise HTTPException(status_code=400, detail="Result is not linked to a collection, cannot regenerate.")

    task = await workshop_service.start_workshop_task(
        db, 
        workshop_id=db_result.workshop_id, 
        collection_id=db_result.favorite_item_id
    )
    
    # We need to pass the original result_id to the task runner
    # so it knows to update this result instead of creating a new one.
    background_tasks.add_task(
        workshop_service.run_workshop_task, 
        db=db, 
        task_id=task.id,
        result_to_update_id=id
    )
    
    return task
