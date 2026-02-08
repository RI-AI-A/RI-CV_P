"""CV ingestion router for receiving CV events."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from api_service.deps import get_database
from schemas.cv_event import CVEventCreate, CVEventResponse
from db.models import Customer, CustomerBranchMovement, Branch

logger = structlog.get_logger()

router = APIRouter(prefix="/cv", tags=["CV Ingestion"])


@router.post("/events", response_model=dict, status_code=status.HTTP_200_OK)
async def ingest_cv_event(
    event: CVEventCreate,
    db: AsyncSession = Depends(get_database)
):
    """
    Ingest CV event from computer vision service.
    
    Args:
        event: CV event data
        db: Database session
        
    Returns:
        Success response
    """
    try:
        # Ensure customer exists
        customer_result = await db.execute(
            select(Customer).where(Customer.customer_id == event.customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            # Create new customer
            customer = Customer(customer_id=event.customer_id)
            db.add(customer)
            logger.info("New customer created", customer_id=str(event.customer_id))
        
        # Ensure branch exists
        branch_result = await db.execute(
            select(Branch).where(Branch.id == event.branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        
        if not branch:
            logger.warning("Branch not found, creating placeholder", branch_id=event.branch_id)
            branch = Branch(
                id=event.branch_id,
                name=f"Branch {event.branch_id}",
                capacity=100  # Default capacity
            )
            db.add(branch)
        
        # Create movement record
        movement = CustomerBranchMovement(
            customer_id=event.customer_id,
            branch_id=event.branch_id,
            enter_time=event.enter_time,
            exit_time=event.exit_time,
            action_type=event.action_type
        )
        db.add(movement)
        
        await db.commit()
        
        logger.info(
            "CV event ingested",
            customer_id=str(event.customer_id),
            branch_id=event.branch_id,
            action_type=event.action_type.value
        )
        
        return {
            "status": "success",
            "message": "Event ingested successfully",
            "customer_id": str(event.customer_id)
        }
    
    except Exception as e:
        await db.rollback()
        logger.error("Error ingesting CV event", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest event: {str(e)}"
        )
