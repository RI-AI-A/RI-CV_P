from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

class SituationType(str, Enum):
    CROWDING = "crowding"
    UNDERPERFORMANCE = "underperformance"
    HIGH_TRAFFIC_LOW_CONVERSION = "high_traffic_low_conversion"
    OPTIMAL = "optimal"
    UNDERSTAFFED = "understaffed"
    NORMAL = "normal"

@dataclass
class SituationEvidence:
    """Evidence supporting a situation classification."""
    kpi_name: str
    value: float
    threshold: float
    description: str

@dataclass
class SituationResult:
    """Result of situation classification."""
    situation_label: SituationType
    severity: float  # 0.0 to 1.0
    evidence: List[SituationEvidence]
    details: str

class SituationClassifier:
    """Abstract base class for situation classifiers."""
    
    def classify(self, kpis: Dict[str, Optional[float]]) -> SituationResult:
        """
        Classifies the current situation based on KPI values.
        
        Args:
            kpis: Dictionary of KPI names to values
            
        Returns:
            SituationResult object
        """
        raise NotImplementedError
