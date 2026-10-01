import numpy as np
import cv2

def euclidean_distance(p1, p2):
    """Calculate Euclidean distance between two points"""
    return np.linalg.norm(np.array(p1) - np.array(p2))

def calculate_ear(eye_points):
    """
    Calculates Eye Aspect Ratio (EAR) given 6 points of the eye.
    Ref: Soukupova and Cech (2016)

    LBF 68-point layout for the left eye (indices 36-41):
        36 = outer corner (p1)
        37 = top-left     (p2)
        38 = top-right    (p3)
        39 = inner corner (p4)
        40 = bottom-right (p5)
        41 = bottom-left  (p6)

    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    p1, p2, p3, p4, p5, p6 = eye_points

    # Vertical distances (upper-lower pairs)
    A = euclidean_distance(p2, p6)
    B = euclidean_distance(p3, p5)

    # Horizontal distance (eye width)
    C = euclidean_distance(p1, p4)

    if C < 1e-6:          # degenerate landmark — treat as open
        return 0.35       # safe "open" value

    ear = (A + B) / (2.0 * C)
    return ear

def calculate_mar(mouth_points):
    """
    Calculates Mouth Aspect Ratio (MAR) to detect yawning given 4 inner-lip points.
    mouth_points = [left_corner, right_corner, top_center, bottom_center]
    
    If a hand covers the mouth, horizontal_dist often stays similar but 
    vertical_dist becomes extremely small or noisy.
    """
    horizontal_dist = euclidean_distance(mouth_points[0], mouth_points[1])
    vertical_dist   = euclidean_distance(mouth_points[2], mouth_points[3])

    if horizontal_dist < 5.0:  # Mouth too small/occluded to measure accurately
        return 0.0

    mar = vertical_dist / horizontal_dist
    return mar

def estimate_head_pose(landmarks_2d, image_shape):
    """
    Estimates the head pose using 2D facial landmarks and a standard 3D face model.
    Returns (pitch, yaw, roll) in degrees, or (None, None, None) on failure.
    """
    h, w = image_shape[:2]
    image_points = np.array(landmarks_2d, dtype="double")

    # Standard 3D model points (in mm, centred at nose tip)
    model_points = np.array([
        (0.0,    0.0,    0.0),       # Nose tip
        (0.0,  -330.0,  -65.0),      # Chin
        (-225.0, 170.0, -135.0),     # Left eye left corner
        ( 225.0, 170.0, -135.0),     # Right eye right corner
        (-150.0,-150.0, -125.0),     # Left mouth corner
        ( 150.0,-150.0, -125.0)      # Right mouth corner
    ])

    focal_length  = w
    center        = (w / 2.0, h / 2.0)
    camera_matrix = np.array([
        [focal_length, 0,            center[0]],
        [0,            focal_length, center[1]],
        [0,            0,            1         ]
    ], dtype="double")

    dist_coeffs = np.zeros((4, 1))   # Assuming no lens distortion

    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return None, None, None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    mat = np.hstack((rotation_matrix, translation_vector))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(mat)

    pitch = float(euler_angles[0][0])
    yaw   = float(euler_angles[1][0])
    roll  = float(euler_angles[2][0])

    return pitch, yaw, roll
