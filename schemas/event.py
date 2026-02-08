"""Pydantic schemas for events."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class EventCreate(BaseModel):
    """Event creation schema."""
    start_time: datetime = Field(..., description="Event start time")
    end_time: Optional[datetime] = Field(None, description="Event end time")
    type: str = Field(..., description="Event type: sale, holiday, maintenance, etc.")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[Dict[str, Any]] = Field(None, description="Location data (flexible JSONB)")
    repetition: Optional[str] = Field(None, description="Repetition pattern: daily, weekly, monthly")
    global_event: bool = Field(False, description="Whether this is a global event")

    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2026-02-10T09:00:00Z",
                "end_time": "2026-02-10T21:00:00Z",
                "type": "sale",
                "description": "Valentine's Day Sale",
                "location": {"branch_ids": ["branch_001", "branch_002"]},
                "repetition": None,
                "global_event": False
            }
        }


class EventResponse(BaseModel):
    """Event response schema."""
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    type: str
    description: Optional[str]
    location: Optional[Dict[str, Any]]
    repetition: Optional[str]
    global_event: bool

    class Config:
        from_attributes = True
