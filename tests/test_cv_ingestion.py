"""Tests for CV ingestion endpoint."""
import pytest
from httpx import AsyncClient
from datetime import datetime
import uuid

from api_service.main import app


@pytest.mark.asyncio
async def test_ingest_cv_event_valid():
    """Test CV event ingestion with valid payload."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        event_data = {
            "customer_id": str(uuid.uuid4()),
            "branch_id": "test_branch_001",
            "enter_time": datetime.utcnow().isoformat(),
            "exit_time": datetime.utcnow().isoformat(),
            "action_type": "entered"
        }
        
        response = await client.post("/cv/events", json=event_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "customer_id" in data


@pytest.mark.asyncio
async def test_ingest_cv_event_invalid_action_type():
    """Test CV event ingestion with invalid action type."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        event_data = {
            "customer_id": str(uuid.uuid4()),
            "branch_id": "test_branch_001",
            "enter_time": datetime.utcnow().isoformat(),
            "exit_time": None,
            "action_type": "invalid_action"  # Invalid
        }
        
        response = await client.post("/cv/events", json=event_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_ingest_cv_event_missing_fields():
    """Test CV event ingestion with missing required fields."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        event_data = {
            "customer_id": str(uuid.uuid4()),
            # Missing branch_id, enter_time, action_type
        }
        
        response = await client.post("/cv/events", json=event_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
