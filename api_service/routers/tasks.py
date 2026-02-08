"""Tasks router for task management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import structlog

from api_service.deps import get_database
from schemas.task import TaskCreate, TaskResponse
from db.models import Task

logger = structlog.get_logger()

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_database)
):
    """
    Create a new task.
    
    Args:
        task: Task data
        db: Database session
        
    Returns:
        Created task
    """
    try:
        db_task = Task(
            employee_id=task.employee_id,
            task=task.task,
            time=task.time,
            state=task.state,
            branch_id=task.branch_id,
            note=task.note
        )
        db.add(db_task)
        await db.commit()
        await db.refresh(db_task)
        
        logger.info("Task created", task_id=db_task.id, branch_id=task.branch_id)
        
        return db_task
    
    except Exception as e:
        await db.rollback()
        logger.error("Error creating task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/{branch_id}", response_model=List[TaskResponse])
async def get_tasks_by_branch(
    branch_id: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Get all tasks for a branch.
    
    Args:
        branch_id: Branch ID
        db: Database session
        
    Returns:
        List of tasks
    """
    try:
        result = await db.execute(
            select(Task).where(Task.branch_id == branch_id).order_by(Task.time)
        )
        tasks = result.scalars().all()
        
        return tasks
    
    except Exception as e:
        logger.error("Error retrieving tasks", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tasks: {str(e)}"
        )
