"""Events router for event management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api_service.deps import get_database
from schemas.event import EventCreate, EventResponse
from db.models import Event

logger = structlog.get_logger()

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    db: AsyncSession = Depends(get_database)
):
    """
    Create a new event.
    
    Args:
        event: Event data
        db: Database session
        
    Returns:
        Created event
    """
    try:
        db_event = Event(
            start_time=event.start_time,
            end_time=event.end_time,
            type=event.type,
            description=event.description,
            location=event.location,
            repetition=event.repetition,
            global_event=event.global_event
        )
        db.add(db_event)
        await db.commit()
        await db.refresh(db_event)
        
        logger.info("Event created", event_id=db_event.id, event_type=event.type)
        
        return db_event
    
    except Exception as e:
        await db.rollback()
        logger.error("Error creating event", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )
