from typing import Dict, Optional, List
from domain.situation_classifier import SituationClassifier, SituationResult, SituationType, SituationEvidence
from config.loader import business_rules
import structlog

logger = structlog.get_logger()

class RuleBasedSituationClassifier(SituationClassifier):
    """
    Classifies situations based on deterministic rules and configurable thresholds.
    """
    
    def classify(self, kpis: Dict[str, Optional[float]]) -> SituationResult:
        """
        Classifies the current situation based on KPI values.
        Prioritizes critical operational issues over strategic ones.
        """
        thresholds = business_rules.situation_thresholds
        
        # 1. Check for Crowding (High Priority - Safety/Experience)
        crowding_result = self._check_crowding(kpis, thresholds.get("crowding", {}))
        if crowding_result:
            return crowding_result
            
        # 2. Check for Understaffing (High Priority - Service Level)
        understaffed_result = self._check_understaffed(kpis, thresholds.get("understaffed", {}))
        if understaffed_result:
            return understaffed_result

        # 3. Check for High Traffic Low Conversion (Medium Priority - Opportunity)
        high_traffic_result = self._check_high_traffic_low_conversion(kpis, thresholds.get("high_traffic_low_conversion", {}))
        if high_traffic_result:
            return high_traffic_result
            
        # 4. Check for Underperformance (Low Priority - Strategic)
        underperformance_result = self._check_underperformance(kpis, thresholds.get("underperformance", {}))
        if underperformance_result:
            return underperformance_result
            
        # 5. Default to Normal
        return SituationResult(
            situation_label=SituationType.NORMAL,
            severity=0.0,
            evidence=[],
            details="All KPIs act within normal parameters."
        )

    def _get_value(self, kpis: Dict, key: str) -> float:
        val = kpis.get(key)
        return float(val) if val is not None else 0.0

    def _check_crowding(self, kpis: Dict, limits: Dict) -> Optional[SituationResult]:
        congestion = self._get_value(kpis, "congestion_level")
        threshold = limits.get("congestion_level", 0.8)
        
        if congestion > threshold:
            severity = 0.5
            if congestion > limits.get("severity_high", 0.9):
                severity = 0.9
            elif congestion > limits.get("severity_medium", 0.8):
                severity = 0.7
                
            return SituationResult(
                situation_label=SituationType.CROWDING,
                severity=severity,
                evidence=[
                    SituationEvidence("congestion_level", congestion, threshold, 
                                    f"Congestion {congestion:.2f} exceeds threshold {threshold}")
                ],
                details=f"Branch is experiencing high congestion ({congestion:.0%})."
            )
        return None

    def _check_understaffed(self, kpis: Dict, limits: Dict) -> Optional[SituationResult]:
        adequacy = self._get_value(kpis, "staffing_adequacy_index")
        bottleneck = self._get_value(kpis, "bottleneck_score")
        
        threshold_adequacy = limits.get("staffing_adequacy_index", 0.7)
        threshold_bottleneck = limits.get("bottleneck_score", 0.6)
        
        # Condition: Low adequacy OR High bottleneck
        # We check strictly if adequacy is calculated (not 0.0 implied missing) - wait, _get_value returns 0.0 if missing.
        # Staffing adequacy 0.0 means bad IF we have valid data, but usually implies no staff data.
        # Let's assume valid data for now.
        
        if (0 < adequacy < threshold_adequacy) or (bottleneck > threshold_bottleneck):
            severity = 0.7
            evidence = []
            if 0 < adequacy < threshold_adequacy:
                 evidence.append(SituationEvidence("staffing_adequacy_index", adequacy, threshold_adequacy,
                                                 f"Staffing adequacy {adequacy:.2f} is below {threshold_adequacy}"))
            if bottleneck > threshold_bottleneck:
                 evidence.append(SituationEvidence("bottleneck_score", bottleneck, threshold_bottleneck,
                                                 f"Bottleneck score {bottleneck:.2f} exceeds {threshold_bottleneck}"))
            
            return SituationResult(
                situation_label=SituationType.UNDERSTAFFED,
                severity=severity,
                evidence=evidence,
                details="Branch appears understaffed relative to current traffic."
            )
        return None

    def _check_high_traffic_low_conversion(self, kpis: Dict, limits: Dict) -> Optional[SituationResult]:
        traffic = self._get_value(kpis, "traffic_index")
        conversion = self._get_value(kpis, "conversion_proxy")
        
        limit_traffic = limits.get("traffic_index", 1.2)
        limit_conversion = limits.get("conversion_proxy", 0.6)
        
        if traffic > limit_traffic and conversion < limit_conversion:
             return SituationResult(
                situation_label=SituationType.HIGH_TRAFFIC_LOW_CONVERSION,
                severity=0.6,
                evidence=[
                    SituationEvidence("traffic_index", traffic, limit_traffic, 
                                    f"High traffic {traffic:.2f} > {limit_traffic}"),
                    SituationEvidence("conversion_proxy", conversion, limit_conversion, 
                                    f"Low conversion {conversion:.2f} < {limit_conversion}")
                ],
                details="High visitor traffic but low entered/passed ratio."
            )
        return None

    def _check_underperformance(self, kpis: Dict, limits: Dict) -> Optional[SituationResult]:
        traffic = self._get_value(kpis, "traffic_index")
        # Ensure traffic is not 0 to avoid false positives on empty data
        if 0 < traffic < limits.get("traffic_index", 0.7):
             return SituationResult(
                situation_label=SituationType.UNDERPERFORMANCE,
                severity=0.5,
                evidence=[
                    SituationEvidence("traffic_index", traffic, limits.get("traffic_index", 0.7), 
                                    f"Traffic {traffic:.2f} is significantly below baseline")
                ],
                details="Branch is underperforming in visitor traffic."
            )
        return None
