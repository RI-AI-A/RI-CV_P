"""Aggregation service for time-window data aggregation."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import structlog

from db.models import CustomerBranchMovement, Branch, Task, ActionType

logger = structlog.get_logger()


class AggregationService:
    """Service for aggregating movement data over time windows."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize aggregation service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def aggregate_branch_movements(
        self,
        branch_id: str,
        time_window_start: datetime,
        time_window_end: datetime
    ) -> Dict[str, Any]:
        """
        Aggregate movement data for a branch over a time window.
        
        Args:
            branch_id: Branch ID
            time_window_start: Start of time window
            time_window_end: End of time window
            
        Returns:
            Aggregated metrics dictionary
        """
        # Get all movements in time window
        result = await self.db.execute(
            select(CustomerBranchMovement).where(
                CustomerBranchMovement.branch_id == branch_id,
                CustomerBranchMovement.enter_time >= time_window_start,
                CustomerBranchMovement.enter_time < time_window_end
            )
        )
        movements = result.scalars().all()
        
        # Count action types
        passed_count = sum(1 for m in movements if m.action_type == ActionType.PASSED)
        entered_count = sum(1 for m in movements if m.action_type == ActionType.ENTERED)
        total_visitors = len(movements)
        
        # Calculate dwell times (for entered customers)
        dwell_times = []
        for m in movements:
            if m.action_type == ActionType.ENTERED and m.exit_time:
                dwell_time = (m.exit_time - m.enter_time).total_seconds() / 60.0  # minutes
                dwell_times.append(dwell_time)
        
        avg_dwell_time = sum(dwell_times) / len(dwell_times) if dwell_times else 0.0
        
        # Get branch capacity
        branch_result = await self.db.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        capacity = branch.capacity if branch else 100
        
        # Get staff count (tasks in progress during time window)
        staff_result = await self.db.execute(
            select(func.count(func.distinct(Task.employee_id))).where(
                Task.branch_id == branch_id,
                Task.time >= time_window_start,
                Task.time < time_window_end,
                Task.state.in_(["in_progress", "completed"])
            )
        )
        staff_count = staff_result.scalar() or 0
        
        return {
            "total_visitors": total_visitors,
            "passed_count": passed_count,
            "entered_count": entered_count,
            "avg_dwell_time": avg_dwell_time,
            "capacity": capacity,
            "staff_count": staff_count,
            "time_window_start": time_window_start,
            "time_window_end": time_window_end
        }
    
    async def get_historical_baseline(
        self,
        branch_id: str,
        days: int = 30
    ) -> float:
        """
        Calculate historical baseline visitor count.
        
        Args:
            branch_id: Branch ID
            days: Number of days to look back
            
        Returns:
            Average daily visitors
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(func.count(CustomerBranchMovement.id)).where(
                CustomerBranchMovement.branch_id == branch_id,
                CustomerBranchMovement.enter_time >= cutoff_date
            )
        )
        total_count = result.scalar() or 0
        
        return total_count / days if days > 0 else 0.0
