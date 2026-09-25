import os
import re
import subprocess
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def get_browser_exe():
    if os.path.exists(CHROME_PATH):
        return CHROME_PATH
    if os.path.exists(EDGE_PATH):
        return EDGE_PATH
    raise RuntimeError("No se encontro Google Chrome ni Microsoft Edge para generar los PDFs.")

def markdown_to_html(md_text, title):
    lines = md_text.splitlines()
    html_lines = []
    
    in_code_block = False
    code_block_lines = []
    
    in_table = False
    table_header_done = False
    
    in_ul = False
    in_ol = False
    
    def close_lists():
        nonlocal in_ul, in_ol
        res = []
        if in_ul:
            res.append("</ul>")
            in_ul = False
        if in_ol:
            res.append("</ol>")
            in_ol = False
        return res
    
    def format_inline(text):
        # Bold + Italic
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # Bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        # Inline code
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        return text

    for raw_line in lines:
        line = raw_line.rstrip()
        
        # Check code fence
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("<pre><code>" + "\n".join(code_block_lines) + "</code></pre>")
                code_block_lines = []
                in_code_block = False
            else:
                html_lines.extend(close_lists())
                if in_table:
                    html_lines.append("</tbody></table>")
                    in_table = False
                    table_header_done = False
                in_code_block = True
            continue
            
        if in_code_block:
            escaped = (raw_line
                       .replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
            code_block_lines.append(escaped)
            continue
            
        # Table detection
        if line.startswith("|") and line.endswith("|"):
            html_lines.extend(close_lists())
            cols = [c.strip() for c in line[1:-1].split("|")]
            
            # Check if this is the separator row | :--- | :--- |
            if all(re.match(r'^:?-+:?$', c) for c in cols):
                table_header_done = True
                continue
                
            if not in_table:
                in_table = True
                table_header_done = False
                html_lines.append('<table class="tech-table"><thead><tr>')
                for c in cols:
                    html_lines.append(f"<th>{format_inline(c)}</th>")
                html_lines.append("</tr></thead><tbody>")
            else:
                html_lines.append("<tr>")
                for c in cols:
                    html_lines.append(f"<td>{format_inline(c)}</td>")
                html_lines.append("</tr>")
            continue
        else:
            if in_table:
                html_lines.append("</tbody></table>")
                in_table = False
                table_header_done = False

        stripped = line.strip()
        
        # Blank line
        if not stripped:
            html_lines.extend(close_lists())
            continue
            
        # Horizontal rule
        if stripped in ("---", "***", "___"):
            html_lines.extend(close_lists())
            html_lines.append("<hr/>")
            continue
            
        # Headings
        if stripped.startswith("# "):
            html_lines.extend(close_lists())
            html_lines.append(f"<h1>{format_inline(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            html_lines.extend(close_lists())
            html_lines.append(f"<h2>{format_inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            html_lines.extend(close_lists())
            html_lines.append(f"<h3>{format_inline(stripped[4:])}</h3>")
            continue
        if stripped.startswith("#### "):
            html_lines.extend(close_lists())
            html_lines.append(f"<h4>{format_inline(stripped[5:])}</h4>")
            continue
            
        # Bullet list item
        if stripped.startswith("* ") or stripped.startswith("- "):
            if not in_ul:
                html_lines.extend(close_lists())
                in_ul = True
                html_lines.append("<ul>")
            content = stripped[2:].strip()
            html_lines.append(f"<li>{format_inline(content)}</li>")
            continue
            
        # Numbered list item
        m_num = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m_num:
            if not in_ol:
                html_lines.extend(close_lists())
                in_ol = True
                html_lines.append("<ol>")
            content = m_num.group(2).strip()
            html_lines.append(f"<li>{format_inline(content)}</li>")
            continue

        # Regular paragraph
        html_lines.extend(close_lists())
        html_lines.append(f"<p>{format_inline(stripped)}</p>")

    html_lines.extend(close_lists())
    if in_table:
        html_lines.append("</tbody></table>")

    body_content = "\n".join(html_lines)
    
    html_document = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{
    size: letter;
    margin: 18mm 18mm 18mm 18mm;
  }}
  @page :left {{
    @bottom-left {{ content: none; }}
    @bottom-right {{ content: none; }}
    @top-left {{ content: none; }}
    @top-right {{ content: none; }}
  }}
  @page :right {{
    @bottom-left {{ content: none; }}
    @bottom-right {{ content: none; }}
    @top-left {{ content: none; }}
    @top-right {{ content: none; }}
  }}

  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif;
    color: #1a202c;
    background: #ffffff;
    font-size: 10.5pt;
    line-height: 1.55;
    margin: 0;
    padding: 0;
  }}

  h1 {{
    font-size: 19pt;
    color: #0f172a;
    font-weight: 800;
    border-bottom: 2.5px solid #0284c7;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  h2 {{
    font-size: 13pt;
    color: #0369a1;
    font-weight: 700;
    margin-top: 22px;
    margin-bottom: 10px;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    page-break-after: avoid;
  }}

  h3 {{
    font-size: 11pt;
    color: #0f172a;
    font-weight: 700;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
  }}

  h4 {{
    font-size: 10.5pt;
    color: #334155;
    font-weight: 600;
    margin-top: 10px;
    margin-bottom: 4px;
    page-break-after: avoid;
  }}

  p {{
    margin-top: 0;
    margin-bottom: 10px;
    text-align: justify;
  }}

  ul, ol {{
    margin-top: 4px;
    margin-bottom: 12px;
    padding-left: 24px;
  }}

  li {{
    margin-bottom: 4px;
    text-align: justify;
  }}

  code {{
    font-family: 'Consolas', 'Courier New', monospace;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1.5px 5px;
    border-radius: 4px;
    font-size: 9.5pt;
    border: 1px solid #e2e8f0;
  }}

  pre {{
    font-family: 'Consolas', 'Courier New', monospace;
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px 14px;
    border-radius: 6px;
    font-size: 8.5pt;
    line-height: 1.4;
    overflow-x: auto;
    margin-top: 8px;
    margin-bottom: 14px;
    page-break-inside: avoid;
    box-shadow: inset 0 0 4px rgba(0,0,0,0.2);
  }}

  pre code {{
    background: transparent;
    color: #f8fafc;
    padding: 0;
    border: none;
    font-size: 8.5pt;
  }}

  .tech-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    margin-bottom: 16px;
    font-size: 9pt;
    page-break-inside: avoid;
  }}

  .tech-table th {{
    background-color: #0369a1;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 7px 10px;
    border: 1px solid #0284c7;
  }}

  .tech-table td {{
    padding: 6px 10px;
    border: 1px solid #cbd5e1;
    vertical-align: top;
  }}

  .tech-table tr:nth-child(even) {{
    background-color: #f8fafc;
  }}

  hr {{
    border: none;
    height: 1px;
    background-color: #cbd5e1;
    margin: 18px 0;
  }}

  strong {{
    color: #0f172a;
  }}
