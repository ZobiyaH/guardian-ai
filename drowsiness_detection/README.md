# Real-Time Driver Drowsiness Detection System

## Abstract
This project implements a real-time, non-intrusive safety system that monitors a driver's state using a standard web camera. The system tracks 68 facial landmarks using **OpenCV's Local Binary Features (LBF)** to detect eyelid closures, yawning, and head posture changes indicating exhaustion.

## Features & Mathematical Models
- **Eye Aspect Ratio (EAR):** Computes a scalar value using the 2D Euclidean distance of 6 specific eye landmarks. Drops significantly below `0.22` when a driver's eyes are actually closed (protects against false positives from regular blinks).
- **Mouth Aspect Ratio (MAR):** Computes the openness of the mouth across the vertical axis against the horizontal axis. Detects yawning when exceeding `0.6`.
- **Head Pose Estimation:** Utilizes `cv2.solvePnP` coupled with a standard 3D generic facial model to derive the pitch and yaw of the driver's head. Generates an alert if the user nods off or looks away excessively.
- **Micro-threading Audio Alerts:** Triggers consecutive, high-frequency auditory beeps via Windows' `winsound` interface on an independent thread, maintaining continuous 30 FPS visual processing without bottlenecking.

## Prerequisites
- Python 3.10+ (Fully supports Python 3.13)
- A working Web Camera
- Windows OS (for `winsound`, otherwise the alert logic needs a PyGame port for macOS/Linux)

## Installation Guide
1. Ensure Python dependencies are satisfied:
   ```bash
   pip install -r requirements.txt
   ```
2. The code will automatically load `models/lbfmodel.yaml` and the Haar cascade. (If you cloned without models, run `python download_models.py` first).
3. Run the application:
   ```bash
   python main.py
   ```
4. To exit the application, simply press the **ESC** key while the video window is focused.

## Trade-offs: OpenCV LBF Tracker
This system uses OpenCV's `cv2.face` module instead of older Dlib models or MediaPipe. It is highly efficient and skips the need for complicated C++ Build Tools (CMake) on Windows, while also maintaining robust support for modern Python releases like Python 3.13 natively out of the box!
