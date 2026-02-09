from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

class SituationTypeEnum(str, Enum):
    CROWDING = "crowding"
    UNDERPERFORMANCE = "underperformance"
    HIGH_TRAFFIC_LOW_CONVERSION = "high_traffic_low_conversion"
    OPTIMAL = "optimal"
    UNDERSTAFFED = "understaffed"
    NORMAL = "normal"

class EvidenceSchema(BaseModel):
    kpi_name: str
    value: float
    threshold: float
    description: str

class SituationResponse(BaseModel):
    branch_id: str
    situation: SituationTypeEnum
    severity: float
    evidence: List[EvidenceSchema]
    details: str
