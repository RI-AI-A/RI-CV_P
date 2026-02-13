"""HTTP client for posting CV events to Core Backend API service."""
import asyncio
import queue
import threading
import time
from typing import Dict, Any, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CVAPIClient:
    """Client for posting CV events to backend API with an internal async queue."""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip("/")

        # Core backend is /cv/* based on local router configuration
        self.events_endpoint = f"{self.api_base_url}/cv/events"
        self.events_batch_endpoint = f"{self.api_base_url}/cv/events/batch"

        # ✅ disable batch permanently if backend doesn't support it
        self.batch_enabled = True
        
        # Async Queue Implementation
        self._queue = queue.Queue(maxsize=10000)
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

        logger.info(
            "CV API Client initialized",
            events_endpoint=self.events_endpoint,
            events_batch_endpoint=self.events_batch_endpoint,
        )
        
        self.start_worker()

    def start_worker(self):
        """Start the background worker thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
            
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="CVAPIClient-Worker",
            daemon=True
        )
        self._worker_thread.start()
        logger.info("CV API Client background worker started")

    def stop_worker(self):
        """Stop the background worker thread."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            logger.info("CV API Client background worker stopped")

    def enqueue_event(self, event_data: Dict[str, Any]):
        """Non-blocking: Add a single event to the queue."""
        try:
            self._queue.put_nowait(event_data)
        except queue.Full:
            logger.warning("Event queue full, dropping event", customer_id=event_data.get("customer_id"))

    def enqueue_batch(self, events: List[Dict[str, Any]]):
        """Non-blocking: Add a batch of events to the queue."""
        for event in events:
            self.enqueue_event(event)

    def _worker_loop(self):
        """Background worker loop to flush the queue."""
        # We need a separate event loop for the worker thread to run async calls
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._running:
            batch = []
            # Try to get as many items as possible (up to 100) or wait for 1
            try:
                # Wait for at least one item
                item = self._queue.get(timeout=1.0)
                batch.append(item)
                
                # Drain more items if available immediately
                while len(batch) < 100:
                    try:
                        batch.append(self._queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue

            if batch:
                try:
                    # Run the sync batch posting logic
                    # We reuse the logic but in a dedicated thread
                    success = loop.run_until_complete(self.post_events_batch(batch))
                    if not success:
                        # Fallback to single posts if batch fails
                        for event in batch:
                            loop.run_until_complete(self.post_event(event))
                except Exception as e:
                    logger.error("Worker failed to post events", error=str(e), count=len(batch))
                finally:
                    for _ in range(len(batch)):
                        self._queue.task_done()

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
        - If /cv/events/batch exists => use it
        - Otherwise disable batch and return False (caller will fallback to single)
        """
        if not events:
            return True

        if not self.batch_enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp1 = await client.post(self.events_batch_endpoint, json=events)

                # ✅ backend doesn't support batch -> disable it forever
                if resp1.status_code == 404:
                    self.batch_enabled = False
                    logger.warning(
                        "Batch endpoint not supported by Core backend; disabling batch mode",
                        endpoint=self.events_batch_endpoint,
                        status_code=resp1.status_code,
                    )
                    return False

                if self._is_success(resp1.status_code):
                    logger.info(
                        "Batch events posted successfully",
                        count=len(events),
                    )
                    return True

                logger.warning(
                    "Batch endpoint failed (non-404)",
                    status_code=resp1.status_code,
                    count=len(events),
                )
                return False

        except Exception as e:
            logger.error("Error posting batch events", error=str(e), count=len(events))
            raise

    def post_event_sync(self, event_data: Dict[str, Any]) -> bool:
        """Legacy sync method (now mostly used by worker or fallback)"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.post_event(event_data))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(self.post_event(event_data))

    def post_events_batch_sync(self, events: List[Dict[str, Any]]) -> bool:
        """Legacy sync method (now mostly used by worker or fallback)"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.post_events_batch(events))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(self.post_events_batch(events))
