# -*- coding: utf-8 -*-
"""
Motor de Renderizado Automatizado de Diagramas de Análisis de Clases (BCE)
Estilo profesional idéntico a los diagramas aprobados:
- Cajas con borde púrpura/violeta (#7c3aed), cabecera lavanda (#ede9fe), fondo pastel (#f5f3ff)
- Tipografía monoespaciada para atributos y métodos
- Stick figure UML para actores
- Flechas punteadas de dependencia (..>) con puntas abiertas/rellenas limpias
- Enlaces sólidos de asociación entre entidades
- Exportación en PNG de ultra alta resolución (200 DPI) para Microsoft Word
"""

import os
import re
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from diagram_definitions import ALL_USE_CASES

OUTPUT_DIR = os.path.join("documentacion_analisis_clases", "imagenes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def sanitize_filename(name):
    clean = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean

def draw_actor(ax, x, y, name="Actor"):
    # Head
    circle = patches.Circle((x, y + 0.35), 0.12, facecolor='white', edgecolor='#111827', lw=1.2, zorder=5)
    ax.add_patch(circle)
    # Body
    ax.plot([x, x], [y + 0.23, y - 0.1], color='#111827', lw=1.2, zorder=5)
    # Arms
    ax.plot([x - 0.2, x + 0.2], [y + 0.12, y + 0.12], color='#111827', lw=1.2, zorder=5)
    # Legs
    ax.plot([x, x - 0.18], [y - 0.1, y - 0.4], color='#111827', lw=1.2, zorder=5)
    ax.plot([x, x + 0.18], [y - 0.1, y - 0.4], color='#111827', lw=1.2, zorder=5)
    # Label multiline if needed
    lines = name.split('/')
    if len(lines) > 1:
        ax.text(x, y - 0.55, lines[0].strip(), ha='center', va='top', fontsize=8.5, fontfamily='sans-serif', color='#111827', fontweight='normal')
        ax.text(x, y - 0.78, "/ " + lines[1].strip(), ha='center', va='top', fontsize=8, fontfamily='sans-serif', color='#111827', fontweight='normal')
    else:
        ax.text(x, y - 0.55, name, ha='center', va='top', fontsize=8.5, fontfamily='sans-serif', color='#111827', fontweight='normal')

def draw_class_box(ax, x, y, width, title, attributes, methods=None):
    title_h = 0.45
    num_attr = len(attributes) if attributes else 0
    attr_h = (0.26 * num_attr + 0.15) if num_attr > 0 else 0.2
    
    num_meth = len(methods) if methods else 0
    meth_h = (0.26 * num_meth + 0.15) if num_meth > 0 else 0
    
    total_h = title_h + attr_h + meth_h
    top_y = y + total_h / 2
    bot_y = y - total_h / 2
    left_x = x - width / 2
    right_x = x + width / 2

    # Background & border
    rect = patches.Rectangle((left_x, bot_y), width, total_h, 
                             facecolor='white', edgecolor='#111827', lw=1.1, zorder=3)
    ax.add_patch(rect)
    
    # Title bar
    title_rect = patches.Rectangle((left_x, top_y - title_h), width, title_h,
                                   facecolor='#f3f4f6', edgecolor='#111827', lw=1.1, zorder=4)
    ax.add_patch(title_rect)
    
    # Title text
    ax.text(x, top_y - title_h / 2, title, ha='center', va='center', fontsize=9.5, 
            fontfamily='sans-serif', fontweight='bold', color='#111827', zorder=5)
    
    # Attributes
    curr_y = top_y - title_h - 0.14
    if attributes:
        for attr in attributes:
            ax.text(left_x + 0.12, curr_y, attr, ha='left', va='center', fontsize=8.2, 
                    fontfamily='monospace', color='#111827', zorder=5)
            curr_y -= 0.26
            
    # Methods
    if methods:
        sep_y = top_y - title_h - attr_h
        ax.plot([left_x, right_x], [sep_y, sep_y], color='#111827', lw=1.0, zorder=4)
        curr_y = sep_y - 0.14
        for m in methods:
            ax.text(left_x + 0.12, curr_y, m, ha='left', va='center', fontsize=8.2, 
                    fontfamily='monospace', color='#111827', zorder=5)
            curr_y -= 0.26
            
    return {
        "left": left_x,
        "right": right_x,
        "top": top_y,
        "bottom": bot_y,
        "center_x": x,
        "center_y": y,
        "width": width,
        "height": total_h
    }

def render_use_case_diagram(cu):
    cu_id = cu["id"]
    actor_name = cu["actor"]
    iu = cu["boundary"]
    ctr = cu["controller"]
    entities = cu["entities"]
    associations = cu.get("associations", [])

    num_entities = len(entities)
    
    # Dimensions calculation
    fig_w = 17.0
    fig_h = 8.5
    center_y = 3.9
    
    if num_entities >= 4:
        fig_w = 19.5
        fig_h = 8.9
        center_y = 4.4
    elif num_entities == 3:
        fig_h = 8.0
        center_y = 4.0

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # 1. Actor
    actor_x = 1.1
    actor_y = center_y
    draw_actor(ax, actor_x, actor_y, actor_name)

    # 2. Boundary IU_*
    iu_w = 3.8
    iu_x = 4.3
    iu_box = draw_class_box(ax, iu_x, center_y, iu_w, iu["name"], iu["attributes"], iu["methods"])

    # Line: Actor -> IU_*
    ax.plot([actor_x + 0.25, iu_box["left"]], [actor_y, actor_y], color='#111827', lw=1.1, zorder=2)

    # 3. Controller CTR_*
    ctr_w = 4.4
    ctr_x = 9.4
    ctr_box = draw_class_box(ax, ctr_x, center_y, ctr_w, ctr["name"], [], ctr["methods"])

    # Dashed arrow: IU_* -> CTR_*
    ax.annotate('', xy=(ctr_box["left"], center_y), xytext=(iu_box["right"], center_y),
                arrowprops=dict(arrowstyle="-|>", ls="--", color="#111827", lw=1.1, mutation_scale=11))

    # 4. Entities
    entity_boxes = {}
    ent_w = 3.6
    
    if num_entities == 1:
        ent_y_positions = [center_y]
        ent_x_positions = [14.6]
    elif num_entities == 2:
        ent_y_positions = [center_y + 1.8, center_y - 1.8]
        ent_x_positions = [14.6, 14.6]
    elif num_entities == 3:
        ent_y_positions = [center_y + 2.8, center_y, center_y - 2.8]
        ent_x_positions = [14.6, 14.6, 14.6]
    elif num_entities == 4:
        ent_y_positions = [center_y + 2.2, center_y - 2.2, center_y + 2.2, center_y - 2.2]
        ent_x_positions = [14.4, 14.4, 18.2, 18.2]
    else:
        # Fallback spacing
        ent_y_positions = [center_y + (i - (num_entities-1)/2)*2.2 for i in range(num_entities)]
        ent_x_positions = [14.6]*num_entities

    for i, ent in enumerate(entities):
        ex = ent_x_positions[i]
        ey = ent_y_positions[i]
        ebox = draw_class_box(ax, ex, ey, ent_w, ent["name"], ent["attributes"])
        entity_boxes[ent["name"]] = ebox
        
        # Dependency arrow from CTR to entity (if in first entity column or direct)
        if ex < 16.0:
            target_pt = (ebox["left"], ey)
            source_pt = (ctr_box["right"], center_y + (ey - center_y)*0.4)
            ax.annotate('', xy=target_pt, xytext=source_pt,
                        arrowprops=dict(arrowstyle="-|>", ls="--", color="#111827", lw=1.1, mutation_scale=11))

    # Associations between entities
    for e1_name, e2_name in associations:
        if e1_name in entity_boxes and e2_name in entity_boxes:
            b1 = entity_boxes[e1_name]
            b2 = entity_boxes[e2_name]
            
            # Decide connection orientation
            if abs(b1["center_x"] - b2["center_x"]) < 0.5:
                # Vertical connection
                if b1["center_y"] > b2["center_y"]:
                    ax.plot([b1["center_x"], b2["center_x"]], [b1["bottom"], b2["top"]], color='#111827', lw=1.1, zorder=2)
                else:
                    ax.plot([b1["center_x"], b2["center_x"]], [b1["top"], b2["bottom"]], color='#111827', lw=1.1, zorder=2)
            else:
                # Horizontal connection
                if b1["center_x"] < b2["center_x"]:
                    ax.plot([b1["right"], b2["left"]], [b1["center_y"], b2["center_y"]], color='#111827', lw=1.1, zorder=2)
                else:
                    ax.plot([b1["left"], b2["right"]], [b1["center_y"], b2["center_y"]], color='#111827', lw=1.1, zorder=2)

    ax.set_xlim(0, fig_w)
    ax.set_ylim(-0.2, fig_h)
    ax.axis('off')

    safe_name = f"{cu_id}_{sanitize_filename(title.split(':', 1)[-1].strip())}.png"
    out_file = os.path.join(OUTPUT_DIR, safe_name)
    plt.tight_layout()
    plt.savefig(out_file, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return out_file

def main():
    print(f"Iniciando renderizado masivo de {len(ALL_USE_CASES)} diagramas BCE...")
    generated = []
    for i, cu in enumerate(ALL_USE_CASES):
        out_p = render_use_case_diagram(cu)
        generated.append(out_p)
        print(f"[{i+1}/{len(ALL_USE_CASES)}] Generado: {os.path.basename(out_p)}")
    print(f"\n¡Éxito! Se generaron {len(generated)} diagramas en '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    main()
