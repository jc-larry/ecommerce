const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const vm = require("vm");

const root = __dirname;
const defsPath = path.join(root, "diagram_definitions.py");
const outDir = path.join(root, "documentacion_analisis_clases", "imagenes");
const tmpDir = path.join(root, "documentacion_analisis_clases", "_tmp_render");
const chromeProfileDir = path.join(tmpDir, "chrome_profile");
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(tmpDir, { recursive: true });
fs.mkdirSync(chromeProfileDir, { recursive: true });

function sanitizeFilename(name) {
  return name.replace(/[^a-zA-Z0-9_-]/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
}

function loadUseCases() {
  const src = fs.readFileSync(defsPath, "utf8");
  const start = src.indexOf("ALL_USE_CASES");
  const eq = src.indexOf("=", start);
  let literal = src.slice(eq + 1).trim();
  literal = literal.replace(/^\s*#.*$/gm, "");
  literal = literal.replace(/\("([^"]+)",\s*"([^"]+)"\)/g, '["$1", "$2"]');
  return vm.runInNewContext(literal, {});
}

function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function boxHeight(cls) {
  const title = 54;
  const attr = cls.attributes?.length ? 28 * cls.attributes.length + 18 : 24;
  const meth = cls.methods?.length ? 28 * cls.methods.length + 18 : 0;
  return title + attr + meth;
}

function boxWidth(cls, minWidth) {
  const values = [cls.name, ...(cls.attributes || []), ...(cls.methods || [])];
  const maxLen = Math.max(...values.map((value) => String(value).length));
  return Math.max(minWidth, Math.min(760, maxLen * 12 + 44));
}

function classBox(x, y, w, cls) {
  const h = boxHeight(cls);
  const titleH = 54;
  const attrH = cls.attributes?.length ? 28 * cls.attributes.length + 18 : 24;
  const lines = [];
  lines.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff" stroke="#111827" stroke-width="2"/>`);
  lines.push(`<rect x="${x}" y="${y}" width="${w}" height="${titleH}" fill="#f3f4f6" stroke="#111827" stroke-width="2"/>`);
  lines.push(`<text x="${x + w / 2}" y="${y + 34}" text-anchor="middle" class="title">${esc(cls.name)}</text>`);
  let cy = y + titleH + 30;
  for (const attr of cls.attributes || []) {
    lines.push(`<text x="${x + 18}" y="${cy}" class="member">${esc(attr)}</text>`);
    cy += 28;
  }
  if (cls.methods?.length) {
    const sepY = y + titleH + attrH;
    lines.push(`<line x1="${x}" y1="${sepY}" x2="${x + w}" y2="${sepY}" stroke="#111827" stroke-width="2"/>`);
    cy = sepY + 30;
    for (const method of cls.methods) {
      lines.push(`<text x="${x + 18}" y="${cy}" class="member">${esc(method)}</text>`);
      cy += 28;
    }
  }
  return { svg: lines.join("\n"), x, y, w, h, cx: x + w / 2, cy: y + h / 2 };
}

function actor(x, y, name) {
  const [line1, line2] = name.split("/").map((s) => s.trim());
  return `
    <circle cx="${x}" cy="${y - 78}" r="18" fill="#fff" stroke="#111827" stroke-width="3"/>
    <line x1="${x}" y1="${y - 60}" x2="${x}" y2="${y - 8}" stroke="#111827" stroke-width="3"/>
    <line x1="${x - 32}" y1="${y - 38}" x2="${x + 32}" y2="${y - 38}" stroke="#111827" stroke-width="3"/>
    <line x1="${x}" y1="${y - 8}" x2="${x - 28}" y2="${y + 42}" stroke="#111827" stroke-width="3"/>
    <line x1="${x}" y1="${y - 8}" x2="${x + 28}" y2="${y + 42}" stroke="#111827" stroke-width="3"/>
    <text x="${x}" y="${y + 82}" text-anchor="middle" class="actor">${esc(line1)}</text>
    ${line2 ? `<text x="${x}" y="${y + 108}" text-anchor="middle" class="actor">${esc("/ " + line2)}</text>` : ""}
  `;
}

function connector(x1, y1, x2, y2, dashed = false) {
  const dash = dashed ? ' stroke-dasharray="8 6" marker-end="url(#arrow)"' : "";
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#111827" stroke-width="2"${dash}/>`;
}

function dependencyPath(x1, y1, x2, y2) {
  const lane = x1 + 70;
  return `<polyline points="${x1},${y1} ${lane},${y1} ${lane},${y2} ${x2},${y2}" fill="none" stroke="#111827" stroke-width="2" stroke-dasharray="8 6" marker-end="url(#arrow)"/>`;
}

function associationPath(b1, b2) {
  if (Math.abs(b1.cx - b2.cx) < 10) {
    const lane = Math.min(b1.x, b2.x) - 36;
    return `<polyline points="${b1.x},${b1.cy} ${lane},${b1.cy} ${lane},${b2.cy} ${b2.x},${b2.cy}" fill="none" stroke="#111827" stroke-width="2"/>`;
  }
  const left = b1.cx < b2.cx ? b1 : b2;
  const right = b1.cx < b2.cx ? b2 : b1;
  return connector(left.x + left.w, left.cy, right.x, right.cy);
}

function renderSvg(cu) {
  const entities = cu.entities;
  const width = entities.length >= 4 ? 3300 : 2600;
  const height = entities.length >= 4 ? 1300 : 1180;
  const centerY = height / 2;
  const actorX = 150;
  const iuW = boxWidth(cu.boundary, 560);
  const ctrData = { name: cu.controller.name, attributes: [], methods: cu.controller.methods };
  const ctrW = boxWidth(ctrData, 660);
  const iu = classBox(360, centerY - boxHeight(cu.boundary) / 2, iuW, cu.boundary);
  const ctr = classBox(1040, centerY - boxHeight(ctrData) / 2, ctrW, {
    name: cu.controller.name,
    attributes: [],
    methods: cu.controller.methods,
  });
  const positions = [];
  const entityX = ctr.x + ctr.w + 520;
  if (entities.length === 1) positions.push([entityX, centerY]);
  else if (entities.length === 2) positions.push([entityX, centerY - 210], [entityX, centerY + 210]);
  else if (entities.length === 3) positions.push([entityX, centerY - 330], [entityX, centerY], [entityX, centerY + 330]);
  else positions.push([ctr.x + ctr.w + 430, centerY - 280], [ctr.x + ctr.w + 430, centerY + 280], [ctr.x + ctr.w + 910, centerY - 280], [ctr.x + ctr.w + 910, centerY + 280]);
  const entityBoxes = new Map();
  const parts = [];
  parts.push(actor(actorX, centerY, cu.actor));
  parts.push(iu.svg, ctr.svg);
  parts.push(connector(actorX + 45, centerY - 38, iu.x, centerY - 38));
  parts.push(connector(iu.x + iu.w, centerY, ctr.x, centerY, true));
  entities.forEach((ent, i) => {
    const w = boxWidth(ent, ent.attributes.length > 6 ? 560 : 500);
    const [cx, cy] = positions[i];
    const box = classBox(cx - w / 2, cy - boxHeight(ent) / 2, w, ent);
    entityBoxes.set(ent.name, box);
    parts.push(box.svg);
    if (box.x < 2000) {
      parts.push(dependencyPath(ctr.x + ctr.w, ctr.cy + (box.cy - centerY) * 0.15, box.x, box.cy));
    } else if (entities.length <= 3) {
      parts.push(dependencyPath(ctr.x + ctr.w, ctr.cy + (box.cy - centerY) * 0.15, box.x, box.cy));
    }
  });
  for (const [a, b] of cu.associations || []) {
    const b1 = entityBoxes.get(a);
    const b2 = entityBoxes.get(b);
    if (!b1 || !b2) continue;
    parts.push(associationPath(b1, b2));
  }
  return `<!doctype html>
  <html><head><meta charset="utf-8"/>
  <style>
    html,body{margin:0;background:#fff;width:${width}px;height:${height}px;overflow:hidden}
    svg{width:${width}px;height:${height}px;background:#fff}
    .title{font:700 23px Arial, sans-serif;fill:#111827}
    .member{font:19px Consolas, "Courier New", monospace;fill:#111827}
    .actor{font:19px Arial, sans-serif;fill:#111827}
  </style></head><body>
  <svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
    <defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="11" refY="6" orient="auto">
      <path d="M1,1 L11,6 L1,11" fill="none" stroke="#111827" stroke-width="2"/>
    </marker></defs>
    ${parts.join("\n")}
  </svg></body></html>`;
}

function chromePath() {
  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  ];
  return candidates.find((candidate) => fs.existsSync(candidate));
}

const chrome = chromePath();
if (!chrome) {
  throw new Error("No se encontro Chrome para exportar PNG.");
}

const cases = loadUseCases().filter((cu) => cu.cycle === "Ciclo 3");
for (const cu of cases) {
  const safe = `${cu.id}_${sanitizeFilename(cu.title.split(":").slice(1).join(":").trim())}`;
  const htmlPath = path.join(tmpDir, `${safe}.html`);
  const pngPath = path.join(outDir, `${safe}.png`);
  const html = renderSvg(cu);
  const width = html.match(/width:(\d+)px/)[1];
  const height = html.match(/height:(\d+)px/)[1];
  fs.writeFileSync(htmlPath, html, "utf8");
  const result = spawnSync(chrome, [
    "--headless=new",
    "--disable-gpu",
    "--disable-gpu-compositing",
    "--disable-software-rasterizer",
    "--disable-3d-apis",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--hide-scrollbars",
    `--user-data-dir=${chromeProfileDir}`,
    `--disk-cache-dir=${path.join(tmpDir, "chrome_cache")}`,
    `--window-size=${width},${height}`,
    `--screenshot=${pngPath}`,
    `file:///${htmlPath.replace(/\\/g, "/")}`,
  ], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || `Chrome fallo al renderizar ${cu.id}`);
  }
  console.log(pngPath);
}
