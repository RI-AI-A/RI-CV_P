"""ROI definitions and validation utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from shapely.geometry import LineString, Point, Polygon


PointTuple = Tuple[float, float]


class ROIConfigError(ValueError):
    """Raised when ROI configuration is invalid."""


@dataclass
class ROIState:
    """Per-track ROI state."""
    inside: bool = False
    entered_sent: bool = False
    exited_sent: bool = False
    roi_enter_time: Optional[datetime] = None


@dataclass
class ROIBase:
    """Base ROI class."""
    roi_id: str
    roi_type: str

    def validate(self) -> None:
        """Validate ROI definition."""
        raise NotImplementedError

    def is_inside(self, point: PointTuple) -> bool:
        """Check if a point is inside the ROI."""
        raise NotImplementedError

    def crossed(self, prev_point: Optional[PointTuple], curr_point: PointTuple) -> bool:
        """Check if a line is crossed between two points."""
        return False


@dataclass
class PolygonROI(ROIBase):
    """Polygon ROI with Shapely."""
    points: List[PointTuple] = field(default_factory=list)
    _polygon: Polygon = field(init=False)

    def __post_init__(self) -> None:
        self._polygon = Polygon(self.points)

    def validate(self) -> None:
        if len(self.points) < 3:
            raise ROIConfigError("Polygon ROI requires at least 3 points.")
        if not self._polygon.is_valid:
            raise ROIConfigError("Polygon ROI is not a valid polygon.")

    def is_inside(self, point: PointTuple) -> bool:
        return Point(point).within(self._polygon)


@dataclass
class LineROI(ROIBase):
    """Line ROI for crossing detection."""
    points: List[PointTuple] = field(default_factory=list)
    _line: LineString = field(init=False)

    def __post_init__(self) -> None:
        self._line = LineString(self.points)

    def validate(self) -> None:
        if len(self.points) != 2:
            raise ROIConfigError("Line ROI requires exactly 2 points.")

    def is_inside(self, point: PointTuple) -> bool:
        return False

    def crossed(self, prev_point: Optional[PointTuple], curr_point: PointTuple) -> bool:
        if prev_point is None:
            return False
        segment = LineString([prev_point, curr_point])
        return segment.crosses(self._line)


def build_rois(roi_configs: Iterable[Dict]) -> List[ROIBase]:
    """Build ROI objects from configuration."""
    rois: List[ROIBase] = []
    for index, roi in enumerate(roi_configs):
        roi_type = roi.get("type")
        points = roi.get("points", [])
        roi_id = roi.get("id") or f"roi_{index + 1}"
        if roi_type == "polygon":
            roi_obj = PolygonROI(roi_id=roi_id, roi_type=roi_type, points=points)
        elif roi_type == "line":
            roi_obj = LineROI(roi_id=roi_id, roi_type=roi_type, points=points)
        else:
            raise ROIConfigError(f"Unsupported ROI type: {roi_type}")
        roi_obj.validate()
        rois.append(roi_obj)
    if not rois:
        raise ROIConfigError("At least one ROI must be configured.")
    return rois
