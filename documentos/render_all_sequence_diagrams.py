import os
import re
import subprocess
import unicodedata
import time
from PIL import Image, ImageChops

def sanitize_diagram(code):
    lines = []
    for line in code.splitlines():
        # Eliminar autonumber si existe para evitar conflictos
        if re.match(r'^\s*autonumber\b', line, re.IGNORECASE):
            continue
            
        # Sanitizar actor: actor U as Usuario (No Autenticado) -> actor U as "Usuario"
        m_act = re.match(r'^(\s*actor\s+[\w_]+\s+as\s+)(.+)$', line)
        if m_act:
            pref = m_act.group(1)
            val = re.sub(r'\s*\([^)]*\)', '', m_act.group(2).strip()).strip('\"\'')
            line = f'{pref}"{val}"'
            
        # Sanitizar participante: participant IU as Interfaz (Web / Movil) -> participant IU as "Interfaz"
        m_part = re.match(r'^(\s*participant\s+[\w_]+\s+as\s+)(.+)$', line)
        if m_part:
            pref = m_part.group(1)
            val = re.sub(r'\s*\([^)]*\)', '', m_part.group(2).strip()).strip('\"\'')
            line = f'{pref}"{val}"'
            
        lines.append(line)
    return '\n'.join(lines)

def make_filename(cu_id, cu_title):
    # Formato limpio y consistente: CU01_Iniciar_Sesion.png
    clean = unicodedata.normalize('NFKD', cu_title).encode('ASCII', 'ignore').decode('ASCII')
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', clean).strip('_')
    # Limitar longitud si es muy largo
    words = clean.split('_')
    if len(words) > 7:
        clean = '_'.join(words[:7])
    return f"{cu_id}_{clean}.png"

def main():
    doc_path = 'documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md'
    out_dir = os.path.abspath('documentos/diagramas_secuencia_imagenes')
    temp_dir = os.path.abspath('scratch/sequence_render_temp')
    js_path = os.path.abspath('scratch/mermaid.min.js').replace('\\', '/')
    chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        text = f.read()
        
    sections = re.split(r'\n(?=### CU\d+:)', text)
    cus = []
    for sec in sections:
        m_header = re.match(r'### (CU\d+):\s*([^\n]+)', sec)
        if not m_header:
            continue
        cu_id = m_header.group(1)
        cu_title = m_header.group(2).strip()
        
        m_diag = re.search(r'`{1,3}(?:mermaid)?\s*\n(sequenceDiagram\b.*?)\n`{1,3}', sec, re.DOTALL)
        if m_diag:
            diag_code = m_diag.group(1).strip()
            cus.append({
                'id': cu_id,
                'title': cu_title,
                'diagram': diag_code,
                'filename': make_filename(cu_id, cu_title)
            })
            
    print(f"=== INICIANDO RENDERIZADO DE {len(cus)} DIAGRAMAS DE SECUENCIA UML ===")
    
    total = len(cus)
    success_count = 0
    errors = []
    
    for idx, cu in enumerate(cus, 1):
        cu_id = cu['id']
        cu_title = cu['title']
        filename = cu['filename']
        final_png = os.path.join(out_dir, filename)
        
        sanitized_diag = sanitize_diagram(cu['diagram'])
        
        html_file = os.path.join(temp_dir, f"{cu_id}.html")
        raw_png = os.path.join(temp_dir, f"{cu_id}_raw.png")
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="{js_path}"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 35px;
            background: #ffffff;
            overflow: hidden !important;
            font-family: Arial, Helvetica, sans-serif;
        }}
        ::-webkit-scrollbar {{
            display: none !important;
        }}
        .mermaid {{
            background: #ffffff;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="mermaid">
{sanitized_diag}
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'base',
            themeVariables: {{
                primaryColor: '#ffffff',
                primaryBorderColor: '#111827',
                primaryTextColor: '#111827',
                lineColor: '#111827',
                actorBkg: '#ffffff',
                actorBorder: '#111827',
                actorTextColor: '#111827',
                signalColor: '#111827',
                signalTextColor: '#111827',
                labelBoxBkgColor: '#f9fafb',
                labelBoxBorderColor: '#111827',
                labelTextColor: '#111827',
                loopTextColor: '#111827',
                noteBkgColor: '#fef3c7',
                noteBorderColor: '#b45309',
                noteTextColor: '#78350f',
                activationBkgColor: '#ffffff',
                activationBorderColor: '#111827',
                sequenceNumberColor: '#111827'
            }},
            sequence: {{
                useMaxWidth: false,
                diagramMarginX: 20,
                diagramMarginY: 20,
                boxMargin: 12,
                boxTextMargin: 6,
                noteMargin: 10,
                messageMargin: 36
            }}
        }});
    </script>
</body>
</html>"""
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        html_url = f"file:///{html_file.replace(chr(92), '/')}"
        
        cmd = [
            chrome,
            '--headless=new',
            '--disable-gpu',
            '--hide-scrollbars',
            '--window-size=3800,5000',
            f'--screenshot={raw_png}',
            html_url
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(raw_png):
                raise RuntimeError("Chrome no generó el archivo de captura.")
                
            img = Image.open(raw_png).convert('RGB')
            bg = Image.new('RGB', img.size, (255, 255, 255))
            diff = ImageChops.difference(img, bg)
            bbox = diff.getbbox()
            
            if not bbox:
                raise RuntimeError("El canvas renderizado está completamente en blanco.")
                
            # Margen de seguridad limpio de 30px alrededor del diagrama
            margin = 30
            left = max(0, bbox[0] - margin)
            top = max(0, bbox[1] - margin)
            right = min(img.width, bbox[2] + margin)
            bottom = min(img.height, bbox[3] + margin)
            
            cropped = img.crop((left, top, right, bottom))
            cropped.save(final_png, format='PNG', optimize=True)
            
            success_count += 1
            print(f"[{idx:02d}/{total:02d}] OK: {cu_id} -> {filename} ({cropped.width}x{cropped.height} px)")
            
        except Exception as e:
            print(f"[{idx:02d}/{total:02d}] ERROR en {cu_id}: {str(e)}")
            errors.append((cu_id, str(e)))
            
    print("\n" + "="*60)
    print(f"PROCESO FINALIZADO: {success_count} de {total} diagramas renderizados con éxito.")
    if errors:
        print(f"ERRORES ENCONTRADOS ({len(errors)}):")
        for eid, err in errors:
            print(f"  - {eid}: {err}")
    else:
        print("¡TODOS LOS 40 DIAGRAMAS SE GENERARON PERFECTAMENTE!")
    print(f"Ubicación de imágenes: {out_dir}")
    print("="*60)

if __name__ == '__main__':
    main()
