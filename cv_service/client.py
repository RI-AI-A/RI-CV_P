"""HTTP client for posting CV events to Core Backend API service."""
import asyncio
from typing import Dict, Any, List

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CVAPIClient:
    """Client for posting CV events to backend API."""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip("/")

        # Core backend is /api/v1/*
        self.events_endpoint = f"{self.api_base_url}/api/v1/events"
        self.events_batch_endpoint = f"{self.api_base_url}/api/v1/events/batch"

        # ✅ disable batch permanently if backend doesn't support it
        self.batch_enabled = True

        logger.info(
            "CV API Client initialized",
            events_endpoint=self.events_endpoint,
            events_batch_endpoint=self.events_batch_endpoint,
        )

    def _is_success(self, status_code: int) -> bool:
        return status_code in (200, 201, 204)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def post_event(self, event_data: Dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.events_endpoint, json=event_data)

            if self._is_success(response.status_code):
                logger.info(
                    "Event posted successfully",
                    endpoint=self.events_endpoint,
                    status_code=response.status_code,
                    customer_id=event_data.get("customer_id"),
                    action_type=event_data.get("action_type"),
                    branch_id=event_data.get("branch_id"),
                    roi_id=event_data.get("roi_id"),
                )
                return True

            logger.error(
                "Failed to post event",
                endpoint=self.events_endpoint,
                status_code=response.status_code,
                response_text=response.text[:500],
            )
            return False

        except Exception as e:
            logger.error("Error posting event", endpoint=self.events_endpoint, error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def post_events_batch(self, events: List[Dict[str, Any]]) -> bool:
        """
        Batch strategy:
        - If /api/v1/events/batch exists => use it
        - Otherwise disable batch and return False (caller will fallback to single)
        """
        if not events:
            return True

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if self.batch_enabled:
                    resp1 = await client.post(self.events_batch_endpoint, json=events)

                    # ✅ backend doesn't support batch -> disable it forever
                    if resp1.status_code == 404:
                        self.batch_enabled = False
                        logger.warning(
                            "Batch endpoint not supported by Core backend; disabling batch mode",
                            endpoint=self.events_batch_endpoint,
                            status_code=resp1.status_code,
                            response_text=resp1.text[:300],
                        )
                        return False

                    if self._is_success(resp1.status_code):
                        logger.info(
                            "Batch events posted successfully (batch endpoint)",
                            endpoint=self.events_batch_endpoint,
                            status_code=resp1.status_code,
                            count=len(events),
                        )
                        return True

                    logger.warning(
                        "Batch endpoint failed (non-404), will fallback to single",
                        endpoint=self.events_batch_endpoint,
                        status_code=resp1.status_code,
                        response_text=resp1.text[:300],
                        count=len(events),
                    )
                    return False

                # If batch is disabled, tell caller to fallback
                return False

        except Exception as e:
            logger.error("Error posting batch events", error=str(e), count=len(events))
            raise

    def post_event_sync(self, event_data: Dict[str, Any]) -> bool:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                new_loop = asyncio.new_event_loop()
                try:
                    return new_loop.run_until_complete(self.post_event(event_data))
                finally:
                    new_loop.close()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.post_event(event_data))

    def post_events_batch_sync(self, events: List[Dict[str, Any]]) -> bool:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                new_loop = asyncio.new_event_loop()
                try:
                    return new_loop.run_until_complete(self.post_events_batch(events))
                finally:
                    new_loop.close()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.post_events_batch(events))
