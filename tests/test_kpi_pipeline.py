"""Tests for KPI pipeline and computation."""
import pytest
from api_service.services.kpi_service import KPIService


def test_traffic_index_computation():
    """Test traffic index calculation."""
    traffic_index = KPIService.compute_traffic_index(
        current_visitors=150,
        historical_baseline=100.0
    )
    
    assert traffic_index == 1.5


def test_conversion_proxy_computation():
    """Test conversion proxy calculation."""
    conversion_proxy = KPIService.compute_conversion_proxy(
        entered_count=65,
        passed_count=35
    )
    
    assert conversion_proxy == 0.65


def test_congestion_level_computation():
    """Test congestion level calculation."""
    congestion_level = KPIService.compute_congestion_level(
        people_in_branch=45,
        capacity=100
    )
    
    assert congestion_level == 0.45


def test_utilization_ratio_computation():
    """Test utilization ratio calculation."""
    utilization_ratio = KPIService.compute_utilization_ratio(
        entered_count=48,
        capacity=100
    )
    
    assert utilization_ratio == 0.48


def test_staffing_adequacy_computation():
    """Test staffing adequacy index calculation."""
    staffing_adequacy = KPIService.compute_staffing_adequacy_index(
        staff_count=8,
        visitor_count=100,
        target_ratio=0.1
    )
    
    assert staffing_adequacy == 0.8


def test_bottleneck_score_computation():
    """Test bottleneck score calculation."""
    bottleneck_score = KPIService.compute_bottleneck_score(
        congestion_level=0.7,
        staffing_adequacy=0.5
    )
    
    assert 0.0 <= bottleneck_score <= 1.0
    assert bottleneck_score > 0.4  # Should be relatively high


def test_compute_all_kpis():
    """Test computing all KPIs from aggregated data."""
    aggregated_data = {
        "total_visitors": 150,
        "passed_count": 50,
        "entered_count": 100,
        "capacity": 200,
        "staff_count": 10
    }
    
    kpis = KPIService.compute_all_kpis(
        aggregated_data=aggregated_data,
        historical_baseline=100.0
    )
    
    assert kpis["traffic_index"] == 1.5
    assert kpis["conversion_proxy"] is not None
    assert kpis["congestion_level"] is not None
    assert kpis["utilization_ratio"] is not None
    assert kpis["staffing_adequacy_index"] is not None
    assert kpis["bottleneck_score"] is not None
