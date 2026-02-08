"""KPI computation service implementing all KPI formulas."""
from typing import Dict, Any, Optional
import numpy as np
import structlog

logger = structlog.get_logger()


class KPIService:
    """Service for computing KPI metrics from aggregated data."""
    
    @staticmethod
    def compute_traffic_index(
        current_visitors: int,
        historical_baseline: float
    ) -> Optional[float]:
        """
        Compute traffic index.
        Formula: visitors / historical_baseline
        
        Args:
            current_visitors: Current visitor count
            historical_baseline: Historical average
            
        Returns:
            Traffic index or None
        """
        if historical_baseline == 0:
            return None
        return current_visitors / historical_baseline
    
    @staticmethod
    def compute_conversion_proxy(
        entered_count: int,
        passed_count: int
    ) -> Optional[float]:
        """
        Compute conversion proxy.
        Formula: entered / passed
        
        Args:
            entered_count: Number who entered
            passed_count: Number who passed
            
        Returns:
            Conversion proxy or None
        """
        total = entered_count + passed_count
        if total == 0:
            return None
        return entered_count / total
    
    @staticmethod
    def compute_congestion_level(
        people_in_branch: int,
        capacity: int
    ) -> Optional[float]:
        """
        Compute congestion level.
        Formula: people_in_branch / capacity
        
        Args:
            people_in_branch: Current occupancy
            capacity: Branch capacity
            
        Returns:
            Congestion level or None
        """
        if capacity == 0:
            return None
        return min(people_in_branch / capacity, 1.0)  # Cap at 1.0
    
    @staticmethod
    def compute_growth_momentum(
        visitor_counts: list,
        time_points: list
    ) -> Optional[float]:
        """
        Compute growth momentum.
        Formula: slope(visitors over time)
        
        Args:
            visitor_counts: List of visitor counts
            time_points: List of time points (as timestamps)
            
        Returns:
            Growth momentum (slope) or None
        """
        if len(visitor_counts) < 2:
            return None
        
        try:
            # Linear regression to find slope
            coefficients = np.polyfit(time_points, visitor_counts, 1)
            slope = coefficients[0]
            return float(slope)
        except Exception as e:
            logger.error("Error computing growth momentum", error=str(e))
            return None
    
    @staticmethod
    def compute_utilization_ratio(
        entered_count: int,
        capacity: int
    ) -> Optional[float]:
        """
        Compute utilization ratio.
        Formula: actual usage / capacity
        
        Args:
            entered_count: Number who entered
            capacity: Branch capacity
            
        Returns:
            Utilization ratio or None
        """
        if capacity == 0:
            return None
        return min(entered_count / capacity, 1.0)
    
    @staticmethod
    def compute_staffing_adequacy_index(
        staff_count: int,
        visitor_count: int,
        target_ratio: float = 0.1
    ) -> Optional[float]:
        """
        Compute staffing adequacy index.
        Formula: staff_on_duty / required_staff
        
        Args:
            staff_count: Current staff count
            visitor_count: Visitor count
            target_ratio: Target staff-to-visitor ratio
            
        Returns:
            Staffing adequacy index or None
        """
        required_staff = visitor_count * target_ratio
        if required_staff == 0:
            return None
        return staff_count / required_staff
    
    @staticmethod
    def compute_bottleneck_score(
        congestion_level: Optional[float],
        staffing_adequacy: Optional[float]
    ) -> Optional[float]:
        """
        Compute bottleneck score.
        Formula: Combination of congestion and staffing issues
        
        Args:
            congestion_level: Congestion level
            staffing_adequacy: Staffing adequacy index
            
        Returns:
            Bottleneck score or None
        """
        if congestion_level is None:
            return None
        
        # High congestion + low staffing = high bottleneck
        staffing_factor = 1.0 - (staffing_adequacy or 0.5)
        bottleneck = (congestion_level * 0.6) + (staffing_factor * 0.4)
        
        return min(bottleneck, 1.0)
    
    @classmethod
    def compute_all_kpis(
        cls,
        aggregated_data: Dict[str, Any],
        historical_baseline: float
    ) -> Dict[str, Optional[float]]:
        """
        Compute all KPIs from aggregated data.
        
        Args:
            aggregated_data: Aggregated movement data
            historical_baseline: Historical baseline for traffic index
            
        Returns:
            Dictionary of all KPI metrics
        """
        total_visitors = aggregated_data.get("total_visitors", 0)
        passed_count = aggregated_data.get("passed_count", 0)
        entered_count = aggregated_data.get("entered_count", 0)
        capacity = aggregated_data.get("capacity", 100)
        staff_count = aggregated_data.get("staff_count", 0)
        
        # Compute individual KPIs
        traffic_index = cls.compute_traffic_index(total_visitors, historical_baseline)
        conversion_proxy = cls.compute_conversion_proxy(entered_count, passed_count)
        congestion_level = cls.compute_congestion_level(entered_count, capacity)
        utilization_ratio = cls.compute_utilization_ratio(entered_count, capacity)
        staffing_adequacy = cls.compute_staffing_adequacy_index(staff_count, total_visitors)
        
        # Growth momentum requires historical data (simplified here)
        growth_momentum = None  # Would need time series data
        
        # Bottleneck score
        bottleneck_score = cls.compute_bottleneck_score(congestion_level, staffing_adequacy)
        
        return {
            "traffic_index": traffic_index,
            "conversion_proxy": conversion_proxy,
            "congestion_level": congestion_level,
            "growth_momentum": growth_momentum,
            "utilization_ratio": utilization_ratio,
            "staffing_adequacy_index": staffing_adequacy,
            "bottleneck_score": bottleneck_score
        }
