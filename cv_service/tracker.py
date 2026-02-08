"""ByteTrack multi-object tracker with UUID generation."""
import uuid
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import numpy as np
import structlog

logger = structlog.get_logger()


class Track:
    """Individual track with UUID and state."""
    
    def __init__(self, track_id: int, bbox: Tuple[int, int, int, int]):
        """
        Initialize track.
        
        Args:
            track_id: Numeric track ID from tracker
            bbox: Initial bounding box
        """
        self.track_id = track_id
        self.customer_id = uuid.uuid4()  # Generate UUID v4
        self.bbox = bbox
        self.enter_time = datetime.utcnow()
        self.exit_time: Optional[datetime] = None
        self.last_seen = datetime.utcnow()
        self.crossed_roi = False
        self.inside_roi = False
        self.history: List[Tuple[int, int]] = []  # Center point history
        
    def update(self, bbox: Tuple[int, int, int, int]):
        """Update track with new bounding box."""
        self.bbox = bbox
        self.last_seen = datetime.utcnow()
        
        # Update history
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        self.history.append((cx, cy))
        
        # Keep only last 30 positions
        if len(self.history) > 30:
            self.history.pop(0)


class ByteTracker:
    """
    ByteTrack-based multi-object tracker using Ultralytics implementation.
    Generates unique UUID v4 for each track.
    """
    
    def __init__(self, max_age: int = 30, min_hits: int = 3):
        """
        Initialize ByteTrack tracker.
        
        Args:
            max_age: Maximum frames to keep track alive without detection
            min_hits: Minimum hits before track is confirmed
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracks: Dict[int, Track] = {}
        self.next_track_id = 1
        
        logger.info("ByteTracker initialized", max_age=max_age, min_hits=min_hits)
    
    def update(self, detections: List[Tuple[int, int, int, int, float]]) -> Dict[int, Track]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of (x1, y1, x2, y2, confidence)
            
        Returns:
            Dictionary of active tracks {track_id: Track}
        """
        # Simple tracking implementation (can be replaced with actual ByteTrack)
        # For production, use Ultralytics' built-in tracker
        
        if not detections:
            # Age out tracks
            self._age_tracks()
            return self.tracks
        
        # Match detections to existing tracks (simple IoU matching)
        matched_tracks = set()
        
        for det in detections:
            bbox = det[:4]
            best_match = None
            best_iou = 0.3  # Minimum IoU threshold
            
            # Find best matching track
            for track_id, track in self.tracks.items():
                iou = self._calculate_iou(bbox, track.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_match = track_id
            
            if best_match is not None:
                # Update existing track
                self.tracks[best_match].update(bbox)
                matched_tracks.add(best_match)
            else:
                # Create new track
                new_track = Track(self.next_track_id, bbox)
                self.tracks[self.next_track_id] = new_track
                matched_tracks.add(self.next_track_id)
                self.next_track_id += 1
                
                logger.info(
                    "New track created",
                    track_id=new_track.track_id,
                    customer_id=str(new_track.customer_id)
                )
        
        # Age out unmatched tracks
        self._age_tracks(matched_tracks)
        
        return self.tracks
    
    def _calculate_iou(self, bbox1: Tuple[int, int, int, int], 
                       bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union between two bounding boxes."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _age_tracks(self, matched_tracks: set = None):
        """Remove old tracks that haven't been seen recently."""
        if matched_tracks is None:
            matched_tracks = set()
        
        current_time = datetime.utcnow()
        tracks_to_remove = []
        
        for track_id, track in self.tracks.items():
            if track_id not in matched_tracks:
                age = (current_time - track.last_seen).total_seconds()
                if age > self.max_age:
                    tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            logger.info("Track aged out", track_id=track_id)
            del self.tracks[track_id]
    
    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        """Get track by ID."""
        return self.tracks.get(track_id)
