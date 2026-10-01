import cv2
import numpy as np
import time
import threading
from collections import deque
import webbrowser
from flask import Flask, render_template, Response, jsonify
from face_analyzer import FaceAnalyzer
from metrics import calculate_ear, calculate_mar, estimate_head_pose
from alert_system import AlertSystem

# Configuration (mirrored from main.py)
PERCLOS_WINDOW   = 45
PERCLOS_ALERT    = 0.30
EAR_CLOSE_RATIO  = 0.75
EAR_HARD_FLOOR   = 0.21
MAR_THRESHOLD    = 0.55   # Slightly higher to avoid false positives from talking
MAR_FRAMES       = 15     # Consecutive frames to count as a yawn
MAR_OCCLUSION_THR = 0.12  # Below this, mouth is likely covered
SQUINT_RATIO     = 0.82   # Eye closure % during yawn relative to baseline
PITCH_THRESHOLD  = -20
YAW_THRESHOLD    = 38
POSE_FRAMES      = 25
BASELINE_FRAMES  = 90
ALERT_COOLDOWN_S = 6.0

app = Flask(__name__)

class DrowsinessDetector:
    def __init__(self):
        self.analyzer = FaceAnalyzer()
        self.alert = AlertSystem()
        self.cap = None
        self.is_running = False
        self.thread = None
        
        # State
        self.latest_frame = None
        self.status = "Stopped"
        self.perclos = 0.0
        self.ear = 0.0
        self.mar = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.is_dark = False
        self.calibrating = True
        self.calibration_progress = 0
        self.baseline_ear = None
        self.ear_samples = []
        self.alert_triggered = False
        self.alert_message = ""
        
        self.lock = threading.Lock()

    def start(self):
        if not self.is_running:
            # Try DirectShow first (most reliable on Windows), fallback to default
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                print("[WARN] CAP_DSHOW failed, trying default backend...")
                self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("[ERROR] Cannot open camera! Check if another app is using it.")
                return
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.is_running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def reset_calibration(self):
        with self.lock:
            self.calibrating = True
            self.calibration_progress = 0
            self.baseline_ear = None
            self.ear_samples = []
            self.status = "Calibrating"

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
        self.alert.stop()

    def _run(self):
        eye_closed_buf = deque(maxlen=PERCLOS_WINDOW)
        yawn_counter = 0
        pose_counter = 0
        alarm_on = False
        last_alert_time = 0.0
        prev_time = 0.0

        while self.is_running:
            success, frame = self.cap.read()
            if not success:
                time.sleep(0.1)
                continue

            now = time.time()
            fps = 1.0 / (now - prev_time) if prev_time > 0 else 0.0
            prev_time = now

            frame = cv2.flip(frame, 1)
            
            # Simple brightness check
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            is_dark = brightness < 70

            result = self.analyzer.process_frame(frame)
            
            # Temporary state variables
            current_status = "Active"
            current_alert_triggered = False
            current_alert_message = ""
            current_perclos = 0.0
            current_ear = 0.0
            current_mar = 0.0
            current_pitch = 0.0
            current_yaw = 0.0
            dynamic_thr = EAR_HARD_FLOOR

            if result:
                left_eye = result["left_eye"]
                right_eye = result["right_eye"]
                mouth = result["mouth"]
                pose_pts = result["pose_points"]
                face_box = result["face_box"]
                eye_fallback = result["eye_fallback"]

                current_ear = (calculate_ear(left_eye) + calculate_ear(right_eye)) / 2.0
                current_mar = calculate_mar(mouth)
                p, y, r = estimate_head_pose(pose_pts, frame.shape)
                current_pitch, current_yaw = p, y

                if self.calibrating:
                    if current_ear > EAR_HARD_FLOOR:
                        self.ear_samples.append(current_ear)
                    
                    progress = int(len(self.ear_samples) / BASELINE_FRAMES * 100)
                    with self.lock:
                        self.calibration_progress = progress
                        
                    if len(self.ear_samples) >= BASELINE_FRAMES:
                        self.baseline_ear = float(np.percentile(self.ear_samples, 85))
                        self.calibrating = False
                
                if self.baseline_ear is not None:
                    dynamic_thr = max(EAR_HARD_FLOOR, self.baseline_ear * EAR_CLOSE_RATIO)
                
                is_eye_closed = int(current_ear < dynamic_thr)
                eye_closed_buf.append(is_eye_closed)

                if len(eye_closed_buf) >= PERCLOS_WINDOW // 2:
                    current_perclos = sum(eye_closed_buf) / len(eye_closed_buf)
                    if current_perclos >= PERCLOS_ALERT and not self.calibrating:
                        current_alert_triggered = True
                        current_status = "Drowsy"
                        current_alert_message = "Eyes Closing Detected!"
                
                # Dynamic Squint Check: If baseline is available, use it. Otherwise fallback.
                if self.baseline_ear is not None:
                    squint_thr = self.baseline_ear * SQUINT_RATIO
                else:
                    squint_thr = 0.25 # Fallback

                # Improved Yawn Detection:
                # 1. Normal Yawn: Mouth wide open AND a slight eye squint (distinguishes from talking/singing)
                is_normal_yawn = (current_mar > MAR_THRESHOLD) and (current_ear < squint_thr)
                
                # 2. Covered Yawn: Mouth occluded AND eyes are squinting
                is_occluded = (current_mar < MAR_OCCLUSION_THR) 
                is_covered_yawn = is_occluded and (current_ear < squint_thr)
                
                is_yawning_now = is_normal_yawn or (is_covered_yawn and not self.calibrating)

                if is_yawning_now:
                    yawn_counter += 1
                    if yawn_counter >= MAR_FRAMES and not self.calibrating:
                        current_alert_triggered = True
                        current_status = "Drowsy"
                        current_alert_message = "Yawn Detected!" if not is_occluded else "Covered Yawn Detected!"
                else:
                    # Faster decay if not yawning to prevent "talking" buildup
                    yawn_counter = max(0, yawn_counter - 2)

                has_bad_pose = False
                if current_pitch is not None:
                    has_bad_pose = (current_pitch < PITCH_THRESHOLD or abs(current_yaw) > YAW_THRESHOLD)

                if has_bad_pose:
                    pose_counter += 1
                    if pose_counter >= POSE_FRAMES and not self.calibrating:
                        current_alert_triggered = True
                        current_status = "Drowsy"
                        current_alert_message = "Head Nodding Detected!"
                else:
                    pose_counter = max(0, pose_counter - 2)

                # Alert Logic
                if current_alert_triggered:
                    if now - last_alert_time >= ALERT_COOLDOWN_S:
                        self.alert.trigger()
                        alarm_on = True
                        last_alert_time = now
                else:
                    if alarm_on:
                        self.alert.stop()
                        alarm_on = False

                # Draw UI overlays on frame for the stream
                self._draw_overlay(frame, result, current_status, current_perclos, current_ear, dynamic_thr, current_mar, current_pitch, current_yaw, is_dark, fps)

            else:
                eye_closed_buf.clear()
                yawn_counter = 0
                pose_counter = 0
                if alarm_on:
                    self.alert.stop()
                    alarm_on = False
                current_status = "No Face Detected"
                self._draw_no_face(frame)

            # Update shared state
            with self.lock:
                self.latest_frame = frame
                self.status = current_status
                self.perclos = current_perclos
                self.ear = current_ear
                self.mar = current_mar
                self.pitch = current_pitch
                self.yaw = current_yaw
                self.is_dark = is_dark
                self.alert_triggered = current_alert_triggered
                self.alert_message = current_alert_message

    def _draw_overlay(self, frame, result, status, perclos, ear, thr, mar, pitch, yaw, is_dark, fps):
        # Semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (280, 160), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        color = (0, 0, 255) if status == "Drowsy" else (0, 255, 0)
        cv2.putText(frame, f"STATUS: {status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"PERCLOS: {perclos*100:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"EAR: {ear:.3f} (Thr: {thr:.3f})", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"MAR: {mar:.3f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        if pitch is not None:
            cv2.putText(frame, f"P: {pitch:.1f} Y: {yaw:.1f}", (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(frame, f"FPS: {int(fps)}", (frame.shape[1]-80, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        if is_dark:
            cv2.putText(frame, "NIGHT MODE", (frame.shape[1]-120, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Draw landmarks
        for pt in result["left_eye"] + result["right_eye"]:
            cv2.circle(frame, pt, 1, (0, 255, 255), -1)
        for pt in result["mouth"]:
            cv2.circle(frame, pt, 1, (255, 0, 255), -1)
        
        x, y, w, h = result["face_box"]
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

    def _draw_no_face(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (280, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.putText(frame, "NO FACE DETECTED", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

detector = DrowsinessDetector()

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    while True:
        # Check without holding the lock to avoid starving the camera thread
        with detector.lock:
            frame_data = detector.latest_frame
        if frame_data is None:
            time.sleep(0.05)
            continue
        ret, buffer = cv2.imencode('.jpg', frame_data)
        if not ret:
            time.sleep(0.05)
            continue
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.033)  # ~30fps cap to reduce CPU load

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def get_status():
    with detector.lock:
        return jsonify({
            "status": detector.status,
            "perclos": detector.perclos,
            "ear": detector.ear,
            "mar": detector.mar,
            "pitch": detector.pitch,
            "yaw": detector.yaw,
            "is_dark": detector.is_dark,
            "calibrating": detector.calibrating,
            "calibration_progress": detector.calibration_progress,
            "alert_triggered": detector.alert_triggered,
            "alert_message": detector.alert_message
        })

@app.route('/start')
def start_detector():
    detector.start()
    return jsonify({"result": "started"})

@app.route('/calibrate')
def calibrate_detector():
    detector.reset_calibration()
    return jsonify({"result": "calibration_reset"})

@app.route('/stop')
def stop_detector():
    detector.stop()
    return jsonify({"result": "stopped"})

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8000")

if __name__ == '__main__':
    detector.start()
    # Open browser after 1.5 seconds to ensure server is up
    threading.Timer(1.5, open_browser).start()
    app.run(host='0.0.0.0', port=8000, debug=True)
