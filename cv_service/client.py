"""HTTP client for posting CV events to API service."""
import httpx
import structlog
from typing import Dict, Any, List
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CVAPIClient:
    """Client for posting CV events to backend API."""
    
    def __init__(self, api_base_url: str):
        """
        Initialize API client.
        
        Args:
            api_base_url: Base URL of API service
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.events_endpoint = f"{self.api_base_url}/cv/events"
        
        logger.info("CV API Client initialized", endpoint=self.events_endpoint)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def post_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Post CV event to API with retry logic.
        
        Args:
            event_data: Event payload dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.events_endpoint,
                    json=event_data
                )
                
                if response.status_code == 200:
                    logger.info(
                        "Event posted successfully",
                        customer_id=event_data.get("customer_id"),
                        action_type=event_data.get("action_type")
                    )
                    return True
                else:
                    logger.error(
                        "Failed to post event",
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False
                    
        except Exception as e:
            logger.error("Error posting event", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def post_events_batch(self, events: List[Dict[str, Any]]) -> bool:
        """
        Post batch of CV events to API with retry logic.

        Args:
            events: List of event payload dictionaries

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.events_endpoint,
                    json=events
                )

                if response.status_code == 200:
                    logger.info("Batch events posted successfully", count=len(events))
                    return True

                logger.warning(
                    "Batch post failed, falling back to single events",
                    status_code=response.status_code,
                    response=response.text
                )
                return False
        except Exception as e:
            logger.error("Error posting batch events", error=str(e))
            raise
    
    def post_event_sync(self, event_data: Dict[str, Any]) -> bool:
        """
        Synchronous wrapper for posting events.
        
        Args:
            event_data: Event payload dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.post_event(event_data))

    def post_events_batch_sync(self, events: List[Dict[str, Any]]) -> bool:
        """
        Synchronous wrapper for posting batch events.

        Args:
            events: List of event payload dictionaries

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.post_events_batch(events))
