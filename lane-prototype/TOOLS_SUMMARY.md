# Configuration Tools Summary

## Overview

The lane violation detection system includes three interactive configuration tools to help you set up your site easily.

## 1. Lane Polygon Configuration (`configure_lane.py`)

**Purpose:** Define the truck/bus lane area by clicking 4 corners.

**Usage:**
```bash
python configure_lane.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml
```

**How it works:**
1. Opens a window with your video frame
2. Click 4 corners to define the lane polygon
3. Points are numbered 1, 2, 3, 4 and connected with lines
4. Semi-transparent fill shows the complete polygon
5. Press 's' to save, 'r' to reset, 'q' to quit

**Output:** Updates `truck_bus_lane_polygon` in config.yaml

**When to use:** Always - required for lane violation detection

## 2. Camera Calibration (`calibrate_camera.py`)

**Purpose:** Calibrate camera for accurate speed estimation by mapping pixels to real-world meters.

**Usage:**
```bash
python calibrate_camera.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml
```

**How it works:**
1. Opens a window with your video frame
2. Click 4 points on the road plane (lane markings, crosswalk, etc.)
3. For each point, enter its real-world coordinates in meters via console
4. Points are numbered and connected with lines
5. Press 's' to save, 'r' to reset, 'q' to quit

**Output:** Updates `homography.image_points` and `homography.world_points` in config.yaml

**When to use:** Optional - only needed if you want accurate speed estimation

**Tips:**
- Choose points that form a rectangle or quadrilateral
- Use known distances (standard lane width: 3.5m)
- Measure distances using Google Maps satellite view
- All points must be on the same flat road surface

## 3. Demo Runner (`run_demo.py`)

**Purpose:** Quick automated test of both image and video modes.

**Usage:**
```bash
python run_demo.py
```

**What it does:**
1. Creates test files (frame and short video)
2. Runs image processing mode
3. Runs video processing mode
4. Shows summary of results

**Output:**
- `runs/images/demo_image.jpg`
- `runs/overlays/demo_video.mp4`
- `events/logs/*.json`

**When to use:** Testing and verification

## Configuration Workflow

### Recommended Order:

**1. Configure Lane Polygon** (Required)
```bash
python configure_lane.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml
```
- Click 4 corners of truck/bus lane
- Save with 's'

**2. Calibrate Camera** (Optional, for speed)
```bash
python calibrate_camera.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml
```
- Click 4 points on road with known distances
- Enter real-world coordinates for each point
- Save with 's'

**3. Process Video**
```bash
python -m src.main --config footage/siteA/config.yaml --video footage/siteA/video.mp4 --output runs/overlays/output.mp4
```

## Quick Reference

| Tool | Required? | Purpose | Output |
|------|-----------|---------|--------|
| `configure_lane.py` | ✅ Yes | Define lane area | `truck_bus_lane_polygon` |
| `calibrate_camera.py` | ⚠️ Optional | Enable speed estimation | `homography` points |
| `run_demo.py` | ℹ️ Testing | Verify system works | Demo outputs |

## Keyboard Controls

All tools use the same keyboard controls:
- **'s'** - Save configuration
- **'r'** - Reset and start over
- **'q'** - Quit without saving

## Common Issues

### configure_lane.py

**Issue:** Can't click 4th point
- **Solution:** Press 'r' to reset if you made a mistake

**Issue:** Polygon looks wrong
- **Solution:** Press 'r' and click corners in correct order (clockwise or counter-clockwise)

### calibrate_camera.py

**Issue:** Program crashes after clicking point
- **Solution:** Make sure to enter valid numbers when prompted for coordinates

**Issue:** Don't know real-world coordinates
- **Solution:** 
  - Use Google Maps to measure distances
  - Standard lane width is 3.5m
  - Crosswalks are typically 3-4m
  - Skip calibration if you don't need speed estimation

**Issue:** Accidentally pressed Ctrl+C during input
- **Solution:** Press 'r' to reset and start over

### General Issues

**Issue:** Window doesn't open
- **Solution:** Check OpenCV is installed: `pip install opencv-python`

**Issue:** Can't find video file
- **Solution:** Use full path or verify file exists

## Example Session

### Configuring Lane Polygon:
```
> python configure_lane.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml

Extracting frame from video...
Saved temporary frame: temp_config_frame.jpg

============================================================
Lane Polygon Configuration Tool
============================================================
Image: temp_config_frame.jpg
Config: footage/siteA/config.yaml
Image size: 854x480

Instructions:
  - Click 4 corners to define the truck/bus lane polygon
  - Points will be numbered 1, 2, 3, 4
  - Press 's' to save the configuration
  - Press 'r' to reset and start over
  - Press 'q' to quit without saving
============================================================

Point 1: (108, 475)
Point 2: (299, 474)
Point 3: (211, 8)
Point 4: (194, 7)

Saved lane polygon to: footage/siteA/config.yaml
  Point 1: (108, 475)
  Point 2: (299, 474)
  Point 3: (211, 8)
  Point 4: (194, 7)
```

### Calibrating Camera:
```
> python calibrate_camera.py --image footage/siteA/video.mp4 --config footage/siteA/config.yaml

Extracting frame from video...
Saved temporary frame: temp_calibration_frame.jpg

======================================================================
Camera Calibration Tool
======================================================================
Image: temp_calibration_frame.jpg
Config: footage/siteA/config.yaml
Image size: 854x480

Instructions:
  1. Click 4 points on the ROAD PLANE (not on walls/signs)
  2. For each point, enter its real-world coordinates in METERS
  3. Use known distances (lane width, markings, etc.)
  4. Press 's' to save, 'r' to reset, 'q' to quit

Tips:
  - Choose points that form a rectangle or quadrilateral
  - Standard lane width: 3.5m
  - Use Google Maps to measure distances
  - All points must be on the same flat road surface
======================================================================

Point 1 clicked at pixel: (100, 400)

Enter real-world coordinates for Point 1:
  (These are the actual distances in METERS on the road)
  X coordinate (meters, horizontal): 0
  Y coordinate (meters, depth/forward): 0
  Point 1: Pixel(100, 400) = World(0.0m, 0.0m)

Point 2 clicked at pixel: (240, 400)

Enter real-world coordinates for Point 2:
  (These are the actual distances in METERS on the road)
  X coordinate (meters, horizontal): 3.5
  Y coordinate (meters, depth/forward): 0
  Point 2: Pixel(240, 400) = World(3.5m, 0.0m)

[... continue for points 3 and 4 ...]

Saved camera calibration to: footage/siteA/config.yaml

Calibration Summary:
  Point 1: Pixel(100, 400) -> World(0.0m, 0.0m)
  Point 2: Pixel(240, 400) -> World(3.5m, 0.0m)
  Point 3: Pixel(260, 200) -> World(3.5m, 10.0m)
  Point 4: Pixel(120, 200) -> World(0.0m, 10.0m)
```

## PowerShell Compatibility

All commands are single-line and work in PowerShell without modification. No backslash line continuations needed!

## Next Steps

After configuration:
1. Test with short video: `python -m src.main --config footage/siteA/config.yaml --video footage/siteA/test_short.mp4 --output runs/overlays/test.mp4`
2. Process full video: `python -m src.main --config footage/siteA/config.yaml --video footage/siteA/video.mp4 --output runs/overlays/output.mp4`
3. Review violations: Check `events/logs/*.json`

For more details, see:
- `README.md` - Complete documentation
- `QUICKSTART.md` - Quick start guide
- `example_usage.md` - Usage examples

