"""Pasa un video por MediaPipe (CPU, modelo local) y guarda los landmarks de cada fotograma.

    python pruebas_camara/extraer_landmarks_video.py "C:/ruta/video.mp4" pruebas_camara/video_landmarks.json
"""
import json, sys
from pathlib import Path
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision

raiz = Path(__file__).resolve().parents[1]
video, salida = Path(sys.argv[1]), Path(sys.argv[2])
det = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path=str(raiz / "00_modelos_base" / "pose_landmarker_lite.task"),
                                 delegate=mpp.BaseOptions.Delegate.CPU),
    running_mode=vision.RunningMode.VIDEO, num_poses=1,
    min_pose_detection_confidence=0.55, min_pose_presence_confidence=0.55, min_tracking_confidence=0.55))
cap = cv2.VideoCapture(str(video)); fps = cap.get(5); frames = []; i = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    r = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB)),
                             int(i * 1000 / fps))
    frames.append(None if not r.pose_landmarks else [[q.x, q.y, q.z, float(q.visibility or 0)] for q in r.pose_landmarks[0]])
    i += 1
salida.write_text(json.dumps(dict(fps=fps, frames=frames)))
print(f"{len(frames)} fotogramas, {sum(f is not None for f in frames)} con pose -> {salida}")
