import cv2
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# LOW-LIGHT ENHANCEMENT
# ─────────────────────────────────────────────────────────────────────────────

def adjust_gamma(image, gamma=1.6):
    """Brighten a dark grayscale image with gamma correction (γ > 1 = brighter)."""
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(image, table)

def enhance_frame(gray):
    """
    CLAHE + gamma boost so face / eye detection works reliably at night.
    Always applied so behaviour is consistent across lighting conditions.
    """
    clahe    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    enhanced = adjust_gamma(enhanced, gamma=1.6)
    return enhanced


# ─────────────────────────────────────────────────────────────────────────────
# FACE ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class FaceAnalyzer:
    """
    Detects a face and returns 68-point landmarks.

    Detection strategy (cascaded, handles cap / scarf / partial occlusion):
      1. haarcascade_frontalface_alt2  – best tolerance for partial occlusion
      2. haarcascade_frontalface_default – reliable fallback
      3. Direct eye detection          – when BOTH cascades miss (cap pulled low,
                                         scarf over chin, very dark) we still locate
                                         the eyes and synthesise a face bounding box
                                         so landmark fitting can proceed.

    Landmark smoothing:
      Averages the last 3 landmark frames to kill single-frame jitter – the
      primary cause of false "eyes closed" EAR readings.
    """

    # LBF 68-point landmark index groups
    LEFT_EYE_IDX   = [36, 37, 38, 39, 40, 41]
    RIGHT_EYE_IDX  = [42, 43, 44, 45, 46, 47]
    MOUTH_IDX      = [60, 64, 62, 66]          # inner lip corners + top/bottom
    POSE_IDX       = [30, 8, 36, 45, 48, 54]  # nose tip, chin, eye corners, mouth corners

    _SMOOTH_N      = 6   # landmark averaging window (frames)

    def __init__(self):
        # ── Face detectors ──────────────────────────────────────────────────
        self._face_alt2 = cv2.CascadeClassifier(
            'models/haarcascade_frontalface_alt2.xml')        # partial-occlusion tolerant
        self._face_def  = cv2.CascadeClassifier(
            'models/haarcascade_frontalface_default.xml')     # reliable general purpose

        # ── Eye detectors (fallback when face box not found) ─────────────
        self._eye_left  = cv2.CascadeClassifier(
            'models/haarcascade_lefteye_2splits.xml')
        self._eye_right = cv2.CascadeClassifier(
            'models/haarcascade_righteye_2splits.xml')

        # ── LBF 68-point landmark model ───────────────────────────────────
        self._lbf = cv2.face.createFacemarkLBF()
        self._lbf.loadModel('models/lbfmodel.yaml')

        # ── Landmark smoothing buffer ─────────────────────────────────────
        self._lm_buf = []   # list of raw landmark arrays (last _SMOOTH_N frames)

        # ── Last known face box (used when detection temporarily fails) ───
        self._last_box = None
        self._box_ttl  = 0   # "time-to-live": frames we keep using the stale box

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def process_frame(self, frame):
        """
        Returns a dict with eye/mouth/pose landmark lists and the face box,
        or None if no usable data could be extracted.

        Keys: 'left_eye', 'right_eye', 'mouth', 'pose_points', 'face_box',
              'eye_fallback' (True when we located eyes without a face cascade).
        """
        gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = enhance_frame(gray)

        face_box, eye_fallback = self._detect_face(enhanced, frame.shape)

        if face_box is None:
            # Total failure – clear buffer and give up
            self._lm_buf.clear()
            self._last_box = None
            return None

        # Remember this box for potential re-use next frame
        self._last_box = face_box
        self._box_ttl  = 6   # allow up to 6 frames of re-use

        bboxes = np.array([face_box])
        ok, lm_coll = self._lbf.fit(enhanced, bboxes)
        if not ok or len(lm_coll) == 0:
            # Landmark fit failed but face was found – try with plain gray
            ok, lm_coll = self._lbf.fit(gray, bboxes)
            if not ok or len(lm_coll) == 0:
                self._lm_buf.clear()
                return None

        raw_lm = lm_coll[0][0]   # shape (68, 2)

        # Temporal smoothing
        self._lm_buf.append(raw_lm.copy())
        if len(self._lm_buf) > self._SMOOTH_N:
            self._lm_buf.pop(0)
        lm = np.mean(self._lm_buf, axis=0)

        def pts(indices):
            return [(int(lm[i][0]), int(lm[i][1])) for i in indices]

        return {
            "left_eye":    pts(self.LEFT_EYE_IDX),
            "right_eye":   pts(self.RIGHT_EYE_IDX),
            "mouth":       pts(self.MOUTH_IDX),
            "pose_points": pts(self.POSE_IDX),
            "face_box":    face_box,
            "eye_fallback": eye_fallback,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_face(self, enhanced, shape):
        """
        Returns (face_box_xywh, eye_fallback_flag).

        Strategy:
          1. Try alt2 cascade  (handles caps/scarves best)
          2. Try default cascade
          3. Try synthesising a face box from eye positions
          4. Re-use last known box for up to _box_ttl frames (handles momentary failures)
        """
        h, w = shape[:2]

        # ── Attempt 1: frontalface_alt2 (partial-occlusion tolerant) ──────
        box = self._best_face(self._face_alt2.detectMultiScale(
            enhanced,
            scaleFactor=1.05, minNeighbors=3, minSize=(70, 70),
            flags=cv2.CASCADE_SCALE_IMAGE
        ))
        if box is not None:
            return box, False

        # ── Attempt 2: frontalface_default ────────────────────────────────
        box = self._best_face(self._face_def.detectMultiScale(
            enhanced,
            scaleFactor=1.05, minNeighbors=3, minSize=(70, 70),
            flags=cv2.CASCADE_SCALE_IMAGE
        ))
        if box is not None:
            return box, False

        # ── Attempt 3: eye-based synthesis ────────────────────────────────
        box = self._synthesise_from_eyes(enhanced, h, w)
        if box is not None:
            return box, True

        # ── Attempt 4: stale box re-use ───────────────────────────────────
        if self._last_box is not None and self._box_ttl > 0:
            self._box_ttl -= 1
            return self._last_box, False

        return None, False

    @staticmethod
    def _best_face(faces):
        """Return the largest detected face bounding box, or None."""
        if len(faces) == 0:
            return None
        return tuple(max(faces, key=lambda r: r[2] * r[3]))

    def _synthesise_from_eyes(self, enhanced, h, w):
        """
        Locate left + right eyes independently and build a synthetic face box
        around them.  Used when a cap/scarf blocks the full-face cascade.
        The synthesised box is intentionally tall/wide so LBF can still fit.
        """
        left_eyes  = self._eye_left.detectMultiScale(
            enhanced, scaleFactor=1.1, minNeighbors=5, minSize=(25, 25))
        right_eyes = self._eye_right.detectMultiScale(
            enhanced, scaleFactor=1.1, minNeighbors=5, minSize=(25, 25))

        if len(left_eyes) == 0 or len(right_eyes) == 0:
            return None

        # Take the largest detection from each side
        lx, ly, lw, lh = max(left_eyes,  key=lambda r: r[2] * r[3])
        rx, ry, rw, rh = max(right_eyes, key=lambda r: r[2] * r[3])

        # Eye centre points
        lcx, lcy = lx + lw // 2, ly + lh // 2
        rcx, rcy = rx + rw // 2, ry + rh // 2

        # Sanity check: eyes should be roughly on the same horizontal plane
        if abs(lcy - rcy) > 40:
            return None

        # Build a bounding box:  extend 1.5× the inter-eye distance in each direction
        eye_dist   = abs(rcx - lcx)
        if eye_dist < 20:
            return None
        pad        = int(eye_dist * 0.9)
        fx         = max(0, min(lcx, rcx) - pad)
        fy         = max(0, min(lcy, rcy) - pad)
        fx2        = min(w, max(lcx, rcx) + pad)
        fy2        = min(h, max(lcy, rcy) + int(eye_dist * 1.5))
        fw, fh     = fx2 - fx, fy2 - fy

        if fw < 50 or fh < 50:
            return None

        return (fx, fy, fw, fh)
