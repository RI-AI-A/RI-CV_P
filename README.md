# 🎥 Retail AI — Computer Vision Service (MVP v1)

Computer Vision service for the AI-Driven Retail Decision Support System.

---

## 🚀 Overview

This CV service:

- Uses YOLOv8 for person detection
- Tracks customers across frames
- Detects ROI (Region of Interest) interactions
- Calculates dwell time
- Sends structured events to the Backend API

> In this project, "branch" means **shelf / in-store zone**, not a physical store branch.

---

## 🏗 Architecture (MVP)

Video Stream  
      ↓  
YOLO Detection  
      ↓  
Object Tracking  
      ↓  
ROI Logic  
      ↓  
Event Builder  
      ↓  
FastAPI Backend  

---

## ⚙️ Tech Stack

- Python
- YOLOv8 (Ultralytics)
- OpenCV
- Shapely (ROI geometry)
- httpx (API client)

---

## 📦 Event Flow

When a tracked customer:

- Enters an ROI → `action_type = "entered"`
- Passes through a line ROI → `action_type = "passed"`

The CV service sends a POST request to:

```
POST /api/v1/events
```

Example event payload:

```json
{
  "customer_id": "uuid",
  "branch_id": "shelf_zone_1",
  "enter_time": "2026-02-12T20:00:00Z",
  "exit_time": null,
  "action_type": "entered",
  "camera_id": "camera_001",
  "roi_id": "roi_1",
  "track_id": 1,
  "dwell_time_seconds": null,
  "confidence_avg": 0.91,
  "frame_time": "2026-02-12T20:00:00Z"
}
```

---

# 🔧 Local Setup Guide

## 1️⃣ Clone Repository

```bash
git clone https://github.com/RI-AI-A/cv_service_v1.git
cd cv_service_v1
```

---

## 2️⃣ Create Virtual Environment

### Windows (PowerShell)

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Configure Environment Variables

Set the backend connection and video source.

### Windows (PowerShell)

```bash
$env:API_BASE_URL    = "http://127.0.0.1:8000"
$env:CV_VIDEO_SOURCE = ".\data\retail_sample.mp4"
$env:CV_BRANCH_ID    = "shelf_zone_1"
$env:CV_VISUALIZE    = "false"
```

### macOS / Linux

```bash
export API_BASE_URL="http://127.0.0.1:8000"
export CV_VIDEO_SOURCE="./data/retail_sample.mp4"
export CV_BRANCH_ID="shelf_zone_1"
export CV_VISUALIZE="false"
```

---

## 5️⃣ Run the Stream Processor

```bash
python -m cv_service.stream_processor
```

You should see logs like:

```
YOLO model loaded successfully
Stream processor initialized
Event posted successfully
```

---

# 📐 ROI Configuration

ROIs can be defined as:

- Polygon ROI (zone detection)
- Line ROI (crossing detection)

Example polygon ROI:

```python
{
  "type": "polygon",
  "id": "roi_1",
  "points": [(100,100), (400,100), (400,400), (100,400)]
}
```

---

# 🔄 Integration Requirements

Backend must be running:

```
http://127.0.0.1:8000
```

Required backend endpoint:

```
POST /api/v1/events
```

---

# 🧠 Roadmap

Next improvements:

- Multi-camera support
- Batch event posting
- Re-identification across cameras
- Performance optimization
- Real-time dashboard integration

---

# 👨‍💻 Version

CV Service MVP v1  
Status: Stable — Detection + Tracking + ROI + Backend integration working.
