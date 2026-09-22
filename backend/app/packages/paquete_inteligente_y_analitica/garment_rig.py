"""Rig de prenda para el vestidor virtual en vivo (CU32).

El probador en vivo no puede pedir al servidor una imagen por fotograma: un motor de
difusión tarda segundos y una llamada de red por frame arruina el seguimiento. Lo que sí
puede hacerse una sola vez, y cachear, es **medir** la prenda: recortarla del fondo y
averiguar dónde están de verdad su costura de hombro, su cintura, su bajo y sus mangas.

Con ese "rig" el cliente (web o móvil) deforma el recorte sobre los landmarks de pose en
cada fotograma sin tocar la red. Antes, tanto la web como el móvil anclaban la prenda a
fracciones fijas de la imagen (0.25, 0.75, 0.92...), y por eso una blusa con mucho aire
alrededor o una chaqueta con mangas abiertas salía descuadrada.

Todas las coordenadas del rig son fracciones [0..1] **del recorte ya ajustado a su caja**,
no de la foto original: el cliente ya no tiene que adivinar los márgenes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

from PIL import Image

from app.packages.paquete_inteligente_y_analitica.vton_service import VirtualTryonAIService

logger = logging.getLogger(__name__)

# Subir esta versión invalida todos los rigs en caché (cambio de criterio de medición).
RIG_VERSION = "4"

# Número de filas del perfil del torso. 18 da una malla suficientemente densa para que la
# prenda acompañe inclinaciones y giros sin que el cliente tenga que interpolar mucho.
TORSO_ROWS = 18

_BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
RIGS_DIR = os.path.join(_BACKEND_DIR, "uploads", "rigs")


def _source_fingerprint(source: str) -> str:
    """Huella de la imagen de origen, para invalidar la caché si la foto cambia."""
    clean = source.lstrip("/\\")
    candidates = [
        os.path.join(_BACKEND_DIR, clean),
        os.path.join(_BACKEND_DIR, "uploads",
                     clean.replace("uploads/", "").replace("uploads\\", "")),
    ]
    for path in candidates:
        if os.path.isfile(path):
            stat = os.stat(path)
            return f"{stat.st_size}-{int(stat.st_mtime)}"
    return "remote"


def _cache_key(product_id: int, source: str) -> str:
    raw = f"{RIG_VERSION}|{product_id}|{source}|{_source_fingerprint(source)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def classify_kind(category_name: str, product_name: str) -> str:
    """Superior, inferior o prenda de una pieza, a partir del catálogo."""
    haystack = f"{category_name or ''} {product_name or ''}".lower()
    if any(token in haystack for token in (
        "vestido", "dress", "enterizo", "mono", "romper", "jumpsuit", "one piece", "kaftan",
    )):
        return "dress"
    if any(token in haystack for token in (
        "pantal", "jean", "mezclilla", "falda", "skirt", "short", "bermuda", "legging",
        "palazzo", "trouser", "pants",
    )):
        return "bottom"
    if any(token in haystack for token in (
        "chaqueta", "chamarra", "abrigo", "blazer", "saco", "cardigan", "jacket", "coat",
    )):
        return "outer"
    return "top"


def classify_sleeve(sleeve_length: str, product_name: str, measured_has_sleeves: bool) -> str:
    """Largo de manga: primero el dato del catálogo, y la medición como desempate.

    El campo `sleeve_length` del producto es la fuente fiable; adivinar por el nombre
    acertaba poco. La medición sobre el alfa sólo se usa cuando el catálogo calla, o para
    degradar a 'none' una prenda que el catálogo declara con manga pero cuyo recorte no
    muestra ninguna (fotos de producto dobladas, por ejemplo).
    """
    normalized = (sleeve_length or "").lower().strip()
    declared: Optional[str] = None
    if normalized and normalized != "n/a":
        if "larga" in normalized or "long" in normalized:
            declared = "long"
        elif "sin mangas" in normalized or "sleeveless" in normalized:
            declared = "short" if "cap" in normalized else "none"
        elif "corta" in normalized or "short" in normalized or "cap" in normalized:
            declared = "short"

    if declared is None:
        text = (product_name or "").lower()
        if any(t in text for t in ("chaqueta", "chamarra", "abrigo", "sueter", "camisa", "blazer")):
            declared = "long"
        elif any(t in text for t in ("top", "crop", "tirantes", "bividi", "halter")):
            declared = "none"
        else:
            declared = "short" if measured_has_sleeves else "none"

    if declared != "none" and not measured_has_sleeves:
        return "none"
    return declared


def _torso_rows(center, torso_half, width: int, height: int,
                top_row: int, bottom_row: int) -> List[Dict[str, float]]:
    """Muestrea el perfil del torso en filas normalizadas.

    Cada fila lleva su altura, el centro de la prenda y el semiancho **sin manga**: el
    cliente convierte eso en dos vértices (izquierdo y derecho) y arma una malla de
    triángulos. Al ir el semiancho medido fila a fila, una prenda acampanada, un peplum o
    una blusa entallada conservan su silueta al deformarse sobre el cuerpo.
    """
    rows: List[Dict[str, float]] = []
    span = max(1, bottom_row - top_row)
    for index in range(TORSO_ROWS):
        fraction = index / (TORSO_ROWS - 1)
        row = max(0, min(height - 1, int(round(top_row + fraction * span))))
        rows.append({
            "y": round(row / height, 5),
            "cx": round(float(center[row]) / width, 5),
            "half": round(float(torso_half[row]) / width, 5),
        })
    return rows


def _sleeve_boxes(center, half, torso_half, width: int, height: int,
                  top_row: int, sleeve_end_row: int) -> Optional[Dict[str, Any]]:
    """Caja que ocupa cada manga dentro del recorte, a ambos lados del torso.

    La manga de una foto de producto sale en diagonal hacia fuera. El cliente la reproyecta
    sobre el eje hombro→codo→muñeca, así que lo único que necesita del rig es qué trozo de
    la imagen es manga: todo lo que sobresale del ancho de torso por cada lado.
    """
    end_row = max(top_row + 2, min(height - 1, sleeve_end_row))

    left_x0, left_x1 = float(width), 0.0
    right_x0, right_x1 = float(width), 0.0
    for row in range(top_row, end_row + 1):
        outer_left = float(center[row] - half[row])
        inner_left = float(center[row] - torso_half[row])
        outer_right = float(center[row] + half[row])
        inner_right = float(center[row] + torso_half[row])
        if inner_left - outer_left > 1.0:
            left_x0 = min(left_x0, outer_left)
            left_x1 = max(left_x1, inner_left)
        if outer_right - inner_right > 1.0:
            right_x0 = min(right_x0, inner_right)
            right_x1 = max(right_x1, outer_right)

    if left_x1 <= left_x0 or right_x1 <= right_x0:
        return None

    return {
        "y0": round(top_row / height, 5),
        "y1": round(end_row / height, 5),
        "left": {"x0": round(max(0.0, left_x0) / width, 5),
                 "x1": round(left_x1 / width, 5)},
        "right": {"x0": round(right_x0 / width, 5),
                  "x1": round(min(float(width), right_x1) / width, 5)},
    }


def _measure_chest_half(half, shoulder_row: int, bottom_row: int, sleeve_end_row: int,
                        has_sleeves: bool, torso_reference: float) -> float:
    """Semiancho de la prenda a la altura del PECHO, que es la referencia de escala.

    La escala no puede anclarse al hombro: `shoulder_row` cae al 5 % del alto, o sea sobre
    el cuello o la solapa, donde la prenda es mucho más estrecha. Pero tampoco sirve el
    ancho que calcula `_split_torso_and_sleeves`, que se mide al 45 % del alto: en una
    blusa entallada o con peplum esa altura es la **cintura**, la parte más estrecha de la
    prenda, y tomarla por pecho hacía que la prenda se dibujase ensanchada sobre el cuerpo.

    El pecho de una prenda está justo por debajo de la sisa: ahí ya no hay manga que sume
    ancho y el cuerpo de la prenda está en su medida real. Se promedia una banda estrecha
    para no depender de una sola fila del recorte.
    """
    import numpy as np

    span = max(4, bottom_row - shoulder_row)
    probe = sleeve_end_row if has_sleeves else int(shoulder_row + span * 0.15)
    probe = max(shoulder_row, min(bottom_row - 1, probe))
    band_end = min(bottom_row, probe + max(2, int(span * 0.08)))
    band = half[probe:band_end + 1]
    if band.size == 0:
        return max(1.0, torso_reference)
    return max(1.0, float(np.median(band)))


def _bottom_rig(center, half, width: int, height: int,
                top_row: int, bottom_row: int) -> Dict[str, Any]:
    """Perfil para prendas inferiores: cintura, tiro y cada pernera por separado.

    En un pantalón no hay manga ni costura de hombro, así que se mide el ancho real de
    cintura y se busca la horcajadura (la fila donde el alfa se parte en dos piernas) para
    que el cliente pueda anclar cada pernera a su cadera y su tobillo.
    """
    span = max(1, bottom_row - top_row)
    waist_row = top_row
    hip_row = min(bottom_row, top_row + int(span * 0.18))
    # La horcajadura se estima donde el semiancho deja de crecer tras la cadera.
    crotch_row = min(bottom_row, top_row + int(span * 0.34))
    return {
        "waist": {
            "y": round(waist_row / height, 5),
            "cx": round(float(center[waist_row]) / width, 5),
            "half": round(float(half[waist_row]) / width, 5),
        },
        "hip": {
            "y": round(hip_row / height, 5),
            "cx": round(float(center[hip_row]) / width, 5),
            "half": round(float(half[hip_row]) / width, 5),
        },
        "crotch_y": round(crotch_row / height, 5),
        "hem": {
            "y": round(bottom_row / height, 5),
            "cx": round(float(center[bottom_row]) / width, 5),
            "half": round(float(half[bottom_row]) / width, 5),
        },
    }


def build_rig(product_id: int, image_source: str, category_name: str,
              product_name: str, sleeve_length: str,
              force: bool = False) -> Optional[Dict[str, Any]]:
    """Construye (o recupera de caché) el rig de una prenda.

    Devuelve ``None`` si la imagen no se puede cargar o el recorte no deja prenda
    medible; el cliente debe degradar a su modo estático en ese caso.
    """
    os.makedirs(RIGS_DIR, exist_ok=True)
    key = _cache_key(product_id, image_source)
    png_name = f"rig_p{product_id}_{key}.png"
    png_path = os.path.join(RIGS_DIR, png_name)
    json_path = os.path.join(RIGS_DIR, f"rig_p{product_id}_{key}.json")

    if not force and os.path.isfile(png_path) and os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as handle:
                cached = json.load(handle)
            cached["cached"] = True
            return cached
        except Exception as exc:  # caché corrupta: se regenera
            logger.warning("Rig en caché ilegible para el producto %s: %s", product_id, exc)

    source_image = VirtualTryonAIService._load_image(image_source)
    if source_image is None:
        logger.warning("No se pudo cargar la imagen '%s' del producto %s",
                       image_source[:80], product_id)
        return None

    cutout = VirtualTryonAIService._isolate_garment(source_image)
    if cutout.width < 24 or cutout.height < 24:
        return None

    profile = VirtualTryonAIService._measure_garment_profile(cutout)
    if profile is None:
        logger.warning("El recorte del producto %s no es medible", product_id)
        return None

    width, height = cutout.width, cutout.height
    center = profile["center"]
    half = profile["half_width"]
    top_row = int(profile["top_row"])
    bottom_row = int(profile["bottom_row"])
    shoulder_row = int(profile["shoulder_row"])

    kind = classify_kind(category_name, product_name)

    if kind == "bottom":
        rig: Dict[str, Any] = {
            "product_id": product_id,
            "cutout_url": f"/uploads/rigs/{png_name}",
            "width": width,
            "height": height,
            "kind": kind,
            "sleeve": "none",
            "bottom": _bottom_rig(center, half, width, height, top_row, bottom_row),
            "measured": True,
        }
    else:
        split = VirtualTryonAIService._split_torso_and_sleeves(profile)
        torso_half = split["torso_half"]
        sleeve = classify_sleeve(sleeve_length, product_name, bool(split["has_sleeves"]))
        rows = _torso_rows(center, torso_half, width, height, shoulder_row, bottom_row)

        chest_half_px = _measure_chest_half(
            half, shoulder_row, bottom_row, int(split["sleeve_end_row"]),
            bool(split["has_sleeves"]), float(split["torso_reference"]),
        )
        shoulder_half_px = max(1.0, float(torso_half[shoulder_row]))
        torso_length_px = max(1.0, float(bottom_row - shoulder_row))

        sleeves = None
        if sleeve != "none":
            sleeves = _sleeve_boxes(center, half, torso_half, width, height,
                                    top_row, int(split["sleeve_end_row"]))

        rig = {
            "product_id": product_id,
            "cutout_url": f"/uploads/rigs/{png_name}",
            "width": width,
            "height": height,
            "kind": kind,
            "sleeve": sleeve,
            "torso": {
                "rows": rows,
                "neck_y": round(top_row / height, 5),
                "shoulder_y": round(shoulder_row / height, 5),
                "chest_y": round(int(split["chest_row"]) / height, 5),
                "hem_y": round(bottom_row / height, 5),
                # Largo del torso medido en anchos de PECHO: es la magnitud que el cliente
                # necesita para saber cuánto baja del cuerpo el bajo de la prenda, y es
                # independiente de la resolución de la foto.
                "length_ratio": round(torso_length_px / (chest_half_px * 2.0), 4),
                # Semiancho de pecho del recorte: la referencia de escala. El cliente
                # calcula el pecho de la persona a partir de sus hombros y estira la
                # prenda por este factor, de modo que todas las filas del perfil
                # conservan su proporción real.
                "chest_half": round(chest_half_px / width, 5),
                "shoulder_half": round(shoulder_half_px / width, 5),
            },
            "sleeves": sleeves,
            "measured": True,
        }

    try:
        cutout.save(png_path, format="PNG")
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(rig, handle, ensure_ascii=False)
    except Exception as exc:
        logger.warning("No se pudo cachear el rig del producto %s: %s", product_id, exc)

    rig["cached"] = False
    return rig
