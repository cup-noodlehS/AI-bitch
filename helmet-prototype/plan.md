# Helmet Non-Use Violation Detection (Fixed CCTV) — Prototype

This repository contains a **working prototype** that detects **motorcycle helmet non-use** from a **fixed surveillance camera**. The goal is to (1) stand up an end-to-end pipeline you can demo to your adviser and (2) give you clean material for your **Methodology** section. The prototype trains (or reuses) a small detector for **motorcycle / person / helmet**, tracks targets across frames, applies a **temporal rule** (no helmet in rider head-ROI for K consecutive frames), and emits **auditable evidence** (JSON + still images + short MP4 clip per event).

**Why this approach?**
Fixed-view CCTV allows stable geometry and consistent scale. A lightweight detector (YOLO family) plus a modern tracker (e.g., BYTETrack) provides reliable **per-rider tracks**; a simple, explainable **temporal rule** then flags violations. This keeps the prototype real-time on modest GPUs and easy to extend later (LPR, red-light, speed).

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [What This Prototype Does](#what-this-prototype-does)
3. [Datasets You’ll Use](#datasets-youll-use)
4. [Quick Start](#quick-start)
5. [Data Preparation](#data-preparation)
6. [Training the Detector](#training-the-detector)
7. [Tracking & Association](#tracking--association)
8. [Violation Logic (How We Decide “No Helmet”)](#violation-logic-how-we-decide-no-helmet)
9. [Running Inference on CCTV Footage](#running-inference-on-cctv-footage)
10. [Evidence Output (What gets saved?)](#evidence-output-what-gets-saved)
11. [Minimal Evaluation Plan](#minimal-evaluation-plan)
12. [Configuration Reference](#configuration-reference)
13. [Common Failure Modes & Mitigations](#common-failure-modes--mitigations)
14. [Ethics & Privacy Notes (PH Context)](#ethics--privacy-notes-ph-context)
15. [Roadmap](#roadmap)
16. [References (APA)](#references-apa)

---

## Repository Structure

```text
helmet-violation-proto/
├─ README.md
├─ configs/
│  ├─ detector_yolov8s.yaml           # or detector_yolox_s.yaml
│  ├─ tracker_bytetrack.yaml
│  └─ module_helmet.yaml              # thresholds (K frames), class names, etc.
├─ data/
│  ├─ raw/
│  │  └─ helmet/                      # HELMET dataset archives (videos/labels)
│  └─ prepared/
│     └─ helmet/                      # normalized images/labels for training
├─ detectors/
│  ├─ train_yolov8.py                 # or train_yolox.py
│  └─ export_detections.py            # dumps per-frame detections for tracker
├─ trackers/
│  └─ bytetrack_runner.py             # associates detections → tracks
├─ modules/
│  ├─ helmet_violation.py             # temporal rule logic + head-ROI
│  └─ roi_utils.py                    # head region, IoU/overlap helpers
├─ app/
│  ├─ streamlit_app.py                # demo UI with overlays + live log
│  └─ cli_player.py                   # CLI: run inference & save evidence
├─ eval/
│  ├─ make_splits.py                  # create small train/val/test splits
│  ├─ helmet_metrics.py               # per-rider P/R and confusion matrix
│  └─ sample_report.ipynb             # tiny notebook for plots/tables
└─ events/
   ├─ clips/                          # mp4 snippets per event
   ├─ images/                         # enter/commit stills
   └─ logs/                           # JSON event records
```

---

## What This Prototype Does

* **Detects** motorcycles, riders/persons, and helmets in each frame.
* **Tracks** riders across frames (unique IDs) using a multi-object tracker.
* **Decides** violations via a simple, explainable rule: if a rider’s **head region** shows **no helmet** for **K consecutive frames**, emit a violation event.
* **Saves evidence** (JSON metadata + 2 stills + short MP4) per event for easy human review.

---

## Datasets You’ll Use

* **HELMET (Myanmar)** — ~910 short roadside clips captured from **fixed cameras**, with riders and helmet labels. Use it to train/validate your helmet and rider detection heads. (OSF, 2020).
* *(Optional, for smoketests)* **UA-DETRAC** — fixed-camera traffic videos. Helpful for early detection/tracking overlays if you’re still downloading HELMET. (Wen et al., 2020).

> This prototype assumes your final **demo CCTV** will be your own intersection/corridor footage (fixed camera). You can still train on HELMET and run inference on your CCTV after a small visual sanity check.

---

## Quick Start

```bash
# 0) Create folders
mkdir -p data/raw/helmet data/prepared/helmet events/{clips,images,logs}

# 1) Put HELMET dataset archives under data/raw/helmet/
#    (see Data Preparation below)

# 2) Prepare & split
python eval/make_splits.py --in data/raw/helmet --out data/prepared/helmet \
  --train-ratio 0.7 --val-ratio 0.15 --test-ratio 0.15

# 3) Train a small detector (YOLOv8-s by default)
python detectors/train_yolov8.py --cfg configs/detector_yolov8s.yaml \
  --data data/prepared/helmet

# 4) Export per-frame detections for your test CCTV clip
python detectors/export_detections.py --weights runs/detect/best.pt \
  --video path/to/cctv_clip.mp4 --out runs/dets/cctv01.txt

# 5) Track with BYTETrack
python trackers/bytetrack_runner.py --dets runs/dets/cctv01.txt \
  --cfg configs/tracker_bytetrack.yaml --out runs/tracks/cctv01.txt

# 6) Run helmet violation logic (produces JSON + stills + mp4)
python modules/helmet_violation.py --video path/to/cctv_clip.mp4 \
  --tracks runs/tracks/cctv01.txt --cfg configs/module_helmet.yaml \
  --events-dir events/
```

---

## Data Preparation

1. **Download HELMET** (Myanmar helmet-use dataset) and place archives in `data/raw/helmet/`.
2. **Extract** videos and labels (we standardize to COCO/YOLO-style annotations).
3. **Split** into train/val/test using `eval/make_splits.py` (stratify by scene and time-of-day if metadata allows).
4. **Sanity check**: visualize random samples to ensure class names match `module_helmet.yaml` (e.g., `motorcycle`, `person`, `helmet`).

> Why HELMET? It’s fixed-camera, SEA-like traffic, and already focused on riders and helmets—excellent domain transfer to Philippine CCTV conditions. (OSF, 2020)

---

## Training the Detector

Choose **either** YOLOv8-s **or** YOLOX-s (both are solid small backbones):

* **YOLOv8-s** (simple trainer & good defaults):

  * img size: 640
  * epochs: 100–150
  * augmentation: moderate (HSV, flip, scale jitter)
  * classes: `{motorcycle, person, helmet}`
* **YOLOX-s** (anchor-free, competitive baseline): similar settings.

Save the best checkpoint by mAP (helmet class is the key). You can also bootstrap from COCO pretrained weights to converge faster.

---

## Tracking & Association

We use **BYTETrack** on the exported per-frame detections:

* Keep **low-score detections** for association (BYTETrack’s key idea).
* Tune only a few params (`conf_high`, `conf_low`, `match_thresh`, `track_buffer`).
* Output is a MOT-style text file with **track IDs** and boxes per frame.

> Reliable tracking is important so the temporal helmet rule is applied to the **same rider** across frames.

---

## Violation Logic (How We Decide “No Helmet”)

For each **motorcycle track**:

1. **Extract rider head-ROI** per frame (top ~30–40% of rider/person bbox; configurable).
2. Check for **overlap** between any detected **helmet** box and the head-ROI (IoU ≥ θ).
3. Maintain a **counter**: if “no helmet overlap” persists for **K consecutive frames** (e.g., K=8–12 at 25–30 FPS), mark **violation**.
4. **Debounce** around short occlusions (helmet temporarily missing) with a small forgiveness window (e.g., allow ≤2 missed frames inside a sliding window).
5. Emit event at the first commit frame; also capture the **enter frame** when the track first became a candidate.

Tunable parameters live in `configs/module_helmet.yaml`:

```yaml
head_roi_ratio_top: 0.35     # portion of rider bbox considered "head"
helmet_iou_threshold: 0.2    # minimum IoU helmet ↔ head ROI
frames_required: 10          # K consecutive frames without helmet
grace_misses: 2              # tolerance for brief misses
min_track_len: 15            # ignore ultra-short tracks
min_speed_px_s: 2            # optional: ignore stationary mannequins/posters
```

---

## Running Inference on CCTV Footage

* Use a **fixed camera** clip (15–60 s) where motorcycles are visible.
* Export detections → run BYTETrack → run `helmet_violation.py`.
* The module will write **events** to `events/` (JSON, stills, MP4).
* Use `app/streamlit_app.py` for a simple **overlay viewer** and event table.

---

## Evidence Output (What gets saved?)

Each violation produces:

* **JSON** (`events/logs/{event_id}.json`) with timestamps, track_id, confidences, tunable params snapshot.
* **Two stills**: `*_enter.jpg` and `*_commit.jpg` (first seen vs. commit frame).
* **Short clip** (`events/clips/{event_id}.mp4`, ~5–10 s around commit).

**JSON schema (example)**

```json
{
  "event_id": "cctv01_2025-11-02_19-05-33_000423",
  "camera_id": "cctv01",
  "type": "HELMET_NON_USE",
  "track_id": 87,
  "timestamp_enter": "2025-11-02T19:05:31.900",
  "timestamp_commit": "2025-11-02T19:05:33.120",
  "frames_without_helmet": 12,
  "params": {
    "head_roi_ratio_top": 0.35,
    "helmet_iou_threshold": 0.2,
    "frames_required": 10,
    "grace_misses": 2
  },
  "artifacts": {
    "enter_img": "events/images/.._enter.jpg",
    "commit_img": "events/images/.._commit.jpg",
    "clip": "events/clips/..mp4"
  }
}
```

---

## Minimal Evaluation Plan

You don’t need a heavy benchmark; just enough to report **utility**:

1. **Val split (HELMET)**:

   * Compute **per-rider** Precision/Recall on the validation subset (treat each track as a sample; “helmet present” vs “absent”).
   * Show a small confusion matrix and 2–3 qualitative failures (e.g., cap misread as helmet).

2. **CCTV clip(s)** (your target domain):

   * Manually label **20–30 rider passes** (helmet vs no-helmet).
   * Report event-level **P/R** with the chosen K and θ; include 2 success + 2 failure evidence clips in your slide deck.

> Keep an `EVAL.md` with exact clip names, counts, and thresholds so results are reproducible.

---

## Configuration Reference

* `configs/detector_yolov8s.yaml` — image size, NMS/conf thresholds, classes.
* `configs/tracker_bytetrack.yaml` — `conf_high`, `conf_low`, `match_thresh`, `track_buffer`.
* `configs/module_helmet.yaml` — ROI ratio, IoU threshold, required frames K, grace misses, min track length.

---

## Common Failure Modes & Mitigations

* **Occlusion (pillions / umbrellas / deliveries):** raise `grace_misses`, consider a tiny **keypoint** head later for better head localization.
* **Small/blurred helmets:** increase input resolution (e.g., 960) or sharpen detector with HELMET hard examples.
* **Reflective caps / hoodies misdetected as helmets:** tighten `helmet_iou_threshold` and add **negative samples** in fine-tuning.
* **Night scenes:** enable exposure-invariant augmentation, consider a night-only fine-tune set.

---

## Ethics & Privacy Notes (PH Context)

* Store **only short windows** around flagged events; purge non-events.
* If using public CCTV, consider **blurring faces/plates** by default unless you have explicit authority to retain PII (align with the **Data Privacy Act of 2012** best practices in subsequent stages).
* Keep a **data retention** note in `README`/`EVAL.md` for presentation transparency.

---

## Roadmap

* **Add ALPR** (plate detector + LPRNet/CRNN) to tag violating riders’ vehicles.
* **Add red-light** module (stop-line + traffic light state).
* **Hard negative mining** (caps/hoods) and a small **keypoint** model for precise head ROI.
* **Attribute slices** (day/night, rain) once you have local Cebu data.

---

## References (APA)

OSF. (2020). *HELMET: Myanmar motorcycle helmet dataset (images & videos).* Open Science Framework. [https://osf.io/62ch5/](https://osf.io/62ch5/)

Ultralytics. (2023). *YOLOv8 documentation.* [https://docs.ultralytics.com/models/yolov8/](https://docs.ultralytics.com/models/yolov8/)

Zhang, Y., Sun, P., Jiang, Y., Yu, D., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-object tracking by associating every detection box. *European Conference on Computer Vision (ECCV)*. [https://arxiv.org/abs/2110.06864](https://arxiv.org/abs/2110.06864)

Wen, L., Du, D., Cai, Z., Lei, Z., Chang, M.-C., Qi, H., Lim, J., Yang, M.-H., & Lyu, S. (2020). UA-DETRAC: A new benchmark and protocol for multi-object detection and tracking. *Computer Vision and Image Understanding, 193*, 102907. [https://doi.org/10.1016/j.cviu.2019.102907](https://doi.org/10.1016/j.cviu.2019.102907)

Ge, Z., Liu, S., Wang, F., Li, Z., & Sun, J. (2021). YOLOX: Exceeding YOLO series in 2021. *arXiv preprint arXiv:2107.08430.* [https://arxiv.org/abs/2107.08430](https://arxiv.org/abs/2107.08430)

*(If you prefer YOLOX over YOLOv8, replace the YOLOv8 training script/config with YOLOX equivalents—everything else stays the same.)*
