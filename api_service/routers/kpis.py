"""KPIs router for ETL and KPI retrieval."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import structlog

from api_service.deps import get_database
from api_service.services.etl_service import ETLService
from schemas.kpi import KPIResponse, ETLRunRequest, ETLRunResponse
from db.models import BranchKPITimeseries

logger = structlog.get_logger()

router = APIRouter(tags=["KPIs"])


@router.post("/etl/run", response_model=ETLRunResponse)
async def run_etl(
    request: ETLRunRequest = ETLRunRequest(),
    db: AsyncSession = Depends(get_database)
):
    """
    Trigger ETL pipeline to compute KPIs.
    
    Args:
        request: ETL run request
        db: Database session
        
    Returns:
        ETL run summary
    """
    try:
        etl_service = ETLService(db)
        result = await etl_service.run_etl(
            branch_id=request.branch_id,
            time_window_minutes=request.time_window_minutes
        )
        
        return ETLRunResponse(**result)
    
    except Exception as e:
        logger.error("Error running ETL", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run ETL: {str(e)}"
        )


@router.get("/kpis/branch/{branch_id}", response_model=List[KPIResponse])
async def get_branch_kpis(
    branch_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_database)
):
    """
    Get KPIs for a branch.
    
    Args:
        branch_id: Branch ID
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of KPI records
    """
    try:
        result = await db.execute(
            select(BranchKPITimeseries)
            .where(BranchKPITimeseries.branch_id == branch_id)
            .order_by(BranchKPITimeseries.time_window_start.desc())
            .limit(limit)
        )
        kpis = result.scalars().all()
        
        return kpis
    
    except Exception as e:
        logger.error("Error retrieving KPIs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve KPIs: {str(e)}"
        )
