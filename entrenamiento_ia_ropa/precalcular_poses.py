"""Precalcula la pose (33 landmarks) de cada persona con MediaPipe en TU PC.

Por qué existe: en Colab (Python 3.13) MediaPipe no siempre instala o detecta, y el respaldo
por segmentación tiene ~20 % de error en hombros. Aquí, donde MediaPipe sí funciona, se guarda
una vez la pose de cada imagen; el cuaderno la lee de Drive y ya no necesita MediaPipe.

Uso (desde la carpeta entrenamiento_ia_ropa):
    python precalcular_poses.py                 # cuerpos HD + personas vestidas
    python precalcular_poses.py --force         # recalcula aunque ya exista

Salida, en 06_poses_precalculadas/:
    <id>_pose.npy   arreglo float32 (33, 3) = x, y NORMALIZADOS (0-1, fracción de ancho/alto) y visibilidad 0-1;
                    el cuaderno los multiplica por el tamaño de la imagen que use
    reporte.json    cuántas se detectaron y cuáles no

El script es reanudable: si se corta, al repetirlo salta lo que ya está hecho.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


def _crear_detector(modelo: Path, umbral: float):
    import mediapipe as mp  # noqa: F401  (se importa aquí para dar un error claro)
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    opciones = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path=str(modelo),
            delegate=python.BaseOptions.Delegate.CPU,
        ),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=umbral,
        min_pose_presence_confidence=umbral,
    )
    return vision.PoseLandmarker.create_from_options(opciones)


def _listar(raiz: Path) -> list[tuple[str, Path]]:
    """(id, ruta) de los cuerpos HD y de las personas vestidas del caché."""
    encontrados: list[tuple[str, Path]] = []
    cuerpos = raiz / "01_cuerpos"
    if cuerpos.is_dir():
        for ruta in sorted(cuerpos.iterdir()):
            if ruta.suffix.lower() in EXTENSIONES and not ruta.name.endswith("_parse.png"):
                encontrados.append((f"hd_{ruta.stem}", ruta))
    cache = raiz / "04_checkpoints_modelos" / "resultados_vton_previos" / "cache"
    if cache.is_dir():
        for ruta in sorted(cache.glob("*.jpg")):
            encontrados.append((f"v_{ruta.stem}", ruta))
    return encontrados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("raiz", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--umbral", type=float, default=0.3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    raiz = args.raiz.resolve()
    modelo = raiz / "00_modelos_base" / "pose_landmarker_lite.task"
    if not modelo.is_file():
        print(f"ERROR: falta el modelo local {modelo}")
        return 2

    try:
        detector = _crear_detector(modelo, args.umbral)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: MediaPipe no se pudo iniciar: {exc}")
        return 2

    salida = raiz / "06_poses_precalculadas"
    salida.mkdir(exist_ok=True)
    reporte_ruta = salida / "reporte.json"
    previo = json.loads(reporte_ruta.read_text(encoding="utf-8")) if reporte_ruta.exists() else {}
    sin_pose: dict[str, str] = dict(previo.get("sin_pose", {}))

    imagenes = _listar(raiz)
    if not imagenes:
        print("ERROR: no se encontraron imágenes (01_cuerpos / cache).")
        return 2

    import mediapipe as mp

    hechas = nuevas = 0
    for indice, (ident, ruta) in enumerate(imagenes, 1):
        destino = salida / f"{ident}_pose.npy"
        if destino.exists() and not args.force:
            hechas += 1
            continue
        if ident in sin_pose and not args.force:
            continue
        try:
            with Image.open(ruta) as fuente:
                rgb = np.asarray(ImageOps.exif_transpose(fuente).convert("RGB"))
            resultado = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            if not resultado.pose_landmarks:
                sin_pose[ident] = "sin detección"
                continue
            puntos = resultado.pose_landmarks[0]
            arreglo = np.array(
                [[p.x, p.y, float(p.visibility or 0.0)] for p in puntos],
                dtype=np.float32,
            )
            # Escritura atómica: si se corta a mitad, no queda un .npy a medias.
            temporal = destino.with_suffix(".tmp.npy")
            np.save(temporal, arreglo)
            temporal.replace(destino)
            sin_pose.pop(ident, None)
            nuevas += 1
        except Exception as exc:  # noqa: BLE001
            sin_pose[ident] = f"error: {str(exc)[:80]}"
        if indice % 100 == 0:
            print(f"  {indice}/{len(imagenes)}")

    detector.close()
    con_pose = len(list(salida.glob("*_pose.npy")))
    reporte = {
        "total_imagenes": len(imagenes),
        "con_pose": con_pose,
        "sin_pose": sin_pose,
        "porcentaje_detectado": round(100 * con_pose / len(imagenes), 1),
        "umbral": args.umbral,
        "modelo": str(modelo.name),
    }
    reporte_ruta.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {con_pose}/{len(imagenes)} con pose ({reporte['porcentaje_detectado']} %). "
          f"Nuevas: {nuevas}. Reporte: {reporte_ruta}")
    return 0 if con_pose else 1


if __name__ == "__main__":
    sys.exit(main())
