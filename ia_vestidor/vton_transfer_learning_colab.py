# [CELDA ÚNICA] RE-ENTRENAMIENTO VTON: CARGAR IA PREVIA + CATÁLOGO + CUERPOS DIVERSOS + CASTIGOS
# ==============================================================================================
# Esta celda hace TODO el proceso en un solo paso:
# 1. Carga la IA ya entrenada ('best.pth') sin borrar su conocimiento (Transfer Learning).
# 2. Usa 'entrenamiento_ia_ropa/cuerpos' (diversos cuerpos y poses de mujeres) y el catálogo
#    ('Vestidos', 'Tops - Crop Tops', 'Suéteres y Tejidos', 'Pantalones', etc.).
# 3. Corrige el error de "solo cambiar el color":
#    - Las mangas y el corte de la prenda nueva se dibujan sobre los brazos y el torso.
#    - Respeta estrictamente el CABELLO, rostro y cuello (Regla de Oro).
#    - Aplica CASTIGO SEVERO ANTI-COLAPSO para que la prenda no pierda mangas ni se achique.
#    - Aplica pérdida perceptual VGG (triple peso) para evitar pixelado y preservar texturas.
#    - Suaviza el flujo de deformación para que funcione fluido con la cámara/video en movimiento.
# 4. Genera gráficas de evolución en vivo y un grid visual con el resultado adaptado.
# 5. Exporta el modelo final a ONNX corregido para FastAPI y la aplicación móvil.
# ==============================================================================================

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
from pathlib import Path
from collections import defaultdict

# 1. Entorno y Dependencias
EN_COLAB = 'google.colab' in sys.modules or os.path.isdir('/content/sample_data')
EN_NOTEBOOK = 'ipykernel' in sys.modules

if EN_COLAB:
    subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-q',
        'transformers', 'onnx', 'onnxruntime', 'onnxscript',
        'pandas', 'pyarrow', 'accelerate'
    ], check=False)

import numpy as np
from PIL import Image, ImageOps, ImageFilter
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

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
USA_AMP = DEVICE.type == 'cuda'
torch.backends.cudnn.benchmark = DEVICE.type == 'cuda'

print(f"🚀 Dispositivo: {DEVICE} | Precisión mixta AMP: {USA_AMP}")

H, W = 256, 192
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

# 2. Rutas en Google Drive
def obtener_base_dir():
    if not EN_COLAB:
        return Path('.')
    try:
        from google.colab import drive
        if not os.path.exists('/content/drive/MyDrive'):
            drive.mount('/content/drive', force_remount=False)
    except Exception as e:
        pass
    candidatos = [
        Path('/content/drive/MyDrive/entrenamiento_ia_vestidor'),
        Path('/content/gdrive/MyDrive/entrenamiento_ia_vestidor'),
        Path('/content/drive/MyDrive'),
        Path('.')
    ]
    for c in candidatos:
        if (c / 'entrenamiento_ia_ropa').is_dir():
            return c
    return Path('/content/drive/MyDrive/entrenamiento_ia_vestidor')

BASE_DIR = obtener_base_dir()
DIR_ROPA = BASE_DIR / 'entrenamiento_ia_ropa'
SALIDA = BASE_DIR / 'resultados_vton'
CACHE_DRIVE = SALIDA / 'cache'
CACHE_LOCAL = Path('/content/cache_vton') if EN_COLAB else CACHE_DRIVE

for p in (SALIDA, CACHE_DRIVE, CACHE_LOCAL):
    p.mkdir(parents=True, exist_ok=True)

# 3. Identificar carpeta 'cuerpos' y catálogo de ropa de mujer
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

DIR_CUERPOS = DIR_ROPA / 'cuerpos'
if not DIR_CUERPOS.is_dir() and DIR_ROPA.exists():
    try:
        for d in DIR_ROPA.iterdir():
            if d.is_dir() and 'cuerpo' in norm_txt(d.name).lower():
                DIR_CUERPOS = d
                break
    except Exception:
        pass

