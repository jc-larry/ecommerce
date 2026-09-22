# 🚀 Guía de Entrenamiento en Kaggle: Vestidor Virtual (VTON)

Esta guía te explica paso a paso cómo entrenar el modelo de vestidor virtual (modo cámara destilado de CatVTON) utilizando **Kaggle** con **GPU gratuita (T4 x2 o P100)** y 30 horas semanales de cuota.

---

## 🌟 Ventajas de Kaggle vs Google Colab
1. **GPU gratuita y estable:** Kaggle ofrece 30 horas semanales de GPU (GPU T4 x2 o GPU P100) con límites de tiempo continuo más holgados que la capa gratuita de Colab.
2. **Sin fallos de FUSE ni Google Drive:** En Kaggle los archivos se montan en almacenamiento local ultrarrápido (`/kaggle/input/`).
3. **Descarga directa:** Al finalizar, el archivo `vestidor_camara_onnx.zip` se descarga en 1 clic desde la pestaña de **Output**.

---

## 📦 Paso 1: Subir el Dataset a Kaggle

Ya tienes el dataset completo, optimizado y precalculado empaquetado en tu carpeta de proyecto:
- **Archivo:** `entrenamiento_ia_ropa_PARA_DRIVE_V5.zip` (pesa ~60 MB).
  *(Ubicado en la raíz de tu proyecto: `Primer_parcial/entrenamiento_ia_ropa_PARA_DRIVE_V5.zip`)*.

### Pasos para subirlo:
1. Inicia sesión en [kaggle.com](https://www.kaggle.com/).
2. En el menú de la izquierda, haz clic en **Datasets** y luego en el botón **+ New Dataset** (arriba a la derecha).
3. Arrastra y suelta el archivo `entrenamiento_ia_ropa_PARA_DRIVE_V5.zip`.
4. Asígnale un título, por ejemplo: `entrenamiento-ia-ropa` o `vestidor-vton-v5`.
5. Si deseas mantenerlo privado, selecciona **Private**.
6. Haz clic en **Create** y espera unos segundos a que Kaggle procese el archivo zip.

---

## 📓 Paso 2: Subir el Cuaderno (Notebook)

1. En Kaggle, ve a **Code** en el menú de la izquierda y haz clic en **+ New Notebook**.
2. En la barra superior del nuevo notebook, ve a **File** > **Upload Notebook**.
3. Selecciona el archivo que acabamos de generar:
   `entrenamiento_ia_ropa/03_notebooks_kaggle/VESTIDOR_VIRTUAL_ENTRENAMIENTO_KAGGLE.ipynb`
   *(También puedes usar `03_notebooks_colab/VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb`, ya que ahora ambos son 100% compatibles con Kaggle y Colab)*.

---

## ⚙️ Paso 3: Configuración Imprescindible en Kaggle

En el panel lateral derecho del notebook en Kaggle (si está oculto, haz clic en la flechita `|<-` o en el icono de engranaje **Notebook options**):

### 1. Vincular el Dataset (`+ Add Input`):
- Haz clic en **+ Add Input** (en la sección **Data**).
- En la pestaña **Your Datasets**, selecciona el dataset que subiste en el Paso 1 (`entrenamiento-ia-ropa`) y haz clic en el icono **+**.
- Ahora verás tu dataset listado en `/kaggle/input/`.

### 2. Acelerador GPU:
- En **Settings** > **Accelerator**, selecciona **GPU T4 x2** (o **GPU P100**).

### 3. Activar Internet (¡CRÍTICO!):
- En **Settings** > **Internet**, cambia la opción a **Internet on**.
  > ⚠️ **Nota:** Kaggle tiene el internet desactivado por defecto en notebooks nuevos. Es obligatorio activarlo para que pueda descargar `diffusers`, `transformers` y los pesos preentrenados de CatVTON (~5 GB) desde Hugging Face. Si nunca has verificado tu cuenta de Kaggle, te pedirá verificar un número de teléfono por SMS una sola vez.

---

## ▶️ Paso 4: Ejecutar el Entrenamiento

1. Haz clic en **Run All** (o ejecuta celda por celda):
   - **Celda 1:** Valida dependencias, conexión a internet y GPU.
   - **Celda 2:** Detecta automáticamente el dataset en `/kaggle/input/...` y crea las carpetas de salida en `/kaggle/working/05_entrenamiento_v3`.
   - **Celda 3-5:** Segmentación y verificación de prendas y cuerpos.
   - **Celda 6:** Descarga de CatVTON (modo foto).
   - **Celda 7-8:** Destilación de los 420 pares con filtro de calidad.
   - **Celda 9-11:** Entrenamiento del alumno (modo cámara, 40 épocas a 192×256).
   - **Celda 12-13:** Puerta B de calidad y exportación a formato **ONNX**.
   - **Celda 14:** Empaquetado automático en archivo ZIP para descarga.

2. **Tiempo estimado total:** ~1 hora y 20 minutos con GPU T4.

---

## 💾 Paso 5: Descargar los Resultados

Al terminar la ejecución:
1. En la celda final aparecerá un enlace de descarga interactivo.
2. También puedes ir al panel lateral derecho, en la sección **Output** (`/kaggle/working/`):
   - Encontrarás el archivo **`vestidor_camara_onnx.zip`**.
   - Haz clic en los tres puntos `...` al lado del archivo y selecciona **Download**.

### Contenido del archivo descargado:
- `vestidor_camara.onnx`: El modelo optimizado para el vestidor en vivo a ~30 fps.
- `metadatos.json`: El contrato de entrada y salida para integrarlo en tu frontend y backend.
