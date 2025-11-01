# Quick Start Guide

Get started with lane violation detection in 4 easy steps!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Your Lane Polygon

Use the interactive tool to define the truck/bus lane by clicking 4 corners:

```bash
python configure_lane.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml
```

**What to do:**
- A window will open showing a frame from your video
- Click 4 corners to define the lane polygon
- Points will be numbered 1, 2, 3, 4
- Press **'s'** to save the configuration
- Press **'q'** to quit

The tool will automatically update your `config.yaml` file with the polygon coordinates.

## Step 3: Calibrate Camera for Speed (Optional)

For accurate speed estimation, calibrate the camera with real-world measurements:

```bash
python calibrate_camera.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml
```

**What to do:**
- Click 4 points on the road plane (lane markings, crosswalk, etc.)
- For each point, enter its real-world coordinates in meters
- Use known distances (standard lane width is 3.5m)
- Press **'s'** to save

**Skip this step if you only need lane violation detection without speed.**

## Step 4: Process Your Video

Run the lane violation detection:

```bash
python -m src.main --config footage/siteA/config.yaml --video footage/siteA/video.mp4 --output runs/overlays/output.mp4
```

**What happens:**
- Live preview window shows processing in real-time
- Detects vehicles and tracks them
- Estimates speed in km/h
- Flags lane violations
- Press **'q'** in the preview to stop early

## View Results

**Output Video:**
```bash
# Open the annotated video
runs/overlays/output.mp4
```

**Violation Events:**
```bash
# View violation logs (JSON)
cat events/logs/*.json
```

## Bonus: Process a Single Image

Want to test with just one frame?

```bash
python -m src.process_image --config footage/siteA/config.yaml --image footage/siteA/frame.jpg --output runs/images/frame_annotated.jpg
```

## Next Steps

### Fine-tune Detection
Edit `configs/detector_yolov8s.yaml`:
```yaml
conf_thres: 0.25  # Lower = more detections, Higher = fewer false positives
```

### Adjust Violation Threshold
Edit `footage/siteA/config.yaml`:
```yaml
violation:
  dwell_frames: 10  # Increase to reduce false positives
```

### Calibrate for Speed Accuracy
For accurate speed estimation, you need to calibrate the camera. See the full README for details on homography calibration.

## Troubleshooting

**"Could not open video"**
- Check the video path is correct
- Try a different video format (MP4 with H.264 codec works best)

**No violations detected**
- Make sure the lane polygon is correctly positioned
- Check that `classes_truck_ok` in config matches your needs
- Try lowering `dwell_frames` threshold

**Slow processing**
- Reduce `img_size` in `configs/detector_yolov8s.yaml` (e.g., 480)
- Disable live preview: set `show_live_preview: false` in config
- Use a GPU if available (automatically detected)

## Full Documentation

For complete documentation, see:
- `README.md` - Full system documentation
- `example_usage.md` - Detailed usage examples
- `IMPLEMENTATION_SUMMARY.md` - Technical details

## Demo Script

Run a quick demo to test everything:

```bash
python run_demo.py
```

This will:
1. Extract test frames
2. Run image mode
3. Run video mode
4. Show you where the outputs are

---

**That's it! You're ready to detect lane violations.** 🚗🚛

