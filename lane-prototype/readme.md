# Implementation Plan — **Single-Footage Speed + Truck/Bus-Lane Violation (Rectangle Lane)**

This document is the step-by-step plan for a **simple, one-footage** prototype that:

1. draws **bounding boxes** around vehicles and estimates their **speed** (km/h), and
2. flags a **lane violation** when a **non-truck** (e.g., car) enters a **manually defined rectangular lane** reserved for **truck/bus**.

It assumes a **fixed CCTV** camera and no benchmarking—just a clean demo with overlays and a tiny JSON log.

---

## 0) Tech choices (kept minimal)

* **Detector**: YOLOv8-s **pretrained** on COCO (no labeling needed) for `car, bus, truck, motorcycle` classes. (Ultralytics, 2023)
* **Tracker**: BYTETrack (stable IDs; keeps low-score detections when associating). (Zhang et al., 2022)
* **Speed**: single-camera **road-plane calibration** → project pixel motion to meters, then speed = Δdistance/Δtime; stabilize with a Kalman/EMA. (Dubska et al., 2014; Sochor et al., 2017)
* **Lane rule**: user-drawn **rectangle** (truck/bus lane). Violation if a **non-truck/non-bus** track centroid stays **inside** the rectangle ≥ N frames.

---

## 1) Folder layout (single-footage friendly)

```
project/
├─ footage/
│  └─ siteA/
│     ├─ video.mp4
│     └─ config.yaml          # camera & lane config (see schema below)
├─ runs/
│  ├─ dets/                   # per-frame detections
│  ├─ tracks/                 # MOT-format tracks
│  └─ overlays/               # .mp4 with boxes+speed+violations
├─ events/
│  ├─ logs/                   # JSON events (lane violations)
│  └─ images/                 # optional snapshots
├─ configs/
│  ├─ detector_yolov8s.yaml
│  └─ tracker_bytetrack.yaml
└─ src/
   ├─ detect.py
   ├─ track.py
   ├─ calibrate.py
   ├─ speed.py
   ├─ rules.py
   ├─ overlay.py
   └─ main.py
```

---

## 2) `footage/siteA/config.yaml` (single source of truth)

```yaml
# ===== Camera/Video =====
video_path: "footage/siteA/video.mp4"
fps_override: null            # null => auto-read from video; else number
# frame_index_offset is 0 unless you start mid-video
frame_index_offset: 0

# ===== Road-plane calibration (choose ONE approach) =====
# A) Homography-based (recommended): 4 points on road plane → world (meters)
homography:
  image_points: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]   # click 4 road corners
  world_points: [[X1,Y1],[X2,Y2],[X3,Y3],[X4,Y4]]   # meters in same plane
# B) Simple scale (fallback): assume straight lane with L meters spanning S pixels
# simple_scale: { meters_per_pixel: 0.025 }

# Optional camera height if you implement Sochor’s auto-calib variants
camera_height_m: null

# ===== Truck/Bus lane rectangle (in image pixels) =====
truck_bus_lane_rect: { x: 820, y: 300, w: 220, h: 380 }

# ===== Rule thresholds =====
violation:
  dwell_frames: 10           # inside-rectangle frames to call a violation
  classes_truck_ok: ["truck","bus"]
speed:
  smoothing: "ema"           # "ema" or "kalman"
  ema_alpha: 0.2
  min_pixels_per_sec: 3      # ignore jitter below this motion
  report_every_n_frames: 3   # reduce UI flicker

# ===== Overlay =====
overlay:
  draw_speed: true
  draw_lane_rect: true
  draw_track_ids: true
  out_video_path: "runs/overlays/siteA_overlay.mp4"
```

> **Where do the points come from?** Use a tiny helper script that pauses a frame and lets you **click 4 road-plane points** (e.g., lane corners, crosswalk corners). Enter the corresponding **meter coordinates** (measure with Google Maps/known lane width) to build the homography H. (Dubska et al., 2014)

---

## 3) Pipeline (single command)

```bash
python -m src.main --config footage/siteA/config.yaml \
  --det-cfg configs/detector_yolov8s.yaml \
  --trk-cfg configs/tracker_bytetrack.yaml \
  --events-dir events/
```

**Under the hood:**

1. `detect.py`: run YOLOv8-s on each frame, keep classes `{car,bus,truck,motorcycle}`.
2. `track.py`: feed detections → BYTETrack → per-frame tracks with IDs.
3. `calibrate.py`: build **H** (image→world plane) from `config.yaml` (or use simple scale).
4. `speed.py`:

   * Take track centroids `p_t` (image px).
   * Map to world `P_t = H(p_t)` (meters).
   * Instant speed (m/s) = `||P_t − P_{t−Δ}|| / (Δframes/fps)`. Convert to km/h; smooth (EMA/Kalman).
   * Ignore tiny motions (`min_pixels_per_sec`). (Dubska et al., 2014; Sochor et al., 2017)
5. `rules.py`: For each track at frame t, test centroid against **truck/bus rectangle**:

   * If class ∉ {truck, bus} **AND** centroid inside rect for `dwell_frames` → **violation**.
6. `overlay.py`: draw box, track ID, **speed km/h**, rectangle, and red border for violations.
7. Write **events JSON** + optional snapshots.

---

## 4) File-by-file details

### `src/detect.py`

