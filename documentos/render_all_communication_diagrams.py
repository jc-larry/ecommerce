import os
import re
import subprocess
import unicodedata
from PIL import Image, ImageChops

def make_filename(cu_id, cu_title):
    clean = unicodedata.normalize('NFKD', cu_title).encode('ASCII', 'ignore').decode('ASCII')
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', clean).strip('_')
    words = clean.split('_')
    if len(words) > 7:
        clean = '_'.join(words[:7])
    return f"{cu_id}_{clean}.png"

def parse_all_40_cus():
    with open('documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md', 'r', encoding='utf-8') as f:
        text = f.read()

    sections = re.split(r'\n(?=### CU\d+:)', text)
    cus_parsed = []

    for sec in sections:
        m_h = re.match(r'### (CU\d+):\s*([^\n]+)', sec)
        if not m_h:
            continue
        cid = m_h.group(1)
        ctitle = m_h.group(2).strip()
        
        m_diag = re.search(r'`{1,3}(?:mermaid)?\s*\n(sequenceDiagram\b.*?)\n`{1,3}', sec, re.DOTALL)
        if not m_diag:
            continue
        diag = m_diag.group(1).strip()
        
        actors = []
        boundaries = []
        controllers = []
        entities = []
        externals = []
        
        for line in diag.splitlines():
            line = line.strip()
            m_act = re.match(r'^actor\s+([\w_]+)(?:\s+as\s+(.+))?$', line)
            if m_act:
                alias = m_act.group(1)
                name = (m_act.group(2) or alias).strip('"\'')
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not any(a['alias'] == alias for a in actors):
                    actors.append({'alias': alias, 'name': name})
                continue
                
            m_part = re.match(r'^participant\s+([\w_]+)(?:\s+as\s+(.+))?$', line)
            if m_part:
                alias = m_part.group(1)
                name = (m_part.group(2) or alias).strip('"\'')
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                
                if alias.startswith('IU') or 'Interfaz' in name or 'IU_' in name:
                    if not any(b['alias'] == alias for b in boundaries):
                        boundaries.append({'alias': alias, 'name': name})
                elif alias.startswith('CTR') or 'Controlador' in name or 'Service' in name or 'Servicio' in name or alias.startswith('SVC'):
                    if not any(c['alias'] == alias for c in controllers):
                        controllers.append({'alias': alias, 'name': name})
                elif alias.startswith('CE') or 'Entidad' in name or 'CE_' in name:
                    if not any(e['alias'] == alias for e in entities):
                        entities.append({'alias': alias, 'name': name})
                else:
                    if not any(x['alias'] == alias for x in externals):
                        externals.append({'alias': alias, 'name': name})
                    
        # Parse messages
        msgs = []
        for line in diag.splitlines():
            line = line.strip()
            m_m = re.match(r'^([\w_]+)\s*(-{1,2}>>[+-]?)\s*([\w_]+)\s*:\s*(.+)$', line)
            if m_m:
                src = m_m.group(1)
                arr = m_m.group(2)
                dst = m_m.group(3)
                txt = m_m.group(4).strip().strip('"\'')
                is_ret = '-->>' in arr
                msgs.append({'src': src, 'dst': dst, 'txt': txt, 'is_ret': is_ret})
                
        cus_parsed.append({
            'id': cid,
            'title': ctitle,
            'filename': make_filename(cid, ctitle),
            'actors': actors,
            'boundaries': boundaries,
            'controllers': controllers,
            'entities': entities,
            'externals': externals,
            'msgs': msgs
        })
    return cus_parsed

