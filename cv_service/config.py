"""Configuration management for CV service."""
from pydantic_settings import BaseSettings
from typing import Tuple
import os


class CVConfig(BaseSettings):
    """CV service configuration."""
    
    # Branch configuration
    branch_id: str = os.getenv("CV_BRANCH_ID", "branch_001")
    
    # Video source (RTSP URL or file path)
    video_source: str = os.getenv("CV_VIDEO_SOURCE", "rtsp://camera:554/stream")
    
    # Path to streams config JSON
    streams_config_path: str = os.getenv("CV_STREAMS_CONFIG_PATH", "streams_config.json")
    
    # ROI coordinates (x1,y1,x2,y2)
    roi_coordinates: str = os.getenv("CV_ROI_COORDINATES", "100,100,500,400")
    
    # YOLO model configuration
    yolo_model_path: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    yolo_confidence_threshold: float = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5"))
    
    # Tracker configuration
    tracker_type: str = os.getenv("TRACKER_TYPE", "bytetrack")
    tracker_max_age: int = int(os.getenv("TRACKER_MAX_AGE", "30"))
    tracker_min_hits: int = int(os.getenv("TRACKER_MIN_HITS", "3"))
    
    # API configuration
    api_base_url: str = os.getenv("API_BASE_URL", "http://api_service:8000")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def roi_box(self) -> Tuple[int, int, int, int]:
        """Parse ROI coordinates into tuple."""
        coords = [int(x.strip()) for x in self.roi_coordinates.split(",")]
        if len(coords) != 4:
            raise ValueError("ROI coordinates must be in format: x1,y1,x2,y2")
        return tuple(coords)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables


# Global config instance
cv_config = CVConfig()
