"""Valida el paquete FashionStore antes de consumir GPU en Colab."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
UPPER_BODY_CATEGORIES = {
    "Blusas",
    "Camisas",
    "Camisetas - T-Shirts",
    "Chaquetas - Chamarras",
    "Sueteres y Tejidos",
    "Suéteres y Tejidos",
    "Tops - Crop Tops",
}


def image_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_images(paths: list[Path], root: Path) -> tuple[list[dict], list[str], dict[str, list[str]]]:
    details: list[dict] = []
    invalid: list[str] = []
    hashes: dict[str, list[str]] = defaultdict(list)

    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
                mode = image.mode
            details.append({"path": relative, "width": width, "height": height, "mode": mode})
            hashes[sha256(path)].append(relative)
        except Exception as exc:
            invalid.append(f"{relative}: {exc}")

    duplicates = {key: values for key, values in hashes.items() if len(values) > 1}
    return details, invalid, duplicates


def read_catalog_metadata(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def paired_counts(root: Path) -> dict[str, int]:
    paired_root = root / "dataset_pareado"
    counts: dict[str, int] = {}
    for split in ("train", "val", "test"):
        split_dir = paired_root / split
        manifests = list(split_dir.rglob("metadata.json")) if split_dir.is_dir() else []
        counts[split] = len(manifests)
    return counts


def build_report(root: Path) -> dict:
    bodies_dir = root / "01_cuerpos"
    garments_dir = root / "02_prendas"
    body_paths = image_files(bodies_dir)
    garment_paths = image_files(garments_dir)
    details, invalid, duplicates = inspect_images(body_paths + garment_paths, root)

    metadata = read_catalog_metadata(root / "dataset_metadata.csv")
    actual_relative = {
        path.relative_to(garments_dir).as_posix() for path in garment_paths
    }
    metadata_relative = {
        row.get("relative_path", "").replace("\\", "/").strip() for row in metadata
        if row.get("relative_path", "").strip()
    }
    category_counts = Counter(
        path.relative_to(garments_dir).parts[0]
        for path in garment_paths
        if len(path.relative_to(garments_dir).parts) > 1
    )
    upper_count = sum(category_counts[name] for name in UPPER_BODY_CATEGORIES)
    paired = paired_counts(root)

    errors = list(invalid)
    if not body_paths:
        errors.append("No se encontraron imagenes en 01_cuerpos.")
    if not garment_paths:
        errors.append("No se encontraron imagenes en 02_prendas.")
    if not metadata:
        errors.append("Falta dataset_metadata.csv o no contiene filas.")
    missing_files = sorted(metadata_relative - actual_relative)
    missing_metadata = sorted(actual_relative - metadata_relative)
    if missing_files:
        errors.append(f"Hay {len(missing_files)} rutas de metadatos sin archivo.")
    if missing_metadata:
        errors.append(f"Hay {len(missing_metadata)} prendas sin fila de metadatos.")

    thresholds = {"train": 500, "val": 50, "test": 50}
    paired_ready = all(paired[name] >= minimum for name, minimum in thresholds.items())
    catalog_ready = not errors and len(body_paths) >= 5 and upper_count >= 10

    return {
        "root": str(root.resolve()),
        "summary": {
            "bodies": len(body_paths),
            "garments": len(garment_paths),
            "upper_body_garments": upper_count,
            "metadata_rows": len(metadata),
            "invalid_images": len(invalid),
            "duplicate_groups": len(duplicates),
            "paired_samples": paired,
        },
        "category_counts": dict(sorted(category_counts.items())),
        "metadata": {
            "missing_files": missing_files,
            "files_without_metadata": missing_metadata,
        },
        "duplicates": list(duplicates.values()),
        "errors": errors,
        "status": {
            "catalog_and_geometry_pilot_ready": catalog_ready,
            "supervised_vton_training_ready": catalog_ready and paired_ready,
        },
        "decision": (
            "LISTO PARA FINE-TUNING SUPERVISADO"
            if catalog_ready and paired_ready
            else "NO INICIAR FINE-TUNING: falta dataset pareado o hay errores"
        ),
        "image_details": details,
    }


def markdown_report(report: dict) -> str:
    summary = report["summary"]
    status = report["status"]
    paired = summary["paired_samples"]
    lines = [
        "# Reporte de validacion VTON",
        "",
        f"**Decision:** {report['decision']}",
        "",
        f"- Cuerpos: {summary['bodies']}",
        f"- Prendas: {summary['garments']}",
        f"- Prendas de torso: {summary['upper_body_garments']}",
        f"- Filas de metadatos: {summary['metadata_rows']}",
        f"- Imagenes invalidas: {summary['invalid_images']}",
        f"- Grupos duplicados: {summary['duplicate_groups']}",
        f"- Pares train/val/test: {paired['train']}/{paired['val']}/{paired['test']}",
        f"- Piloto geometrico listo: {'si' if status['catalog_and_geometry_pilot_ready'] else 'no'}",
        f"- Fine-tuning supervisado listo: {'si' if status['supervised_vton_training_ready'] else 'no'}",
        "",
        "## Errores",
        "",
    ]
    lines.extend(f"- {item}" for item in report["errors"] or ["Ninguno en los archivos actuales."])
    lines.extend(["", "## Prendas por categoria", ""])
    lines.extend(f"- {name}: {count}" for name, count in report["category_counts"].items())
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--strict", action="store_true", help="Devuelve error si el fine-tuning no esta listo.")
    args = parser.parse_args()

    root = args.root.resolve()
    report = build_report(root)
    output_dir = root / "05_reportes"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validacion_dataset.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "VALIDACION_DATASET.md").write_text(markdown_report(report), encoding="utf-8")

    visible = {
        "summary": report["summary"],
        "status": report["status"],
        "decision": report["decision"],
    }
    print(json.dumps(visible, ensure_ascii=False, indent=2))
    return 1 if args.strict and not report["status"]["supervised_vton_training_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
