import cv2
import time
import os
import urllib.request
import numpy as np
from mediapipe.tasks.python.vision import pose_landmarker
from mediapipe.tasks.python.vision.core import image as mp_image
from mediapipe.tasks.python.core import base_options as base_options_lib
from mediapipe.tasks.python.vision.core import vision_task_running_mode as running_mode_lib

MODEL_PATH = "pose_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

if not os.path.exists(MODEL_PATH):
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

options = pose_landmarker.PoseLandmarkerOptions(
    base_options=base_options_lib.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=running_mode_lib.VisionTaskRunningMode.VIDEO,
    num_poses=1
)

landmarker = pose_landmarker.PoseLandmarker.create_from_options(options)
cap = cv2.VideoCapture(0)

HUNCH_THRESHOLD = 90  # pixels

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp_image.Image(mp_image.ImageFormat.SRGB, np.asarray(rgb))
    result = landmarker.detect_for_video(mp_img, int(time.time()*1000))

    posture_state = "NO PERSON"
    color = (255, 255, 255)

    if result.pose_landmarks:
        l = result.pose_landmarks[0]

        nose = l[0]
        ls = l[11]
        rs = l[12]

        ny = int(nose.y * h)
        lys = int(ls.y * h)
        rys = int(rs.y * h)

        torso_mid_y = (lys + rys) // 2
        vertical_gap = torso_mid_y - ny

        if vertical_gap < HUNCH_THRESHOLD:
            posture_state = "HUNCHING"
            color = (0, 0, 255)
        else:
            posture_state = "GOOD POSTURE"
            color = (0, 255, 0)

    cv2.putText(frame, posture_state, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow("Posture Check", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
landmarker.close()
cv2.destroyAllWindows()