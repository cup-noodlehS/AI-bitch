"""
Overlay drawing module for visualization.
Draws bounding boxes, labels, lane rectangles, and handles live preview.
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any


class OverlayDrawer:
    """Handles all visualization and overlay drawing."""
    
    # Color scheme (BGR format for OpenCV)
    COLORS = {
        'car': (255, 100, 0),      # Blue
        'motorcycle': (0, 165, 255),  # Orange
        'bus': (0, 255, 0),        # Green
        'truck': (0, 200, 0),      # Dark green
        'default': (200, 200, 200)  # Gray
    }
    
    LANE_COLOR_NORMAL = (0, 255, 0)   # Green
    LANE_COLOR_VIOLATION = (0, 0, 255)  # Red
    
    def __init__(self, config: dict):
        """
        Initialize overlay drawer.
        
        Args:
            config: Site configuration dictionary
        """
        self.config = config
        
        overlay_config = config.get('overlay', {})
        self.draw_speed = overlay_config.get('draw_speed', True)
        self.draw_lane_rect = overlay_config.get('draw_lane_rect', True)
        self.draw_track_ids = overlay_config.get('draw_track_ids', True)
        self.show_live_preview = overlay_config.get('show_live_preview', True)
        
        self.window_name = 'Lane Violation Detection'
        self.window_created = False
    
    def draw_detection(self, frame: np.ndarray, detection: Dict[str, Any],
                      track_id: Optional[int] = None,
                      speed_kph: Optional[float] = None,
                      is_violation: bool = False) -> np.ndarray:
        """
        Draw a single detection/track on the frame.
        
        Args:
            frame: Input frame
            detection: Detection dict with 'bbox', 'class_name', 'score'
            track_id: Optional track ID (for video mode)
            speed_kph: Optional speed in km/h (for video mode)
            is_violation: Whether this is a violation
            
        Returns:
            Frame with overlay drawn
        """
        bbox = detection['bbox']
        class_name = detection['class_name']
        score = detection['score']
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Choose color
        color = self.COLORS.get(class_name, self.COLORS['default'])
        
        # Make red if violation
        if is_violation:
            color = (0, 0, 255)
        
        # Draw bounding box
        thickness = 3 if is_violation else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        
        # Build label
        label_parts = []
        
        if track_id is not None and self.draw_track_ids:
            label_parts.append(f"ID:{track_id}")
        
        label_parts.append(class_name)
        
        if speed_kph is not None and self.draw_speed:
            label_parts.append(f"{speed_kph:.1f}km/h")
        
        label = " | ".join(label_parts)
        
        # Draw label background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
        
        # Position label above box
        label_y = max(y1 - 10, label_h + 10)
        
        cv2.rectangle(frame, 
                     (x1, label_y - label_h - baseline - 5),
                     (x1 + label_w + 5, label_y + baseline),
                     color, -1)
        
        # Draw label text
        cv2.putText(frame, label, (x1 + 2, label_y - 5),
                   font, font_scale, (255, 255, 255), font_thickness)
        
        return frame
    
    def draw_lane_polygon(self, frame: np.ndarray, lane_polygon: Optional[np.ndarray],
                         has_violation: bool = False) -> np.ndarray:
        """
        Draw the truck/bus lane polygon.
        
        Args:
            frame: Input frame
            lane_polygon: Polygon points as numpy array [[x1,y1], [x2,y2], ...]
            has_violation: Whether there's currently a violation
            
        Returns:
            Frame with lane polygon drawn
        """
        if not self.draw_lane_rect or lane_polygon is None:
            return frame
        
        # Choose color based on violation status
        color = self.LANE_COLOR_VIOLATION if has_violation else self.LANE_COLOR_NORMAL
        thickness = 3 if has_violation else 2
        
        # Draw polygon outline
        cv2.polylines(frame, [lane_polygon], isClosed=True, color=color, thickness=thickness)
        
        # Fill with semi-transparent overlay
        overlay = frame.copy()
        cv2.fillPoly(overlay, [lane_polygon], color)
        cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
        
        # Add label at centroid
        centroid_x = int(np.mean(lane_polygon[:, 0]))
        centroid_y = int(np.mean(lane_polygon[:, 1]))
        
        label = "TRUCK/BUS LANE"
        if has_violation:
            label += " - VIOLATION!"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2
        
        # Draw label with background
        (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
        label_x = centroid_x - label_w // 2
        label_y = centroid_y - label_h // 2
        
        cv2.rectangle(frame, 
                     (label_x - 5, label_y - label_h - 5),
                     (label_x + label_w + 5, label_y + 5),
                     (0, 0, 0), -1)
        cv2.putText(frame, label, (label_x, label_y),
                   font, font_scale, color, font_thickness)
        
        return frame
    
    def draw_lane_rectangle(self, frame: np.ndarray, lane_rect: Tuple[int, int, int, int],
                           has_violation: bool = False) -> np.ndarray:
        """
        Draw the truck/bus lane rectangle (backward compatibility).
        Converts rectangle to polygon and calls draw_lane_polygon.
        
        Args:
            frame: Input frame
            lane_rect: (x, y, w, h) rectangle
            has_violation: Whether there's currently a violation
            
        Returns:
            Frame with lane rectangle drawn
        """
        if lane_rect is None:
            return frame
        
        x, y, w, h = lane_rect
        polygon = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.int32)
        return self.draw_lane_polygon(frame, polygon, has_violation)
    
    def draw_frame_info(self, frame: np.ndarray, frame_num: int,
                       fps: Optional[float] = None) -> np.ndarray:
        """
        Draw frame information overlay.
        
        Args:
            frame: Input frame
            frame_num: Current frame number
            fps: Optional FPS to display
            
        Returns:
            Frame with info overlay
        """
        info_lines = [f"Frame: {frame_num}"]
        
        if fps is not None:
            info_lines.append(f"FPS: {fps:.1f}")
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        color = (255, 255, 255)
        
        y_offset = 30
        for i, line in enumerate(info_lines):
            y_pos = y_offset + i * 30
            cv2.putText(frame, line, (10, y_pos),
                       font, font_scale, color, font_thickness)
        
        return frame
    
    def show_preview(self, frame: np.ndarray) -> bool:
        """
        Show live preview window.
        
        Args:
            frame: Frame to display
            
        Returns:
            True to continue, False if user pressed 'q' to quit
        """
        if not self.show_live_preview:
            return True
        
        if not self.window_created:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            self.window_created = True
        
        cv2.imshow(self.window_name, frame)
        
        # Wait 1ms and check for 'q' key
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            return False
        
        return True
    
    def close_preview(self):
        """Close preview window."""
        if self.window_created:
            cv2.destroyWindow(self.window_name)
            self.window_created = False
    
    def create_video_writer(self, output_path: str, fps: float,
                           frame_size: Tuple[int, int]) -> cv2.VideoWriter:
        """
        Create video writer for output.
        
        Args:
            output_path: Output video path
            fps: Frame rate
            frame_size: (width, height)
            
        Returns:
            VideoWriter object
        """
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
        return writer

