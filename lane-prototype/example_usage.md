# Example Usage Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Process a Video

```bash
python -m src.main \
  --config footage/siteA/config.yaml \
  --video footage/siteA/video.mp4 \
  --output runs/overlays/output.mp4
```

**What happens:**
- Detects vehicles in each frame
- Tracks vehicles with stable IDs
- Estimates speed in km/h
- Checks for lane violations
- Shows live preview (press 'q' to quit)
- Saves annotated video and violation events

### 3. Process a Single Image

```bash
python -m src.process_image \
  --config footage/siteA/config.yaml \
  --image footage/siteA/frame.jpg \
  --output runs/images/frame_annotated.jpg
```

**What happens:**
- Detects vehicles in the image
- Checks for instant lane violations
- Saves annotated image
- Optionally saves violation events

## Configuration Tips

### Configuring the Lane Rectangle (Interactive Tool)

Use the interactive configuration tool to visually define the truck/bus lane:

```bash
python configure_lane.py \
  --image footage/siteA/video.mp4 \
  --config footage/siteA/config.yaml
```

**Steps:**
1. Window opens showing your video frame
2. Click and drag to draw rectangle around truck/bus lane
3. Press 's' to save
4. Press 'r' to reset and redraw
5. Press 'q' to quit

The tool automatically updates your config file!

### Adjusting the Lane Rectangle (Manual)

Alternatively, edit `footage/siteA/config.yaml` manually:

```yaml
truck_bus_lane_rect: { x: 820, y: 300, w: 220, h: 380 }
#                       ^     ^     ^     ^
#                       |     |     |     height
#                       |     |     width
#                       |     y position
#                       x position
```

### Adjusting Violation Sensitivity

```yaml
violation:
  dwell_frames: 10  # Increase = fewer false positives
                    # Decrease = faster detection
```

### Calibrating for Speed

For accurate speed estimation, you need to calibrate the camera:

1. Identify 4 points on the road plane (e.g., lane markings)
2. Measure their real-world positions in meters
3. Update config:

```yaml
homography:
  image_points: [[100, 400], [540, 400], [640, 300], [0, 300]]  # Pixels
  world_points: [[0, 0], [10, 0], [10, 5], [0, 5]]              # Meters
```

**Tips:**
- Use lane width (typically 3-3.5m) as reference
- Use crosswalk length if visible
- Google Maps can help measure distances

## Output Files

### Video Output
- Location: `runs/overlays/`
- Format: MP4 with annotations
- Contains: bounding boxes, track IDs, speeds, lane rectangle

### Image Output
- Location: `runs/images/`
- Format: JPG with annotations
- Contains: bounding boxes, class labels, lane rectangle

### Event Logs
- Location: `events/logs/`
- Format: JSON
- Contains: violation details with timestamps

Example event:
```json
{
  "event_id": "siteA_00000064_t17",
  "media": "footage/siteA/video.mp4",
  "timestamp_ms": 2153.87,
  "frame_num": 64,
  "track_id": 17,
  "class": "car",
  "violation": "TRUCK_BUS_LANE",
  "dwell_frames": 10,
  "speed_kph": 32.5
}
```

## Testing

### Test Image Mode

```bash
# Extract a test frame
python test_image.py

# Process it
python -m src.process_image \
  --config footage/siteA/config.yaml \
  --image footage/siteA/test_frame.jpg \
  --output runs/images/test_annotated.jpg
```

### Test Video Mode (Short Clip)

```bash
# Create short test video (5 seconds)
python test_video_short.py

# Process it (with live preview disabled for automation)
python -m src.main \
  --config footage/siteA/config_test.yaml \
  --video footage/siteA/test_short.mp4 \
  --output runs/overlays/test_output.mp4
```

## Common Issues

### "Could not open video"
- Check video path is correct
- Ensure video codec is supported (H.264 recommended)
- Try converting with: `ffmpeg -i input.mp4 -c:v libx264 output.mp4`

### No speed displayed
- Check `homography` configuration in config.yaml
- Verify `draw_speed: true` in overlay settings
- Ensure calibration points are on the same plane

### Too many false violations
- Increase `dwell_frames` (e.g., from 10 to 20)
- Adjust lane rectangle to be more precise
- Check that `classes_truck_ok` includes correct classes

### Slow processing
- Reduce `img_size` in detector config (e.g., 480 instead of 640)
- Disable live preview: `show_live_preview: false`
- Use GPU if available (automatically detected by PyTorch)

## Advanced Usage

### Custom Detector Settings

Edit `configs/detector_yolov8s.yaml`:

```yaml
model: yolov8s.pt      # or yolov8n.pt (faster), yolov8m.pt (more accurate)
img_size: 640          # Lower = faster, Higher = more accurate
conf_thres: 0.25       # Lower = more detections, Higher = fewer false positives
```

### Custom Tracker Settings

Edit `configs/tracker_bytetrack.yaml`:

```yaml
track_thresh: 0.6      # Confidence threshold for tracks
track_buffer: 30       # Frames to keep lost tracks
match_thresh: 0.8      # IoU threshold for matching
```

### Disable Live Preview

For batch processing or headless servers:

```yaml
overlay:
  show_live_preview: false
```

## Performance Benchmarks

Tested on:
- CPU: Intel i7 (8 cores)
- GPU: NVIDIA RTX 3060
- Video: 854x480 @ 30 FPS

Results:
- **With GPU**: ~30 FPS (real-time)
- **CPU only**: ~13 FPS (0.4x real-time)

## Next Steps

1. **Calibrate your camera** for accurate speed estimation
2. **Adjust lane rectangle** to match your footage
3. **Tune violation thresholds** to reduce false positives
4. **Process full videos** and review violation events
5. **Integrate with your workflow** (e.g., automated alerts)

