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


from datetime import datetime
from typing import Optional

@router.get("/kpis/branch/{branch_id}", response_model=List[KPIResponse])
async def get_branch_kpis(
    branch_id: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_database)
):
    """
    Get KPIs for a branch.
    
    Args:
        branch_id: Branch ID
        from_date: Optional start date filter
        to_date: Optional end date filter
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of KPI records
    """
    try:
        query = select(BranchKPITimeseries).where(BranchKPITimeseries.branch_id == branch_id)
        
        if from_date:
            query = query.where(BranchKPITimeseries.time_window_start >= from_date)
            
        if to_date:
            query = query.where(BranchKPITimeseries.time_window_end <= to_date)
            
        result = await db.execute(
            query.order_by(BranchKPITimeseries.time_window_start.desc()).limit(limit)
        )
        return result.scalars().all()
    
    except Exception as e:
        logger.error("Error retrieving KPIs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve KPIs: {str(e)}"
        )
