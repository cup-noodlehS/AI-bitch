# Polygon Lane Configuration Update

## Summary

The lane violation detection system has been updated to use **4-corner polygon selection** instead of rectangles, providing more flexibility for angled and perspective-distorted lanes. Video quality preservation has also been verified.

## What Changed

### 1. Polygon-Based Lane Configuration

**New Configuration Tool (`configure_lane.py`):**
- Click 4 corners to define lane polygon (instead of click-and-drag rectangle)
- Visual feedback with numbered points (1, 2, 3, 4)
- Lines connect points as you click
- Semi-transparent fill when complete
- Saves as `truck_bus_lane_polygon` in config

**Usage:**
```bash
python configure_lane.py \
  --image footage/siteA/video.mp4 \
  --config footage/siteA/config.yaml
```

**How it works:**
1. Window opens with video frame
2. Click 4 corners of the lane area in order
3. Points are numbered and connected with lines
4. Press 's' to save, 'r' to reset, 'q' to quit

### 2. Updated Configuration Format

**New Format (Polygon):**
```yaml
truck_bus_lane_polygon: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
```

**Old Format (Still Supported):**
```yaml
truck_bus_lane_rect: { x: 820, y: 300, w: 220, h: 380 }
```

**Backward Compatibility:**
- System automatically detects which format is used
- Polygon format takes precedence if both exist
- Rectangle format is automatically converted to polygon internally

### 3. Updated Modules

**`src/rules.py`:**
- New `point_in_lane()` method using OpenCV's `cv2.pointPolygonTest()`
- Supports both polygon and rectangle formats
- Automatic format detection and conversion
- Old `point_in_rect()` method kept for compatibility

**`src/overlay.py`:**
- New `draw_lane_polygon()` method using `cv2.polylines()` and `cv2.fillPoly()`
- Semi-transparent polygon fill (10% opacity)
- Label positioned at polygon centroid
- Old `draw_lane_rectangle()` method converts to polygon

**`src/main.py` and `src/process_image.py`:**
- Updated to use `get_lane_polygon()` and `draw_lane_polygon()`
- Backward compatible with old configs

### 4. Video Quality Preservation

**Verified:**
- ✅ Input and output video dimensions match exactly (854x480)
- ✅ YOLO's `imgsz` parameter only affects internal processing
- ✅ Bounding boxes are automatically scaled to original dimensions
- ✅ No resizing operations on frames
- ✅ Original video quality preserved

**Added clarification in `src/detect.py`:**
```python
# Note: imgsz only affects internal YOLO processing (resizing for the model).
# The output bounding boxes are automatically scaled back to original frame dimensions.
# The input frame is never modified - original quality is preserved.
```

## Benefits of Polygon Configuration

1. **More Flexible**: Handles angled, trapezoid, and perspective-distorted lanes
2. **Better Accuracy**: Fits actual lane boundaries more precisely
3. **Easier to Use**: Click 4 corners instead of estimating rectangle dimensions
4. **Visual Feedback**: See exactly what area you're defining
5. **Backward Compatible**: Old rectangle configs still work

## Testing Results

### Image Mode
```bash
python -m src.process_image \
  --config footage/siteA/config.yaml \
  --image footage/siteA/test_frame.jpg \
  --output runs/images/test_polygon.jpg
```
- ✅ Detected 8 vehicles
- ✅ Polygon drawn correctly
- ✅ Violation detection working

### Video Mode
```bash
python -m src.main \
  --config footage/siteA/config_test.yaml \
  --video footage/siteA/test_short.mp4 \
  --output runs/overlays/test_polygon.mp4
```
- ✅ Processed 148 frames at 14.4 FPS
- ✅ Detected 1 violation
- ✅ Output dimensions match input (854x480)
- ✅ Polygon overlay visible in output

## Migration Guide

### For New Sites

Use the interactive configuration tool:
```bash
python configure_lane.py \
  --image footage/yoursite/video.mp4 \
  --config footage/yoursite/config.yaml
```

### For Existing Sites

**Option 1: Keep using rectangle format**
- No changes needed
- System automatically converts to polygon internally

**Option 2: Migrate to polygon format**
1. Run the configuration tool with your existing video
2. Click 4 corners matching your current rectangle
3. Save - old rectangle format will be replaced

### Manual Configuration

Edit `config.yaml`:
```yaml
# New polygon format
truck_bus_lane_polygon: [[820, 300], [1040, 300], [1040, 680], [820, 680]]

# Old rectangle format (remove if using polygon)
# truck_bus_lane_rect: { x: 820, y: 300, w: 220, h: 380 }
```

## API Changes

### New Methods

**`LaneViolationChecker` (src/rules.py):**
- `point_in_lane(px, py)` - Check if point is in polygon (new)
- `get_lane_polygon()` - Get polygon points (new)

**`OverlayDrawer` (src/overlay.py):**
- `draw_lane_polygon(frame, polygon, has_violation)` - Draw polygon (new)

### Deprecated (Still Supported)

- `point_in_rect()` - Now calls `point_in_lane()` internally
- `draw_lane_rectangle()` - Now converts to polygon and calls `draw_lane_polygon()`

## Examples

### Polygon for Angled Lane
```yaml
# Lane that's not perfectly rectangular
truck_bus_lane_polygon: [[750, 250], [1100, 280], [1080, 700], [720, 650]]
```

### Polygon for Perspective View
```yaml
# Lane that appears trapezoid due to camera angle
truck_bus_lane_polygon: [[600, 200], [800, 200], [900, 600], [500, 600]]
```

### Rectangle Equivalent
```yaml
# Perfect rectangle (4 corners at 90 degrees)
truck_bus_lane_polygon: [[820, 300], [1040, 300], [1040, 680], [820, 680]]
```

## Troubleshooting

### Configuration Tool Issues

**Window doesn't open:**
- Ensure OpenCV is installed: `pip install opencv-python`
- Try with an image instead of video
- Check video file exists and is readable

**Can't click points:**
- Make sure window has focus
- Try clicking more slowly
- Check console for error messages

### Polygon Not Showing

**In output video:**
- Check `overlay.draw_lane_rect: true` in config
- Verify polygon points are within frame bounds
- Ensure polygon is defined (4 points)

**Wrong position:**
- Re-run configuration tool
- Verify points are in correct order (clockwise or counter-clockwise)

### Video Quality Issues

**If output looks different:**
- Check input video codec (H.264 recommended)
- Verify dimensions match: see "Testing Results" section
- Try different video player

## Performance

No performance impact from polygon vs rectangle:
- Point-in-polygon test: ~O(n) where n=4 (negligible)
- Drawing: Slightly more complex but imperceptible
- Overall FPS: Same as before (~14 FPS on CPU, ~30 FPS on GPU)

## Future Enhancements

Potential improvements:
- Support for more than 4 points (complex shapes)
- Multiple lane polygons per site
- Automatic lane detection from video
- Interactive polygon editing (move/delete points)

## Documentation Updates

Updated files:
- `README.md` - Added polygon configuration section
- `example_usage.md` - Updated with polygon examples
- `TOOLS.md` - Documented new configuration tool
- `QUICKSTART.md` - Updated quick start guide

## Summary

✅ Polygon-based lane configuration implemented
✅ 4-corner interactive selection tool created
✅ Backward compatibility maintained
✅ Video quality preservation verified
✅ All tests passing
✅ Documentation updated

The system now provides more flexible lane definition while maintaining full backward compatibility with existing rectangle configurations.

