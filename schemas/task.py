"""Pydantic schemas for tasks."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


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
