﻿import cv2
import numpy as np

# --------------------------------------------------------------------------------------------------
# 1) CAMERA SPECIFICATIONS (LOGITECH C900/C920)
# --------------------------------------------------------------------------------------------------

# Given specs:
focal_length_mm = 3.67               # focal length (mm)
pixel_size_mm   = 3.98e-3            # pixel size (mm; 3.98 µm = 3.98e-3 mm)
focal_length_px = focal_length_mm / pixel_size_mm  
#   => ~922.6 pixels

# Both cameras are 1920×1080 (1080p)
image_width  = 1920
image_height = 1080
cx = image_width  / 2.0
cy = image_height / 2.0

# Camera intrinsic matrix (assume zero skew, principal point at center)
K = np.array([
    [focal_length_px,             0.0, cx],
    [            0.0, focal_length_px, cy],
    [            0.0,             0.0,  1.0]
], dtype=np.float64)

# Assume negligible lens distortion (for rough depth mapping)
dist_coeffs = np.zeros((5, 1), dtype=np.float64)

# --------------------------------------------------------------------------------------------------
# 2) STEREO GEOMETRY: choose baseline = 0.20 m (≈8 in)
# --------------------------------------------------------------------------------------------------

# Place left camera at (0,0,0), right camera at (B,0,0)
baseline_m = 0.20  # meters
R = np.eye(3, dtype=np.float64)
T = np.array([ baseline_m, 0.0, 0.0 ], dtype=np.float64)  # translation from left→right

# Stereo rectify (zero disparity constraint: principal rows aligned)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
    cameraMatrix1=K, distCoeffs1=dist_coeffs,
    cameraMatrix2=K, distCoeffs2=dist_coeffs,
    imageSize=(image_width, image_height),
    R=R, T=T,
    flags=cv2.CALIB_ZERO_DISPARITY,
    alpha=0
)

# Build undistort+rectify maps for each camera
map1x, map1y = cv2.initUndistortRectifyMap(
    cameraMatrix=K, distCoeffs=dist_coeffs, R=R1, newCameraMatrix=P1,
    size=(image_width, image_height), m1type=cv2.CV_32FC1
)
map2x, map2y = cv2.initUndistortRectifyMap(
    cameraMatrix=K, distCoeffs=dist_coeffs, R=R2, newCameraMatrix=P2,
    size=(image_width, image_height), m1type=cv2.CV_32FC1
)

# --------------------------------------------------------------------------------------------------
# 3) OPEN VIDEO STREAMS (USB CAMERAS 0 and 1) AND SET RESOLUTION
# --------------------------------------------------------------------------------------------------

capL = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # left camera
capR = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # right camera

# Force both to 1080p if supported
capL.set(cv2.CAP_PROP_FRAME_WIDTH,  image_width)
capL.set(cv2.CAP_PROP_FRAME_HEIGHT, image_height)
capR.set(cv2.CAP_PROP_FRAME_WIDTH,  image_width)
capR.set(cv2.CAP_PROP_FRAME_HEIGHT, image_height)

if not capL.isOpened() or not capR.isOpened():
    print("Error: One or both cameras failed to open.")
    exit(1)

# --------------------------------------------------------------------------------------------------
# 4) CREATE THE STEREOBM ALGORITHM INSTANCE
# --------------------------------------------------------------------------------------------------

# numDisparities must be divisible by 16, blockSize odd in [5..255]
num_disparities = 16 * 5   # e.g. 80
block_size       = 15      # tune for noise vs detail

stereoBM = cv2.StereoBM_create(numDisparities=num_disparities, blockSize=block_size)

# --------------------------------------------------------------------------------------------------
# 5) MAIN LOOP: CAPTURE, RECTIFY, COMPUTE DISPARITY, REPROJECT TO 3D
# --------------------------------------------------------------------------------------------------

window_name = "Stereo 3D Mapping"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

while True:
    retL, frameL = capL.read()
    retR, frameR = capR.read()
    if not retL or not retR:
        print("Warning: Failed to grab frames.")
        break

    # Rectify both frames
    rectL = cv2.remap(frameL, map1x, map1y, interpolation=cv2.INTER_LINEAR)
    rectR = cv2.remap(frameR, map2x, map2y, interpolation=cv2.INTER_LINEAR)

    # Convert to grayscale (StereoBM works on 8-bit gray)
    grayL = cv2.cvtColor(rectL, cv2.COLOR_BGR2GRAY)
    grayR = cv2.cvtColor(rectR, cv2.COLOR_BGR2GRAY)

    # Compute disparity (16× scaling factor internally)
    disparity_16S = stereoBM.compute(grayL, grayR)  # 16S output
    disparity = disparity_16S.astype(np.float32) / 16.0  # real‐valued disparity

    # Reproject to 3D: each (x,y,disp) → (X,Y,Z) in meters
    # Q was returned by stereoRectify; reprojectImageTo3D yields X,Y,Z in same unit as T (here meters).
    points_3D = cv2.reprojectImageTo3D(disparity, Q)

    # OPTIONAL: mask out points with zero or negative disparity
    mask = disparity > disparity.min()
    out_points = points_3D[mask]

    # Normalize disparity for display (0..255) and convert to 8-bit
    disp_norm = cv2.normalize(disparity, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    disp_uint8 = np.uint8(disp_norm)

    # Show rectified left, right, and disparity
    cv2.imshow("Left Rectified",  rectL)
    cv2.imshow("Right Rectified", rectR)
    cv2.imshow("Disparity",       disp_uint8)

    # Press 'q' to quit
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

# Cleanup
capL.release()
capR.release()
cv2.destroyAllWindows()

