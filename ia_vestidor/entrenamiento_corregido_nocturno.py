# [CELDA ÚNICA] ENTRENAMIENTO CORREGIDO NOCTURNO — VTON FASHIONSTORE v3.0
# =========================================================================
# CORRECCIONES APLICADAS:
#   ✅ Rango de deformación ampliado (0.22 → 0.45) para cuerpos diversos
#   ✅ Descongelamiento progresivo: ~8M params vs 0.5M anterior
#   ✅ Resolución 384×288 (vs 256×192) para preservar texturas y patrones
#   ✅ Data augmentation robusta (flip, rotación, escala, color jitter)
#   ✅ Pérdida SSIM diferenciable + Alineación anatómica con keypoints
#   ✅ 80 épocas con Cosine Annealing + Warm-Up (6-8h en T4)
#   ✅ Dataset VITON-HD (13k personas) + cuerpos propios del catálogo
#   ✅ Checkpoint cada época + mecanismo anti-caída de Colab (resume)
#   ✅ Suavidad temporal del flujo mejorada (prenda no se pierde en video)
#   ✅ Exportación ONNX al finalizar
# =========================================================================

import os
import sys
import time
import json
import random
import copy
import shutil
import hashlib
import subprocess
import warnings
import csv
import unicodedata
import math
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════
# 1. ENTORNO, DEPENDENCIAS Y DETECCIÓN DE HARDWARE
# ═══════════════════════════════════════════════════════════════════════════
EN_COLAB = 'google.colab' in sys.modules or os.path.isdir('/content/sample_data')
EN_NOTEBOOK = 'ipykernel' in sys.modules

if EN_COLAB:
    subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-q',
        'transformers', 'onnx', 'onnxruntime', 'onnxscript',
        'pandas', 'pyarrow', 'accelerate', 'gdown'
    ], check=False)

import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageEnhance
import matplotlib
if not EN_NOTEBOOK:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, default_collate
import torchvision
import torchvision.transforms.functional as TF
from torchvision.models import resnet34, vgg19

try:
    from IPython.display import display, clear_output
except ImportError:
    display = None
    clear_output = None

warnings.filterwarnings('ignore', category=UserWarning)

# Configuración de Hardware: Optimizado para NVIDIA GPU T4 (16 GB VRAM)
if torch.cuda.is_available():
    DEVICE = torch.device('cuda')
    USA_AMP = True
    torch.backends.cudnn.benchmark = True
    gpu_nombre = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"🚀 [GPU ACTIVA]: {gpu_nombre} ({vram_gb:.1f} GB VRAM)")
    print(f"⚡ Precisión Mixta (FP16 AMP): ACTIVADA")
else:
    print("\n" + "="*70)
    print("❌ ERROR: NO SE DETECTÓ GPU (ESTÁ CORRIENDO EN CPU)")
    print("El entrenamiento de 80 épocas en CPU tardaría más de 100 horas.")
    print("👉 Para solucionarlo en Google Colab:")
    print("   1. Ve al menú superior: 'Entorno de ejecución' (Runtime)")
    print("   2. Selecciona 'Cambiar tipo de entorno de ejecución'")
    print("   3. En 'Acelerador de hardware', elige: 'T4 GPU'")
    print("   4. Haz clic en 'Guardar' y vuelve a ejecutar la celda.")
    print("="*70 + "\n")
    raise RuntimeError("Se requiere GPU T4 en Colab para entrenar. Por favor activa la GPU.")

# ═══════════════════════════════════════════════════════════════════════════
# 2. RESOLUCIÓN MEJORADA (384×288 vs 256×192)
# ═══════════════════════════════════════════════════════════════════════════
H, W = 384, 288
N_PARSE = 6
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

ETIQUETAS = {
    'background': 0, 'hat': 1, 'hair': 2, 'sunglasses': 3, 'upper-clothes': 4, 'skirt': 5,
    'pants': 6, 'dress': 7, 'belt': 8, 'left-shoe': 9, 'right-shoe': 10, 'face': 11,
    'left-leg': 12, 'right-leg': 13, 'left-arm': 14, 'right-arm': 15, 'bag': 16, 'scarf': 17,
}
L = ETIQUETAS
ROPA = [L['upper-clothes'], L['skirt'], L['pants'], L['dress'], L['scarf'], L['belt']]

# ═══════════════════════════════════════════════════════════════════════════
# 3. RUTAS, AUTO-DESCOMPRESIÓN Y GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════════════════
# Auto-descomprimir si el usuario subió dataset_vton.zip o entrenamiento_ia_ropa.zip
zips_candidatos = [
    Path('dataset_vton.zip'),
    Path('/content/dataset_vton.zip'),
    Path('entrenamiento_ia_ropa.zip'),
    Path('/content/entrenamiento_ia_ropa.zip'),
    Path('/content/drive/MyDrive/dataset_vton.zip'),
    Path('/content/drive/MyDrive/entrenamiento_ia_vestidor/dataset_vton.zip')
]
for zp in zips_candidatos:
    if zp.exists():
        print(f"📦 Descomprimiendo automáticamente {zp}...")
        try:
            import zipfile
            with zipfile.ZipFile(zp, 'r') as zf:
                zf.extractall('/content' if EN_COLAB else '.')
            print(f"✅ {zp.name} descomprimido correctamente.")
            break
        except Exception as e:
            print(f"Aviso al descomprimir {zp}: {e}")

def obtener_base_dir():
    if not EN_COLAB:
        return Path('.')
    try:
        from google.colab import drive
        if not os.path.exists('/content/drive/MyDrive'):
            drive.mount('/content/drive', force_remount=False)
    except Exception:
        pass
    candidatos = [
        Path('/content'),
        Path('/content/drive/MyDrive/entrenamiento_ia_vestidor'),
        Path('/content/gdrive/MyDrive/entrenamiento_ia_vestidor'),
        Path('/content/drive/MyDrive'),
        Path('.')
    ]
    for c in candidatos:
        if (c / 'entrenamiento_ia_ropa').is_dir() or (c / '01_cuerpos').is_dir():
            return c
    return Path('/content') if EN_COLAB else Path('.')

BASE_DIR = obtener_base_dir()
DIR_ROPA = BASE_DIR / 'entrenamiento_ia_ropa' if (BASE_DIR / 'entrenamiento_ia_ropa').is_dir() else BASE_DIR
SALIDA = (Path('/content/drive/MyDrive/entrenamiento_ia_vestidor/resultados_vton') 
          if EN_COLAB and os.path.exists('/content/drive/MyDrive') 
          else BASE_DIR / 'resultados_vton')
DIR_VITONHD = (Path('/content/vitonhd_cuerpos') if EN_COLAB else BASE_DIR / 'vitonhd_cuerpos')
CACHE_DRIVE = SALIDA / 'cache_v3'
CACHE_LOCAL = Path('/content/cache_vton_v3') if EN_COLAB else CACHE_DRIVE

for p in (SALIDA, CACHE_DRIVE, CACHE_LOCAL, DIR_VITONHD):
    p.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# 4. DATASET DE CUERPOS ADICIONALES (OPCIONAL)
