"""Pydantic schemas for branches."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BranchCreate(BaseModel):
    """Branch creation schema."""
    id: str = Field(..., description="Branch identifier")
    name: str = Field(..., description="Branch name")
    capacity: int = Field(..., gt=0, description="Maximum capacity")
    peak_time: Optional[str] = Field(None, description="Peak time in HH:MM format")
    neighbors: Optional[List[str]] = Field(None, description="List of neighboring branch IDs")
    state: Optional[str] = Field("active", description="Branch state")
    expiry: Optional[datetime] = Field(None, description="Expiry date")
    restocking_schedule: Optional[str] = Field(None, description="Restocking schedule")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "branch_001",
                "name": "Downtown Branch",
                "capacity": 150,
                "peak_time": "18:00",
                "neighbors": ["branch_002", "branch_003"],
                "state": "active",
                "restocking_schedule": "Daily at 06:00"
            }
        }


class BranchResponse(BaseModel):
    """Branch response schema."""
    id: str
    name: str
    capacity: int
    peak_time: Optional[str]
    neighbors: Optional[List[str]]
    state: Optional[str]
    expiry: Optional[datetime]
    restocking_schedule: Optional[str]

    class Config:
        from_attributes = True
