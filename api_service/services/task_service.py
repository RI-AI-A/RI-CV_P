from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional, List
import structlog

from db.models import Task
from schemas.task import TaskFromRecommendation, TaskStatusUpdate, TaskAction, TaskResponse

logger = structlog.get_logger()

class TaskService:
    """
    Service for managing tasks and workflows.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_from_recommendation(
        self, 
        req: TaskFromRecommendation
    ) -> Task:
        """
        Create a new task based on a recommendation.
        Initial state is 'pending'.
        """
        description = f"{req.action} (Priority: {req.priority})"
        if req.expected_impact:
            description += f" - Impact: {req.expected_impact}"
            
        note = req.note or ""
        if req.details:
            note += f"\nDetails: {req.details}"
            
        task = Task(
            employee_id=req.employee_id,
            branch_id=req.branch_id,
            task=description,
            time=datetime.utcnow(),
            state="pending",
            note=note.strip()
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Task created from recommendation: {task.id}")
        return task

    async def update_status(self, task_id: int, update: TaskStatusUpdate) -> Optional[Task]:
        """
        Update task status based on action (workflow transition).
        """
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            return None
            
        old_state = task.state
        new_state = old_state
        
        if update.action == TaskAction.APPROVE:
            if old_state == "pending":
                new_state = "in_progress"
            else:
                logger.warning(f"Invalid transition: approve {old_state}")
                # For MVP, allowing flexible transitions or ignoring invalid ones
                # Ideally raise error
                
        elif update.action == TaskAction.COMPLETE:
            new_state = "completed"
            
        elif update.action == TaskAction.REJECT:
            new_state = "rejected"
            
        task.state = new_state
        if update.note:
            task.note = (task.note or "") + f"\n[{datetime.utcnow().isoformat()}] {new_state.upper()}: {update.note}"
            
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Task {task_id} transition: {old_state} -> {new_state}")
        return task
