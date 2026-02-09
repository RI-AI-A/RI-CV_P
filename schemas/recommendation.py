from typing import List, Optional
from pydantic import BaseModel
from schemas.situation import SituationTypeEnum, SituationResponse

class RecommendationSchema(BaseModel):
    action: str
    priority: str
    expected_impact: str
    value_factor: Optional[float] = 0.0
    details: Optional[str] = None
    
class RecommendationResponse(BaseModel):
    branch_id: str
    situation: SituationResponse
    recommendations: List[RecommendationSchema]
