"""CV event builder for constructing event payloads."""
from datetime import datetime
from typing import Optional
import uuid
from schemas.cv_event import ActionType


class CVEventBuilder:
    """Builds CV event payloads matching the exact contract."""
    
    @staticmethod
    def build_event(
        customer_id: uuid.UUID,
        branch_id: str,
        enter_time: datetime,
        exit_time: Optional[datetime],
        action_type: ActionType,
        camera_id: str,
        roi_id: str,
        track_id: int,
        dwell_time_seconds: Optional[float],
        confidence_avg: Optional[float],
        frame_time: datetime
    ) -> dict:
        """
        Build CV event payload.
        
        Args:
            customer_id: Anonymized customer UUID
            branch_id: Branch identifier
            enter_time: Entry timestamp
            exit_time: Exit timestamp (optional)
            action_type: Action type (passed or entered)
            camera_id: Camera identifier
            roi_id: ROI identifier
            track_id: Stable tracker ID
            dwell_time_seconds: Dwell time in seconds for exit events
            confidence_avg: Average confidence for the track
            frame_time: Frame timestamp
            
        Returns:
            Event payload dictionary
        """
        return {
            "customer_id": str(customer_id),
            "branch_id": branch_id,
            "enter_time": enter_time.isoformat(),
            "exit_time": exit_time.isoformat() if exit_time else None,
            "action_type": action_type.value,
            "camera_id": camera_id,
            "roi_id": roi_id,
            "track_id": track_id,
            "dwell_time_seconds": dwell_time_seconds,
            "confidence_avg": confidence_avg,
            "frame_time": frame_time.isoformat()
        }