# A. Cargar cuerpos: primero desde cuerpos_metadata.csv si existe
csv_cuerpos = DIR_CUERPOS / 'cuerpos_metadata.csv'
if not csv_cuerpos.exists():
    csv_cuerpos = DIR_ROPA / 'cuerpos_metadata.csv'
if not csv_cuerpos.exists():
    csv_cuerpos = BASE_DIR / 'cuerpos_metadata.csv'

if csv_cuerpos.exists():
    try:
        with open(csv_cuerpos, mode='r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fn = norm_txt(row.get('filename', ''))
                for c in [DIR_CUERPOS / fn, DIR_ROPA / 'cuerpos' / fn, DIR_ROPA / fn]:
                    if c.exists() and c not in FOTOS_CUERPOS:
                        FOTOS_CUERPOS.append(c)
                        break
    except Exception as e:
        print(f"Aviso al leer cuerpos_metadata.csv: {e}")

# Escaneo directo de carpeta cuerpos
for img in listar_imgs(DIR_CUERPOS):
    if img not in FOTOS_CUERPOS:
        FOTOS_CUERPOS.append(img)

# B. Cargar prendas: primero desde dataset_metadata.csv
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
                
                candidatos = [
                    DIR_ROPA / rel,
                    DIR_ROPA / cat / fn_clean,
                    DIR_ROPA / cat / fn_orig,
                    DIR_ROPA / fn_clean,
                    DIR_ROPA / fn_orig
                ]
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

# Si faltan prendas por indexar, escanear subcarpetas directamente
if DIR_ROPA.exists():
    try:
        for sub in DIR_ROPA.iterdir():
            sub_nom = norm_txt(sub.name)
            if sub.is_dir() and sub != DIR_CUERPOS and 'cuerpo' not in sub_nom.lower() and not sub_nom.startswith('.'):
                imgs = listar_imgs(sub)
                for img in imgs:
                    if img not in FOTOS_PRENDAS:
                        FOTOS_PRENDAS.append(img)
                        CATEGORIAS[sub_nom] = CATEGORIAS.get(sub_nom, 0) + 1
    except Exception:
        pass

# Respaldo con os.walk recursivo si FUSE no listó subcarpetas
if len(FOTOS_PRENDAS) == 0 and DIR_ROPA.exists():
    for f in listar_imgs(DIR_ROPA):
        if 'cuerpo' not in str(f).lower():
            cat = norm_txt(f.parent.name)
            CATEGORIAS[cat] = CATEGORIAS.get(cat, 0) + 1
            if f not in FOTOS_PRENDAS:
                FOTOS_PRENDAS.append(f)

print(f"\n📂 Datos detectados para el re-entrenamiento:")
print(f"  🧍‍♀️ Cuerpos diversos de mujeres ('cuerpos/'): {len(FOTOS_CUERPOS)} fotos")
for cat, cnt in sorted(CATEGORIAS.items()):
    print(f"  👗 Subcarpeta Catálogo [{cat}]: {cnt} prendas")
print(f"  👉 Total prendas del catálogo: {len(FOTOS_PRENDAS)}")

if not FOTOS_CUERPOS:
    print("⚠️  Buscando fotos de personas de respaldo en archive...")
    for cand_p in [BASE_DIR / 'archive', BASE_DIR / 'archive' / 'selected_images']:
        p_imgs = listar_imgs(cand_p)
        if p_imgs:
            FOTOS_CUERPOS.extend(p_imgs[:300])
            break

# 4. Utilidades y Parsing Humano (SegFormer)
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

# Asegurar caché en Drive
def asegurar_cache(rutas, lote=16):
    pendientes = [r for r in rutas if not (CACHE_DRIVE / f"{clave_de(r)}.jpg").exists() or not (CACHE_DRIVE / f"{clave_de(r)}_parse.png").exists()]
    if pendientes:
        parser = obtener_parser()
        print(f"⏳ Preprocesando {len(pendientes)} imágenes nuevas...")
        for i in range(0, len(pendientes), lote):
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

asegurar_cache(FOTOS_CUERPOS)
asegurar_cache(FOTOS_PRENDAS)

if CACHE_LOCAL != CACHE_DRIVE:
    shutil.copytree(CACHE_DRIVE, CACHE_LOCAL, dirs_exist_ok=True)

# 5. Máscaras y Regla de Oro (Cabello, Rostro, Cuello y Mangas Liberadas)
def derivar_mascaras_cuerpo(parse):
    alto, ancho = parse.shape
    ropa_sup = np.isin(parse, [L['upper-clothes'], L['dress']])
    cara_pelo = np.isin(parse, [L['hat'], L['hair'], L['sunglasses'], L['face']])
    brazos = np.isin(parse, [L['left-arm'], L['right-arm']])
    inferior = np.isin(parse, [L['skirt'], L['pants'], L['belt'], L['left-shoe'], L['right-shoe'],
                               L['left-leg'], L['right-leg'], L['bag']])
    
    # Cuello protegido
    cuello = np.zeros_like(ropa_sup)
    ys, xs = np.nonzero(parse == L['face'])
    if ys.size > 20:
        y1, x0, x1 = ys.max(), xs.min(), xs.max()
        h_cara, w_cara = y1 - ys.min() + 1, x1 - x0 + 1
        cuello[y1:min(alto, y1 + int(0.45 * h_cara)),
               max(0, x0 - int(0.10 * w_cara)):min(ancho, x1 + int(0.10 * w_cara) + 1)] = True
        cuello &= ~ropa_sup & ~cara_pelo

    # Zona que se limpia en la agnóstica para permitir mangas y cortes nuevos
    area_ropa = dilatar(ropa_sup, 9)
    area_mangas = brazos & dilatar(ropa_sup, 16)
    area_borrar = (area_ropa | area_mangas) & ~cara_pelo & ~cuello

    # Cabello, cara, cuello e inferior NUNCA se sobreescriben
    preservar_fijo = cara_pelo | cuello | inferior

    fondo = parse == L['background']
    silueta = np.array(Image.fromarray((parse > 0).astype(np.uint8) * 255)
                       .resize((ancho // 8, alto // 8), Image.BILINEAR)
                       .resize((ancho, alto), Image.BILINEAR)) / 255.0

    t = lambda a: torch.from_numpy(np.asarray(a, dtype=np.float32))[None]
    parse_t = torch.cat([
        t(preservar_fijo),
        t(area_borrar),
        t(brazos),
        t(cara_pelo | cuello),
        t(silueta),
        t(fondo)
    ], 0)

    # El área donde la prenda puede crecer incluye torso y brazos
    mascara_anatomica = torch.from_numpy(((ropa_sup | brazos) & ~preservar_fijo).astype(np.float32))[None]
    visible = 1.0 - t(area_borrar)

    return parse_t, visible, mascara_anatomica, t(cuello)

# 6. Dataset para Re-entrenamiento
class DatasetCatalogoCuerpos(Dataset):
    def __init__(self, lista_cuerpos, lista_prendas, dir_cache, entrenamiento=True):
        self.cuerpos = [clave_de(r) for r in lista_cuerpos]
        self.prendas = [clave_de(r) for r in lista_prendas]
        self.dir = Path(dir_cache)
        self.entrenamiento = entrenamiento

    def __len__(self):
        return max(len(self.prendas) * 3, 200) if self.entrenamiento else min(len(self.prendas), 40)

    def __getitem__(self, idx):
        rng = random if self.entrenamiento else random.Random(idx)
        k_cuerpo = rng.choice(self.cuerpos)
        k_prenda = self.prendas[idx % len(self.prendas)]
        try:
            img_cuerpo = Image.open(self.dir / f"{k_cuerpo}.jpg").convert('RGB')
            parse_cuerpo = np.array(Image.open(self.dir / f"{k_cuerpo}_parse.png"), dtype=np.uint8)

            img_prenda = Image.open(self.dir / f"{k_prenda}.jpg").convert('RGB')
            parse_prenda = np.array(Image.open(self.dir / f"{k_prenda}_parse.png"), dtype=np.uint8)

            if self.entrenamiento and random.random() < 0.5:
                img_cuerpo = ImageOps.mirror(img_cuerpo)
                parse_cuerpo = np.ascontiguousarray(parse_cuerpo[:, ::-1])

            parse_t, visible, obj_forma, cuello = derivar_mascaras_cuerpo(parse_cuerpo)
            persona_t = pil_a_tensor(img_cuerpo)
            agnostica = persona_t * visible

            mprenda_np = mascara_de_prenda(img_prenda, parse_prenda).astype(np.float32)
            mprenda_t = torch.from_numpy(mprenda_np)[None]
            prenda_t = pil_a_tensor(img_prenda) * mprenda_t + (1.0 - mprenda_t)

            return dict(
                persona=persona_t,
                agnostica=agnostica,
                parse=parse_t,
                prenda=prenda_t,
                mascara_prenda=mprenda_t,
                mascara_objetivo=obj_forma,
                cuello=cuello
            )
        except Exception:
            return None

def collate_seguro(batch):
    batch = [b for b in batch if b is not None]
    return default_collate(batch) if batch else None

random.seed(42)
n_val = max(1, int(len(FOTOS_CUERPOS) * 0.15))
val_cuerpos = FOTOS_CUERPOS[:n_val]
tr_cuerpos = FOTOS_CUERPOS[n_val:] if len(FOTOS_CUERPOS) > 1 else FOTOS_CUERPOS

val_prendas = FOTOS_PRENDAS[:max(1, int(len(FOTOS_PRENDAS) * 0.15))]
tr_prendas = FOTOS_PRENDAS[len(val_prendas):] if len(FOTOS_PRENDAS) > 1 else FOTOS_PRENDAS

loader_train = DataLoader(DatasetCatalogoCuerpos(tr_cuerpos, tr_prendas, CACHE_LOCAL, True),
                          batch_size=4, shuffle=True, collate_fn=collate_seguro, drop_last=True)
loader_val = DataLoader(DatasetCatalogoCuerpos(val_cuerpos, val_prendas, CACHE_LOCAL, False),
                        batch_size=4, shuffle=False, collate_fn=collate_seguro)

# 7. Arquitectura Modelo VTON
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
        flujo = torch.tanh(flujo) * 0.22
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
        preservar_fijo = parse[:, 0:1]  # Cabello, cara, cuello, piernas
        brazos = parse[:, 2:3]
        fondo = parse[:, 5:6]

        mascara_ef = mascara_def * (1.0 - preservar_fijo)
        render, comp = self.tom(agnostica, parse, prenda_def, mascara_ef)

        comp = comp * torch.clamp((mascara_ef - 0.15) / 0.5, 0, 1)
        tryon = comp * prenda_def + (1.0 - comp) * render

        # Las mangas se dibujan sobre los brazos; la piel descubierta se conserva
        conservar_brazos = brazos * torch.clamp(1.0 - mascara_def * 1.5, 0, 1)
        conservar_fondo = fondo * torch.clamp(1.0 - mascara_def, 0, 1)
        conservar_total = torch.clamp(preservar_fijo + conservar_brazos + conservar_fondo, 0, 1)

        final = conservar_total * agnostica + (1.0 - conservar_total) * tryon
        return dict(final=final, tryon=tryon, render=render, comp=comp,
                    prenda_def=prenda_def, mascara_def=mascara_def, mascara_ef=mascara_ef, flujo=flujo)

# 8. Carga de Pesos Previos Sin Pérdida de Conocimiento (Transfer Learning)
modelo_previo_ram = globals().get('modelo', None)
if not isinstance(modelo_previo_ram, nn.Module):
    modelo_previo_ram = None

modelo = ModeloVTON().to(DEVICE)

candidatos_ckpt = [
    SALIDA / 'etapa2_v2' / 'checkpoints' / 'best.pth',
    SALIDA / 'etapa1_v2' / 'checkpoints' / 'best.pth',
    SALIDA / 'etapa2_v2' / 'checkpoints' / 'last.pth',
    SALIDA / 'etapa1_v2' / 'checkpoints' / 'last.pth',
]
for root, _, files in os.walk(SALIDA):
    for f in files:
        if f.endswith('.pth'):
            candidatos_ckpt.append(Path(root) / f)

ckpt_encontrado = next((c for c in candidatos_ckpt if c.exists()), None)
if ckpt_encontrado:
    print(f"📦 Cargando modelo previamente entrenado desde Drive: {ckpt_encontrado}")
    ck = torch.load(ckpt_encontrado, map_location=DEVICE, weights_only=False)
    modelo.load_state_dict(ck.get('modelo', ck), strict=False)
    print("✅ Conocimiento previo cargado exitosamente desde Google Drive.")
elif modelo_previo_ram is not None:
    print("📦 Reutilizando los pesos del 'modelo' presente en la memoria de esta sesión de Colab.")
    try:
        modelo.load_state_dict(modelo_previo_ram.state_dict(), strict=False)
        print("✅ Conocimiento previo transferido exitosamente desde la memoria RAM.")
    except Exception as e:
        print(f"Aviso al transferir pesos de memoria: {e}")
else:
    print("⚠️  Iniciando con pesos base de ImageNet.")

# Congelar encoders para conservar el conocimiento y solo adaptar la deformación y fusión
for p in modelo.parameters():
    p.requires_grad = False
for p in modelo.gmm.estimadores.parameters():
    p.requires_grad = True
for p in modelo.tom.up1.parameters():
    p.requires_grad = True
for p in modelo.tom.fusion.parameters():
    p.requires_grad = True

params_entrenables = [p for p in modelo.parameters() if p.requires_grad]
print(f"🎯 Parámetros entrenables para el catálogo: {sum(p.numel() for p in params_entrenables) / 1e6:.2f} M (Backbone protegido)")

optimizador = torch.optim.AdamW(params_entrenables, lr=4e-5, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizador, mode='min', factor=0.6, patience=2)
scaler = torch.amp.GradScaler('cuda', enabled=True) if USA_AMP else None

# 9. Función de Pérdidas con Castigos Severos
class PerdidaVGG(nn.Module):
    def __init__(self):
        super().__init__()
        self.vgg = vgg19(weights=torchvision.models.VGG19_Weights.IMAGENET1K_V1).features[:27].eval()
        for p in self.vgg.parameters():
            p.requires_grad = False
        self.capas = {3: 1 / 32, 8: 1 / 16, 17: 1 / 8, 26: 1 / 4}
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

def calcular_perdidas_con_castigos(o, b):
    tm = b['mascara_objetivo']
    cuello = b['cuello']
    wm = o['mascara_def']
    wc = o['prenda_def']
    flujo = o['flujo']
    me = o['mascara_ef']

    # 1. Castigo TV de Suavidad (movimiento estable en video/cámara)
    tv1 = (flujo[:, :, 1:] - flujo[:, :, :-1]).abs().mean() + (flujo[:, :, :, 1:] - flujo[:, :, :, :-1]).abs().mean()
    tv2 = (flujo[:, :, 2:] - 2 * flujo[:, :, 1:-1] + flujo[:, :, :-2]).abs().mean() if flujo.shape[2] > 2 else 0.0
    castigo_tv = (tv1 + 0.5 * tv2) * 1.5

    # 2. Castigo Cuello/Rostro
    inv_cuello = (wm * cuello).sum() / (cuello.sum() + 1e-5)
    castigo_cuello = 25.0 * (inv_cuello ** 2) + 10.0 * inv_cuello

    # 3. Dice de Silueta Anatómica
    dice = 1.0 - ((2 * (wm * tm).flatten(1).sum(1) + 1) / ((wm + tm).flatten(1).sum(1) + 1)).mean()

    # 4. 🔥 CASTIGO ANTI-COLAPSO DE MANGAS Y ESTRUCTURA (Evita que solo cambie de color)
    area_orig = b['mascara_prenda'].sum(dim=[-2, -1]) + 1e-5
    area_def = wm.sum(dim=[-2, -1])
    ratio_area = area_def / area_orig
    castigo_colapso = F.relu(0.70 - ratio_area).mean() * 35.0

    # 5. 🔥 Nitidez y Textura de la Prenda (VGG 3.0x + L1) para CERO pixelado
    l1_textura = ((o['tryon'] - wc).abs() * me).sum() / (me.sum() * 3 + 1e-5)
    vg_textura = VGG(o['tryon'] * me, wc * me)

    total = 1.5 * dice + castigo_tv + castigo_cuello + castigo_colapso + 1.2 * l1_textura + 3.0 * vg_textura
    return total, dict(loss=float(total), vgg=float(vg_textura), l1=float(l1_textura), colapso=float(castigo_colapso))

# 10. Bucle de Entrenamiento y Gráficas
DIR_CKPT = SALIDA / 'etapa2_v2' / 'checkpoints'
DIR_CKPT.mkdir(parents=True, exist_ok=True)

EPOCAS = 12
historial = defaultdict(list)
mejor_loss = float('inf')

print(f"\n🚀 Iniciando re-entrenamiento con el catálogo real femenino ({EPOCAS} épocas)...")

for epoca in range(1, EPOCAS + 1):
    t_ep = time.time()
    modelo.train()
    acum_train, n_train = defaultdict(float), 0

    for lote in loader_train:
        if lote is None:
            continue
        b = {k: v.to(DEVICE, non_blocking=True) for k, v in lote.items()}
        optimizador.zero_grad(set_to_none=True)

        with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USA_AMP):
            o = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
            loss, metricas = calcular_perdidas_con_castigos(o, b)

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

    # Validación
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
                _, metricas = calcular_perdidas_con_castigos(o, b)
            bs = b['persona'].shape[0]
            for k, v in metricas.items():
                acum_val[k] += v * bs
            n_val += bs

    res_val = {k: v / max(1, n_val) for k, v in acum_val.items()}
    scheduler.step(res_val['loss'])

    historial['epoca'].append(epoca)
    historial['tr_loss'].append(res_tr['loss'])
    historial['val_loss'].append(res_val['loss'])
    historial['tr_vgg'].append(res_tr['vgg'])
    historial['val_vgg'].append(res_val['vgg'])
    historial['tr_l1'].append(res_tr['l1'])
    historial['val_l1'].append(res_val['l1'])

    if res_val['loss'] < mejor_loss:
        mejor_loss = res_val['loss']
        torch.save(dict(modelo=modelo.state_dict()), DIR_CKPT / 'best.pth')

    torch.save(dict(modelo=modelo.state_dict()), DIR_CKPT / 'last.pth')

    if EN_NOTEBOOK and clear_output is not None:
        clear_output(wait=True)

    print(f"Época [{epoca}/{EPOCAS}] ({time.time() - t_ep:.1f}s) | LR: {optimizador.param_groups[0]['lr']:.2e}")
    print(f"  Train -> Loss: {res_tr['loss']:.4f} | VGG: {res_tr['vgg']:.4f} | L1: {res_tr['l1']:.4f} | Castigo Colapso: {res_tr['colapso']:.4f}")
    print(f"  Val   -> Loss: {res_val['loss']:.4f} | VGG: {res_val['vgg']:.4f} | L1: {res_val['l1']:.4f} (Mejor: {mejor_loss:.4f})")

    # Gráficas y Grid cada 2 épocas o al final
    if epoca % 2 == 0 or epoca == EPOCAS:
        fig, ax = plt.subplots(1, 3, figsize=(15, 4))
        ax[0].plot(historial['epoca'], historial['tr_loss'], 'b-o', label='Train')
        ax[0].plot(historial['epoca'], historial['val_loss'], 'r-s', label='Val')
        ax[0].set_title('Pérdida Total (Loss)')
        ax[0].grid(True, alpha=0.3); ax[0].legend()

        ax[1].plot(historial['epoca'], historial['tr_vgg'], 'b-o', label='Train')
        ax[1].plot(historial['epoca'], historial['val_vgg'], 'r-s', label='Val')
        ax[1].set_title('Nitidez Textura (VGG)')
        ax[1].grid(True, alpha=0.3); ax[1].legend()

        ax[2].plot(historial['epoca'], historial['tr_l1'], 'b-o', label='Train')
        ax[2].plot(historial['epoca'], historial['val_l1'], 'r-s', label='Val')
        ax[2].set_title('Fidelidad Píxeles (L1)')
        ax[2].grid(True, alpha=0.3); ax[2].legend()
        plt.tight_layout()
        plt.savefig(SALIDA / 'etapa2_v2' / 'curvas_catalogo.png', dpi=100)
        if EN_NOTEBOOK and display:
            display(fig)
        plt.close(fig)

        if lote_demo is not None:
            b = {k: v[:4].to(DEVICE) for k, v in lote_demo.items()}
            with torch.no_grad():
                with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USA_AMP):
                    out = modelo(b['agnostica'], b['parse'], b['prenda'], b['mascara_prenda'])
            n = b['persona'].shape[0]
            fig, ax = plt.subplots(n, 4, figsize=(11, 3.2 * n), squeeze=False)
            titulos = ['1. Cuerpo Real', '2. Agnóstica (Pelo/Rostro)', '3. Prenda Catálogo', '4. Resultado con Mangas']
            for i in range(n):
                for j, img in enumerate([b['persona'][i], b['agnostica'][i], b['prenda'][i], out['final'][i]]):
                    ax[i, j].imshow(tensor_a_numpy_img(img))
                    ax[i, j].axis('off')
                    if i == 0:
                        ax[i, j].set_title(titulos[j], fontsize=11, fontweight='bold')
            fig.suptitle(f'Re-entrenamiento Época {epoca} — Probador Virtual FashionStore', fontsize=13)
            plt.tight_layout()
            plt.savefig(SALIDA / 'etapa2_v2' / f'grid_epoca_{epoca:02d}.png', dpi=100)
            if EN_NOTEBOOK and display:
                display(fig)
            plt.close(fig)

# 11. Exportar a ONNX con Corrección Anti-Distorsión
print("\n" + "=" * 70)
print("📦 Exportando modelo re-entrenado a ONNX sin distorsión...")

DIR_ONNX = SALIDA / 'onnx'
DIR_ONNX.mkdir(parents=True, exist_ok=True)
RUTA_ONNX = DIR_ONNX / 'vton_fashionstore.onnx'

class ModeloVTONRefinado(nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, agnostica, parse, prenda, mascara_prenda):
        o = self.m(agnostica, parse, prenda, mascara_prenda)
        return o['final']

if (DIR_CKPT / 'best.pth').exists():
    modelo.load_state_dict(torch.load(DIR_CKPT / 'best.pth', map_location=DEVICE, weights_only=False)['modelo'])

exportable = ModeloVTONRefinado(copy.deepcopy(modelo).float().cpu()).eval()
ejemplo = (
    torch.randn(1, 3, H, W),
    torch.randn(1, N_PARSE, H, W),
    torch.randn(1, 3, H, W),
    torch.randn(1, 1, H, W)
)

nombres_entrada = ['agnostic', 'parse', 'cloth', 'cloth_mask']
nombres_salida = ['result']
ejes_dinamicos = {k: {0: 'batch'} for k in nombres_entrada + nombres_salida}

torch.onnx.export(
    exportable, ejemplo, str(RUTA_ONNX),
    input_names=nombres_entrada,
    output_names=nombres_salida,
    dynamic_axes=ejes_dinamicos,
    opset_version=17,
    do_constant_folding=True
)

metadatos = dict(
    modelo='vton_fashionstore.onnx',
    fecha=time.strftime('%Y-%m-%d %H:%M:%S'),
    alto=H, ancho=W, opset=17,
    descripcion="Modelo VTON re-entrenado con catálogo real femenino, diversos cuerpos y preservación de mangas/cabello."
)
(DIR_ONNX / 'vton_metadatos.json').write_text(json.dumps(metadatos, indent=2, ensure_ascii=False), encoding='utf-8')

print(f"🎉 ¡PROCESO COMPLETO FINALIZADO CON ÉXITO!")
print(f"📁 Checkpoint guardado en: {DIR_CKPT / 'best.pth'}")
print(f"⚡ Modelo ONNX listo para la app y web en: {RUTA_ONNX} ({RUTA_ONNX.stat().st_size / 1e6:.1f} MB)")
print("=" * 70)
