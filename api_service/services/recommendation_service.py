from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List, Dict, Any, Optional
import structlog

from db.models import BranchKPITimeseries
from domain.situation_classifier import SituationResult
from domain.rule_based_classifier import RuleBasedSituationClassifier
from domain.rule_based_recommendation import RuleBasedRecommendationEngine
from domain.recommendation_engine import Recommendation
from domain.explanation_generator import ExplanationGenerator

logger = structlog.get_logger()

class RecommendationService:
    """
    Service for generating recommendations for branches.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.situation_classifier = RuleBasedSituationClassifier()
        self.recommendation_engine = RuleBasedRecommendationEngine()
        self.explainer = ExplanationGenerator()
        
    async def get_recommendations(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate recommendations for a branch based on latest situation.
        
        Args:
            branch_id: The ID of the branch
            
        Returns:
            Dictionary containing situation and recommendations
        """
        try:
            # Fetch latest KPI record with branch details
            stmt = select(BranchKPITimeseries).options(
                joinedload(BranchKPITimeseries.branch)
            ).where(
                BranchKPITimeseries.branch_id == branch_id
            ).order_by(BranchKPITimeseries.time_window_start.desc()).limit(1)
            
            result = await self.db.execute(stmt)
            kpi_record = result.scalar_one_or_none()
            
            if not kpi_record:
                logger.warning(f"No KPI data found for recommendation, branch {branch_id}")
                return None
                
            # Convert to dictionary
            kpis = {
                "traffic_index": kpi_record.traffic_index,
                "conversion_proxy": kpi_record.conversion_proxy,
                "congestion_level": kpi_record.congestion_level,
                "growth_momentum": kpi_record.growth_momentum,
                "utilization_ratio": kpi_record.utilization_ratio,
                "staffing_adequacy_index": kpi_record.staffing_adequacy_index,
                "bottleneck_score": kpi_record.bottleneck_score
            }
            # Clean None values
            kpis = {k: v for k, v in kpis.items() if v is not None}
            
            # 1. Analyze Situation
            situation_result = self.situation_classifier.classify(kpis)
            
            # 2. Generate Recommendations
            context = {"kpis": kpis, "branch_id": branch_id}
            recommendations = self.recommendation_engine.generate_recommendations(
                situation_result, context
            )
            
            # 3. Generate Explanation
            branch_name = kpi_record.branch.name if kpi_record.branch else branch_id
            explanation = self.explainer.generate(branch_name, situation_result, kpis, recommendations)
            situation_result.details = explanation
            
            logger.info(f"Generated {len(recommendations)} recommendations for branch {branch_id}")
            
            return {
                "situation": situation_result,
                "recommendations": recommendations,
                "kpis": kpis
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendations for branch {branch_id}: {e}")
            raise
