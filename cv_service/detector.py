"""YOLOv8 person detection module."""
from ultralytics import YOLO
import numpy as np
from typing import List, Tuple
import structlog
import os

# Disable PyTorch 2.6 weights_only restriction for Ultralytics models
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

logger = structlog.get_logger()


class PersonDetector:
    """YOLOv8-based person detector."""
    
    # COCO dataset person class ID
    PERSON_CLASS_ID = 0
    
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.5):
        """
        Initialize YOLOv8 detector.
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        
        logger.info("Loading YOLO model", model_path=model_path)
        self.model = YOLO(model_path)
        logger.info("YOLO model loaded successfully")
    
    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect persons in a frame.
        
        Args:
            frame: Input image frame (BGR format)
            
        Returns:
            List of detections as (x1, y1, x2, y2, confidence)
        """
        # Run inference
        results = self.model(frame, verbose=False)
        
        detections = []
        
        # Process results
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                # Get class ID
                class_id = int(box.cls[0])
                
                # Filter for person class only
                if class_id != self.PERSON_CLASS_ID:
                    continue
                
                # Get confidence
                confidence = float(box.conf[0])
                
                # Filter by confidence threshold
                if confidence < self.confidence_threshold:
                    continue
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                detections.append((
                    int(x1), int(y1), int(x2), int(y2), confidence
                ))
        
        return detections
    
    def get_center(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        Get center point of bounding box.
        
        Args:
            bbox: Bounding box as (x1, y1, x2, y2)
            
        Returns:
            Center point as (cx, cy)
        """
        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return cx, cy
