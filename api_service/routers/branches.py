"""Branches router for branch management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from api_service.deps import get_database
from schemas.branch import BranchCreate, BranchResponse
from db.models import Branch

logger = structlog.get_logger()

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    branch: BranchCreate,
    db: AsyncSession = Depends(get_database)
):
    """
    Create a new branch.
    
    Args:
        branch: Branch data
        db: Database session
        
    Returns:
        Created branch
    """
    try:
        # Check if branch already exists
        result = await db.execute(
            select(Branch).where(Branch.id == branch.id)
        )
        existing_branch = result.scalar_one_or_none()
        
        if existing_branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Branch with ID {branch.id} already exists"
            )
        
        # Create new branch
        db_branch = Branch(
            id=branch.id,
            name=branch.name,
            capacity=branch.capacity,
            peak_time=branch.peak_time,
            neighbors=branch.neighbors,
            state=branch.state,
            expiry=branch.expiry,
            restocking_schedule=branch.restocking_schedule
        )
        db.add(db_branch)
        await db.commit()
        await db.refresh(db_branch)
        
        logger.info("Branch created", branch_id=branch.id)
        
        return db_branch
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error creating branch", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create branch: {str(e)}"
        )


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Get branch by ID.
    
    Args:
        branch_id: Branch ID
        db: Database session
        
    Returns:
        Branch data
    """
    try:
        result = await db.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        branch = result.scalar_one_or_none()
        
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch {branch_id} not found"
            )
        
        return branch
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving branch", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve branch: {str(e)}"
        )
