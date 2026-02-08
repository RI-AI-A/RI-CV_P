"""Pydantic schemas for KPIs."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class KPIResponse(BaseModel):
    """KPI response schema with all computed metrics."""
    id: int
    branch_id: str
    time_window_start: datetime
    time_window_end: datetime
    traffic_index: Optional[float] = Field(None, description="Visitors / historical baseline")
    conversion_proxy: Optional[float] = Field(None, description="Entered / passed ratio")
    congestion_level: Optional[float] = Field(None, description="People in branch / capacity")
    growth_momentum: Optional[float] = Field(None, description="Slope of visitors over time")
    utilization_ratio: Optional[float] = Field(None, description="Actual usage / capacity")
    staffing_adequacy_index: Optional[float] = Field(None, description="Staff on duty / required staff")
    bottleneck_score: Optional[float] = Field(None, description="Queue pressure + flow entropy")
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "branch_id": "branch_001",
                "time_window_start": "2026-02-08T10:00:00Z",
                "time_window_end": "2026-02-08T11:00:00Z",
                "traffic_index": 1.25,
                "conversion_proxy": 0.65,
                "congestion_level": 0.45,
                "growth_momentum": 0.12,
                "utilization_ratio": 0.48,
                "staffing_adequacy_index": 0.85,
                "bottleneck_score": 0.32,
                "created_at": "2026-02-08T11:05:00Z"
            }
        }


class ETLRunRequest(BaseModel):
    """ETL run request schema."""
    branch_id: Optional[str] = Field(None, description="Branch ID to process, or None for all branches")
    time_window_minutes: int = Field(60, description="Time window in minutes for aggregation")


class ETLRunResponse(BaseModel):
    """ETL run response schema."""
    status: str
    message: str
    branches_processed: int
    kpis_computed: int
