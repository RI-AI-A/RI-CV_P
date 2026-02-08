"""Pydantic schemas for CV events."""
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional
from enum import Enum


class ActionType(str, Enum):
    """Customer action types."""
    PASSED = "passed"
    ENTERED = "entered"


class CVEventCreate(BaseModel):
    """CV event creation schema matching exact contract."""
    customer_id: UUID4 = Field(..., description="Anonymized customer UUID")
    branch_id: str = Field(..., description="Branch identifier")
    enter_time: datetime = Field(..., description="Entry timestamp (ISO-8601)")
    exit_time: Optional[datetime] = Field(None, description="Exit timestamp (ISO-8601), null if still in branch")
    action_type: ActionType = Field(..., description="Action type: passed or entered")

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "branch_id": "branch_001",
                "enter_time": "2026-02-08T10:00:00Z",
                "exit_time": "2026-02-08T10:15:00Z",
                "action_type": "entered"
            }
        }


class CVEventResponse(BaseModel):
    """CV event response schema."""
    id: int
    customer_id: UUID4
    branch_id: str
    enter_time: datetime
    exit_time: Optional[datetime]
    action_type: ActionType

    class Config:
        from_attributes = True
