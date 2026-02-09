from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import Optional, Dict
import structlog

from db.models import BranchKPITimeseries
from domain.rule_based_classifier import RuleBasedSituationClassifier
from domain.situation_classifier import SituationResult, SituationType
from domain.explanation_generator import ExplanationGenerator

logger = structlog.get_logger()

class SituationService:
    """
    Service for situational analysis of branches.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.classifier = RuleBasedSituationClassifier()
        self.explainer = ExplanationGenerator()
        
    async def analyze_branch(self, branch_id: str) -> Optional[SituationResult]:
        """
        Analyzes the current situation of a branch based on latest KPIs.
        
        Args:
            branch_id: The ID of the branch to analyze
            
        Returns:
            SituationResult or None if no data found
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
                logger.warning(f"No KPI data found for branch {branch_id}")
                return None
                
            # Convert to dictionary for classifier
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
            
            # Classify
            situation = self.classifier.classify(kpis)
            
            # Generate Explanation
            branch_name = kpi_record.branch.name if kpi_record.branch else branch_id
            explanation = self.explainer.generate(branch_name, situation, kpis)
            situation.details = explanation
            
            logger.info(f"Situation analyzed for branch {branch_id}: {situation.situation_label}")
            return situation
            
        except Exception as e:
            logger.error(f"Error analyzing branch {branch_id}: {e}")
            raise