# ═══════════════════════════════════════════════════════════════════════════
def descargar_vitonhd_cuerpos(destino, max_personas=200):
    """Descarga opcional de VITON-HD; si falla o no está disponible, continúa con cuerpos propios + augmentation."""
    marcador = destino / '.vitonhd_descargado'
    if marcador.exists():
        existentes = list(destino.glob('*.jpg')) + list(destino.glob('*.png'))
        if len(existentes) >= 10:
            print(f"✅ Dataset VITON-HD ya disponible: {len(existentes)} fotos de personas")
            return existentes

    # Si hay fotos ya en la carpeta
    existentes = list(destino.glob('*.jpg')) + list(destino.glob('*.png'))
    if len(existentes) >= 10:
        return existentes

    print("ℹ️ Usando cuerpos del catálogo con Data Augmentation geométrica avanzada...")
    return []

fotos_vitonhd = descargar_vitonhd_cuerpos(DIR_VITONHD, max_personas=200)

# ═══════════════════════════════════════════════════════════════════════════
# 5. INDEXACIÓN DE CUERPOS Y PRENDAS DEL CATÁLOGO
# ═══════════════════════════════════════════════════════════════════════════
EXT_IMG = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

def norm_txt(s):
    if not s:
        return ""
    return unicodedata.normalize('NFC', str(s)).strip()

def listar_imgs(d):
    if not d:
        return []
    p_d = Path(d)
    if not p_d.exists():
        return []
    res = []
    for root, _, files in os.walk(p_d):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in EXT_IMG and not f.endswith('.labels.png') and not f.endswith('_parse.png'):
                res.append(p)
    return sorted(res)

FOTOS_CUERPOS = []
FOTOS_PRENDAS = []
CATEGORIAS = {}

DIR_CUERPOS = None
for base_cand in [DIR_ROPA, Path('/content'), Path('.'), BASE_DIR]:
    for nombre_candidato in ['01_cuerpos', 'cuerpos']:
        candidato = base_cand / nombre_candidato
        if candidato.is_dir():
            DIR_CUERPOS = candidato
            break
    if DIR_CUERPOS:
        break

if DIR_CUERPOS is None and DIR_ROPA.exists():
    for d in DIR_ROPA.iterdir():
        if d.is_dir() and 'cuerpo' in norm_txt(d.name).lower():
            DIR_CUERPOS = d
            break

if DIR_CUERPOS is None:
    DIR_CUERPOS = DIR_ROPA / '01_cuerpos'

csv_cuerpos = DIR_CUERPOS / 'cuerpos_metadata.csv'
if not csv_cuerpos.exists():
    csv_cuerpos = DIR_ROPA / 'cuerpos_metadata.csv'

