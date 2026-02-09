from typing import Dict, List, Optional
from domain.situation_classifier import SituationResult, SituationType
from domain.recommendation_engine import Recommendation

class ExplanationGenerator:
    """
    Generates natural language explanations for situations and recommendations.
    """
    
    @staticmethod
    def generate(
        branch_name: str,
        situation: SituationResult,
        kpis: Dict[str, float],
        recommendations: List[Recommendation] = None
    ) -> str:
        """
        Generate a comprehensive explanation.
        """
        if not recommendations:
            recommendations = []
            
        # 1. Situation Description
        explanation = f"{branch_name} is currently experiencing {situation.situation_label.value.replace('_', ' ')}."
        
        # 2. Evidence
        if situation.evidence:
            evidence_parts = []
            for ev in situation.evidence:
                # Format: "traffic dropped 18%" or "congestion is 95% (>80%)"
                # Since we don't have historical context diff easily (unless in kpis), we state current values.
                evidence_parts.append(f"{ev.kpi_name.replace('_', ' ')} is {ev.value:.2f} (threshold: {ev.threshold})")
            
            explanation += f" This is indicated by: {', '.join(evidence_parts)}."
        
        # 3. Recommendations
        if recommendations:
            top_rec = recommendations[0]
            explanation += f" We recommend to {top_rec.action.lower()} which {top_rec.expected_impact.lower()}."
            
            if len(recommendations) > 1:
                explanation += f" ({len(recommendations)-1} other actions available)"
                
        return explanation
