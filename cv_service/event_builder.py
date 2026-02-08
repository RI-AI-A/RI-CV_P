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
        action_type: ActionType
    ) -> dict:
        """
        Build CV event payload.
        
        Args:
            customer_id: Anonymized customer UUID
            branch_id: Branch identifier
            enter_time: Entry timestamp
            exit_time: Exit timestamp (optional)
            action_type: Action type (passed or entered)
            
        Returns:
            Event payload dictionary
        """
        return {
            "customer_id": str(customer_id),
            "branch_id": branch_id,
            "enter_time": enter_time.isoformat(),
            "exit_time": exit_time.isoformat() if exit_time else None,
            "action_type": action_type.value
        }
