"""Feature engineering module for advanced KPI computations."""
import numpy as np
from typing import List, Dict, Any
from scipy import stats
import structlog

logger = structlog.get_logger()


class FeatureEngineer:
    """Advanced feature engineering for retail intelligence."""
    
    @staticmethod
    def calculate_flow_entropy(movement_paths: List[tuple]) -> float:
        """
        Calculate flow entropy from movement paths.
        Higher entropy = more diverse movement patterns.
        
        Args:
            movement_paths: List of (from_location, to_location) tuples
            
        Returns:
            Flow entropy value
        """
        if not movement_paths:
            return 0.0
        
        # Count path frequencies
        path_counts = {}
        for path in movement_paths:
            path_counts[path] = path_counts.get(path, 0) + 1
        
        # Calculate probabilities
        total = len(movement_paths)
        probabilities = [count / total for count in path_counts.values()]
        
        # Calculate entropy
        entropy = stats.entropy(probabilities)
        return float(entropy)
    
    @staticmethod
    def calculate_queue_pressure(
        people_near_checkout: int,
        staff_on_duty: int
    ) -> float:
        """
        Calculate queue pressure metric.
        
        Args:
            people_near_checkout: Number of people in checkout area
            staff_on_duty: Number of staff members
            
        Returns:
            Queue pressure score (0-1)
        """
        if staff_on_duty == 0:
            return 1.0  # Maximum pressure
        
        ratio = people_near_checkout / staff_on_duty
        # Normalize to 0-1 scale (assuming 5:1 is maximum acceptable ratio)
        pressure = min(ratio / 5.0, 1.0)
        return pressure
    
    @staticmethod
    def calculate_peak_detection(
        visitor_counts: List[int],
        threshold_multiplier: float = 1.5
    ) -> List[int]:
        """
        Detect peak periods in visitor counts.
        
        Args:
            visitor_counts: Time series of visitor counts
            threshold_multiplier: Multiplier for mean to detect peaks
            
        Returns:
            List of indices where peaks occur
        """
        if not visitor_counts:
            return []
        
        mean_count = np.mean(visitor_counts)
        threshold = mean_count * threshold_multiplier
        
        peaks = [i for i, count in enumerate(visitor_counts) if count > threshold]
        return peaks
    
    @staticmethod
    def calculate_trend_strength(
        values: List[float],
        time_points: List[float]
    ) -> float:
        """
        Calculate strength of trend (R-squared value).
        
        Args:
            values: Time series values
            time_points: Corresponding time points
            
        Returns:
            R-squared value (0-1)
        """
        if len(values) < 2:
            return 0.0
        
        try:
            # Linear regression
            slope, intercept, r_value, _, _ = stats.linregress(time_points, values)
            r_squared = r_value ** 2
            return float(r_squared)
        except Exception as e:
            logger.error("Error calculating trend strength", error=str(e))
            return 0.0
    
    @staticmethod
    def engineer_features(raw_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Engineer advanced features from raw data.
        
        Args:
            raw_data: Raw movement and operational data
            
        Returns:
            Dictionary of engineered features
        """
        features = {}
        
        # Example feature engineering
        if "visitor_counts" in raw_data:
            visitor_counts = raw_data["visitor_counts"]
            features["visitor_mean"] = float(np.mean(visitor_counts))
            features["visitor_std"] = float(np.std(visitor_counts))
            features["visitor_max"] = float(np.max(visitor_counts))
            features["visitor_min"] = float(np.min(visitor_counts))
        
        if "dwell_times" in raw_data:
            dwell_times = raw_data["dwell_times"]
            features["dwell_time_mean"] = float(np.mean(dwell_times))
            features["dwell_time_median"] = float(np.median(dwell_times))
            features["dwell_time_std"] = float(np.std(dwell_times))
        
        return features
