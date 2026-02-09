"""Stream processor with ROI-based enter/exit detection."""
import cv2
import json
import uuid
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import structlog
import sys

from cv_service.config import cv_config
from cv_service.detector import PersonDetector
from cv_service.event_builder import CVEventBuilder
from cv_service.client import CVAPIClient
from schemas.cv_event import ActionType
from cv_service.roi import ROIBase, ROIConfigError, ROIState, build_rois

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@dataclass
class TrackState:
    """Track state with ROI tracking."""
    track_id: int
    first_seen_time: datetime
    last_seen_time: datetime
    customer_id: uuid.UUID
    last_center: Optional[Tuple[int, int]] = None
    confidence_sum: float = 0.0
    confidence_count: int = 0
    rois: Dict[str, ROIState] = field(default_factory=dict)

    @property
    def confidence_avg(self) -> Optional[float]:
        if self.confidence_count == 0:
            return None
        return self.confidence_sum / self.confidence_count


class StreamProcessor:
    """Main CV stream processor with ROI-based tracking."""
    
    def __init__(
        self, 
        branch_id: Optional[str] = None, 
        video_source: Optional[str] = None,
        roi_coordinates: Optional[str] = None,
        rois: Optional[List[Dict]] = None,
        camera_id: Optional[str] = None
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
        self.api_client = CVAPIClient(self.config.api_base_url)
        self.camera_id = camera_id or self.config.camera_id
        
        # ROI configuration
        self.rois = self._load_rois(rois)
        
        # Track state management
        self.track_states: Dict[int, TrackState] = {}

        # Event batching
        self.event_buffer: List[dict] = []
        self.last_flush_time = datetime.utcnow()
        
        logger.info(
            "Stream processor initialized",
            branch_id=self.branch_id,
            video_source=self.video_source,
            roi_count=len(self.rois)
        )
    
    def _parse_roi(self, roi_str: str) -> List[Dict]:
        """Parse legacy ROI coordinates into a polygon ROI config."""
        coords = [int(x.strip()) for x in roi_str.split(",")]
        if len(coords) != 4:
            raise ROIConfigError("ROI coordinates must be in format: x1,y1,x2,y2")
        x1, y1, x2, y2 = coords
        return [{
            "type": "polygon",
            "points": [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        }]

    def _load_rois(self, rois: Optional[List[Dict]]) -> List[ROIBase]:
        """Load and validate ROI definitions."""
        if rois:
            return build_rois(rois)
        if self.config.roi_config_json:
            try:
                roi_configs = json.loads(self.config.roi_config_json)
            except json.JSONDecodeError as exc:
                raise ROIConfigError("Invalid CV_ROI_CONFIG_JSON payload.") from exc
            return build_rois(roi_configs)
        roi_configs = self._parse_roi(self.roi_coordinates)
        return build_rois(roi_configs)
    
    def get_track_center(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Get center point of bounding box."""
        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return cx, cy

    def _get_track_state(self, track_id: int, frame_time: datetime) -> TrackState:
        """Get or create track state."""
        if track_id not in self.track_states:
            self.track_states[track_id] = TrackState(
                track_id=track_id,
                first_seen_time=frame_time,
                last_seen_time=frame_time,
                customer_id=uuid.uuid4()
            )
        return self.track_states[track_id]

    def _buffer_event(self, event_data: dict) -> None:
        """Buffer an event for batching."""
        self.event_buffer.append(event_data)

    def _flush_events(self) -> None:
        """Flush buffered events in a batch with fallback."""
        if not self.event_buffer:
            return
        events = self.event_buffer
        self.event_buffer = []
        try:
            success = self.api_client.post_events_batch_sync(events)
            if not success:
                for event in events:
                    self.api_client.post_event_sync(event)
        except Exception as exc:
            logger.error("Failed to flush events", error=str(exc))

    def _maybe_flush_events(self, frame_time: datetime) -> None:
        """Flush events based on batch size or interval."""
        if len(self.event_buffer) >= self.config.batch_max_size:
            self._flush_events()
            self.last_flush_time = frame_time
            return
        if (frame_time - self.last_flush_time).total_seconds() >= self.config.batch_interval_seconds:
            self._flush_events()
            self.last_flush_time = frame_time

    def _emit_event(
        self,
        track_id: int,
        action_type: ActionType,
        roi_id: str,
        enter_time: datetime,
        exit_time: Optional[datetime],
        frame_time: datetime,
        confidence_avg: Optional[float]
    ) -> None:
        """Build and buffer a CV event."""
        event_data = CVEventBuilder.build_event(
            customer_id=self.track_states[track_id].customer_id,
            branch_id=self.branch_id,
            enter_time=enter_time,
            exit_time=exit_time,
            action_type=action_type,
            camera_id=self.camera_id,
            roi_id=roi_id,
            track_id=track_id,
            dwell_time_seconds=(exit_time - enter_time).total_seconds() if exit_time else None,
            confidence_avg=confidence_avg,
            frame_time=frame_time
        )
        self._buffer_event(event_data)

    def process_roi_events(
        self,
        track_id: int,
        center: Tuple[int, int],
        frame_time: datetime
    ) -> None:
        """Process ROI crossings and emit events."""
        track_state = self._get_track_state(track_id, frame_time)
        for roi in self.rois:
            roi_state = track_state.rois.setdefault(roi.roi_id, ROIState())
            if roi.roi_type == "line":
                crossed = roi.crossed(track_state.last_center, center)
                if crossed and not roi_state.entered_sent:
                    roi_state.entered_sent = True
                    roi_state.roi_enter_time = frame_time
                    self._emit_event(
                        track_id=track_id,
                        action_type=ActionType.ENTERED,
                        roi_id=roi.roi_id,
                        enter_time=frame_time,
                        exit_time=None,
                        frame_time=frame_time,
                        confidence_avg=track_state.confidence_avg
                    )
                continue

            inside = roi.is_inside(center)
            if not roi_state.inside and inside:
                roi_state.inside = True
                roi_state.roi_enter_time = frame_time
                if not roi_state.entered_sent:
                    roi_state.entered_sent = True
                    self._emit_event(
                        track_id=track_id,
                        action_type=ActionType.ENTERED,
                        roi_id=roi.roi_id,
                        enter_time=frame_time,
                        exit_time=None,
                        frame_time=frame_time,
                        confidence_avg=track_state.confidence_avg
                    )
            elif roi_state.inside and not inside:
                roi_state.inside = False
                if not roi_state.exited_sent and roi_state.roi_enter_time:
                    roi_state.exited_sent = True
                    self._emit_event(
                        track_id=track_id,
                        action_type=ActionType.ENTERED,
                        roi_id=roi.roi_id,
                        enter_time=roi_state.roi_enter_time,
                        exit_time=frame_time,
                        frame_time=frame_time,
                        confidence_avg=track_state.confidence_avg
                    )
    
    def draw_visualization(self, frame: np.ndarray, tracks: Dict[int, TrackState], detections: list) -> np.ndarray:
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
        for roi in self.rois:
            if roi.roi_type == "polygon":
                points = np.array(roi.points, dtype=np.int32)
                cv2.fillPoly(overlay, [points], (0, 255, 0))
                cv2.addWeighted(overlay, 0.1, vis_frame, 0.9, 0, vis_frame)
                cv2.polylines(vis_frame, [points], True, (0, 255, 0), 2)
            elif roi.roi_type == "line":
                (x1, y1), (x2, y2) = roi.points
                cv2.line(vis_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
        
        # Create detection confidence map for lookup
        detection_conf = {}
        for det in detections:
            x1_d, y1_d, x2_d, y2_d, conf = det
            center_x = int((x1_d + x2_d) / 2)
            center_y = int((y1_d + y2_d) / 2)
            detection_conf[(center_x, center_y)] = conf
        
        # Draw tracks
        for track_id, track in tracks.items():
            bbox = track.last_center
            if bbox is None:
                continue
            center = bbox
            state = self.track_states.get(track_id)
            inside = False
            if state:
                inside = any(roi_state.inside for roi_state in state.rois.values())
            action_type = ActionType.ENTERED if inside else "tracking"
            
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
            cv2.circle(vis_frame, center, 5, color, -1)
            
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
            customer_id_short = str(track_id)
            
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
        cv2.putText(vis_frame, f"Camera: {self.camera_id}", (10, 95),
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
        heartbeat_time = datetime.utcnow()

        while True:
            cap = cv2.VideoCapture(self.video_source)

            if not cap.isOpened():
                logger.error("Failed to open video source", source=self.video_source)
                import time
                time.sleep(self.config.reconnect_delay_seconds)
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
                    frame_time = datetime.utcnow()
                    last_frame_time = frame_time

                    results = self.detector.track(frame)
                    detections = []
                    track_centers: Dict[int, Tuple[int, int]] = {}

                    for result in results:
                        boxes = result.boxes
                        if boxes is None:
                            continue
                        for box in boxes:
                            if box.id is None:
                                continue
                            class_id = int(box.cls[0])
                            if class_id != self.detector.PERSON_CLASS_ID:
                                continue
                            confidence = float(box.conf[0])
                            if confidence < self.config.yolo_confidence_threshold:
                                continue
                            track_id = int(box.id[0])
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            detections.append((int(x1), int(y1), int(x2), int(y2), confidence))
                            center = self.get_track_center((int(x1), int(y1), int(x2), int(y2)))
                            track_centers[track_id] = center

                            track_state = self._get_track_state(track_id, frame_time)
                            track_state.last_seen_time = frame_time
                            track_state.last_center = center
                            track_state.confidence_sum += confidence
                            track_state.confidence_count += 1

                    for track_id, center in track_centers.items():
                        self.process_roi_events(track_id, center, frame_time)

                    self._maybe_flush_events(frame_time)

                    if self.config.visualize:
                        vis_frame = self.draw_visualization(frame, self.track_states, detections)
                        cv2.imshow(f"Retail Intelligence - {self.branch_id}", vis_frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            logger.info("User requested quit")
                            cap.release()
                            cv2.destroyAllWindows()
                            return
                        if key == ord('p'):
                            logger.info("Paused - press any key to continue")
                            cv2.waitKey(0)

                    if frame_count % 100 == 0:
                        logger.info(
                            "Processing progress",
                            branch_id=self.branch_id,
                            frame_count=frame_count,
                            active_tracks=len(track_centers)
                        )

                    if (frame_time - last_frame_time).total_seconds() > 10:
                        logger.warning("Stream frozen - reconnecting", branch_id=self.branch_id)
                        break

                    if (frame_time - heartbeat_time).total_seconds() >= self.config.heartbeat_interval_seconds:
                        logger.info(
                            "Stream heartbeat",
                            branch_id=self.branch_id,
                            frame_count=frame_count,
                            active_tracks=len(track_centers)
                        )
                        heartbeat_time = frame_time

            except Exception as e:
                logger.error("Error in processing loop", branch_id=self.branch_id, error=str(e))

            finally:
                cap.release()
                if self.config.visualize:
                    cv2.destroyAllWindows()
                self._flush_events()
                logger.info("Stream released", branch_id=self.branch_id)
                import time
                time.sleep(self.config.reconnect_delay_seconds)


if __name__ == "__main__":
    processor = StreamProcessor()
    processor.run()
