"""Pydantic schemas for tasks."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class TaskCreate(BaseModel):
    """Task creation schema."""
    employee_id: int = Field(..., description="Employee ID")
    task: str = Field(..., description="Task description")
    time: datetime = Field(..., description="Task scheduled time")
    state: str = Field(..., description="Task state: pending, in_progress, completed")
    branch_id: str = Field(..., description="Branch ID")
    note: Optional[str] = Field(None, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": 1,
                "task": "Restock shelves in aisle 3",
                "time": "2026-02-08T14:00:00Z",
                "state": "pending",
                "branch_id": "branch_001",
                "note": "Priority: High"
            }
        }


class TaskResponse(BaseModel):
    """Task response schema."""
    id: int
    employee_id: int
    task: str
    time: datetime
    state: str
    branch_id: str
    note: Optional[str]

    class Config:
        from_attributes = True

class TaskFromRecommendation(BaseModel):
    """Schema for creating a task from a recommendation."""
    employee_id: int
    branch_id: str
    action: str
    priority: str
    expected_impact: str
    details: Optional[str] = None
    note: Optional[str] = None

class TaskAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    COMPLETE = "complete"

class TaskStatusUpdate(BaseModel):
    """Schema for updating task status."""
    action: TaskAction
    note: Optional[str] = None

