import pytest
from domain.situation_classifier import SituationResult, SituationType, SituationEvidence
from domain.rule_based_recommendation import RuleBasedRecommendationEngine
from domain.recommendation_engine import Recommendation

@pytest.fixture
def engine():
    return RuleBasedRecommendationEngine()

def test_recommend_crowding(engine):
    situation = SituationResult(
        situation_label=SituationType.CROWDING,
        severity=0.9,
        evidence=[],
        details="High crowding"
    )
    context = {"kpis": {"congestion_level": 0.95}}
    
    recs = engine.generate_recommendations(situation, context)
    assert len(recs) > 0
    assert any(r.action == "Open additional checkout counters" for r in recs)
    
def test_recommend_underperformance(engine):
    situation = SituationResult(
        situation_label=SituationType.UNDERPERFORMANCE,
        severity=0.5,
        evidence=[],
        details="Underperformance"
    )
    context = {"kpis": {"traffic_index": 0.5, "conversion_proxy": 0.4}}
    
    recs = engine.generate_recommendations(situation, context)
    assert len(recs) > 0
    
def test_recommend_normal(engine):
    situation = SituationResult(
        situation_label=SituationType.NORMAL,
        severity=0.0,
        evidence=[],
        details="Normal"
    )
    context = {"kpis": {}}
    
    recs = engine.generate_recommendations(situation, context)
    assert len(recs) == 0

def test_condition_evaluation(engine):
    kpis = {"congestion_level": 0.9}
    assert engine._evaluate_condition("congestion_level > 0.8", kpis) is True
    assert engine._evaluate_condition("congestion_level > 0.95", kpis) is False
    assert engine._evaluate_condition("congestion_level == 0.9", kpis) is True
    assert engine._evaluate_condition("congestion_level < 0.5", kpis) is False
