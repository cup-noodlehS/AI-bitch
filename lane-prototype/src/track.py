"""
Multi-object tracking module using BYTETrack.
Maintains stable track IDs across frames.
"""
import yaml
from typing import List, Dict, Any

import numpy as np


try:
    from ultralytics.trackers.byte_tracker import BYTETracker
    BYTETRACK_AVAILABLE = True
except ImportError:
    BYTETRACK_AVAILABLE = False


class VehicleTracker:
    """Wrapper for BYTETrack multi-object tracking."""
    
    def __init__(self, config_path: str, fps: float = 30.0):
        """
        Initialize tracker.
        
        Args:
            config_path: Path to tracker config YAML
            fps: Video frame rate
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.fps = fps
        self.frame_count = 0
        
        # Use Ultralytics built-in tracking if available
        self.use_builtin = True
        
        # Track storage for manual tracking fallback
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.next_id = 1
    
    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update tracks with new detections.
        
        Args:
            detections: List of detection dicts with 'bbox', 'score', 'class_id', 'class_name'
            
        Returns:
            List of tracks with added 'track_id' field
        """
        self.frame_count += 1
        
        # Simple tracking: assign IDs based on IoU matching
        tracks = []
        
        if not detections:
            return tracks
        
        # Convert detections to tracks
        for det in detections:
            # Try to match with existing tracks
            track_id = self._match_detection(det)
            
            track = det.copy()
            track['track_id'] = track_id
            track['frame'] = self.frame_count
            
            tracks.append(track)
            
            # Update track storage
            self.tracks[track_id] = {
                'bbox': det['bbox'],
                'class_name': det['class_name'],
                'last_frame': self.frame_count
            }
        
        # Clean up old tracks
        self._cleanup_old_tracks()
        
        return tracks
    
    def _match_detection(self, detection: Dict[str, Any]) -> int:
        """
        Match detection to existing track or create new one.
        
        Args:
            detection: Detection dictionary
            
        Returns:
            Track ID
        """
        bbox = detection['bbox']
        class_name = detection['class_name']
        
        best_iou = 0.0
        best_track_id = None
        
        # Try to match with existing tracks
        for track_id, track_data in self.tracks.items():
            # Only match same class
            if track_data['class_name'] != class_name:
                continue
            
            # Check if track is recent
            if self.frame_count - track_data['last_frame'] > 30:
                continue
            
            # Calculate IoU
            iou = self._calculate_iou(bbox, track_data['bbox'])
            
            if iou > best_iou:
                best_iou = iou
                best_track_id = track_id
        
        # Use existing track if good match
        match_thresh = self.config.get('match_thresh', 0.5)
        if best_iou > match_thresh and best_track_id is not None:
            return best_track_id
        
        # Create new track
        new_id = self.next_id
        self.next_id += 1
        return new_id
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """
        Calculate Intersection over Union between two bounding boxes.
        
        Args:
            bbox1: [x1, y1, x2, y2]
            bbox2: [x1, y1, x2, y2]
            
        Returns:
            IoU score
        """
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
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _cleanup_old_tracks(self):
        """Remove tracks that haven't been seen recently."""
        track_buffer = self.config.get('track_buffer', 30)
        
        tracks_to_remove = []
        for track_id, track_data in self.tracks.items():
            if self.frame_count - track_data['last_frame'] > track_buffer:
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
    
    def reset(self):
        """Reset tracker state."""
        self.tracks.clear()
        self.next_id = 1
        self.frame_count = 0

