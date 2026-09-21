# -*- coding: utf-8 -*-
"""
Generador del Documento Markdown con imágenes y tablas para Word / GitHub
FashionStore - Análisis de Clases (BCE)
"""

import os
from diagram_definitions import ALL_USE_CASES

OUTPUT_DIR = "documentacion_analisis_clases"
MD_FILE = os.path.join(OUTPUT_DIR, "ANALISIS_DE_CLASES_COMPLETO_CICLOS_1_2_3.md")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "imagenes")

def build_markdown():
    image_files = {f: os.path.join("imagenes", f) for f in os.listdir(IMAGES_DIR) if f.endswith(".png")}

    lines = []
    lines.append("# Documentación Completa de Análisis de Clases (UML 2.5+ / PUDS)")
    lines.append("## Realización de los 40 Casos de Uso mediante el Patrón BCE (Boundary - Control - Entity)\n")
    lines.append("**Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual (FashionStore)**  ")
    lines.append("**Grupo #29 — Sistemas de Información II (UAGRM - Semestre 2-2026)**  ")
    lines.append("**Integrantes:** Condori Diaz Marilyn Esther & Larrazabal Rojas Julio Cesar  ")
    lines.append("**Docente:** MSc. Ing. Angélica Garzón Cuéllar  \n")
    lines.append("---\n")

    lines.append("## 1. Fundamento Teórico y Notación del Patrón BCE\n")
    lines.append("Siguiendo el flujo de **Análisis de Casos de Uso del PUDS** y las directrices de robustez de Jacobson/ICONIX, cada caso de uso se modela con tres estereotipos fundamentales de clases:\n")
    lines.append("1. **Interfaz / Boundary (`IU_*`):** Modela la superficie de contacto con el actor (pantallas, diálogos, grillas, formularios). Contiene atributos de interfaz (`+lbl_*`, `+txt_*`, `+tbl_*`, `+cmb_*`, `+btn_*`) y métodos accionados por el usuario (`+abrir_*()`, `+confirmar_*()`, etc.).")
    lines.append("2. **Control (`CTR_*`):** Modela la lógica de negocio pura, orquestación y reglas operativas. No tiene atributos de persistencia. Sus métodos coinciden 1:1 con los servicios y endpoints de la API backend en FastAPI.")
    lines.append("3. **Entidad (`CE_*`):** Modela los datos persistentes del sistema. Sus atributos reflejan fielmente el esquema relacional de las **50 tablas en PostgreSQL** (`+tabla.campo`), manteniendo asociaciones estructurales sólidas entre entidades relacionadas.\n")
    lines.append("---\n")

    cycles = ["Ciclo 1", "Ciclo 2", "Ciclo 3"]
    cycle_descriptions = {
        "Ciclo 1": "Ciclo 1: Infraestructura de Seguridad, Catálogo e Inventario Valorado (15 Casos de Uso)",
        "Ciclo 2": "Ciclo 2: Módulo Comercial, Ventas POS, Pagos y Facturación (13 Casos de Uso)",
        "Ciclo 3": "Ciclo 3: Reservas Omnicanal, Envíos, Vestidor Virtual IA y Notificaciones (13 Casos de Uso)"
    }

    for cycle in cycles:
        lines.append(f"## 2. {cycle_descriptions[cycle]}\n")
        cycle_cus = [cu for cu in ALL_USE_CASES if cu["cycle"] == cycle]

        for cu in cycle_cus:
            cu_id = cu["id"]
            title = cu["title"]
            actor = cu["actor"]
            package = cu["package"]

            lines.append(f"### {title}")
            lines.append(f"**Actor Primario:** `{actor}` | **Paquete:** `{package}` | **Ciclo:** `{cycle}`\n")

            # Image
            img_prefix = f"{cu_id}_"
            img_rel = None
            for fname, rel_path in image_files.items():
                if fname.startswith(img_prefix):
                    img_rel = rel_path.replace("\\", "/")
                    break

            if img_rel:
                lines.append(f"![{title}]({img_rel})\n")

            # Table
            lines.append("| Estereotipo | Nombre de Clase | Responsabilidad y Atributos Principales |")
            lines.append("| :--- | :--- | :--- |")
            lines.append(f"| **Boundary (IU)** | `{cu['boundary']['name']}` | Pantalla/formulario de `{actor}`. Maneja eventos visuales y captura de parámetros. |")
            lines.append(f"| **Control (CTR)** | `{cu['controller']['name']}` | Lógica de negocio y orquestador. Coordina validaciones y transacciones de persistencia. |")
            
            for ent in cu["entities"]:
                attrs = ", ".join([a.split('.')[-1] for a in ent["attributes"][:5]])
                lines.append(f"| **Entity (CE)** | `{ent['name']}` | Persistencia física PostgreSQL. Campos: `{attrs}...` |")
            
            lines.append("\n---\n")

    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Documento Markdown generado exitosamente en:", MD_FILE)

if __name__ == "__main__":
    build_markdown()
