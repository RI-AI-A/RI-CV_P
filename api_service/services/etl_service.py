"""ETL service orchestrating data processing and KPI computation."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import List, Optional
import structlog

from api_service.services.aggregation_service import AggregationService
from api_service.services.kpi_service import KPIService
from db.models import Branch, BranchKPITimeseries

logger = structlog.get_logger()


class ETLService:
    """ETL service for processing movement data and computing KPIs."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize ETL service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.aggregation_service = AggregationService(db)
        self.kpi_service = KPIService()
    
    async def run_etl(
        self,
        branch_id: Optional[str] = None,
        time_window_minutes: int = 60
    ) -> dict:
        """
        Run ETL pipeline for branches.
        
        Args:
            branch_id: Specific branch ID or None for all branches
            time_window_minutes: Time window size in minutes
            
        Returns:
            ETL run summary
        """
        logger.info("Starting ETL run", branch_id=branch_id, time_window_minutes=time_window_minutes)
        
        # Get branches to process
        if branch_id:
            result = await self.db.execute(
                select(Branch).where(Branch.id == branch_id)
            )
            branches = [result.scalar_one_or_none()]
            if not branches[0]:
                logger.error("Branch not found", branch_id=branch_id)
                return {
                    "status": "error",
                    "message": f"Branch {branch_id} not found",
                    "branches_processed": 0,
                    "kpis_computed": 0
                }
        else:
            result = await self.db.execute(select(Branch))
            branches = result.scalars().all()
        
        branches_processed = 0
        kpis_computed = 0
        
        # Process each branch
        for branch in branches:
            try:
                # Define time window (last N minutes)
                time_window_end = datetime.utcnow()
                time_window_start = time_window_end - timedelta(minutes=time_window_minutes)
                
                # Aggregate data
                aggregated_data = await self.aggregation_service.aggregate_branch_movements(
                    branch.id,
                    time_window_start,
                    time_window_end
                )
                
                # Get historical baseline
                historical_baseline = await self.aggregation_service.get_historical_baseline(
                    branch.id,
                    days=30
                )
                
                # Compute KPIs
                kpis = self.kpi_service.compute_all_kpis(
                    aggregated_data,
                    historical_baseline
                )
                
                # Store KPIs
                kpi_record = BranchKPITimeseries(
                    branch_id=branch.id,
                    time_window_start=time_window_start,
                    time_window_end=time_window_end,
                    traffic_index=kpis["traffic_index"],
                    conversion_proxy=kpis["conversion_proxy"],
                    congestion_level=kpis["congestion_level"],
                    growth_momentum=kpis["growth_momentum"],
                    utilization_ratio=kpis["utilization_ratio"],
                    staffing_adequacy_index=kpis["staffing_adequacy_index"],
                    bottleneck_score=kpis["bottleneck_score"]
                )
                self.db.add(kpi_record)
                
                branches_processed += 1
                kpis_computed += 1
                
                logger.info(
                    "KPIs computed for branch",
                    branch_id=branch.id,
                    traffic_index=kpis["traffic_index"],
                    conversion_proxy=kpis["conversion_proxy"]
                )
            
            except Exception as e:
                logger.error("Error processing branch", branch_id=branch.id, error=str(e))
                continue
        
        # Commit all changes
        await self.db.commit()
        
        logger.info(
            "ETL run completed",
            branches_processed=branches_processed,
            kpis_computed=kpis_computed
        )
        
        return {
            "status": "success",
            "message": "ETL completed successfully",
            "branches_processed": branches_processed,
            "kpis_computed": kpis_computed
        }
