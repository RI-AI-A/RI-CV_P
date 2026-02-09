import pytest
from unittest.mock import AsyncMock, MagicMock
from api_service.services.task_service import TaskService
from schemas.task import TaskFromRecommendation, TaskStatusUpdate, TaskAction
from db.models import Task

@pytest.mark.asyncio
async def test_create_from_recommendation():
    mock_db = AsyncMock()
    service = TaskService(mock_db)
    
    req = TaskFromRecommendation(
        employee_id=1,
        branch_id="branch_001",
        action="Test Action",
        priority="high",
        expected_impact="High impact",
        note="Note"
    )
    
    task = await service.create_from_recommendation(req)
    
    assert task.employee_id == 1
    assert "Test Action" in task.task
    assert "High impact" in task.task
    assert task.state == "pending"
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_approve_task():
    mock_db = AsyncMock()
    service = TaskService(mock_db)
    
    # Mock existing task
    mock_task = Task(id=1, state="pending", note="original")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_task
    mock_db.execute.return_value = mock_result
    
    update = TaskStatusUpdate(action=TaskAction.APPROVE, note="Approved by Manager")
    updated_task = await service.update_status(1, update)
    
    assert updated_task.state == "in_progress"
    assert "IN_PROGRESS" in updated_task.note
    
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_complete_task():
    mock_db = AsyncMock()
    service = TaskService(mock_db)
    
    mock_task = Task(id=1, state="in_progress")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_task
    mock_db.execute.return_value = mock_result
    
    update = TaskStatusUpdate(action=TaskAction.COMPLETE)
    updated_task = await service.update_status(1, update)
    
    assert updated_task.state == "completed"
