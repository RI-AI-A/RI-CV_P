"""Stream processor with ROI-based enter/exit detection."""
import cv2
import json
import uuid
import numpy as np
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import structlog

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

        # Graceful stop support
        self._stop_event = threading.Event()

        logger.info(
            "Stream processor initialized",
            branch_id=self.branch_id,
            video_source=self.video_source,
            roi_count=len(self.rois)
        )

    def stop(self) -> None:
        logger.info("Stop requested", branch_id=self.branch_id)
        self._stop_event.set()

    def _parse_roi(self, roi_str: str) -> List[Dict]:
        coords = [int(x.strip()) for x in roi_str.split(",")]
        if len(coords) != 4:
            raise ROIConfigError("ROI coordinates must be in format: x1,y1,x2,y2")
        x1, y1, x2, y2 = coords
        return [{
            "type": "polygon",
            "points": [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        }]

    def _load_rois(self, rois: Optional[List[Dict]]) -> List[ROIBase]:
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
        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return cx, cy

    def _get_track_state(self, track_id: int, frame_time: datetime) -> TrackState:
        if track_id not in self.track_states:
            self.track_states[track_id] = TrackState(
                track_id=track_id,
                first_seen_time=frame_time,
                last_seen_time=frame_time,
                customer_id=uuid.uuid4()
            )
        return self.track_states[track_id]

    def _buffer_event(self, event_data: dict) -> None:
        self.event_buffer.append(event_data)

    def _flush_events(self) -> None:
        if not self.event_buffer:
            return

        events = self.event_buffer
        self.event_buffer = []

        try:
            # Non-blocking: Add to the internal client queue
            self.api_client.enqueue_batch(events)
        except Exception as exc:
            logger.error("Failed to enqueue batch events", error=str(exc))

    def _maybe_flush_events(self, frame_time: datetime) -> None:
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

    # ✅ FIX: accept prev_center for correct LINE crossing detection
    def process_roi_events(
        self,
        track_id: int,
        prev_center: Optional[Tuple[int, int]],
        center: Tuple[int, int],
        frame_time: datetime
    ) -> None:
        track_state = self._get_track_state(track_id, frame_time)

        for roi in self.rois:
            roi_state = track_state.rois.setdefault(roi.roi_id, ROIState())

            # LINE ROI: crossed trigger
            if roi.roi_type == "line":
                crossed = roi.crossed(prev_center, center)
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

            # POLYGON ROI: inside/outside
            inside = roi.is_inside(center)

            # Enter transition
            if (not roi_state.inside) and inside:
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

            # Exit transition
            elif roi_state.inside and (not inside):
                roi_state.inside = False

                # ✅ FIX: DO NOT use ActionType.EXITED (doesn't exist)
                # Exit is represented by exit_time filled.
                if (not roi_state.exited_sent) and roi_state.roi_enter_time:
                    roi_state.exited_sent = True
                    self._emit_event(
                        track_id=track_id,
                        action_type=ActionType.ENTERED,  # keep contract
                        roi_id=roi.roi_id,
                        enter_time=roi_state.roi_enter_time,
                        exit_time=frame_time,
                        frame_time=frame_time,
                        confidence_avg=track_state.confidence_avg
                    )

    def _cleanup_stale_tracks(self, now: datetime) -> None:
        ttl = getattr(self.config, "track_ttl_seconds", 10)
        stale_ids = []
        for track_id, state in self.track_states.items():
            if (now - state.last_seen_time).total_seconds() > ttl:
                stale_ids.append(track_id)

        for tid in stale_ids:
            del self.track_states[tid]

    def run(self):
        logger.info("Starting stream processor", branch_id=self.branch_id)

        heartbeat_time = datetime.utcnow()
        last_good_frame_time = datetime.utcnow()

        while not self._stop_event.is_set():
            cap = cv2.VideoCapture(self.video_source)

            if not cap.isOpened():
                logger.error("Failed to open video source", source=self.video_source)
                import time
                time.sleep(getattr(self.config, "reconnect_delay_seconds", 2))
                continue

            frame_count = 0

            try:
                while not self._stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Stream disconnected or ended", branch_id=self.branch_id)
                        break

                    frame_count += 1
                    frame_time = datetime.utcnow()
                    last_good_frame_time = frame_time

                    results = self.detector.track(frame)
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

                            center = self.get_track_center((int(x1), int(y1), int(x2), int(y2)))
                            track_centers[track_id] = center

                            track_state = self._get_track_state(track_id, frame_time)

                            # ✅ FIX: capture prev_center BEFORE updating last_center
                            prev_center = track_state.last_center

                            track_state.last_seen_time = frame_time
                            track_state.last_center = center
                            track_state.confidence_sum += confidence
                            track_state.confidence_count += 1

                            # ✅ process ROI using prev + curr
                            self.process_roi_events(track_id, prev_center, center, frame_time)

                    self._maybe_flush_events(frame_time)
                    self._cleanup_stale_tracks(frame_time)

                    if frame_count % 100 == 0:
                        logger.info(
                            "Processing progress",
                            branch_id=self.branch_id,
                            frame_count=frame_count,
                            active_tracks=len(track_centers)
                        )

                    freeze_seconds = getattr(self.config, "freeze_reconnect_seconds", 10)
                    if (datetime.utcnow() - last_good_frame_time).total_seconds() > freeze_seconds:
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
                self._flush_events()
                logger.info("Stream released", branch_id=self.branch_id)

                if not self._stop_event.is_set():
                    import time
                    time.sleep(getattr(self.config, "reconnect_delay_seconds", 2))

        logger.info("Stream processor stopped", branch_id=self.branch_id)


if __name__ == "__main__":
    processor = StreamProcessor()
    processor.run()
