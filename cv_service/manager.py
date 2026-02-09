"""CV Stream Manager for handling multiple branch streams."""
import threading
import json
import os
import signal
import sys
import structlog
from typing import List, Dict

from cv_service.stream_processor import StreamProcessor
from cv_service.config import cv_config

logger = structlog.get_logger()

class CVStreamManager:
    """Manages multiple CV stream processors in separate threads."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize stream manager.
        
        Args:
            config_path: Path to JSON config for multi-stream setup
        """
        self.processors: List[StreamProcessor] = []
        self.threads: List[threading.Thread] = []
        self.running = False
        self.config_path = config_path or cv_config.streams_config_path
        
        self._load_config()
        
    def _load_config(self):
        """Load stream configurations."""
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    streams = config_data.get("streams", [])
                    for stream in streams:
                        processor = StreamProcessor(
                            branch_id=stream.get("branch_id"),
                            video_source=stream.get("video_source"),
                            roi_coordinates=stream.get("roi_coordinates"),
                            rois=stream.get("rois"),
                            camera_id=stream.get("camera_id")
                        )
                        self.processors.append(processor)
                logger.info("Loaded multi-stream config", count=len(self.processors))
            except Exception as e:
                logger.error("Failed to load stream config", error=str(e))
        
        # Always add the default one from env if not already present or if no config
        default_branch_id = cv_config.branch_id
        if not any(p.branch_id == default_branch_id for p in self.processors):
            logger.info("Adding default stream from environment")
            self.processors.append(StreamProcessor())

    def start(self):
        """Start all processors in threads."""
        self.running = True
        logger.info("Starting CV Stream Manager", processor_count=len(self.processors))
        
        for processor in self.processors:
            thread = threading.Thread(
                target=processor.run,
                name=f"Processor-{processor.branch_id}",
                daemon=True
            )
            self.threads.append(thread)
            thread.start()
            logger.info("Started processor thread", branch_id=processor.branch_id)

    def wait(self):
        """Wait for all threads (or keep main alive)."""
        try:
            while self.running:
                # Check thread health
                for i, thread in enumerate(self.threads):
                    if not thread.is_alive():
                        logger.warning("Thread died", thread_name=thread.name)
                        # Optional: restart thread or remove from list
                
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop all processors."""
        logger.info("Stopping CV Stream Manager")
        self.running = False
        # In a real scenario, we'd signal processors to stop gracefully
        # Since processors are daemon threads, they will exit with main
        sys.exit(0)

def main():
    """Entry point for manager."""
    manager = CVStreamManager()
    manager.start()
    manager.wait()

if __name__ == "__main__":
    main()