def generate_bce_svg(cu):
    actor = cu['actors'][0] if cu['actors'] else {'alias': 'U', 'name': 'Usuario'}
    boundaries = cu['boundaries'] if cu['boundaries'] else [{'alias': 'IU', 'name': 'IU_Principal'}]
    controllers = cu['controllers'] if cu['controllers'] else [{'alias': 'CTR', 'name': 'CTR_Gestion'}]
    entities = cu['entities'] if cu['entities'] else [{'alias': 'CE', 'name': 'CE_Datos'}]
    externals = cu['externals']

    # Right side elements: entities + externals + secondary controllers
    right_items = []
    for e in entities:
        right_items.append({'item': e, 'type': 'entity'})
    for x in externals:
        right_items.append({'item': x, 'type': 'external'})
    if len(controllers) > 1:
        for c in controllers[1:]:
            right_items.append({'item': c, 'type': 'control'})

    num_right = len(right_items)
    spacing_ent = 125 if num_right <= 3 else (110 if num_right <= 5 else 98)
    height = max(440, num_right * spacing_ent + 110)
    width = 1420
    y_center = height / 2

    # Coordinates
    x_actor = 95
    y_actor = y_center

    x_iu = 415
    y_iu = y_center

    x_ctr = 785
    y_ctr = y_center

    x_right = 1180

    # Calculate Y for right items
    right_positions = {}
    for i, r_obj in enumerate(right_items):
        y_pos = y_center + (i - (num_right - 1) / 2) * spacing_ent
        right_positions[r_obj['item']['alias']] = (x_right, y_pos, r_obj['item'], r_obj['type'])

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background-color: white; font-family: \'Segoe UI\', Arial, sans-serif;">')
    svg.append("""  <defs>
    <!-- Sombra suave para nodos BCE -->
    <filter id="shadow" x="-20%" y="-20%" width="150%" height="150%">
      <feDropShadow dx="2" dy="3" stdDeviation="3" flood-color="#000000" flood-opacity="0.22"/>
    </filter>
    
    <!-- Gradiente azul elegante para círculos BCE -->
    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#c5dcf7"/>
      <stop offset="100%" stop-color="#7faee1"/>
    </linearGradient>

    <!-- Gradiente naranja para externos -->
    <linearGradient id="extGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fed7aa"/>
      <stop offset="100%" stop-color="#fba04b"/>
    </linearGradient>

    <!-- Flecha de llamada sólida -->
    <marker id="solidArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#333333"/>
    </marker>
  </defs>""")

    # 1. ACTOR (STICK FIGURE CON CABEZA DORADA)
    act_name = actor['name']
    svg.append(f"""  <!-- ACTOR: {act_name} -->
  <g transform="translate({x_actor}, {y_actor})">
    <circle cx="0" cy="-45" r="14" fill="#fed766" stroke="#222" stroke-width="2"/>
    <line x1="0" y1="-31" x2="0" y2="15" stroke="#222" stroke-width="2"/>
    <line x1="-22" y1="-18" x2="22" y2="-18" stroke="#222" stroke-width="2"/>
    <line x1="0" y1="15" x2="-18" y2="52" stroke="#222" stroke-width="2"/>
    <line x1="0" y1="15" x2="18" y2="52" stroke="#222" stroke-width="2"/>
    <text x="0" y="75" text-anchor="middle" font-size="13.5" fill="#1e293b" font-weight="600">{act_name}</text>
  </g>""")

    # 2. BOUNDARY (IU_*)
    iu_name = boundaries[0]['name']
    svg.append(f"""  <!-- BOUNDARY: {iu_name} -->
  <g transform="translate({x_iu}, {y_iu})">
    <circle cx="0" cy="0" r="45" fill="url(#blueGrad)" stroke="#4a7eb0" stroke-width="1.8" filter="url(#shadow)"/>
    <line x1="-65" y1="-35" x2="-65" y2="35" stroke="#4a7eb0" stroke-width="2.5"/>
    <line x1="-65" y1="0" x2="-45" y2="0" stroke="#4a7eb0" stroke-width="2.5"/>
    <text x="0" y="5" text-anchor="middle" font-size="12.5" font-weight="600" fill="#1e293b">{iu_name}</text>
  </g>""")

    # 3. CONTROL (CTR_*)
    ctr_name = controllers[0]['name']
    svg.append(f"""  <!-- CONTROL: {ctr_name} -->
  <g transform="translate({x_ctr}, {y_ctr})">
    <circle cx="0" cy="0" r="45" fill="url(#blueGrad)" stroke="#4a7eb0" stroke-width="1.8" filter="url(#shadow)"/>
    <path d="M -15 -42 A 45 45 0 0 1 20 -40" fill="none" stroke="#4a7eb0" stroke-width="2.2"/>
    <path d="M 12 -48 L 22 -40 L 12 -33" fill="none" stroke="#4a7eb0" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="0" y="5" text-anchor="middle" font-size="12.5" font-weight="600" fill="#1e293b">{ctr_name}</text>
  </g>""")

    # 4. ENTITIES & RIGHT SIDE OBJECTS
    for alias, (ex, ey, item, itype) in right_positions.items():
        name = item['name']
        if itype == 'entity':
            svg.append(f"""  <!-- ENTITY: {name} -->
  <g transform="translate({ex}, {ey})">
    <circle cx="0" cy="0" r="42" fill="url(#blueGrad)" stroke="#4a7eb0" stroke-width="1.8" filter="url(#shadow)"/>
    <line x1="-34" y1="46" x2="34" y2="46" stroke="#4a7eb0" stroke-width="2.5"/>
    <text x="0" y="5" text-anchor="middle" font-size="12" font-weight="600" fill="#1e293b">{name}</text>
  </g>""")
        elif itype == 'control':
            svg.append(f"""  <!-- CONTROL 2: {name} -->
  <g transform="translate({ex}, {ey})">
    <circle cx="0" cy="0" r="42" fill="url(#blueGrad)" stroke="#4a7eb0" stroke-width="1.8" filter="url(#shadow)"/>
    <path d="M -13 -39 A 42 42 0 0 1 18 -37" fill="none" stroke="#4a7eb0" stroke-width="2.2"/>
    <path d="M 11 -45 L 20 -37 L 11 -30" fill="none" stroke="#4a7eb0" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="0" y="5" text-anchor="middle" font-size="12" font-weight="600" fill="#1e293b">{name}</text>
  </g>""")
        else: # external
            svg.append(f"""  <!-- EXTERNAL: {name} -->
  <g transform="translate({ex}, {ey})">
    <circle cx="0" cy="0" r="42" fill="url(#extGrad)" stroke="#ea580c" stroke-width="1.8" filter="url(#shadow)"/>
    <text x="0" y="5" text-anchor="middle" font-size="11.5" font-weight="600" fill="#7c2d12">{name}</text>
  </g>""")

    # 5. MESSAGES & ARROWS
    # Parse messages
    # Step 1.1: Actor -> IU
    a_alias = actor['alias']
    iu_alias = boundaries[0]['alias']
    ctr_alias = controllers[0]['alias']

    # Filter messages
    a_to_iu = [m for m in cu['msgs'] if m['src'] == a_alias and m['dst'] == iu_alias]
    iu_to_a = [m for m in cu['msgs'] if m['src'] == iu_alias and m['dst'] == a_alias]

    iu_to_c = [m for m in cu['msgs'] if m['src'] == iu_alias and m['dst'] == ctr_alias]
    c_to_iu = [m for m in cu['msgs'] if m['src'] == ctr_alias and m['dst'] == iu_alias]

    # Clean text helper
    def clean_msg(txt, prefix):
        # strip existing "1: " or "1.1: "
        cleaned = re.sub(r'^\d+(\.\d+)?:\s*', '', txt).strip()
        # limit length for visual elegance
        if len(cleaned) > 34:
            cleaned = cleaned[:32] + "..."
        return f"{prefix} {cleaned}"

    msg_1_1 = clean_msg(a_to_iu[0]['txt'] if a_to_iu else "solicitar()", "1.1")
    msg_1_2 = clean_msg(iu_to_c[0]['txt'] if iu_to_c else "procesar()", "1.2")

    # Forward: Actor -> IU (lower line)
    svg.append(f"""  <!-- 1.1 Actor -> IU -->
  <line x1="{x_actor + 35}" y1="{y_actor + 18}" x2="{x_iu - 68}" y2="{y_iu + 18}" stroke="#333333" stroke-width="1.2" marker-end="url(#solidArrow)"/>
  <rect x="{(x_actor + x_iu)/2 - 95}" y="{y_actor + 26}" width="190" height="20" fill="#f8fafc" rx="3" stroke="#cbd5e1" stroke-width="0.8"/>
  <text x="{(x_actor + x_iu)/2}" y="{y_actor + 40}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{msg_1_1}</text>""")

    # Forward: IU -> CTR (lower line)
    svg.append(f"""  <!-- 1.2 IU -> CTR -->
  <line x1="{x_iu + 47}" y1="{y_iu + 18}" x2="{x_ctr - 47}" y2="{y_ctr + 18}" stroke="#333333" stroke-width="1.2" marker-end="url(#solidArrow)"/>
  <rect x="{(x_iu + x_ctr)/2 - 95}" y="{y_iu + 26}" width="190" height="20" fill="#f8fafc" rx="3" stroke="#cbd5e1" stroke-width="0.8"/>
  <text x="{(x_iu + x_ctr)/2}" y="{y_iu + 40}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{msg_1_2}</text>""")

    # CTR -> Right Items (Entities/Ext)
    # Numbering starts at 1.3
    step_num = 3
    for alias, (ex, ey, item, itype) in right_positions.items():
        # Look for message to this item
        fwd_m = [m for m in cu['msgs'] if m['src'] == ctr_alias and m['dst'] == alias]
        if fwd_m:
            raw_txt = fwd_m[0]['txt']
        else:
            raw_txt = f"operacion_{item['name'].lower()}()"

        msg_label = clean_msg(raw_txt, f"1.{step_num}")
        step_num += 1

        start_x = x_ctr + 45
        start_y = y_ctr + (ey - y_ctr) * 0.18
        end_x = ex - 45
        end_y = ey

        lbl_x = (start_x + end_x) / 2
        lbl_y = (start_y + end_y) / 2 - 12

        svg.append(f"""  <!-- 1.{step_num-1} CTR -> {alias} -->
  <line x1="{start_x:.1f}" y1="{start_y:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" stroke="#333333" stroke-width="1.2" marker-end="url(#solidArrow)"/>
  <rect x="{lbl_x - 85:.1f}" y="{lbl_y - 10:.1f}" width="170" height="20" fill="#f8fafc" rx="3" stroke="#cbd5e1" stroke-width="0.8"/>
  <text x="{lbl_x:.1f}" y="{lbl_y + 4:.1f}" text-anchor="middle" font-size="10.5" font-weight="500" fill="#334155">{msg_label}</text>""")

    # Return: CTR -> IU (upper line, dotted)
    ret_c_txt = c_to_iu[-1]['txt'] if c_to_iu else "datos / confirmacion"
    msg_ret_c = clean_msg(ret_c_txt, f"1.{step_num}")
    step_num += 1

    svg.append(f"""  <!-- 1.{step_num-1} CTR -> IU (Return) -->
  <line x1="{x_ctr - 47}" y1="{y_ctr - 18}" x2="{x_iu + 47}" y2="{y_iu - 18}" stroke="#333333" stroke-width="1.2" stroke-dasharray="4,4" marker-end="url(#solidArrow)"/>
  <rect x="{(x_iu + x_ctr)/2 - 95}" y="{y_iu - 42}" width="190" height="20" fill="#f8fafc" rx="3" stroke="#cbd5e1" stroke-width="0.8"/>
  <text x="{(x_iu + x_ctr)/2}" y="{y_iu - 28}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{msg_ret_c}</text>""")

    # Return: IU -> Actor (upper line, dotted)
    ret_iu_txt = iu_to_a[-1]['txt'] if iu_to_a else "mostrarResultado()"
    msg_ret_iu = clean_msg(ret_iu_txt, f"1.{step_num}")

    svg.append(f"""  <!-- 1.{step_num} IU -> Actor (Return) -->
  <line x1="{x_iu - 68}" y1="{y_iu - 18}" x2="{x_actor + 35}" y2="{y_actor - 18}" stroke="#333333" stroke-width="1.2" stroke-dasharray="4,4" marker-end="url(#solidArrow)"/>
  <rect x="{(x_actor + x_iu)/2 - 105}" y="{y_actor - 42}" width="210" height="20" fill="#f8fafc" rx="3" stroke="#cbd5e1" stroke-width="0.8"/>
  <text x="{(x_actor + x_iu)/2}" y="{y_actor - 28}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{msg_ret_iu}</text>""")

    svg.append("</svg>")
    return '\n'.join(svg)