</style>
</head>
<body>
{body_content}
</body>
</html>
"""
    return html_document

def convert_file(md_path, pdf_path, title):
    print(f"Leyendo {md_path}...")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_content = markdown_to_html(md_text, title)
    
    html_temp_path = md_path.with_suffix(".html")
    with open(html_temp_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"HTML temporal generado: {html_temp_path}")
    
    browser_exe = get_browser_exe()
    file_url = f"file:///{str(html_temp_path.resolve()).replace(chr(92), '/')}"
    
    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(pdf_path.resolve())}",
        file_url
    ]
    
    print(f"Ejecutando generador Chromium PDF...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error al generar PDF: {res.stderr}")
    else:
        print(f"PDF generado con exito: {pdf_path} (Tamano: {os.path.getsize(pdf_path)} bytes)")

    if os.path.exists(html_temp_path):
        os.remove(html_temp_path)

if __name__ == "__main__":
    base_dir = Path(r"c:\Users\MARILYN\Documents\Carpeta Esther\Semestre 2-2026\SI 2\primer_parcial.1.0\documentos")
    
    # 1. Switch
    switch_md = base_dir / "INFORME_INVESTIGACION_SWITCH_CAPA_2.md"
    switch_pdf = base_dir / "INFORME_INVESTIGACION_SWITCH_CAPA_2.pdf"
    convert_file(switch_md, switch_pdf, "Informe de Investigacion: El Switch de Capa 2")
    
    # 2. IEEE 802
    ieee_md = base_dir / "INFORME_INVESTIGACION_ESTANDARES_IEEE_802.md"
    ieee_pdf = base_dir / "INFORME_INVESTIGACION_ESTANDARES_IEEE_802.pdf"
    convert_file(ieee_md, ieee_pdf, "Informe de Investigacion: Estandares IEEE 802 (802.11 y 802.15.1)")
