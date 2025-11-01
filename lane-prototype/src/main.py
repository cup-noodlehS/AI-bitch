"""
Main video processing pipeline for lane violation detection.
Orchestrates detection, tracking, speed estimation, and violation checking.
"""
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import cv2
import yaml

from src.detect import VehicleDetector
from src.track import VehicleTracker
from src.calibrate import CameraCalibrator
from src.speed import SpeedEstimator
from src.rules import LaneViolationChecker
from src.overlay import OverlayDrawer


def process_video(config_path: str, video_path: str, output_path: str,
                 detector_config: str = "configs/detector_yolov8s.yaml",
                 tracker_config: str = "configs/tracker_bytetrack.yaml"):
    """
    Process video for lane violations with tracking and speed estimation.
    
    Args:
        config_path: Path to site config YAML
        video_path: Path to input video
        output_path: Path to save output video
        detector_config: Path to detector config
        tracker_config: Path to tracker config
    """
    print(f"Processing video: {video_path}")
    
    # Load site config
    with open(config_path, 'r') as f:
        site_config = yaml.safe_load(f)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    # Get video properties
    fps = site_config.get('fps_override') or cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video: {frame_width}x{frame_height} @ {fps:.2f} FPS, {total_frames} frames")
    
    # Initialize modules
    print("Initializing detector, tracker, and calibrator...")
    detector = VehicleDetector(detector_config)
    tracker = VehicleTracker(tracker_config, fps=fps)
    calibrator = CameraCalibrator(site_config)
    speed_estimator = SpeedEstimator(calibrator, site_config, fps)
    violation_checker = LaneViolationChecker(site_config)
    overlay_drawer = OverlayDrawer(site_config)
    
    # Create output video writer
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    video_writer = overlay_drawer.create_video_writer(
        output_path, fps, (frame_width, frame_height)
    )
    
    # Event storage
    violation_events = []
    
    # Processing loop
    frame_num = 0
    start_time = time.time()
    
    print("\\nProcessing frames...")
    print("Press 'q' in the preview window to stop early")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_num += 1
            
            # Progress indicator
            if frame_num % 30 == 0 or frame_num == 1:
                elapsed = time.time() - start_time
                fps_actual = frame_num / elapsed if elapsed > 0 else 0
                progress = (frame_num / total_frames * 100) if total_frames > 0 else 0
                print(f"Frame {frame_num}/{total_frames} ({progress:.1f}%) - {fps_actual:.1f} FPS")
            
            # 1. Detect vehicles
            detections = detector.detect(frame)
            
            # 2. Track vehicles
            tracks = tracker.update(detections)
            
            # 3. Estimate speed and check violations
            frame_has_violation = False
            
            for track in tracks:
                track_id = track['track_id']
                centroid = detector.get_centroid(track['bbox'])
                
                # Estimate speed
                speed_kph = None
                if calibrator.is_calibrated():
                    speed_kph = speed_estimator.update_track(track_id, centroid, frame_num)
                
                # Check violation
                is_violation, dwell_count = violation_checker.check_track_violation(
                    track_id, centroid, track['class_name']
                )
                
                if is_violation:
                    frame_has_violation = True
                    
                    # Log violation event (only once when first triggered)
                    if dwell_count == violation_checker.dwell_frames:
                        timestamp_ms = (frame_num / fps) * 1000
                        site_name = Path(config_path).parent.name
                        
                        event = {
                            'event_id': f"{site_name}_{frame_num:08d}_t{track_id}",
                            'media': video_path,
                            'timestamp_ms': timestamp_ms,
                            'frame_num': frame_num,
                            'track_id': track_id,
                            'class': track['class_name'],
                            'violation': 'TRUCK_BUS_LANE',
                            'dwell_frames': dwell_count,
                            'speed_kph': speed_kph if speed_kph else 0.0
                        }
                        
                        violation_events.append(event)
                        print(f"  VIOLATION: Track {track_id} ({track['class_name']}) - {speed_kph:.1f} km/h")
                
                # 4. Draw overlay
                frame = overlay_drawer.draw_detection(
                    frame, track,
                    track_id=track_id,
                    speed_kph=speed_kph,
                    is_violation=is_violation
                )
            
            # Draw lane polygon
            lane_polygon = violation_checker.get_lane_polygon()
            frame = overlay_drawer.draw_lane_polygon(frame, lane_polygon, frame_has_violation)
            
            # Draw frame info
            frame = overlay_drawer.draw_frame_info(frame, frame_num, fps)
            
            # 5. Write output frame
            video_writer.write(frame)
            
            # 6. Show live preview
            if not overlay_drawer.show_preview(frame):
                print("\\nStopped by user")
                break
    
    finally:
        # Cleanup
        cap.release()
        video_writer.release()
        overlay_drawer.close_preview()
        cv2.destroyAllWindows()
    
    # Save violation events
    if violation_events:
        events_dir = Path("events/logs")
        events_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        site_name = Path(config_path).parent.name
        event_file = events_dir / f"{site_name}_video_{timestamp}.json"
        
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'media': video_path,
            'site_config': config_path,
            'total_frames': frame_num,
            'fps': fps,
            'violations': violation_events
        }
        
        with open(event_file, 'w') as f:
            json.dump(event_data, f, indent=2)
        
        print(f"\\nSaved {len(violation_events)} violation event(s) to: {event_file}")
    
    elapsed = time.time() - start_time
    print(f"\\nProcessing complete!")
    print(f"  Frames processed: {frame_num}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"  Average FPS: {frame_num/elapsed:.1f}")
    print(f"  Output video: {output_path}")
    print(f"  Violations detected: {len(violation_events)}")


def main():
    """Main entry point for video processing."""
    parser = argparse.ArgumentParser(
        description='Process video for lane violation detection with tracking and speed'
    )
    parser.add_argument('--config', required=True,
                       help='Path to site config YAML')
    parser.add_argument('--video', required=True,
                       help='Path to input video')
    parser.add_argument('--output', required=True,
                       help='Path to save output video')
    parser.add_argument('--detector-config', default='configs/detector_yolov8s.yaml',
                       help='Path to detector config')
    parser.add_argument('--tracker-config', default='configs/tracker_bytetrack.yaml',
                       help='Path to tracker config')
    
    args = parser.parse_args()
    
    process_video(
        config_path=args.config,
        video_path=args.video,
        output_path=args.output,
        detector_config=args.detector_config,
        tracker_config=args.tracker_config
    )


if __name__ == '__main__':
    main()

