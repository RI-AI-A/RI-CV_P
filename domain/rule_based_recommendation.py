from typing import List, Dict, Any, Optional
import structlog
import re

from domain.recommendation_engine import RecommendationEngine, Recommendation
from domain.situation_classifier import SituationResult, SituationType
from config.loader import business_rules

logger = structlog.get_logger()

class RuleBasedRecommendationEngine(RecommendationEngine):
    """
    Generates recommendations based on configurable business rules.
    """
    
    def generate_recommendations(
        self, 
        situation_result: SituationResult,
        branch_context: Dict[str, Any] = None
    ) -> List[Recommendation]:
        """
        Generate recommendations for the diagnosed situation.
        """
        if not branch_context:
            branch_context = {}
            
        situation_label = situation_result.situation_label.value
        all_rules = business_rules.recommendation_rules
        
        # Get rules for this situation
        situation_rules = all_rules.get(situation_label, [])
        if not situation_rules:
            logger.debug(f"No recommendation rules found for situation {situation_label}")
            return []
            
        recommendations = []
        kpis = branch_context.get("kpis", {})
            
        for rule in situation_rules:
            condition = rule.get("condition")
            if self._evaluate_condition(condition, kpis):
                rec = self._create_recommendation(rule, kpis)
                recommendations.append(rec)
                
        return sorted(recommendations, key=lambda x: self._priority_value(x.priority), reverse=True)

    def _evaluate_condition(self, condition: str, kpis: Dict[str, float]) -> bool:
        """
        Evaluate a string condition like 'congestion_level > 0.9'.
        Supported operators: >, <, >=, <=, ==
        """
        if not condition:
            return True
            
        try:
            # Parse condition pattern: metric operator value
            match = re.match(r"([a-zA-Z_]+)\s*(>|<|>=|<=|==)\s*([0-9.]+)", condition.strip())
            if not match:
                logger.warning(f"Invalid condition format: {condition}")
                return False
                
            metric, operator, threshold_str = match.groups()
            threshold = float(threshold_str)
            value = kpis.get(metric, 0.0)
            
            if operator == ">":
                return value > threshold
            elif operator == "<":
                return value < threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == "==":
                return value == threshold
                
            return False
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False

    def _create_recommendation(self, rule: Dict, kpis: Dict) -> Recommendation:
        """Create recommendation object with dynamic formatting."""
        impact_template = rule.get("impact_template", "")
        # Very improved template formatting could go here
        # For now simple replacement if needed, though yaml templates currently rely on pre-calc values?
        # The yaml says: "Reduces queue wait time by ~{value}%". 
        # I'll just format strictly what's necessary or leave as string.
        # Actually value_factor is used for prioritization, maybe not display.
        
        return Recommendation(
            action=rule.get("action"),
            priority=rule.get("priority", "medium"),
            expected_impact=impact_template,
            value_factor=rule.get("value_factor", 0.0),
            details=None
        )

    def _priority_value(self, priority: str) -> int:
        mapping = {"high": 3, "medium": 2, "low": 1}
        return mapping.get(priority.lower(), 1)
