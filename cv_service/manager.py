"""
CV Stream Manager for handling multiple branch streams.

Changes:
- Added graceful shutdown (no sys.exit in stop)
- Added signal handling (Ctrl+C / SIGTERM)
- Added optional auto-restart for dead threads
- Cleaned main entrypoint
"""

import threading
import json
import os
import signal
import sys
import time
import structlog
from typing import List, Optional

from cv_service.stream_processor import StreamProcessor
from cv_service.config import cv_config

logger = structlog.get_logger()


class CVStreamManager:
    """Manages multiple CV stream processors in separate threads."""

    def __init__(self, config_path: Optional[str] = None, auto_restart: bool = True):
        """
        Initialize stream manager.

        Args:
            config_path: Path to JSON config for multi-stream setup
            auto_restart: Restart a stream thread if it dies
        """
        self.processors: List[StreamProcessor] = []
        self.threads: List[threading.Thread] = []
        self.running = False
        self.auto_restart = auto_restart

        self.config_path = config_path or getattr(cv_config, "streams_config_path", None)

        # Used to stop the wait loop cleanly
        self._stop_event = threading.Event()

        self._load_config()

        # Register signals for clean stop
        self._register_signal_handlers()

    def _register_signal_handlers(self):
        """Register OS signals for graceful shutdown."""
        def _handler(signum, frame):
            logger.info("Shutdown signal received", signum=signum)
            self.stop()

        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
        except Exception as e:
            # On some environments, SIGTERM may not exist / not be supported
            logger.warning("Signal handling not fully supported", error=str(e))

    def _load_config(self):
        """Load stream configurations."""
        loaded_any = False

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                streams = config_data.get("streams", [])
                for stream in streams:
                    processor = StreamProcessor(
                        branch_id=stream.get("branch_id"),
                        video_source=stream.get("video_source"),
                        roi_coordinates=stream.get("roi_coordinates"),
                        rois=stream.get("rois"),
                        camera_id=stream.get("camera_id"),
                    )
                    self.processors.append(processor)

                loaded_any = len(self.processors) > 0
                logger.info("Loaded multi-stream config", count=len(self.processors), path=self.config_path)

            except Exception as e:
                logger.error("Failed to load stream config", error=str(e), path=self.config_path)

        # Always add the default one from env if not already present or if no config
        default_branch_id = getattr(cv_config, "branch_id", None)
        if not default_branch_id:
            default_branch_id = "default_branch"

        if (not loaded_any) or (not any(p.branch_id == default_branch_id for p in self.processors)):
            logger.info("Adding default stream from environment", branch_id=default_branch_id)
            self.processors.append(StreamProcessor())

    def start(self):
        """Start all processors in threads."""
        if self.running:
            logger.warning("CV Stream Manager already running")
            return

        self.running = True
        self._stop_event.clear()

        logger.info("Starting CV Stream Manager", processor_count=len(self.processors))

        self.threads = []
        for processor in self.processors:
            thread = threading.Thread(
                target=self._run_processor_safe,
                args=(processor,),
                name=f"Processor-{processor.branch_id}",
                daemon=True
            )
            self.threads.append(thread)
            thread.start()
            logger.info("Started processor thread", branch_id=processor.branch_id, thread_name=thread.name)

    def _run_processor_safe(self, processor: StreamProcessor):
        """Run a processor with exception protection."""
        try:
            processor.run()
        except Exception as e:
            logger.error("Processor crashed", branch_id=getattr(processor, "branch_id", "unknown"), error=str(e))

    def wait(self):
        """Wait for all threads (or keep main alive)."""
        try:
            while self.running and not self._stop_event.is_set():
                # Check thread health
                for i, thread in enumerate(list(self.threads)):
                    if not thread.is_alive():
                        logger.warning("Thread died", thread_name=thread.name)

                        if self.auto_restart:
                            # Find matching processor by thread name convention
                            branch_id = thread.name.replace("Processor-", "")
                            processor = next((p for p in self.processors if str(p.branch_id) == branch_id), None)

                            if processor is not None:
                                logger.info("Restarting processor thread", branch_id=branch_id)
                                new_thread = threading.Thread(
                                    target=self._run_processor_safe,
                                    args=(processor,),
                                    name=f"Processor-{branch_id}",
                                    daemon=True
                                )
                                # Replace dead thread in list
                                self.threads[i] = new_thread
                                new_thread.start()

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            self.stop()

    def stop(self):
        """Stop all processors gracefully."""
        if not self.running:
            return

        logger.info("Stopping CV Stream Manager")
        self.running = False
        self._stop_event.set()

        # Ask processors to stop if they provide a stop() method
        for p in self.processors:
            if hasattr(p, "stop") and callable(getattr(p, "stop")):
                try:
                    p.stop()
                    logger.info("Stop signal sent to processor", branch_id=getattr(p, "branch_id", "unknown"))
                except Exception as e:
                    logger.warning("Failed stopping processor", branch_id=getattr(p, "branch_id", "unknown"), error=str(e))

        # Join threads briefly
        for t in self.threads:
            try:
                t.join(timeout=3)
            except Exception:
                pass

        logger.info("CV Stream Manager stopped cleanly")


def main():
    """Entry point for manager."""
    manager = CVStreamManager()
    manager.start()
    manager.wait()


if __name__ == "__main__":
    main()
