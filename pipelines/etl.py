"""ETL pipeline for processing movement data."""
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import structlog

from db.session import AsyncSessionLocal
from api_service.services.etl_service import ETLService

logger = structlog.get_logger()


async def run_etl_pipeline(
    branch_id: Optional[str] = None,
    time_window_minutes: int = 60
):
    """
    Run ETL pipeline asynchronously.
    
    Args:
        branch_id: Specific branch ID or None for all branches
        time_window_minutes: Time window size in minutes
    """
    async with AsyncSessionLocal() as db:
        etl_service = ETLService(db)
        result = await etl_service.run_etl(
            branch_id=branch_id,
            time_window_minutes=time_window_minutes
        )
        
        logger.info("ETL pipeline completed", result=result)
        return result


if __name__ == "__main__":
    # Run ETL pipeline
    asyncio.run(run_etl_pipeline())