def render_all_40():
    cus = parse_all_40_cus()
    out_dir = os.path.abspath('documentos/diagramas_comunicacion_imagenes')
    temp_dir = os.path.abspath('scratch/comm_bce_temp')
    chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Iniciando generación de {len(cus)} diagramas de comunicación BCE...")
    
    for idx, cu in enumerate(cus, 1):
        cid = cu['id']
        filename = cu['filename']
        svg_code = generate_bce_svg(cu)
        
        svg_file = os.path.join(temp_dir, f"{cid}.svg")
        png_temp = os.path.join(temp_dir, f"{cid}.png")
        png_final = os.path.join(out_dir, filename)
        
        with open(svg_file, 'w', encoding='utf-8') as f:
            f.write(svg_code)
            
        cmd = [
            chrome,
            '--headless=new',
            '--disable-gpu',
            '--hide-scrollbars',
            '--window-size=2600,1600',
            f'--screenshot={png_temp}',
            f'file:///{svg_file.replace(chr(92), "/")}'
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        img = Image.open(png_temp).convert('RGB')
        diff = ImageChops.difference(img, Image.new('RGB', img.size, (255, 255, 255)))
        bbox = diff.getbbox()
        if bbox:
            margin = 25
            cropped = img.crop((
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(img.width, bbox[2] + margin),
                min(img.height, bbox[3] + margin)
            ))
            cropped.save(png_final, format='PNG', optimize=True)
            print(f"[{idx:02d}/40] Generado con éxito: {filename} ({cropped.width}x{cropped.height} px)")
        else:
            print(f"[{idx:02d}/40] ALERTA: BBox vacío en {cid}")

    print("\n¡Todos los 40 diagramas de comunicación BCE se han renderizado con éxito en alta resolución!")

if __name__ == '__main__':
    render_all_40()
