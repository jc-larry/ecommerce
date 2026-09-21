# -*- coding: utf-8 -*-
"""
Generador del Documento Oficial de Análisis de Clases (BCE) para Word (.docx, .html, .md)
FashionStore - Sistemas de Información II (UAGRM)
Grupo #29
"""

import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from diagram_definitions import ALL_USE_CASES

OUTPUT_DIR = "documentacion_analisis_clases"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "imagenes")

def sanitize_filename(name):
    clean = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_table_borders(table, color="D1D5DB", sz="4"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_word_document():
    doc = Document()
    
    # Page setup (margins)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # =========================================================================
    # PORTADA / ENCABEZADO
    # =========================================================================
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_inst.add_run("UNIVERSIDAD AUTÓNOMA GABRIEL RENÉ MORENO\nFACULTAD DE INGENIERÍA EN CIENCIAS DE LA COMPUTACIÓN Y TELECOMUNICACIONES")
    r.font.name = "Calibri"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(20)
    p_title.paragraph_format.space_after = Pt(8)
    r_title = p_title.add_run("DOCUMENTACIÓN DE ANÁLISIS DE CLASES (UML 2.5+ / PUDS)\nREALIZACIÓN DE CASOS DE USO (PATRÓN BCE)")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x43, 0x38, 0xCA) # Indigo

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual (FashionStore)")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(13)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    # Info box
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(15)
    p_meta.paragraph_format.space_after = Pt(25)
    r_meta = p_meta.add_run(
        "Materia: Sistemas de Información II (Semestre 2-2026)\n"
        "Docente: MSc. Ing. Angélica Garzón Cuéllar\n"
        "Grupo: #29\n"
        "Integrantes: Condori Diaz Marilyn Esther & Larrazabal Rojas Julio Cesar"
    )
    r_meta.font.name = "Calibri"
    r_meta.font.size = Pt(10.5)
    r_meta.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    doc.add_page_break()

    # =========================================================================
    # INTRODUCCIÓN Y MARCO METODOLÓGICO
    # =========================================================================
    h1 = doc.add_heading("1. Marco Metodológico: Análisis de Clases (Patrón BCE)", level=1)
    h1.paragraph_format.space_before = Pt(10)
    h1.paragraph_format.space_after = Pt(8)

    p_intro = doc.add_paragraph()
    p_intro.paragraph_format.line_spacing = 1.15
    p_intro.add_run(
        "En el Proceso Unificado de Desarrollo de Software (PUDS), el flujo de Análisis tiene como propósito "
        "transformar la captura de requisitos (casos de uso) en una arquitectura preliminar de objetos antes de pasar "
        "al diseño técnico de implementación. Siguiendo el estándar de Robustez de Jacobson / ICONIX, cada caso de uso "
        "se descompone en tres estereotipos esenciales de clases:\n\n"
    )

    bce_items = [
        ("• Interfaz / Boundary (IU_*): ", "Representa las pantallas, formularios, grillas y diálogos mediante los cuales los actores interactúan con el sistema. Modela los controles de interfaz gráfica (+lbl_*, +txt_*, +tbl_*, +btn_*, +cmb_*) y los eventos del usuario (+abrir_*(), +confirmar_*(), etc.)."),
        ("• Control (CTR_*): ", "Encapsula la lógica de negocio, reglas de validación, cálculos tributarios y orquestación de transacciones. Son clases sin atributos de persistencia, cuyos métodos coinciden 1:1 con los servicios y endpoints de la API backend."),
        ("• Entidad (CE_*): ", "Modela la información persistente que sobrevive a la ejecución del caso de uso. Sus atributos reflejan con exactitud 1:1 el esquema relacional de la base de datos física PostgreSQL (+tabla.campo).")
    ]
    for prefix, body in bce_items:
        p_item = doc.add_paragraph()
        p_item.paragraph_format.left_indent = Inches(0.25)
        p_item.paragraph_format.space_after = Pt(4)
        r_pre = p_item.add_run(prefix)
        r_pre.bold = True
        r_pre.font.color.rgb = RGBColor(0x43, 0x38, 0xCA)
        p_item.add_run(body)

    # =========================================================================
    # DESARROLLO POR CICLOS Y CASOS DE USO
    # =========================================================================
    cycles_order = ["Ciclo 1", "Ciclo 2", "Ciclo 3"]
    cycles_titles = {
        "Ciclo 1": "2. Análisis de Clases — Ciclo 1: Infraestructura de Seguridad, Catálogo e Inventario Valorado",
        "Ciclo 2": "3. Análisis de Clases — Ciclo 2: Módulo Comercial, Ventas POS, Pagos y Facturación",
        "Ciclo 3": "4. Análisis de Clases — Ciclo 3: Reservas Omnicanal, Envíos, Vestidor Virtual IA y Notificaciones"
    }

    image_files = {f: os.path.join(IMAGES_DIR, f) for f in os.listdir(IMAGES_DIR) if f.endswith(".png")}

    for cycle in cycles_order:
        doc.add_page_break()
        h_cycle = doc.add_heading(cycles_titles[cycle], level=1)
        h_cycle.paragraph_format.space_before = Pt(12)
        h_cycle.paragraph_format.space_after = Pt(10)

        cycle_cus = [cu for cu in ALL_USE_CASES if cu["cycle"] == cycle]

        for idx, cu in enumerate(cycle_cus):
            cu_id = cu["id"]
            title = cu["title"]
            actor = cu["actor"]
            package = cu["package"]
            
            # Heading 2 for each Use Case
            h_cu = doc.add_heading(title, level=2)
            h_cu.paragraph_format.space_before = Pt(14)
            h_cu.paragraph_format.space_after = Pt(4)

            p_meta_cu = doc.add_paragraph()
            r_act = p_meta_cu.add_run(f"Actor Primario: {actor}   |   Paquete Arquitectónico: {package}")
            r_act.bold = True
            r_act.font.size = Pt(10)
            r_act.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
            p_meta_cu.paragraph_format.space_after = Pt(8)

            # Find matching image
            img_prefix = f"{cu_id}_"
            img_match = None
            for fname, fpath in image_files.items():
                if fname.startswith(img_prefix):
                    img_match = fpath
                    break
            
            if img_match and os.path.exists(img_match):
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(6)
                p_img.paragraph_format.space_after = Pt(6)
                run_img = p_img.add_run()
                run_img.add_picture(img_match, width=Inches(6.6))
                
                # Image caption
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_cap = p_cap.add_run(f"Figura: Diagrama de Análisis de Clases (BCE) — {title}")
                r_cap.font.size = Pt(8.5)
                r_cap.font.italic = True
                r_cap.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
                p_cap.paragraph_format.space_after = Pt(8)

            # Table of Participants & Responsibilities
            p_tbl_title = doc.add_paragraph()
            r_tt = p_tbl_title.add_run("Especificación de Clases y Responsabilidades del Caso de Uso:")
            r_tt.bold = True
            r_tt.font.size = Pt(9.5)
            r_tt.font.color.rgb = RGBColor(0x1E, 0x1B, 0x4B)
            p_tbl_title.paragraph_format.space_after = Pt(3)

            table = doc.add_table(rows=1, cols=3)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            set_table_borders(table)

            # Table Header
            hdr_cells = table.rows[0].cells
            hdr_titles = ["Estereotipo", "Nombre de Clase", "Responsabilidad en el Caso de Uso"]
            col_widths = [Inches(1.3), Inches(2.2), Inches(3.3)]
            
            for c_idx, h_text in enumerate(hdr_titles):
                cell = hdr_cells[c_idx]
                cell.width = col_widths[c_idx]
                cell.text = h_text
                set_cell_background(cell, "EDE9FE") # Lavender header
                p = cell.paragraphs[0]
                p.runs[0].font.bold = True
                p.runs[0].font.size = Pt(9)
                p.runs[0].font.color.rgb = RGBColor(0x43, 0x38, 0xCA)

            # 1. Boundary Row
            row_iu = table.add_row().cells
            row_iu[0].text = "Boundary (IU)"
            row_iu[1].text = cu["boundary"]["name"]
            row_iu[2].text = f"Interfaz gráfica del actor {actor}. Captura eventos de usuario y despliega datos y alertas."
            
            # 2. Controller Row
            row_ctr = table.add_row().cells
            row_ctr[0].text = "Control (CTR)"
            row_ctr[1].text = cu["controller"]["name"]
            row_ctr[2].text = f"Orquestador de lógica del negocio. Ejecuta validaciones y coordina operaciones sobre las entidades."
            
            # 3. Entity Rows
            for ent in cu["entities"]:
                row_ent = table.add_row().cells
                row_ent[0].text = "Entity (CE)"
                row_ent[1].text = ent["name"]
                attrs_summary = ", ".join([a.split('.')[-1] for a in ent["attributes"][:4]])
                row_ent[2].text = f"Persistencia física en PostgreSQL. Mapea atributos ({attrs_summary}...) y estado transaccional."

            # Formatting cell text sizes
            for r_idx in range(1, len(table.rows)):
                row_cells = table.rows[r_idx].cells
                for c_idx, cell in enumerate(row_cells):
                    cell.width = col_widths[c_idx]
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(2)
                    for run in p.runs:
                        run.font.size = Pt(8.5)
                        run.font.name = "Calibri"

            doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Save document
    docx_path = os.path.join(OUTPUT_DIR, "ANALISIS_DE_CLASES_COMPLETO_CICLOS_1_2_3.docx")
    doc.save(docx_path)
    print("Documento Word (.docx) generado exitosamente en:", docx_path)

if __name__ == "__main__":
    build_word_document()
