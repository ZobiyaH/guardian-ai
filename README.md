```markdown
# Guardian AI — Real-Time Driver Drowsiness Detection System

**Guardian AI** is an intelligent, low-latency computer vision system designed to prevent driver fatigue accidents. Running locally at 30+ FPS, it processes video streams in real time using 68-point facial landmark alignment, mathematical geometric models (EAR, MAR), and head pose tracking to deliver immediate visual and auditory alerts.

---

## 📸 Core Features

- **Real-Time Facial Landmark Tracking:** Utilizes OpenCV's LBF Facemark model (`lbfmodel.yaml`) to track 68 keypoints on the driver's face.
- **Mathematical Telemetry Engine:**
  - **Eye Aspect Ratio (EAR):** Tracks eye closure durations to detect micro-sleeps and blinks.
  - **Mouth Aspect Ratio (MAR):** Detects yawns and prolonged mouth opening.
- **Dynamic Calibration & Thresholding:** Filters out short natural blinks using rolling-window smoothing.
- **Audio & Visual Alerting:** Triggered audio warnings and live overlay cues during detected risk conditions.
- **Flask Monitoring Dashboard:** Asynchronous web dashboard to view live processing feeds and continuous telemetry.

---

## 📁 Repository Structure

```text
drowsiness_detection/
├── models/
│   ├── haarcascade_eye.xml
│   ├── haarcascade_frontalface_alt2.xml
│   ├── haarcascade_frontalface_default.xml
│   ├── haarcascade_lefteye_2splits.xml
│   ├── haarcascade_righteye_2splits.xml
│   └── lbfmodel.yaml
├── static/
│   ├── css/
│   └── js/
├── templates/
│   └── index.html
├── alert_system.py       # Audio and visual alert handler
├── app.py                 # Flask web interface server
├── download_models.py     # Script to auto-fetch pre-trained models
├── face_analyzer.py      # Facial detection & landmark processing pipeline
├── generate_docs.py      # Automated documentation engine
├── main.py                # Standalone CLI / OpenCV local application execution
├── metrics.py             # Geometric algorithms (EAR, MAR computation)
├── requirements.txt       # Python dependencies
└── README.md

```

---

## ⚙️ Core Architecture & Pipeline

1. **Face Detection (`face_analyzer.py`):** Cascades identify spatial bounding regions.
2. **Landmark Extraction (`models/lbfmodel.yaml`):** Tracks 68 2D coordinates across ocular and oral points.
3. **Metric Calculation (`metrics.py`):**
* $$\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \|p_1 - p_4\|}$$


* $$\text{MAR} = \frac{\|p_{51} - p_{59}\| + \|p_{53} - p_{57}\|}{2 \|p_{49} - p_{55}\|}$$




4. **Alert System (`alert_system.py`):** Evaluates consecutive frame windows to flag drowsiness vs. normal eye activity.

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.8 or higher
* Webcam / Video input device

### 2. Installation

Clone the repository and install required packages:

```bash
git clone [https://github.com/ZobiyaH/Guardian-AI.git](https://github.com/ZobiyaH/Guardian-AI.git)
cd drowsiness_detection
pip install -r requirements.txt

```

### 3. Download Models

If pre-trained cascade files or `lbfmodel.yaml` are missing, run the utility script:

```bash
python download_models.py

```

---

## 💻 Running the Application

### Option A: Run Flask Web Dashboard

```bash
python app.py

```

Open your browser and navigate to `http://127.0.0.1:5000`.

### Option B: Run Standalone Local Desktop App

```bash
python main.py

```

Press `q` to terminate the application video loop.

---

## 🛠️ Tech Stack

* **Language:** Python
* **Computer Vision:** OpenCV, LBF Facemark Model, Haar Cascades
* **Math & Signal Processing:** NumPy, SciPy
* **Web Framework:** Flask, HTML5/CSS3, JavaScript

```

<FollowUp>
<Suggest>Would you like me to generate a matching sample `requirements.txt` file for this repository?</Suggest>
<Suggest>Would you like me to draft a high-impact GitHub repository bio and project summary tags for this project?</Suggest>
</FollowUp>

```
