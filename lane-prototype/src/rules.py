"""
Lane violation detection rules.
Checks if non-truck/bus vehicles enter designated truck/bus lanes.
Supports both polygon and rectangle lane definitions.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional


class LaneViolationChecker:
    """Checks for lane violations based on vehicle position and class."""
    
    def __init__(self, config: dict):
        """
        Initialize violation checker.
        
        Args:
            config: Site configuration dictionary
        """
        self.config = config
        
        # Lane definition - supports both polygon (new) and rectangle (old)
        self.lane_polygon = None
        self.lane_rect = None
        
        # Prefer polygon format if available
        if 'truck_bus_lane_polygon' in config and config['truck_bus_lane_polygon']:
            self.lane_polygon = np.array(config['truck_bus_lane_polygon'], dtype=np.int32)
        # Fall back to rectangle format
        elif 'truck_bus_lane_rect' in config:
            lane_rect = config['truck_bus_lane_rect']
            self.lane_rect = (
                lane_rect.get('x', 0),
                lane_rect.get('y', 0),
                lane_rect.get('w', 0),
                lane_rect.get('h', 0)
            )
            # Convert rectangle to polygon for uniform handling
            x, y, w, h = self.lane_rect
            self.lane_polygon = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.int32)
        
        # Violation rules
        violation_config = config.get('violation', {})
        self.dwell_frames = violation_config.get('dwell_frames', 10)
        self.classes_truck_ok = set(violation_config.get('classes_truck_ok', ['truck', 'bus']))
        
        # Track dwell counters for video mode
        self.track_dwell_counters: Dict[int, int] = {}
        self.track_violations: Dict[int, bool] = {}
    
    def point_in_lane(self, px: float, py: float) -> bool:
        """
        Check if a point is inside the lane polygon.
        
        Args:
            px: Point x coordinate
            py: Point y coordinate
            
        Returns:
            True if point is inside lane polygon
        """
        if self.lane_polygon is None:
            return False
        
        # Use OpenCV's pointPolygonTest for accurate polygon containment
        # Returns positive if inside, negative if outside, 0 if on edge
        result = cv2.pointPolygonTest(self.lane_polygon, (float(px), float(py)), False)
        return result >= 0
    
    # Keep old method name for backward compatibility
    def point_in_rect(self, px: float, py: float) -> bool:
        """Deprecated: Use point_in_lane() instead."""
        return self.point_in_lane(px, py)
    
    def check_instant_violation(self, centroid: Tuple[float, float], 
                                class_name: str) -> bool:
        """
        Check for instant violation (for image mode).
        
        Args:
            centroid: (cx, cy) vehicle centroid
            class_name: Vehicle class name
            
        Returns:
            True if violation detected
        """
        cx, cy = centroid
        
        # Check if vehicle is in lane and not allowed
        if self.point_in_lane(cx, cy):
            if class_name not in self.classes_truck_ok:
                return True
        
        return False
    
    def check_track_violation(self, track_id: int, centroid: Tuple[float, float],
                             class_name: str) -> Tuple[bool, int]:
        """
        Check for violation with dwell time (for video mode).
        
        Args:
            track_id: Unique track identifier
            centroid: (cx, cy) vehicle centroid
            class_name: Vehicle class name
            
        Returns:
            (is_violation, dwell_count) tuple
        """
        cx, cy = centroid
        
        # Initialize counters if new track
        if track_id not in self.track_dwell_counters:
            self.track_dwell_counters[track_id] = 0
            self.track_violations[track_id] = False
        
        # Check if vehicle is in lane and not allowed
        in_lane = self.point_in_lane(cx, cy)
        is_allowed = class_name in self.classes_truck_ok
        
        if in_lane and not is_allowed:
            # Increment dwell counter
            self.track_dwell_counters[track_id] += 1
            
            # Check if violation threshold reached
            if self.track_dwell_counters[track_id] >= self.dwell_frames:
                if not self.track_violations[track_id]:
                    # First time violation triggered
                    self.track_violations[track_id] = True
                return True, self.track_dwell_counters[track_id]
        else:
            # Reset counter if vehicle leaves lane
            self.track_dwell_counters[track_id] = 0
        
        return self.track_violations[track_id], self.track_dwell_counters[track_id]
    
    def reset_track(self, track_id: int):
        """Reset tracking data for a specific track."""
        if track_id in self.track_dwell_counters:
            del self.track_dwell_counters[track_id]
        if track_id in self.track_violations:
            del self.track_violations[track_id]
    
    def get_lane_polygon(self) -> Optional[np.ndarray]:
        """Get lane polygon points."""
        return self.lane_polygon
    
    def get_lane_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Get lane rectangle coordinates (for backward compatibility)."""
        return self.lane_rect

