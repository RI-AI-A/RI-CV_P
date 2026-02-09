from dataclasses import dataclass
from typing import List, Optional
from domain.situation_classifier import SituationResult

@dataclass
class Recommendation:
    """Actionable recommendation based on situation analysis."""
    action: str
    priority: str  # high, medium, low
    expected_impact: str
    value_factor: float = 0.0  # Normalized impact score if applicable
    details: Optional[str] = None

class RecommendationEngine:
    """Abstract base class for recommendation generation."""
    
    def generate_recommendations(
        self, 
        situation_result: SituationResult,
        branch_context: dict = None
    ) -> List[Recommendation]:
        """
        Generates recommendations based on the diagnosed situation.
        
        Args:
            situation_result: The result from the SituationClassifier
            branch_context: Optional context like branch capacity, staff count, etc.
            
        Returns:
            List of Recommendation objects
        """
        raise NotImplementedError