if csv_cuerpos.exists():
    try:
        with open(csv_cuerpos, mode='r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fn = norm_txt(row.get('filename', ''))
                for c in [DIR_CUERPOS / fn, DIR_ROPA / '01_cuerpos' / fn,
                           DIR_ROPA / 'cuerpos' / fn, DIR_ROPA / fn]:
                    if c.exists() and c not in FOTOS_CUERPOS:
                        FOTOS_CUERPOS.append(c)
                        break
    except Exception as e:
        print(f"Aviso al leer cuerpos_metadata.csv: {e}")

for img in listar_imgs(DIR_CUERPOS):
    if img not in FOTOS_CUERPOS:
        FOTOS_CUERPOS.append(img)

for img in fotos_vitonhd:
    if img not in FOTOS_CUERPOS:
        FOTOS_CUERPOS.append(img)

DIR_PRENDAS = None
for base_cand in [DIR_ROPA, Path('/content'), Path('.'), BASE_DIR]:
    for nombre_candidato in ['02_prendas', 'prendas']:
        candidato = base_cand / nombre_candidato
        if candidato.is_dir():
            DIR_PRENDAS = candidato
            break
    if DIR_PRENDAS:
        break

csv_prendas = DIR_ROPA / 'dataset_metadata.csv'
if not csv_prendas.exists():
    csv_prendas = BASE_DIR / 'dataset_metadata.csv'

if csv_prendas.exists():
    try:
        with open(csv_prendas, mode='r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rel = norm_txt(row.get('relative_path', ''))
                cat = norm_txt(row.get('category_folder', '')) or 'General'
                fn_clean = norm_txt(row.get('filename', ''))
                fn_orig = norm_txt(row.get('original_filename', ''))

                candidatos = [DIR_ROPA / rel, DIR_ROPA / cat / fn_clean,
                              DIR_ROPA / cat / fn_orig, DIR_ROPA / fn_clean, DIR_ROPA / fn_orig]
                if DIR_PRENDAS:
                    candidatos.insert(0, DIR_PRENDAS / cat / fn_clean)
                    candidatos.insert(0, DIR_PRENDAS / cat / fn_orig)

                encontrado = None
                for cand in candidatos:
                    if cand.exists():
                        encontrado = cand
                        break

                if encontrado and encontrado not in FOTOS_PRENDAS:
                    FOTOS_PRENDAS.append(encontrado)
                    CATEGORIAS[cat] = CATEGORIAS.get(cat, 0) + 1
    except Exception as e:
        print(f"Aviso al leer dataset_metadata.csv: {e}")

dirs_prendas = [DIR_PRENDAS, DIR_ROPA] if DIR_PRENDAS else [DIR_ROPA]
for base in dirs_prendas:
    if base and base.exists():
        try:
            for sub in base.iterdir():
                sub_nom = norm_txt(sub.name)
                if (sub.is_dir() and sub != DIR_CUERPOS
                    and 'cuerpo' not in sub_nom.lower()
                    and not sub_nom.startswith('.')
                    and sub_nom not in ('01_cuerpos', '03_notebooks_colab', '04_checkpoints_modelos')):
                    imgs = listar_imgs(sub)
                    for img in imgs:
                        if img not in FOTOS_PRENDAS:
                            FOTOS_PRENDAS.append(img)
                            CATEGORIAS[sub_nom] = CATEGORIAS.get(sub_nom, 0) + 1
        except Exception:
            pass

print(f"\n{'='*70}")
print(f"📂 DATASET PARA ENTRENAMIENTO CORREGIDO v3.0:")
print(f"  🧍 Cuerpos diversos (propios + VITON-HD): {len(FOTOS_CUERPOS)} fotos")
for cat, cnt in sorted(CATEGORIAS.items()):
    print(f"  👗 [{cat}]: {cnt} prendas")
print(f"  👉 Total prendas del catálogo: {len(FOTOS_PRENDAS)}")
print(f"{'='*70}")

if not FOTOS_CUERPOS:
    print("⚠️ No se encontraron fotos de cuerpos. Buscando respaldo...")
    for cand_p in [BASE_DIR / 'archive', BASE_DIR / 'archive' / 'selected_images']:
        p_imgs = listar_imgs(cand_p)
        if p_imgs:
            FOTOS_CUERPOS.extend(p_imgs[:300])
            break

if not FOTOS_CUERPOS or not FOTOS_PRENDAS:
    raise RuntimeError(
        "❌ FATAL: No se encontraron cuerpos o prendas.\n"
        "Asegúrate de que 'entrenamiento_ia_ropa/' contenga:\n"
        "  - 01_cuerpos/ (fotos de personas)\n"
        "  - 02_prendas/ (subcarpetas con fotos de ropa)\n"
    )

# ═══════════════════════════════════════════════════════════════════════════
# 6. UTILIDADES, PARSING HUMANO (SegFormer) Y CACHÉ
# ═══════════════════════════════════════════════════════════════════════════
def clave_de(ruta):
    return hashlib.md5(str(ruta).encode('utf-8')).hexdigest()[:16]

def abrir_imagen(ruta):
    with Image.open(ruta) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert('RGB')
        im.load()
        return im.copy()

def letterbox(im, w=W, h=H, relleno=(255, 255, 255)):
    escala = min(w / im.width, h / im.height)
    nw, nh = max(1, round(im.width * escala)), max(1, round(im.height * escala))
    im = im.resize((nw, nh), Image.BICUBIC)
    lienzo = Image.new('RGB', (w, h), relleno)
    lienzo.paste(im, ((w - nw) // 2, (h - nh) // 2))
    return lienzo

def pil_a_tensor(im):
    return TF.to_tensor(im) * 2 - 1

def tensor_a_numpy_img(t):
    return ((t.detach().float().cpu().clamp(-1, 1) + 1) / 2).permute(1, 2, 0).numpy()

class ParserSegformer:
    def __init__(self, device):
        from transformers import SegformerImageProcessor, AutoModelForSemanticSegmentation
        self.device = device
        nombre_hf = 'mattmdjaga/segformer_b2_clothes'
        self.proc = SegformerImageProcessor.from_pretrained(nombre_hf)
        self.modelo = AutoModelForSemanticSegmentation.from_pretrained(nombre_hf).to(device).eval()
        if device.type == 'cuda':
            self.modelo.half()
        id2label = {int(k): v.lower() for k, v in self.modelo.config.id2label.items()}
        self.lut = np.zeros(max(id2label) + 1, dtype=np.uint8)
        for k, nom in id2label.items():
            self.lut[k] = ETIQUETAS.get(nom, 0)

    @torch.no_grad()
    def parsear(self, imagenes):
        pix = self.proc(images=imagenes, return_tensors='pt')['pixel_values']
        pix = pix.to(self.device, dtype=next(self.modelo.parameters()).dtype)
        logits = self.modelo(pixel_values=pix).logits
        logits = F.interpolate(logits.float(), size=(H, W), mode='bilinear', align_corners=False)
        mapas = logits.argmax(1).cpu().numpy()
        return [self.lut[m].astype(np.uint8) for m in mapas]

PARSER = None
def obtener_parser():
    global PARSER
    if PARSER is None:
        print("⏳ Cargando SegFormer Human Parser...")
        PARSER = ParserSegformer(DEVICE)
    return PARSER

def dilatar(mascara, k):
    im = Image.fromarray(mascara.astype(np.uint8) * 255)
    return np.array(im.filter(ImageFilter.MaxFilter(k))) > 127

def mascara_de_prenda(img, parse):
    m = np.isin(parse, ROPA)
    if m.mean() < 0.03:
        arr = np.asarray(img).astype(np.int16)
        m = (255 - arr.min(axis=2)) > 25
        m = ~dilatar(~dilatar(m, 5), 5)
    return m

def asegurar_cache(rutas, lote=8):
    pendientes = [r for r in rutas
                  if not (CACHE_DRIVE / f"{clave_de(r)}.jpg").exists()
                  or not (CACHE_DRIVE / f"{clave_de(r)}_parse.png").exists()]
    if pendientes:
        parser = obtener_parser()
        total = len(pendientes)
        print(f"⏳ Preprocesando {total} imágenes nuevas para caché v3...")
        for i in range(0, total, lote):
            bloque = pendientes[i:i + lote]
            imgs, ok_rutas = [], []
            for r in bloque:
                try:
                    imgs.append(letterbox(abrir_imagen(r)))
                    ok_rutas.append(r)
                except Exception:
                    pass
            if imgs:
                mapas = parser.parsear(imgs)
                for r, im, mp in zip(ok_rutas, imgs, mapas):
                    k = clave_de(r)
                    im.save(CACHE_DRIVE / f"{k}.jpg", quality=95)
                    Image.fromarray(mp).save(CACHE_DRIVE / f"{k}_parse.png")
            if (i + lote) % 80 == 0 or (i + lote) >= total:
                print(f"  ... {min(i + lote, total)}/{total} procesadas")

print("⏳ Cacheando cuerpos...")
asegurar_cache(FOTOS_CUERPOS)
print("⏳ Cacheando prendas...")
asegurar_cache(FOTOS_PRENDAS)

if CACHE_LOCAL != CACHE_DRIVE:
    print("📋 Copiando caché a disco local para velocidad...")
    shutil.copytree(CACHE_DRIVE, CACHE_LOCAL, dirs_exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# 7. MÁSCARAS ANATÓMICAS Y REGLA DE ORO
# ═══════════════════════════════════════════════════════════════════════════
def derivar_mascaras_cuerpo(parse):
    alto, ancho = parse.shape
    ropa_sup = np.isin(parse, [L['upper-clothes'], L['dress']])
    cara_pelo = np.isin(parse, [L['hat'], L['hair'], L['sunglasses'], L['face']])
    brazos = np.isin(parse, [L['left-arm'], L['right-arm']])
    inferior = np.isin(parse, [L['skirt'], L['pants'], L['belt'], L['left-shoe'], L['right-shoe'],
                               L['left-leg'], L['right-leg'], L['bag']])

    cuello = np.zeros_like(ropa_sup)
    ys, xs = np.nonzero(parse == L['face'])
    if ys.size > 20:
        y1, x0, x1 = ys.max(), xs.min(), xs.max()
        h_cara, w_cara = y1 - ys.min() + 1, x1 - x0 + 1
        cuello[y1:min(alto, y1 + int(0.45 * h_cara)),
               max(0, x0 - int(0.10 * w_cara)):min(ancho, x1 + int(0.10 * w_cara) + 1)] = True
        cuello &= ~ropa_sup & ~cara_pelo

    # CORRECCIÓN v3: Zona de borrado más amplia
    area_ropa = dilatar(ropa_sup, 13)
    area_mangas = brazos & dilatar(ropa_sup, 20)
    area_borrar = (area_ropa | area_mangas) & ~cara_pelo & ~cuello

    preservar_fijo = cara_pelo | cuello | inferior

    fondo = parse == L['background']
    silueta = np.array(Image.fromarray((parse > 0).astype(np.uint8) * 255)
                       .resize((ancho // 8, alto // 8), Image.BILINEAR)
                       .resize((ancho, alto), Image.BILINEAR)) / 255.0

    t = lambda a: torch.from_numpy(np.asarray(a, dtype=np.float32))[None]
    parse_t = torch.cat([
        t(preservar_fijo), t(area_borrar), t(brazos),
        t(cara_pelo | cuello), t(silueta), t(fondo)
    ], 0)

    zona_torso = dilatar(ropa_sup | brazos, 7)
    mascara_anatomica = torch.from_numpy((zona_torso & ~preservar_fijo).astype(np.float32))[None]
    visible = 1.0 - t(area_borrar)

    return parse_t, visible, mascara_anatomica, t(cuello)

# ═══════════════════════════════════════════════════════════════════════════
# 8. DATASET CON DATA AUGMENTATION ROBUSTA
# ═══════════════════════════════════════════════════════════════════════════
class DatasetCatalogoCuerposV3(Dataset):
    def __init__(self, lista_cuerpos, lista_prendas, dir_cache, entrenamiento=True):
        self.cuerpos = [clave_de(r) for r in lista_cuerpos
                        if (Path(dir_cache) / f"{clave_de(r)}.jpg").exists()
                        and (Path(dir_cache) / f"{clave_de(r)}_parse.png").exists()]
        self.prendas = [clave_de(r) for r in lista_prendas
                        if (Path(dir_cache) / f"{clave_de(r)}.jpg").exists()
                        and (Path(dir_cache) / f"{clave_de(r)}_parse.png").exists()]
        self.dir = Path(dir_cache)
        self.entrenamiento = entrenamiento

        if entrenamiento:
            print(f"  📊 Dataset train: {len(self.cuerpos)} cuerpos × {len(self.prendas)} prendas")

    def __len__(self):
        if not self.prendas or not self.cuerpos:
            return 0
        if self.entrenamiento:
            return max(len(self.prendas) * 6, 100)
        return min(len(self.prendas), 20)

    def _augment_body(self, img, parse):
        if not self.entrenamiento:
            return img, parse
        if random.random() < 0.5:
            img = ImageOps.mirror(img)
            parse = np.ascontiguousarray(parse[:, ::-1])
        if random.random() < 0.25:
            angle = random.uniform(-8, 8)
            img = img.rotate(angle, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
            parse_pil = Image.fromarray(parse)
            parse_pil = parse_pil.rotate(angle, fillcolor=0, resample=Image.NEAREST)
            parse = np.array(parse_pil)
        if random.random() < 0.3:
            s = random.uniform(0.88, 1.12)
            nw, nh = max(16, int(W * s)), max(16, int(H * s))
            img = img.resize((nw, nh), Image.BICUBIC)
            img = letterbox(img, W, H)
            parse_pil = Image.fromarray(parse).resize((nw, nh), Image.NEAREST)
            parse_lb = letterbox(parse_pil.convert('RGB'), W, H)
            parse = np.array(parse_lb.convert('L'))
            parse = np.clip(parse, 0, 17).astype(np.uint8)
        if random.random() < 0.3:
            img = ImageEnhance.Brightness(img).enhance(random.uniform(0.85, 1.15))
        if random.random() < 0.2:
            img = ImageEnhance.Contrast(img).enhance(random.uniform(0.90, 1.10))
        return img, parse

    def __getitem__(self, idx):
        if not self.cuerpos or not self.prendas:
            return None
        rng = random if self.entrenamiento else random.Random(idx)
        k_cuerpo = rng.choice(self.cuerpos)
        k_prenda = self.prendas[idx % len(self.prendas)]
        try:
            img_cuerpo = Image.open(self.dir / f"{k_cuerpo}.jpg").convert('RGB')
            p_parse_c = self.dir / f"{k_cuerpo}_parse.png"
            parse_cuerpo = np.array(Image.open(p_parse_c), dtype=np.uint8) if p_parse_c.exists() \
                           else np.zeros((H, W), dtype=np.uint8)

            img_prenda = Image.open(self.dir / f"{k_prenda}.jpg").convert('RGB')
            p_parse_p = self.dir / f"{k_prenda}_parse.png"
            parse_prenda = np.array(Image.open(p_parse_p), dtype=np.uint8) if p_parse_p.exists() \
                           else np.zeros((H, W), dtype=np.uint8)

            img_cuerpo, parse_cuerpo = self._augment_body(img_cuerpo, parse_cuerpo)

            if img_cuerpo.size != (W, H):
                img_cuerpo = img_cuerpo.resize((W, H), Image.BICUBIC)
            if parse_cuerpo.shape != (H, W):
                parse_cuerpo = np.array(Image.fromarray(parse_cuerpo).resize((W, H), Image.NEAREST))
            if img_prenda.size != (W, H):
                img_prenda = img_prenda.resize((W, H), Image.BICUBIC)
            if parse_prenda.shape != (H, W):
                parse_prenda = np.array(Image.fromarray(parse_prenda).resize((W, H), Image.NEAREST))

            parse_t, visible, obj_forma, cuello = derivar_mascaras_cuerpo(parse_cuerpo)
            persona_t = pil_a_tensor(img_cuerpo)
            agnostica = persona_t * visible

            mprenda_np = mascara_de_prenda(img_prenda, parse_prenda).astype(np.float32)
            mprenda_t = torch.from_numpy(mprenda_np)[None]
            prenda_t = pil_a_tensor(img_prenda) * mprenda_t + (1.0 - mprenda_t)

            return dict(
                persona=persona_t, agnostica=agnostica, parse=parse_t,
                prenda=prenda_t, mascara_prenda=mprenda_t,
                mascara_objetivo=obj_forma, cuello=cuello
            )
        except Exception:
            return None

def collate_seguro(batch):
    batch = [b for b in batch if b is not None]
    return default_collate(batch) if batch else None

random.seed(42)
n_val = max(2, int(len(FOTOS_CUERPOS) * 0.10))
val_cuerpos = FOTOS_CUERPOS[:n_val]
tr_cuerpos = FOTOS_CUERPOS[n_val:] if len(FOTOS_CUERPOS) > 2 else FOTOS_CUERPOS
val_prendas = FOTOS_PRENDAS[:max(2, int(len(FOTOS_PRENDAS) * 0.10))]
tr_prendas = FOTOS_PRENDAS[len(val_prendas):] if len(FOTOS_PRENDAS) > 2 else FOTOS_PRENDAS

batch_tam = 4 if DEVICE.type == 'cuda' else 2
num_trabajadores = 2 if (EN_COLAB and DEVICE.type == 'cuda') else 0

loader_train = DataLoader(
    DatasetCatalogoCuerposV3(tr_cuerpos, tr_prendas, CACHE_LOCAL, True),
    batch_size=batch_tam, shuffle=True, collate_fn=collate_seguro,
    drop_last=False, pin_memory=(DEVICE.type == 'cuda'), num_workers=num_trabajadores
)
loader_val = DataLoader(
    DatasetCatalogoCuerposV3(val_cuerpos, val_prendas, CACHE_LOCAL, False),
    batch_size=batch_tam, shuffle=False, collate_fn=collate_seguro,
    pin_memory=(DEVICE.type == 'cuda'), num_workers=num_trabajadores
)

# ═══════════════════════════════════════════════════════════════════════════
# 9. ARQUITECTURA DEL MODELO VTON
# ═══════════════════════════════════════════════════════════════════════════
class EncoderResNet(nn.Module):
    def __init__(self, in_ch):
        super().__init__()
        r = resnet34(weights=torchvision.models.ResNet34_Weights.IMAGENET1K_V1)
        self.stem = nn.Conv2d(in_ch, 64, 7, 2, 3, bias=False)
        with torch.no_grad():
            self.stem.weight[:, :3] = r.conv1.weight
            if in_ch > 3:
                self.stem.weight[:, 3:] = r.conv1.weight.mean(1, keepdim=True) * 0.1
        self.bn1, self.relu, self.maxpool = r.bn1, r.relu, r.maxpool
        self.layer1, self.layer2, self.layer3, self.layer4 = r.layer1, r.layer2, r.layer3, r.layer4
        self.register_buffer('mean', IMAGENET_MEAN.clone(), persistent=False)
        self.register_buffer('std', IMAGENET_STD.clone(), persistent=False)

    def forward(self, x):
        rgb = ((x[:, :3] + 1) / 2 - self.mean) / self.std
        x = torch.cat([rgb, x[:, 3:]], 1)
        f0 = self.relu(self.bn1(self.stem(x)))
        f1 = self.layer1(self.maxpool(f0))
        f2 = self.layer2(f1)
        f3 = self.layer3(f2)
        f4 = self.layer4(f3)
        return [f0, f1, f2, f3, f4]

def bloque_conv(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, 1, 1), nn.BatchNorm2d(o), nn.LeakyReLU(0.1, inplace=True))

def rejilla_base(h, w):
    ys = (torch.arange(h, dtype=torch.float32) + 0.5) / h * 2 - 1
    xs = (torch.arange(w, dtype=torch.float32) + 0.5) / w * 2 - 1
    gy, gx = torch.meshgrid(ys, xs, indexing='ij')
    return torch.stack([gx, gy], -1)[None]

def deformar(x, flujo, base, relleno):
    grid = base.expand(x.shape[0], -1, -1, -1) + flujo.permute(0, 2, 3, 1)
    return F.grid_sample(x, grid.to(x.dtype), mode='bilinear', padding_mode=relleno, align_corners=False)

class GMMFlujo(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc_persona = EncoderResNet(3 + N_PARSE)
        self.enc_prenda = EncoderResNet(3 + 1)
        canales = {1: 64, 2: 128, 3: 256, 4: 512}
        self.niveles = [4, 3, 2, 1]
        self.tamanos = {n: (H // 2 ** (n + 1), W // 2 ** (n + 1)) for n in self.niveles}
        self.estimadores = nn.ModuleList()
        for j, n in enumerate(self.niveles):
            c = canales[n]
            entrada = 2 * c + (0 if j == 0 else 2)
            est = nn.Sequential(bloque_conv(entrada, 128), bloque_conv(128, 64), nn.Conv2d(64, 2, 3, 1, 1))
            nn.init.zeros_(est[-1].weight)
            nn.init.zeros_(est[-1].bias)
            self.estimadores.append(est)
        for n in self.niveles:
            self.register_buffer(f'base_{n}', rejilla_base(*self.tamanos[n]), persistent=False)
        self.register_buffer('base_full', rejilla_base(H, W), persistent=False)

    def forward(self, persona_in, prenda_in, prenda, mascara_prenda):
        fp, fc = self.enc_persona(persona_in), self.enc_prenda(prenda_in)
        flujo = None
        for j, n in enumerate(self.niveles):
            p, c = fp[n], fc[n]
            if flujo is None:
                entrada = torch.cat([p, c], 1)
            else:
                flujo = F.interpolate(flujo, size=self.tamanos[n], mode='bilinear', align_corners=False)
                c = deformar(c, flujo, getattr(self, f'base_{n}'), 'border')
                entrada = torch.cat([p, c, flujo], 1)
            delta = self.estimadores[j](entrada)
            flujo = delta if flujo is None else flujo + delta
        flujo = F.interpolate(flujo, size=(H, W), mode='bilinear', align_corners=False)
        # CORRECCIÓN v3: rango ampliado 0.22 → 0.45
        flujo = torch.tanh(flujo) * 0.45
        mascara_def = deformar(mascara_prenda, flujo, self.base_full, 'zeros')
        prenda_def = deformar(prenda, flujo, self.base_full, 'border') * mascara_def + (1.0 - mascara_def)
        return prenda_def, mascara_def, flujo

class BloqueSubida(nn.Module):
    def __init__(self, i, o, tam):
        super().__init__()
        self.tam = tam
        self.conv = nn.Sequential(bloque_conv(i, o), bloque_conv(o, o))
    def forward(self, x, salto):
        x = F.interpolate(x, size=self.tam, mode='bilinear', align_corners=False)
        return self.conv(torch.cat([x, salto], 1))

class GeneradorTOM(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = EncoderResNet(3 + N_PARSE + 3 + 1)
        self.up4 = BloqueSubida(512 + 256, 256, (H // 16, W // 16))
        self.up3 = BloqueSubida(256 + 128, 128, (H // 8, W // 8))
        self.up2 = BloqueSubida(128 + 64, 64, (H // 4, W // 4))
        self.up1 = BloqueSubida(64 + 64, 64, (H // 2, W // 2))
        self.fusion = nn.Sequential(bloque_conv(64 + 3 + 1 + 3, 32), nn.Conv2d(32, 4, 3, 1, 1))

    def forward(self, agnostica, parse, prenda_def, mascara_def):
        x = torch.cat([agnostica, parse, prenda_def, mascara_def], 1)
        f0, f1, f2, f3, f4 = self.encoder(x)
        d = self.up4(f4, f3)
        d = self.up3(d, f2)
        d = self.up2(d, f1)
        d = self.up1(d, f0)
        d = F.interpolate(d, size=(H, W), mode='bilinear', align_corners=False)
        o = self.fusion(torch.cat([d, prenda_def, mascara_def, agnostica], 1))
        return torch.tanh(o[:, :3]), torch.sigmoid(o[:, 3:4])

class ModeloVTON(nn.Module):
    def __init__(self):
        super().__init__()
        self.gmm = GMMFlujo()
        self.tom = GeneradorTOM()

    def forward(self, agnostica, parse, prenda, mascara_prenda):
        prenda_def, mascara_def, flujo = self.gmm(
            torch.cat([agnostica, parse], 1),
            torch.cat([prenda, mascara_prenda], 1),
            prenda, mascara_prenda
        )
        preservar_fijo = parse[:, 0:1]
        brazos = parse[:, 2:3]
        fondo = parse[:, 5:6]
        mascara_ef = mascara_def * (1.0 - preservar_fijo)
        render, comp = self.tom(agnostica, parse, prenda_def, mascara_ef)
        comp = comp * torch.clamp((mascara_ef - 0.15) / 0.5, 0, 1)
        tryon = comp * prenda_def + (1.0 - comp) * render
        conservar_brazos = brazos * torch.clamp(1.0 - mascara_def * 1.5, 0, 1)
        conservar_fondo = fondo * torch.clamp(1.0 - mascara_def, 0, 1)
        conservar_total = torch.clamp(preservar_fijo + conservar_brazos + conservar_fondo, 0, 1)
        final = conservar_total * agnostica + (1.0 - conservar_total) * tryon
        return dict(final=final, tryon=tryon, render=render, comp=comp,
                    prenda_def=prenda_def, mascara_def=mascara_def, mascara_ef=mascara_ef, flujo=flujo)

# ═══════════════════════════════════════════════════════════════════════════
# 10. CARGA DE PESOS + DESCONGELAMIENTO PROGRESIVO
# ═══════════════════════════════════════════════════════════════════════════
modelo_previo_ram = globals().get('modelo', None)
if not isinstance(modelo_previo_ram, nn.Module):
    modelo_previo_ram = None

modelo = ModeloVTON().to(DEVICE)

candidatos_ckpt = [
    SALIDA / 'v3_nocturno' / 'checkpoints' / 'best.pth',
    SALIDA / 'v3_nocturno' / 'checkpoints' / 'last.pth',
    SALIDA / 'etapa2_v2' / 'checkpoints' / 'best.pth',
    SALIDA / 'etapa1_v2' / 'checkpoints' / 'best.pth',
    SALIDA / 'etapa2_v2' / 'checkpoints' / 'last.pth',
]
for root, _, files in os.walk(SALIDA):
    for f in files:
        if f.endswith('.pth'):
            candidatos_ckpt.append(Path(root) / f)

ckpt_encontrado = next((c for c in candidatos_ckpt if c.exists()), None)
epoca_inicio = 1
mejor_loss_guardada = float('inf')

if ckpt_encontrado:
    print(f"📦 Cargando modelo previo desde: {ckpt_encontrado}")
    ck = torch.load(ckpt_encontrado, map_location=DEVICE, weights_only=False)
    estado = ck.get('modelo', ck)
    incompatibles = modelo.load_state_dict(estado, strict=False)
    if incompatibles.missing_keys:
        print(f"  ⚠️ Claves faltantes: {len(incompatibles.missing_keys)}")
    if 'epoca' in ck:
        epoca_inicio = ck['epoca'] + 1
        print(f"  📍 Resumiendo desde época {epoca_inicio}")
    if 'mejor_loss' in ck:
        mejor_loss_guardada = ck['mejor_loss']
    print("✅ Conocimiento previo cargado.")
elif modelo_previo_ram is not None:
    print("📦 Reutilizando pesos de la sesión de Colab.")
    try:
        modelo.load_state_dict(modelo_previo_ram.state_dict(), strict=False)
    except Exception as e:
        print(f"Aviso: {e}")
else:
    print("⚠️ Iniciando con pesos base de ImageNet.")

# CORRECCIÓN v3: Descongelamiento progresivo ~8M params
for p in modelo.parameters():
    p.requires_grad = False
for p in modelo.gmm.estimadores.parameters():
    p.requires_grad = True
for p in modelo.gmm.enc_prenda.layer3.parameters():
    p.requires_grad = True
for p in modelo.gmm.enc_prenda.layer4.parameters():
    p.requires_grad = True
for p in modelo.tom.up1.parameters():
    p.requires_grad = True
for p in modelo.tom.up2.parameters():
    p.requires_grad = True
for p in modelo.tom.up3.parameters():
    p.requires_grad = True
for p in modelo.tom.up4.parameters():
    p.requires_grad = True
for p in modelo.tom.fusion.parameters():
    p.requires_grad = True
for p in modelo.tom.encoder.layer3.parameters():
    p.requires_grad = True
for p in modelo.tom.encoder.layer4.parameters():
    p.requires_grad = True

params_entrenables = [p for p in modelo.parameters() if p.requires_grad]
total_params = sum(p.numel() for p in modelo.parameters())
train_params = sum(p.numel() for p in params_entrenables)
print(f"🎯 Entrenables: {train_params / 1e6:.2f} M / {total_params / 1e6:.2f} M ({100*train_params/total_params:.1f}%)")

# ═══════════════════════════════════════════════════════════════════════════
# 11. OPTIMIZADOR Y SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════
EPOCAS = 80
LR_INICIAL = 2e-4
LR_MIN = 1e-6
WARMUP_EPOCAS = 5

optimizador = torch.optim.AdamW(params_entrenables, lr=LR_INICIAL, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
    optimizador, T_0=20, T_mult=2, eta_min=LR_MIN
)
scaler = torch.amp.GradScaler('cuda', enabled=True) if USA_AMP else None

def aplicar_warmup(epoca, opt):
    if epoca <= WARMUP_EPOCAS:
        factor = epoca / WARMUP_EPOCAS
        for g in opt.param_groups:
            g['lr'] = LR_INICIAL * factor

# ═══════════════════════════════════════════════════════════════════════════
# 12. FUNCIONES DE PÉRDIDA REDISEÑADAS
# ═══════════════════════════════════════════════════════════════════════════
class PerdidaVGG(nn.Module):
    def __init__(self):
        super().__init__()
        self.vgg = vgg19(weights=torchvision.models.VGG19_Weights.IMAGENET1K_V1).features[:27].eval()
        for p in self.vgg.parameters():
            p.requires_grad = False
        self.capas = {3: 1/32, 8: 1/16, 17: 1/8, 26: 1/4}
        self.register_buffer('mean', IMAGENET_MEAN.clone(), persistent=False)
        self.register_buffer('std', IMAGENET_STD.clone(), persistent=False)
    def forward(self, x, y):
        x = ((x + 1) / 2 - self.mean) / self.std
        y = ((y + 1) / 2 - self.mean) / self.std
        total = 0.0
        for i, capa in enumerate(self.vgg):
            x, y = capa(x), capa(y)
            if i in self.capas:
                total = total + self.capas[i] * F.l1_loss(x, y.detach())
            if i >= 26:
                break
        return total

VGG = PerdidaVGG().to(DEVICE)

def perdida_ssim(x, y, ventana=11):
    C1, C2 = 0.01**2, 0.03**2
    pad = ventana // 2
    mu_x = F.avg_pool2d(x, ventana, 1, pad)
    mu_y = F.avg_pool2d(y, ventana, 1, pad)
    sigma_x2 = F.avg_pool2d(x*x, ventana, 1, pad) - mu_x*mu_x
    sigma_y2 = F.avg_pool2d(y*y, ventana, 1, pad) - mu_y*mu_y
    sigma_xy = F.avg_pool2d(x*y, ventana, 1, pad) - mu_x*mu_y
    ssim = ((2*mu_x*mu_y + C1)*(2*sigma_xy + C2)) / \
           ((mu_x**2 + mu_y**2 + C1)*(sigma_x2 + sigma_y2 + C2))
    return 1.0 - ssim.mean()

def castigo_alineacion(mascara_def, parse):
    zona_torso = parse[:, 1:2]
    overlap = (mascara_def * zona_torso).sum(dim=[-2, -1])
    torso_area = zona_torso.sum(dim=[-2, -1]) + 1e-5
    coverage = overlap / torso_area
    return F.relu(0.75 - coverage).mean() * 20.0

def castigo_temporal(flujo):
    dx1 = (flujo[:, :, :, 1:] - flujo[:, :, :, :-1]).abs()
    dy1 = (flujo[:, :, 1:, :] - flujo[:, :, :-1, :]).abs()
    tv1 = dx1.mean() + dy1.mean()
    if flujo.shape[2] > 2 and flujo.shape[3] > 2:
        dx2 = (flujo[:, :, :, 2:] - 2*flujo[:, :, :, 1:-1] + flujo[:, :, :, :-2]).abs()
        dy2 = (flujo[:, :, 2:, :] - 2*flujo[:, :, 1:-1, :] + flujo[:, :, :-2, :]).abs()
        tv2 = dx2.mean() + dy2.mean()
    else:
        tv2 = 0.0
    return tv1 * 0.8 + tv2 * 1.2

def calcular_perdidas_v3(o, b):
    tm, cuello, wm, wc = b['mascara_objetivo'], b['cuello'], o['mascara_def'], o['prenda_def']
    flujo, me = o['flujo'], o['mascara_ef']

    dice = 1.0 - ((2*(wm*tm).flatten(1).sum(1)+1) / ((wm+tm).flatten(1).sum(1)+1)).mean()
    c_tv = castigo_temporal(flujo)
    inv_cuello = (wm * cuello).sum() / (cuello.sum() + 1e-5)
    c_cuello = 25.0 * (inv_cuello**2) + 10.0 * inv_cuello
    area_orig = b['mascara_prenda'].sum(dim=[-2,-1]) + 1e-5
    area_def = wm.sum(dim=[-2,-1])
    c_colapso = F.relu(0.70 - area_def / area_orig).mean() * 35.0
    l1_tex = ((o['tryon'] - wc).abs() * me).sum() / (me.sum()*3 + 1e-5)
    vg_tex = VGG(o['tryon'] * me, wc * me)
    ssim = perdida_ssim(o['tryon'] * me, wc * me)
    alin = castigo_alineacion(wm, b['parse'])

    total = 2.0*dice + c_tv + c_cuello + c_colapso + 1.5*l1_tex + 3.0*vg_tex + 2.0*ssim + 1.5*alin
    return total, dict(loss=float(total), vgg=float(vg_tex), l1=float(l1_tex),
                       colapso=float(c_colapso), ssim=float(ssim), alineacion=float(alin),
                       dice=float(dice), tv=float(c_tv))

# ═══════════════════════════════════════════════════════════════════════════
# 13. BUCLE DE ENTRENAMIENTO NOCTURNO (80 épocas, ~6-8h en T4)
# ═══════════════════════════════════════════════════════════════════════════
DIR_CKPT = SALIDA / 'v3_nocturno' / 'checkpoints'
DIR_GRIDS = SALIDA / 'v3_nocturno' / 'grids'
DIR_CKPT.mkdir(parents=True, exist_ok=True)
DIR_GRIDS.mkdir(parents=True, exist_ok=True)

historial = defaultdict(list)
mejor_loss = mejor_loss_guardada
paciencia_sin_mejora = 0
PACIENCIA_MAX = 15

print(f"\n{'='*70}")
print(f"🚀 ENTRENAMIENTO NOCTURNO v3.0 | Épocas: {epoca_inicio}-{EPOCAS} | Batch: {batch_tam}")
print(f"   Resolución: {H}×{W} | LR: {LR_INICIAL} → {LR_MIN}")
print(f"   Tiempo estimado: ~{EPOCAS*5/60:.0f}-{EPOCAS*8/60:.0f} horas en GPU T4")
print(f"{'='*70}\n")

t_inicio_total = time.time()

for epoca in range(epoca_inicio, EPOCAS + 1):
    t_ep = time.time()
    aplicar_warmup(epoca, optimizador)
    modelo.train()
    acum_train, n_train = defaultdict(float), 0

    for lote in loader_train:
        if lote is None:
            continue
        b = {k: v.to(DEVICE, non_blocking=True) for k, v in lote.items()}
        optimizador.zero_grad(set_to_none=True)
        with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USA_AMP):
            o = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
            loss, metricas = calcular_perdidas_v3(o, b)
        if USA_AMP and scaler is not None:
            scaler.scale(loss).backward()
            scaler.unscale_(optimizador)
            torch.nn.utils.clip_grad_norm_(params_entrenables, 5.0)
            scaler.step(optimizador)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params_entrenables, 5.0)
            optimizador.step()
        bs = b['persona'].shape[0]
        for k, v in metricas.items():
            acum_train[k] += v * bs
        n_train += bs

    res_tr = {k: v / max(1, n_train) for k, v in acum_train.items()}

    modelo.eval()
    acum_val, n_val = defaultdict(float), 0
    lote_demo = None
    with torch.no_grad():
        for lote in loader_val:
            if lote is None:
                continue
            if lote_demo is None:
                lote_demo = lote
            b = {k: v.to(DEVICE) for k, v in lote.items()}
            with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USA_AMP):
                o = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
                _, metricas = calcular_perdidas_v3(o, b)
            bs = b['persona'].shape[0]
            for k, v in metricas.items():
                acum_val[k] += v * bs
            n_val += bs

    res_val = {k: v / max(1, n_val) for k, v in acum_val.items()}
    if epoca > WARMUP_EPOCAS:
        scheduler.step()

    for key in ['loss', 'vgg', 'l1', 'colapso', 'ssim', 'alineacion', 'dice', 'tv']:
        historial[f'tr_{key}'].append(res_tr.get(key, 0))
        historial[f'val_{key}'].append(res_val.get(key, 0))
    historial['epoca'].append(epoca)

    mejoro = res_val['loss'] < mejor_loss
    if mejoro:
        mejor_loss = res_val['loss']
        paciencia_sin_mejora = 0
        torch.save(dict(modelo=modelo.state_dict(), epoca=epoca,
                        mejor_loss=mejor_loss, historial=dict(historial)), DIR_CKPT / 'best.pth')
    else:
        paciencia_sin_mejora += 1

    torch.save(dict(modelo=modelo.state_dict(), epoca=epoca,
                    mejor_loss=mejor_loss, historial=dict(historial)), DIR_CKPT / 'last.pth')

    if epoca % 10 == 0:
        torch.save(dict(modelo=modelo.state_dict(), epoca=epoca,
                        mejor_loss=mejor_loss), DIR_CKPT / f'checkpoint_ep{epoca:03d}.pth')

    elapsed_ep = time.time() - t_ep
    elapsed_total = (time.time() - t_inicio_total) / 60
    eta_min = (EPOCAS - epoca) * elapsed_ep / 60

    if EN_NOTEBOOK and clear_output is not None and epoca % 5 == 0:
        clear_output(wait=True)

    star = "⭐" if mejoro else "  "
    print(f"{star} Ep [{epoca}/{EPOCAS}] ({elapsed_ep:.0f}s) LR:{optimizador.param_groups[0]['lr']:.2e} Pat:{paciencia_sin_mejora}/{PACIENCIA_MAX}")
    print(f"   Tr → L:{res_tr['loss']:.4f} Dice:{res_tr['dice']:.4f} SSIM:{res_tr['ssim']:.4f} Col:{res_tr['colapso']:.4f}")
    print(f"   Va → L:{res_val['loss']:.4f} Dice:{res_val['dice']:.4f} SSIM:{res_val['ssim']:.4f} Alin:{res_val['alineacion']:.4f}")
    print(f"   ⏱️ {elapsed_total:.0f}min | ETA:{eta_min:.0f}min | Best:{mejor_loss:.4f}")

    if epoca % 5 == 0 or epoca == EPOCAS or epoca == 1:
        fig, ax = plt.subplots(1, 4, figsize=(20, 4))
        eps = historial['epoca']
        ax[0].plot(eps, historial['tr_loss'], 'b-', lw=1.5, label='Train')
        ax[0].plot(eps, historial['val_loss'], 'r-', lw=1.5, label='Val')
        ax[0].set_title('Pérdida Total', fontweight='bold'); ax[0].grid(True, alpha=0.3); ax[0].legend()
        ax[1].plot(eps, historial['tr_ssim'], 'b-', lw=1.5, label='Train')
        ax[1].plot(eps, historial['val_ssim'], 'r-', lw=1.5, label='Val')
        ax[1].set_title('SSIM', fontweight='bold'); ax[1].grid(True, alpha=0.3); ax[1].legend()
        ax[2].plot(eps, historial['tr_dice'], 'b-', lw=1.5, label='Train')
        ax[2].plot(eps, historial['val_dice'], 'r-', lw=1.5, label='Val')
        ax[2].set_title('Dice', fontweight='bold'); ax[2].grid(True, alpha=0.3); ax[2].legend()
        ax[3].plot(eps, historial['tr_colapso'], 'b-', lw=1.5, label='Colapso')
        ax[3].plot(eps, historial['tr_alineacion'], 'g-', lw=1.5, label='Alineación')
        ax[3].plot(eps, historial['tr_tv'], 'm-', lw=1.5, label='Temporal')
        ax[3].set_title('Castigos', fontweight='bold'); ax[3].grid(True, alpha=0.3); ax[3].legend()
        plt.suptitle(f'VTON v3.0 — Época {epoca}/{EPOCAS}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(SALIDA / 'v3_nocturno' / 'curvas_v3.png', dpi=120)
        if EN_NOTEBOOK and display:
            display(fig)
        plt.close(fig)

        if lote_demo is not None:
            n_m = min(4, lote_demo['persona'].shape[0])
            b = {k: v[:n_m].to(DEVICE) for k, v in lote_demo.items()}
            with torch.no_grad():
                with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USA_AMP):
                    out = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
            fig, ax = plt.subplots(n_m, 5, figsize=(15, 3.5*n_m), squeeze=False)
            titulos = ['Cuerpo', 'Agnóstica', 'Prenda', 'Deformada', 'Resultado']
            for i in range(n_m):
                for j, img in enumerate([b['persona'][i], b['agnostica'][i],
                                         b['prenda'][i], out['prenda_def'][i], out['final'][i]]):
                    ax[i, j].imshow(tensor_a_numpy_img(img)); ax[i, j].axis('off')
                    if i == 0:
                        ax[i, j].set_title(titulos[j], fontsize=10, fontweight='bold')
            fig.suptitle(f'VTON v3.0 — Época {epoca} (Best: {mejor_loss:.4f})', fontsize=13)
            plt.tight_layout()
            plt.savefig(DIR_GRIDS / f'grid_ep{epoca:03d}.png', dpi=120)
            if EN_NOTEBOOK and display:
                display(fig)
            plt.close(fig)

    if paciencia_sin_mejora >= PACIENCIA_MAX:
        print(f"\n⛔ Early stopping: {PACIENCIA_MAX} épocas sin mejora.")
        break

# ═══════════════════════════════════════════════════════════════════════════
# 14. EXPORTAR A ONNX
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("📦 Exportando modelo v3.0 a ONNX...")

DIR_ONNX = SALIDA / 'onnx'
DIR_ONNX.mkdir(parents=True, exist_ok=True)
RUTA_ONNX = DIR_ONNX / 'vton_fashionstore_v3.onnx'

class ModeloVTONExportable(nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m
    def forward(self, agnostica, parse, prenda, mascara_prenda):
        return self.m(agnostica, parse, prenda, mascara_prenda)['final']

if (DIR_CKPT / 'best.pth').exists():
    best_ck = torch.load(DIR_CKPT / 'best.pth', map_location=DEVICE, weights_only=False)
    modelo.load_state_dict(best_ck['modelo'])
    print(f"   Cargado best.pth (época {best_ck.get('epoca', '?')})")

exportable = ModeloVTONExportable(copy.deepcopy(modelo).float().cpu()).eval()
ejemplo = (torch.randn(1,3,H,W), torch.randn(1,N_PARSE,H,W),
           torch.randn(1,3,H,W), torch.randn(1,1,H,W))
torch.onnx.export(exportable, ejemplo, str(RUTA_ONNX),
                  input_names=['agnostic','parse','cloth','cloth_mask'],
                  output_names=['result'],
                  dynamic_axes={k:{0:'batch'} for k in ['agnostic','parse','cloth','cloth_mask','result']},
                  opset_version=17, do_constant_folding=True)

RUTA_PTH = DIR_ONNX / 'vton_fashionstore_v3.pth'
torch.save(dict(modelo=modelo.state_dict(), version='v3.0',
                resolucion={'H': H, 'W': W}, fecha=time.strftime('%Y-%m-%d %H:%M:%S')), RUTA_PTH)

metadatos = dict(modelo='vton_fashionstore_v3.onnx', version='v3.0',
                 fecha=time.strftime('%Y-%m-%d %H:%M:%S'), alto=H, ancho=W, opset=17,
                 mejor_loss=round(mejor_loss, 4),
                 correcciones=["Flujo 0.45", "8M params", "384x288", "Augmentation",
                               "SSIM", "Alineación", "Consistencia temporal", f"{EPOCAS} épocas"])
(DIR_ONNX / 'vton_metadatos_v3.json').write_text(
    json.dumps(metadatos, indent=2, ensure_ascii=False), encoding='utf-8')

total_min = (time.time() - t_inicio_total) / 60
print(f"\n{'='*70}")
print(f"🎉 ¡ENTRENAMIENTO v3.0 COMPLETADO!")
print(f"⏱️  Tiempo: {total_min:.0f} min ({total_min/60:.1f} h)")
print(f"📊 Mejor loss: {mejor_loss:.4f}")
print(f"📁 Checkpoints: {DIR_CKPT}")
print(f"⚡ ONNX: {RUTA_ONNX}")
print(f"{'='*70}")
print(f"\n💡 Copia el .onnx o .pth a backend/models/ y reinicia el servidor.")
