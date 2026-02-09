from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api_service.deps import get_database
from api_service.services.situation_service import SituationService
from schemas.situation import SituationResponse, EvidenceSchema, SituationTypeEnum

logger = structlog.get_logger()

router = APIRouter(prefix="/situations", tags=["Situations"])

@router.get("/branch/{branch_id}", response_model=SituationResponse)
async def get_branch_situation(
    branch_id: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Get the current situation analysis for a branch.
    Based on the latest available KPI data.
    """
    try:
        service = SituationService(db)
        result = await service.analyze_branch(branch_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No recent KPI data found for branch {branch_id}. Please run ETL first."
            )
            
        # Manually map domain object to response schema for clarity
        evidence_list = [
            EvidenceSchema(
                kpi_name=e.kpi_name,
                value=e.value,
                threshold=e.threshold,
                description=e.description
            ) for e in result.evidence
        ]
        
        return SituationResponse(
            branch_id=branch_id,
            situation=result.situation_label.value,  # Enum value
            severity=result.severity,
            evidence=evidence_list,
            details=result.details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting situation for branch {branch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
