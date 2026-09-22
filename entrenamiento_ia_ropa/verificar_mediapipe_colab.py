"""Prueba el modelo corporal MediaPipe local antes de entrenar en Colab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def check_precomputed(root: Path) -> dict:
    """Valida 06_poses_precalculadas/ (generadas en el PC con precalcular_poses.py).

    En Colab con Python 3.13 MediaPipe puede no instalarse; no hace falta si las poses ya
    estan calculadas. Pasa si hay poses para >= 90 % de las imagenes contadas en el reporte.
    """
    folder = root / "06_poses_precalculadas"
    report = folder / "reporte.json"
    if not report.is_file():
        return {"ok": False, "error": "No hay 06_poses_precalculadas/reporte.json",
                "hint": "En tu PC ejecuta: python precalcular_poses.py y sube la carpeta a Drive."}
    data = json.loads(report.read_text(encoding="utf-8"))
    found = len(list(folder.glob("*_pose.npy")))
    total = int(data.get("total_imagenes", 0))
    return {"ok": total > 0 and found >= 0.9 * total, "source": "precalculadas",
            "poses": found, "total": total,
            "porcentaje": round(100 * found / max(1, total), 1)}


def run_check(root: Path, threshold: float) -> dict:
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except Exception as exc:
        # Sin MediaPipe (habitual en Colab con Python 3.13) se valida lo que de verdad
        # necesita el entrenamiento: las poses precalculadas.
        fallback = check_precomputed(root)
        fallback["mediapipe"] = f"no disponible: {str(exc)[:80]}"
        return fallback

    model_path = root / "00_modelos_base" / "pose_landmarker_lite.task"
    if not model_path.is_file():
        return {"ok": False, "error": f"No existe el modelo local: {model_path}"}

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path=str(model_path),
            delegate=python.BaseOptions.Delegate.CPU,
        ),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=threshold,
        min_pose_presence_confidence=threshold,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    bodies = sorted((root / "01_cuerpos").glob("*"))
    bodies = [path for path in bodies if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    results = []

    try:
        for path in bodies:
            with Image.open(path) as source:
                rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"))
            detection = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            detected = bool(detection.pose_landmarks)
            visibility = 0.0
            if detected:
                relevant = [11, 12, 23, 24]
                points = detection.pose_landmarks[0]
                visibility = sum(
                    min(float(points[index].visibility or 0), float(points[index].presence or 0))
                    for index in relevant
                ) / len(relevant)
            results.append({
                "file": path.name,
                "detected": detected,
                "torso_confidence": round(visibility, 4),
            })
    finally:
        landmarker.close()

    detected_count = sum(item["detected"] for item in results)
    minimum = max(1, int(len(results) * 0.70 + 0.999))
    return {
        "ok": bool(results) and detected_count >= minimum,
        "mediapipe_version": getattr(mp, "__version__", "unknown"),
        "delegate": "CPU",
        "threshold": threshold,
        "model": str(model_path),
        "detected": detected_count,
        "total": len(results),
        "minimum_required": minimum,
        "images": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    report = run_check(root, args.threshold)
    output = root / "05_reportes" / "verificacion_mediapipe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.strict and not report.get("ok", False) else 0


if __name__ == "__main__":
    raise SystemExit(main())
