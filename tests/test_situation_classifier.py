import pytest
from domain.situation_classifier import SituationType
from domain.rule_based_classifier import RuleBasedSituationClassifier

@pytest.fixture
def classifier():
    return RuleBasedSituationClassifier()

def test_detect_crowding(classifier):
    kpis = {
        "congestion_level": 0.95,  # > 0.8
        "traffic_index": 1.0,
        "conversion_proxy": 0.5
    }
    result = classifier.classify(kpis)
    assert result.situation_label == SituationType.CROWDING
    assert result.severity >= 0.9
    assert len(result.evidence) > 0

def test_detect_understaffed(classifier):
    kpis = {
        "congestion_level": 0.5,
        "staffing_adequacy_index": 0.4,  # < 0.7
        "bottleneck_score": 0.3
    }
    result = classifier.classify(kpis)
    assert result.situation_label == SituationType.UNDERSTAFFED
    assert result.severity == 0.7
    
def test_detect_bottleneck(classifier):
    kpis = {
        "congestion_level": 0.5,
        "staffing_adequacy_index": 0.8,
        "bottleneck_score": 0.8  # > 0.6
    }
    result = classifier.classify(kpis)
    assert result.situation_label == SituationType.UNDERSTAFFED
    
def test_detect_high_traffic_low_conversion(classifier):
    kpis = {
        "traffic_index": 1.5,      # > 1.2
        "conversion_proxy": 0.4,   # < 0.6
        "congestion_level": 0.5
    }
    result = classifier.classify(kpis)
    assert result.situation_label == SituationType.HIGH_TRAFFIC_LOW_CONVERSION
    
def test_detect_underperformance(classifier):
    kpis = {
        "traffic_index": 0.5,      # < 0.7
        "conversion_proxy": 0.8,
        "congestion_level": 0.2
    }
    result = classifier.classify(kpis)
    assert result.situation_label == SituationType.UNDERPERFORMANCE
    
def test_detect_normal(classifier):
    kpis = {
        "traffic_index": 1.0,
        "conversion_proxy": 0.8,
        "congestion_level": 0.5,
        "staffing_adequacy_index": 0.9
    }
    result = classifier.classify(kpis)
    assert result.situation_label == SituationType.NORMAL