* Loads YOLOv8-s pretrained; filters to classes `{2:car,5:bus,7:truck,3:motorcycle}` (COCO IDs).
* Outputs list of detections per frame: `[x1,y1,x2,y2,score,class]`.

*(Ultralytics, 2023)*

### `src/track.py`

* Implements BYTETrack wrapper (`conf_high`, `conf_low`, `match_thresh`, `track_buffer` from `tracker_bytetrack.yaml`).
* Outputs MOT-style rows: `frame, id, x, y, w, h, score, class`.

*(Zhang et al., 2022)*

### `src/calibrate.py`

* If `homography` present: compute **H** with `cv2.findHomography(image_points, world_points)`.
* Expose: `pixel_to_world(px, py) -> (X, Y)`; ignore Z (road plane).
* Else if `simple_scale`: `meters_per_pixel` times pixel delta.

*(Dubska et al., 2014; Sochor et al., 2017)*

### `src/speed.py`

* Maintains a per-track buffer of world positions and timestamps.
* `instant_speed = distance(P_t, P_{t-k}) / Δt` (k chosen so Δt ~ 0.1–0.3 s to reduce noise).
* Smoothing:

  * **EMA**: `v_smooth[t] = α * v_inst + (1-α) * v_smooth[t-1]`
  * **Kalman** (optional): constant-velocity model on (x, y, vx, vy).
* Outputs speed (km/h) per track for overlay/logging.

### `src/rules.py`

* `inside_rect(cx, cy, rect)` returns boolean; accumulate dwell count per track.
* If track.class ∉ `classes_truck_ok` **and** `inside_rect(...)` for `dwell_frames` → emit violation event.

### `src/overlay.py`

* Draws:

  * Bounding box (color by class): `car=blue, bus/truck=green, motorcycle=orange`.
  * Label: `id | class | {speed:.1f} km/h`.
  * Lane rectangle (green), turns **red** if current frame has a violation.
* Writes MP4 to `overlay.out_video_path`.

### `src/main.py`

* Orchestrates the above in a single pass over the video.
* Saves events to `events/logs/*.json` and snapshots to `events/images/`.

---

## 5) Event JSON (violation record)

```json
{
  "event_id": "siteA_00001234_laneviolation_t17",
  "video": "footage/siteA/video.mp4",
  "timestamp_ms": 42000,
  "track_id": 17,
  "class": "car",
  "violation": "TRUCK_BUS_LANE",
  "dwell_frames": 13,
  "rect": {"x":820,"y":300,"w":220,"h":380},
  "speed_kph": 32.7,
  "artifacts": {
    "frame_jpg": "events/images/siteA_..._commit.jpg"
  }
}
```

---

## 6) Quick run (end-to-end)

1. Put your **video** and create `footage/siteA/config.yaml`.
2. (Optional) Use a click tool to fill `homography.image_points`; type corresponding `world_points` in meters.
3. Run the single command in §3.
4. Open `runs/overlays/siteA_overlay.mp4`; inspect `events/logs/*.json`.

---

## 7) Practical notes

* **Calibration quality** drives **speed accuracy**. If you can’t measure world points, use **simple_scale** with a known lane width or crosswalk length as a proxy; speed will be approximate but consistent. (Dubska et al., 2014)
* **Tiny vehicles**: increase detector input size (e.g., 960) at the cost of FPS.
* **Jitter**: increase `report_every_n_frames` and use EMA α≈0.2–0.3.
* **Lane leniency**: if false positives occur at edges, shrink the rectangle by 3–5 px (morphological “erode” idea).

---

## 8) Minimal configs (examples)

### `configs/detector_yolov8s.yaml`

```yaml
img_size: 640
conf_thres: 0.25
iou_nms: 0.7
classes_keep: ["car","bus","truck","motorcycle"]
```

### `configs/tracker_bytetrack.yaml`

```yaml
conf_high: 0.6
conf_low: 0.1
match_thresh: 0.8
track_buffer: 30
```

---

## 9) Done & demo checklist

* [ ] Overlay video shows **boxes + speed**.
* [ ] Rectangle drawn and visible.
* [ ] When a **car** stays inside the rectangle for ≥ `dwell_frames`, the border flashes **red** and a JSON appears in `events/logs/`.
* [ ] Two screenshot frames saved for the violating moment (optional).

---

## References (APA)

Dubska, M., Herout, A., Juránek, R., & Sochor, J. (2014). Automatic camera calibration for traffic understanding. *British Machine Vision Conference (BMVC)*. [https://doi.org/10.5244/C.28.36](https://doi.org/10.5244/C.28.36)

Sochor, J., Herout, A., & Havel, J. (2017). BoxCars: Improving fine-grained recognition of vehicles using 3D bounding boxes in traffic surveillance. *IEEE Transactions on Intelligent Transportation Systems, 18*(1), 18–29. (Speed calibration lineage; BrnoCompSpeed resources.)

Ultralytics. (2023). *YOLOv8 documentation*. Retrieved from [https://docs.ultralytics.com/](https://docs.ultralytics.com/)

Zhang, Y., Sun, P., Jiang, Y., Yu, D., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-object tracking by associating every detection box. *European Conference on Computer Vision (ECCV)*. [https://arxiv.org/abs/2110.06864](https://arxiv.org/abs/2110.06864)
