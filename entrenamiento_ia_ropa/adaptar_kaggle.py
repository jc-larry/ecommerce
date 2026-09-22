import json
import os
from pathlib import Path

path_colab = Path("entrenamiento_ia_ropa/03_notebooks_colab/VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb")
path_kaggle = Path("entrenamiento_ia_ropa/03_notebooks_kaggle/VESTIDOR_VIRTUAL_ENTRENAMIENTO_KAGGLE.ipynb")

with open(path_colab, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 1. Celda 0
nb["cells"][0]["source"] = [
    "# ⚠️ Reanudación automática (Kaggle y Colab)\n",
    "\n",
    "Todo lo que importa se guarda en almacenamiento persistente (`05_entrenamiento_v3/`):\n",
    "- En **Kaggle**: Todo se guarda en `/kaggle/working/05_entrenamiento_v3/`.\n",
    "- En **Colab**: Todo se guarda en `MiUnidad/entrenamiento_ia_ropa/05_entrenamiento_v3/`.\n",
    "\n",
    "| Qué | Dónde | Cómo se reanuda |\n",
    "|---|---|---|\n",
    "| Análisis de cuerpos y prendas | `cache/` | cada archivo se escribe atómicamente; se rehace solo lo que faltó |\n",
    "| Pares del profesor (CatVTON) | `pares/` + `filtro_registro.jsonl` | se saltan los aceptados **y** los rechazados |\n",
    "| Entrenamiento | `checkpoints/ultimo_a.pth` / `ultimo_b.pth` | continúa en la época siguiente (modelo + optimizadores + calendario) |\n",
    "| Mejor modelo | `checkpoints/mejor.pth` | no se sobrescribe si no mejora |\n",
    "\n",
    "**Si la sesión se corta o reconecta:** Simplemente vuelve a ejecutar. Cada celda pesada detecta lo ya hecho y sigue por donde quedó.\n",
    "\n",
    "**En Kaggle:** Recuerda activar en el panel lateral derecho:\n",
    "- **Accelerator:** GPU T4 x2 (o GPU P100)\n",
    "- **Internet:** **Internet on** (imprescindible para descargar librerías y pesos de CatVTON)\n"
]

# 2. Celda 1
nb["cells"][1]["source"] = [
    "# FashionStore · Vestidor Virtual — Entrenamiento (Kaggle / Colab, < 2 h)\n",
    "\n",
    "**CU32** · Web + móvil · Modo foto y modo cámara · GPU T4 / P100 gratuita\n",
    "\n",
    "---\n",
    "\n",
    "## Qué se entrena y qué no\n",
    "\n",
    "Esto es **transfer learning por destilación**, no entrenamiento desde cero. Con 68 prendas y\n",
    "sin un solo par real (una foto de *esta* persona con *esta* prenda puesta) no existe forma de\n",
    "aprender try-on partiendo de nada; el intento anterior lo demuestra.\n",
    "\n",
    "| Modo | Modelo | Entrenamiento | Latencia |\n",
    "|---|---|---|---|\n",
    "| **Foto** (la clienta sube su imagen) | CatVTON preentrenado (~13.000 pares VITON-HD) | ninguno, se usa tal cual | 8-15 s |\n",
    "| **Cámara** (vídeo en vivo) | Red propia de ~1,9 M parámetros | **destilada del modo foto** | ~30 fps |\n",
    "\n",
    "El modo foto genera la verdad de terreno que el modo cámara imita. Por eso basta una sola\n",
    "sesión de entrenamiento.\n",
    "\n",
    "---\n",
    "\n",
    "## Presupuesto de tiempo (GPU T4 / P100)\n",
    "\n",
    "| Fase | Tiempo |\n",
    "|---|---|\n",
    "| Dependencias | 6-8 min |\n",
    "| Pose de los cuerpos | 2-3 min |\n",
    "| Descarga de CatVTON | 6-8 min |\n",
    "| **Destilación (420 pares)** | **40-45 min** |\n",
    "| **Entrenamiento (40 épocas @ 192×256)** | **20-22 min** |\n",
    "| Export ONNX verificado | 5 min |\n",
    "| **Total** | **~1 h 25 min** |\n"
]

# 3. Celda 3 (Verificación de internet en Kaggle)
orig_c3 = "".join(nb["cells"][3]["source"])
if "def _hay_internet():" not in orig_c3:
    c3_pre = orig_c3.split("import subprocess, sys, importlib")[0]
    c3_post = "import subprocess, sys, importlib" + orig_c3.split("import subprocess, sys, importlib")[1]
    internet_check = """import subprocess, sys, importlib, importlib.util, importlib.metadata, os, socket
from pathlib import Path

EN_KAGGLE = Path("/kaggle").is_dir()

def _hay_internet():
    try:
        socket.create_connection(("huggingface.co", 443), timeout=4)
        return True
    except Exception:
        return False

if EN_KAGGLE and not _hay_internet():
    raise RuntimeError(
        "⚠️ NO HAY ACCESO A INTERNET en este cuaderno de Kaggle.\\n"
        "👉 En el panel lateral derecho de Kaggle:\\n"
        "   1. Despliega 'Settings' (o 'Notebook options')\\n"
        "   2. Busca 'Internet'\\n"
        "   3. Cámbialo a 'Internet on'\\n"
        "   (Si es tu primera vez, Kaggle pide verificar número telefónico)\\n"
        "   Luego vuelve a ejecutar esta celda."
    )

"""
    new_c3 = c3_pre + internet_check + c3_post[len("import subprocess, sys, importlib"):]
    nb["cells"][3]["source"] = [line + "\n" for line in new_c3.split("\n")]
    if nb["cells"][3]["source"][-1] == "\n":
        nb["cells"][3]["source"].pop()

# 4. Celda 4 (Markdown Celda 2)
nb["cells"][4]["source"] = [
    "---\n",
    "## Celda 2 · Entorno (Kaggle / Colab) y rutas\n",
    "\n",
    "Estructura esperada:\n",
    "\n",
    "```\n",
    "01_cuerpos/                                  9 cuerpos HD + cuerpos_metadata.csv\n",
    "02_prendas/<categoria>/                     68 prendas + prendas_manifest.json\n",
    "04_checkpoints_modelos/\n",
    "    resultados_vton_previos/cache/           1735 personas vestidas ya segmentadas\n",
    "06_poses_precalculadas/                      poses de personas y prendas\n",
    "dataset_manifest.json\n",
    "```\n",
    "\n",
    "- En **Kaggle**: se detecta automáticamente en `/kaggle/input/...` (solo lectura) y escribe en `/kaggle/working/`.\n",
    "- En **Colab**: se detecta en Google Drive y escribe en `MiUnidad/entrenamiento_ia_ropa/`.\n"
]

# 5. Celda 5 (Rutas universales)
nb["cells"][5]["source"] = [
    "import os, shutil\n",
    "from pathlib import Path\n",
    "\n",
    "EN_KAGGLE = Path(\"/kaggle\").is_dir()\n",
    "EN_COLAB = False\n",
    "\n",
    "if not EN_KAGGLE:\n",
    "    try:\n",
    "        from google.colab import drive\n",
    "        drive.mount(\"/content/drive\")\n",
    "        EN_COLAB = True\n",
    "    except Exception:\n",
    "        EN_COLAB = False\n",
    "\n",
    "RAIZ = None\n",
    "\n",
    "if EN_KAGGLE:\n",
    "    print(\"Detectado entorno Kaggle.\")\n",
    "    # Buscar recursivamente la carpeta que contiene 02_prendas en /kaggle/input\n",
    "    for p in Path(\"/kaggle/input\").rglob(\"02_prendas\"):\n",
    "        if p.is_dir():\n",
    "            RAIZ = p.parent\n",
    "            break\n",
    "    if RAIZ is None:\n",
    "        for p in Path(\"/kaggle/input\").rglob(\"dataset_manifest.json\"):\n",
    "            if p.is_file():\n",
    "                RAIZ = p.parent\n",
    "                break\n",
    "    if RAIZ is None:\n",
    "        for cand in Path(\"/kaggle/input\").glob(\"*\"):\n",
    "            if (cand / \"02_prendas\").is_dir() or (cand / \"01_cuerpos\").is_dir():\n",
    "                RAIZ = cand\n",
    "                break\n",
    "            for sub in cand.glob(\"*\"):\n",
    "                if (sub / \"02_prendas\").is_dir() or (sub / \"01_cuerpos\").is_dir():\n",
    "                    RAIZ = sub\n",
    "                    break\n",
    "            if RAIZ:\n",
    "                break\n",
    "else:\n",
    "    CANDIDATAS = [\n",
    "        Path(\"/content/drive/MyDrive/entrenamiento_ia_ropa\"),\n",
    "        Path(\"/content/drive/MyDrive/entrenamiento_ia_vestidor/entrenamiento_ia_ropa\"),\n",
    "        Path(\"/content/drive/My Drive/entrenamiento_ia_ropa\"),\n",
    "        Path(\"entrenamiento_ia_ropa\"), Path(\".\"),\n",
    "    ]\n",
    "    for c in CANDIDATAS:\n",
    "        if (c / \"02_prendas\").is_dir() or (c / \"01_cuerpos\").is_dir():\n",
    "            RAIZ = c\n",
    "            break\n",
    "\n",
    "assert RAIZ is not None, (\n",
    "    \"No encuentro la carpeta del dataset.\\n\"\n",
    "    \"- En Kaggle: agrega el dataset haciendo clic en '+ Add Input' (o sube el zip en Datasets).\\n\"\n",
    "    \"- En Colab: debe estar en MiUnidad/entrenamiento_ia_ropa/ con 01_cuerpos/ y 02_prendas/ dentro.\")\n",
    "\n",
    "DIR_CUERPOS  = RAIZ / \"01_cuerpos\"\n",
    "DIR_PRENDAS  = RAIZ / \"02_prendas\"\n",
    "DIR_VESTIDOS = RAIZ / \"04_checkpoints_modelos\" / \"resultados_vton_previos\" / \"cache\"\n",
    "\n",
    "# En Kaggle, /kaggle/input es de SOLO LECTURA. Todo lo generado se guarda en /kaggle/working\n",
    "if EN_KAGGLE:\n",
    "    SALIDA = Path(\"/kaggle/working/05_entrenamiento_v3\")\n",
    "else:\n",
    "    SALIDA = RAIZ / \"05_entrenamiento_v3\"\n",
    "\n",
    "CACHE     = SALIDA / \"cache\"\n",
    "DIR_PARES = SALIDA / \"pares\"\n",
    "DIR_CKPT  = SALIDA / \"checkpoints\"\n",
    "DIR_ONNX  = SALIDA / \"onnx\"\n",
    "for p in (SALIDA, CACHE, DIR_PARES, DIR_CKPT, DIR_ONNX):\n",
    "    p.mkdir(parents=True, exist_ok=True)\n",
    "\n",
    "# Cache de personas vestidas\n",
    "CACHE_VEST = Path(\"/content/cache_vestidos\") if EN_COLAB else DIR_VESTIDOS\n",
    "if EN_COLAB and DIR_VESTIDOS.is_dir() and not CACHE_VEST.exists():\n",
    "    print(\"Copiando el cache de personas vestidas a disco local (mas rapido)...\")\n",
    "    shutil.copytree(DIR_VESTIDOS, CACHE_VEST)\n",
    "\n",
    "# Poses precalculadas\n",
    "DIR_POSES = RAIZ / \"06_poses_precalculadas\"\n",
    "POSES = Path(\"/content/poses\") if EN_COLAB else DIR_POSES\n",
    "if EN_COLAB and DIR_POSES.is_dir() and not POSES.exists():\n",
    "    shutil.copytree(DIR_POSES, POSES)\n",
    "\n",
    "print(f\"entorno  : {'Kaggle' if EN_KAGGLE else ('Colab' if EN_COLAB else 'Local')}\")\n",
    "print(f\"raiz     : {RAIZ}\")\n",
    "print(f\"poses    : {POSES.is_dir()} ({len(list(POSES.glob('*_pose.npy'))) if POSES.is_dir() else 0} archivos)\")\n",
    "print(f\"cuerpos  : {DIR_CUERPOS.is_dir()}\")\n",
    "print(f\"prendas  : {DIR_PRENDAS.is_dir()}\")\n",
    "print(f\"vestidos : {CACHE_VEST.is_dir()}\")\n",
    "print(f\"salida   : {SALIDA}\")\n"
]

# 6. Celda 16 (CatVTON y HF Cache)
orig_c16 = "".join(nb["cells"][16]["source"])
c16_target = 'os.environ.setdefault("HF_HOME", str(SALIDA / "hf"))\nPath(os.environ["HF_HOME"]).mkdir(parents=True, exist_ok=True)\n\nDIR_CV = SALIDA / "CatVTON"'
c16_repl = '''if EN_KAGGLE:
    os.environ.setdefault("HF_HOME", "/tmp/hf")
    DIR_CV = Path("/tmp/CatVTON")
else:
    os.environ.setdefault("HF_HOME", str(SALIDA / "hf"))
    DIR_CV = SALIDA / "CatVTON"
Path(os.environ["HF_HOME"]).mkdir(parents=True, exist_ok=True)'''

if c16_target in orig_c16:
    new_c16 = orig_c16.replace(c16_target, c16_repl)
    nb["cells"][16]["source"] = [line + "\n" for line in new_c16.split("\n")]
    if nb["cells"][16]["source"][-1] == "\n":
        nb["cells"][16]["source"].pop()

# 7. Celda final de descarga
has_dl = any("vestidor_camara_onnx.zip" in "".join(c["source"]) for c in nb["cells"])
if not has_dl:
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "id": "descarga_final_kaggle",
        "metadata": {},
        "outputs": [],
        "source": [
            "# ===== DESCARGA DE MODELOS (KAGGLE / COLAB) ===========================\n",
            "import shutil\n",
            "from pathlib import Path\n",
            "\n",
            "zip_onnx = Path(\"/kaggle/working/vestidor_camara_onnx.zip\") if EN_KAGGLE else (SALIDA / \"vestidor_camara_onnx.zip\")\n",
            "if DIR_ONNX.is_dir() and (DIR_ONNX / \"vestidor_camara.onnx\").exists():\n",
            "    shutil.make_archive(str(zip_onnx).replace(\".zip\", \"\"), \"zip\", str(DIR_ONNX))\n",
            "    print(f\"✅ Modelo ONNX empaquetado: {zip_onnx} ({zip_onnx.stat().st_size / (1024*1024):.2f} MB)\")\n",
            "    if EN_KAGGLE:\n",
            "        try:\n",
            "            from IPython.display import FileLink, display\n",
            "            display(FileLink(str(zip_onnx)))\n",
            "        except Exception:\n",
            "            pass\n",
            "        print(\"👉 En Kaggle: También puedes descargarlo desde el panel lateral derecho: 'Output' -> /kaggle/working\")\n",
            "else:\n",
            "    print(\"Nota: vestidor_camara.onnx aún no ha sido exportado. Ejecuta las celdas de entrenamiento primero.\")\n"
        ]
    })

# Guardar ambos notebooks
with open(path_colab, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

with open(path_kaggle, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebooks actualizados con éxito para Colab y Kaggle.")
