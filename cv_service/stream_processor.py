"""Stream processor with ROI-based enter/exit detection."""
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional
import structlog
import sys

from cv_service.config import cv_config
from cv_service.detector import PersonDetector
from cv_service.tracker import ByteTracker, Track
from cv_service.event_builder import CVEventBuilder
from cv_service.client import CVAPIClient
from schemas.cv_event import ActionType

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


class StreamProcessor:
    """Main CV stream processor with ROI-based tracking."""
    
    def __init__(
        self, 
        branch_id: Optional[str] = None, 
        video_source: Optional[str] = None,
        roi_coordinates: Optional[str] = None
    ):
        """
        Initialize stream processor.
        
        Args:
            branch_id: ID of the branch
            video_source: RTSP URL or file path
            roi_coordinates: ROI coordinates string "x1,y1,x2,y2"
        """
        self.config = cv_config
        self.branch_id = branch_id or self.config.branch_id
        self.video_source = video_source or self.config.video_source
        self.roi_coordinates = roi_coordinates or self.config.roi_coordinates
        
        self.detector = PersonDetector(
            model_path=self.config.yolo_model_path,
            confidence_threshold=self.config.yolo_confidence_threshold
        )
        self.tracker = ByteTracker(
            max_age=self.config.tracker_max_age,
            min_hits=self.config.tracker_min_hits
        )
        self.api_client = CVAPIClient(self.config.api_base_url)
        
        # ROI configuration
        self.roi_box = self._parse_roi(self.roi_coordinates)
        
        # Track state management
        self.track_states: Dict[int, dict] = {}
        
        logger.info(
            "Stream processor initialized",
            branch_id=self.branch_id,
            video_source=self.video_source,
            roi_box=self.roi_box
        )
    
    def _parse_roi(self, roi_str: str) -> Tuple[int, int, int, int]:
        """Parse ROI coordinates into tuple."""
        coords = [int(x.strip()) for x in roi_str.split(",")]
        if len(coords) != 4:
            raise ValueError("ROI coordinates must be in format: x1,y1,x2,y2")
        return tuple(coords)
    
    def is_inside_roi(self, point: Tuple[int, int]) -> bool:
        """
        Check if a point is inside the ROI.
        
        Args:
            point: (x, y) coordinates
            
        Returns:
            True if inside ROI, False otherwise
        """
        x, y = point
        x1, y1, x2, y2 = self.roi_box
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def get_track_center(self, track: Track) -> Tuple[int, int]:
        """Get center point of track's bounding box."""
        x1, y1, x2, y2 = track.bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return cx, cy
    
    def process_track_roi_crossing(self, track: Track, track_id: int):
        """
        Process ROI crossing for a track and determine action type.
        
        Args:
            track: Track object
            track_id: Track ID
        """
        center = self.get_track_center(track)
        inside_roi = self.is_inside_roi(center)
        
        # Initialize track state if new
        if track_id not in self.track_states:
            self.track_states[track_id] = {
                "was_inside_roi": inside_roi,
                "crossed_roi": False,
                "action_type": None,
                "event_sent": False
            }
            return
        
        state = self.track_states[track_id]
        was_inside = state["was_inside_roi"]
        
        # Detect ROI crossing
        if was_inside != inside_roi:
            state["crossed_roi"] = True
            
            # Determine action type
            if inside_roi:
                # Entered ROI from outside
                state["action_type"] = ActionType.ENTERED
                logger.info(
                    "Track entered ROI",
                    track_id=track_id,
                    customer_id=str(track.customer_id)
                )
            else:
                # Exited ROI (was inside, now outside)
                # If previously entered, this is an exit
                # If never entered, this is a pass
                if state.get("action_type") == ActionType.ENTERED:
                    # Track is exiting after entering
                    track.exit_time = datetime.utcnow()
                    self.send_event(track, ActionType.ENTERED)
                    state["event_sent"] = True
                else:
                    # Track passed by without entering
                    state["action_type"] = ActionType.PASSED
                    track.exit_time = datetime.utcnow()
                    self.send_event(track, ActionType.PASSED)
                    state["event_sent"] = True
                
                logger.info(
                    "Track exited ROI",
                    track_id=track_id,
                    customer_id=str(track.customer_id),
                    action_type=state["action_type"]
                )
        
        # Update state
        state["was_inside_roi"] = inside_roi
    
    def send_event(self, track: Track, action_type: ActionType):
        """
        Send CV event to API.
        
        Args:
            track: Track object
            action_type: Action type (passed or entered)
        """
        event_data = CVEventBuilder.build_event(
            customer_id=track.customer_id,
            branch_id=self.branch_id,
            enter_time=track.enter_time,
            exit_time=track.exit_time,
            action_type=action_type
        )
        
        try:
            self.api_client.post_event_sync(event_data)
        except Exception as e:
            logger.error("Failed to send event", error=str(e))
    
    def draw_visualization(self, frame: np.ndarray, tracks: Dict[int, Track], detections: list) -> np.ndarray:
        """
        Draw enhanced visualization on frame.
        
        Args:
            frame: Input frame
            tracks: Active tracks
            detections: Raw detections with confidence scores
            
        Returns:
            Frame with visualization
        """
        # Create a copy to draw on
        vis_frame = frame.copy()
        
        # Draw semi-transparent overlay for ROI
        overlay = vis_frame.copy()
        x1, y1, x2, y2 = self.roi_box
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
        cv2.addWeighted(overlay, 0.1, vis_frame, 0.9, 0, vis_frame)
        
        # Draw ROI border
        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
        
        # Add ROI label with background
        roi_label = "Region of Interest"
        (label_w, label_h), _ = cv2.getTextSize(roi_label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(vis_frame, (x1, y1 - label_h - 20), (x1 + label_w + 10, y1 - 5), (0, 255, 0), -1)
        cv2.putText(vis_frame, roi_label, (x1 + 5, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # Create detection confidence map for lookup
        detection_conf = {}
        for det in detections:
            x1_d, y1_d, x2_d, y2_d, conf = det
            center_x = int((x1_d + x2_d) / 2)
            center_y = int((y1_d + y2_d) / 2)
            detection_conf[(center_x, center_y)] = conf
        
        # Draw tracks
        for track_id, track in tracks.items():
            bbox = track.bbox
            center = self.get_track_center(track)
            
            # Get track state
            state = self.track_states.get(track_id, {})
            inside = self.is_inside_roi(center)
            action_type = state.get("action_type", "tracking")
            
            # Color coding:
            # Green (inside ROI) / Blue (outside ROI) / Red (passed)
            if action_type == ActionType.ENTERED:
                color = (0, 255, 0)  # Green - entered
                status = "ENTERED"
            elif action_type == ActionType.PASSED:
                color = (0, 0, 255)  # Red - passed
                status = "PASSED"
            elif inside:
                color = (0, 255, 255)  # Yellow - inside ROI
                status = "IN ROI"
            else:
                color = (255, 0, 0)  # Blue - tracking outside
                status = "TRACKING"
            
            # Draw bounding box with thickness based on status
            thickness = 3 if inside else 2
            cv2.rectangle(vis_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness)
            
            # Find closest detection confidence
            conf = 0.0
            min_dist = float('inf')
            for (det_x, det_y), det_conf in detection_conf.items():
                dist = ((center[0] - det_x)**2 + (center[1] - det_y)**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    conf = det_conf
            
            # Prepare labels
            track_label = f"ID:{track_id}"
            conf_label = f"Conf:{conf:.2f}"
            status_label = f"{status}"
            customer_id_short = str(track.customer_id)[:8]
            
            # Draw labels with background
            y_offset = bbox[1] - 10
            labels = [track_label, conf_label, status_label, customer_id_short]
            
            for i, label in enumerate(labels):
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                
                # Background rectangle
                bg_y1 = y_offset - text_h - 5
                bg_y2 = y_offset
                cv2.rectangle(vis_frame, (bbox[0], bg_y1), (bbox[0] + text_w + 5, bg_y2), color, -1)
                
                # Text
                cv2.putText(vis_frame, label, (bbox[0] + 2, y_offset - 2),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                y_offset -= (text_h + 8)
            
            # Draw center point
            cv2.circle(vis_frame, center, 5, color, -1)
            cv2.circle(vis_frame, center, 7, (255, 255, 255), 1)
        
        # Add info panel at top
        info_bg_height = 100
        overlay_info = vis_frame.copy()
        cv2.rectangle(overlay_info, (0, 0), (vis_frame.shape[1], info_bg_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay_info, 0.7, vis_frame, 0.3, 0, vis_frame)
        
        # Add text info
        cv2.putText(vis_frame, "Retail Intelligence - Computer Vision System", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(vis_frame, f"Active Tracks: {len(tracks)}", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(vis_frame, f"Branch: {self.branch_id}", (10, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Add legend
        legend_x = vis_frame.shape[1] - 250
        cv2.putText(vis_frame, "Legend:", (legend_x, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.rectangle(vis_frame, (legend_x, 35), (legend_x + 20, 50), (0, 255, 0), -1)
        cv2.putText(vis_frame, "Entered", (legend_x + 25, 48),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.rectangle(vis_frame, (legend_x, 55), (legend_x + 20, 70), (0, 0, 255), -1)
        cv2.putText(vis_frame, "Passed", (legend_x + 25, 68),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.rectangle(vis_frame, (legend_x, 75), (legend_x + 20, 90), (0, 255, 255), -1)
        cv2.putText(vis_frame, "In ROI", (legend_x + 25, 88),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return vis_frame
    
    def run(self):
        """Main processing loop with reconnection logic."""
        logger.info("Starting stream processor", branch_id=self.branch_id)
        
        while True:
            # Open video source
            cap = cv2.VideoCapture(self.video_source)
            
            if not cap.isOpened():
                logger.error("Failed to open video source", source=self.video_source)
                import time
                time.sleep(5)  # Wait before retrying
                continue
            
            frame_count = 0
            last_frame_time = datetime.utcnow()
            
            try:
                while True:
                    ret, frame = cap.read()
                    
                    if not ret:
                        logger.warning("Stream disconnected or ended", branch_id=self.branch_id)
                        break
                    
                    frame_count += 1
                    last_frame_time = datetime.utcnow()
                    
                    # Detect persons
                    detections = self.detector.detect(frame)
                    
                    # Update tracker
                    tracks = self.tracker.update(detections)
                    
                    # Process each track for ROI crossing
                    for track_id, track in tracks.items():
                        self.process_track_roi_crossing(track, track_id)
                    
                    # Draw visualization (can be disabled for headless)
                    if self.config.log_level == "DEBUG" or True: # Keep enabled for now
                        vis_frame = self.draw_visualization(frame, tracks, detections)
                        cv2.imshow(f"Retail Intelligence - {self.branch_id}", vis_frame)
                    
                    # Press 'q' to quit, 'p' to pause
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("User requested quit")
                        cap.release()
                        cv2.destroyAllWindows()
                        return
                    elif key == ord('p'):
                        logger.info("Paused - press any key to continue")
                        cv2.waitKey(0)
                    
                    # Log progress
                    if frame_count % 100 == 0:
                        logger.info(
                            "Processing progress",
                            branch_id=self.branch_id,
                            frame_count=frame_count,
                            active_tracks=len(tracks)
                        )
                    
                    # Watchdog: if no frame for 10 seconds, reconnect
                    if (datetime.utcnow() - last_frame_time).total_seconds() > 10:
                        logger.warning("Stream frozen - reconnecting", branch_id=self.branch_id)
                        break
            
            except Exception as e:
                logger.error("Error in processing loop", branch_id=self.branch_id, error=str(e))
            
            finally:
                cap.release()
                logger.info("Stream released", branch_id=self.branch_id)
                import time
                time.sleep(2)  # Short delay before reconnecting


if __name__ == "__main__":
    processor = StreamProcessor()
    processor.run()
