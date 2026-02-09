from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import structlog

from api_service.deps import get_database
from api_service.services.recommendation_service import RecommendationService
from schemas.recommendation import RecommendationResponse, RecommendationSchema
from schemas.situation import SituationResponse, EvidenceSchema
from domain.situation_classifier import SituationResult

logger = structlog.get_logger()

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.post("/{branch_id}", response_model=RecommendationResponse)
@router.get("/{branch_id}", response_model=RecommendationResponse)
async def generate_recommendations(
    branch_id: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Generate recommendations for a branch based on current situation.
    """
    try:
        service = RecommendationService(db)
        result = await service.get_recommendations(branch_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No recent KPI data found for branch {branch_id}"
            )
            
        situation_result = result["situation"]
        recommendations = result["recommendations"]
        
        # Map SituationResult -> SituationResponse
        evidence_list = [
            EvidenceSchema(
                kpi_name=e.kpi_name,
                value=e.value,
                threshold=e.threshold,
                description=e.description
            ) for e in situation_result.evidence
        ]
        
        situation_response = SituationResponse(
            branch_id=branch_id,
            situation=situation_result.situation_label.value,
            severity=situation_result.severity,
            evidence=evidence_list,
            details=situation_result.details
        )
        
        # Map Recommendations -> RecommendationSchema
        rec_list = [
            RecommendationSchema(
                action=r.action,
                priority=r.priority,
                expected_impact=r.expected_impact,
                value_factor=r.value_factor,
                details=r.details
            ) for r in recommendations
        ]
        
        return RecommendationResponse(
            branch_id=branch_id,
            situation=situation_response,
            recommendations=rec_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations for branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
