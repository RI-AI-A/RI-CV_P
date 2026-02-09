import pytest
from domain.situation_classifier import SituationResult, SituationType, SituationEvidence
from domain.recommendation_engine import Recommendation
from domain.explanation_generator import ExplanationGenerator

def test_generate_crowding_explanation():
    situation = SituationResult(
        situation_label=SituationType.CROWDING,
        severity=0.9,
        evidence=[
            SituationEvidence("congestion_level", 0.95, 0.8, "High congestion")
        ],
        details="Detail"
    )
    recommendations = [
        Recommendation("Action 1", "high", "Impact 1", 0.0, None)
    ]
    kpis = {"congestion_level": 0.95}
    
    explainer = ExplanationGenerator()
    text = explainer.generate("Branch A", situation, kpis, recommendations)
    
    assert "Branch A is currently experiencing crowding" in text
    assert "congestion level is 0.95" in text
    assert "We recommend to action 1 which impact 1" in text

def test_generate_underperformance_explanation():
    situation = SituationResult(
        situation_label=SituationType.UNDERPERFORMANCE,
        severity=0.5,
        evidence=[
             SituationEvidence("traffic_index", 0.5, 0.7, "Low traffic")
        ],
        details="Detail"
    )
    recommendations = []
    kpis = {"traffic_index": 0.5}
    
    explainer = ExplanationGenerator()
    text = explainer.generate("Branch B", situation, kpis, recommendations)
    
    assert "Branch B is currently experiencing underperformance" in text
    assert "traffic index is 0.50" in text
