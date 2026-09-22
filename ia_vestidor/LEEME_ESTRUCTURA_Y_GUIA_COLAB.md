# 🌟 GUÍA COMPLETA: ENTRENAMIENTO DE VIRTUAL TRY-ON (VTON) EN GOOGLE COLAB
**Estructura reorganizada del Dataset, Solución Técnica de Ajuste de Prendas y Flujo Paso a Paso**

---

## 📁 1. NUEVA ESTRUCTURA ORGANIZADA Y LIMPIA

La carpeta `entrenamiento_ia_ropa/` ha sido completamente reestructurada para ser intuitiva, desacoplar los modelos de las prendas, y permitir un entrenamiento directo en la nube:

```text
entrenamiento_ia_ropa/
│
├── 01_cuerpos/                          <- 🧍 MODELOS HUMANOS / CUERPOS (9 fotos)
│   ├── modelo_cuerpo_01.jpg             <- Vista frontal, cuerpo completo
│   ├── modelo_cuerpo_02.jpg
│   ├── ...
│   ├── modelo_cuerpo_09.jpg
│   ├── cuerpos_manifest.json            <- Registro JSON de dimensiones y tipos
│   └── cuerpos_metadata.csv             <- Metadatos tabulares (altura, pose, género)
│
├── 02_prendas/                          <- 👗 CATÁLOGO DE PRENDAS CLASIFICADAS (68 prendas)
│   ├── Blusas/                          <- Subcarpeta por categoría de moda
│   ├── Camisas/
│   ├── Camisetas - T-Shirts/
│   ├── Chaquetas - Chamarras/
│   ├── Enterizos - Monos/
│   ├── Jeans - Mezclilla/
│   ├── Pantalones/
│   ├── Ropa de dormir - Pijamas/
│   ├── Suéteres y Tejidos/
│   ├── Tops - Crop Tops/
│   ├── Vestidos/
│   ├── prendas_manifest.json            <- Catálogo de inventario con IDs de producto
│   └── prendas_metadata.csv             <- Clasificación por categoría y ruta relativa
│
├── 03_notebooks_colab/                  <- 🚀 CUADERNOS LISTOS PARA GOOGLE COLAB
│   └── ENTRENAMIENTO_VTON_COLAB.ipynb   <- Cuaderno con pipeline GMM + TOM + VGG19
│
├── 04_checkpoints_modelos/              <- 💾 MODELOS ENTRENADOS Y CHECKPOINTS
│   ├── resultados_vton_previos/         <- Respaldo seguro del entrenamiento anterior
│   └── (Aquí Colab guardará los nuevos .pth, .onnx y gráficos comparativos)
│
└── LEEME_ESTRUCTURA_Y_GUIA_COLAB.md     <- Esta guía completa
```

---

## 🔬 2. ¿QUÉ FALLABA ANTES Y CÓMO ESTÁ CORREGIDO?

### ❌ El problema del entrenamiento anterior:
1. **Solo cambiaba de color:** El modelo previo actuaba como una máscara de tinte. Detectaba la silueta del torso y sobreponía un color o mancha difusa, sin adaptar la estructura de la ropa.
2. **Mangas que no llegaban a los brazos:** Si la persona de la foto tenía una prenda sin mangas o mangas cortas, y la prenda a probar tenía mangas largas, el algoritmo anterior **nunca desenmascaraba los brazos**. Por tanto, era imposible que las mangas se extendieran hacia los brazos.
3. **Pérdida y colapso de textura (Blurry Output):** El flujo de deformación se contraía hacia el centro, haciendo que estampados, rayas o texturas desaparecieran en un degradado borroso.

### ✅ La Solución Implementada en el Nuevo Pipeline:
1. **Máscara Agnóstica Inteligente:**
   - La nueva arquitectura genera una máscara del torso y de los brazos según la categoría de la prenda.
   - Si la prenda objetivo tiene mangas largas o intermedias (ej. Camisas, Chaquetas, Suéteres), la máscara agnóstica despeja los brazos del modelo para que la red neuronal pinte las mangas exactamente en las extremidades.
2. **Deformación Geométrica Elástica (GMM Flow Field):**
   - Se aumentó el rango de deformación del campo vectorial a `±0.60` (antes limitado a `±0.22`), permitiendo estiramientos naturales que cubren cuellos, escotes y brazos.
   - Se introdujo una **pérdida anti-colapso**: Si el área deformada de la prenda es inferior al 70% del torso, la red es penalizada severamente, impidiendo que la ropa se encoja o colapse.
3. **Preservación de Textura y Estampados (VGG-19 Perceptual Loss):**
   - Compara las capas convolucionales intermedias `relu2_2`, `relu3_4` y `relu4_4` de VGG-19 entre la prenda original y la prenda vestida. Esto garantiza que las líneas, botones, texturas tejidas y estampados se transfieran con nitidez fotográfica.

---

## ☁️ 3. PASO A PASO: SUBIR A GOOGLE DRIVE

Tienes dos formas sencillas de subir los datos:

### Opción A (Recomendada - Subida Rápida con ZIP):
1. Comprime la carpeta `entrenamiento_ia_ropa` en un archivo `entrenamiento_ia_ropa.zip`.
2. Entra a tu [Google Drive](https://drive.google.com).
3. Crea una carpeta llamada `entrenamiento_ia_vestidor` (o colócalo en tu carpeta de preferencia).
4. Sube el archivo `entrenamiento_ia_ropa.zip` y descomprímelo (o sube la carpeta directamente).

### Opción B (Subir la carpeta directamente):
1. En Google Drive, haz clic en **+ Nuevo** > **Subir carpeta**.
2. Selecciona la carpeta `entrenamiento_ia_ropa`.
3. Espera a que termine de sincronizar las fotos.

> **Rutas que detecta automáticamente el Notebook:**
> - `/content/drive/MyDrive/entrenamiento_ia_vestidor/entrenamiento_ia_ropa`
> - `/content/drive/MyDrive/entrenamiento_ia_ropa`
> - Si lo colocaste en otra subcarpeta, la celda 2 de Colab te permite cambiar la ruta con una sola variable.

---

## ⚡ 4. EJECUTAR EL ENTRENAMIENTO EN GOOGLE COLAB

1. **Abrir Colab:**
   - Ve a [colab.research.google.com](https://colab.research.google.com).
   - Haz clic en **Subir** (Upload) y selecciona el archivo:
     `entrenamiento_ia_ropa/03_notebooks_colab/ENTRENAMIENTO_VTON_COLAB.ipynb`

2. **Activar la GPU Gratuita:**
   - En el menú superior de Colab, ve a: **Entorno de ejecución** > **Cambiar tipo de entorno de ejecución**.
   - En "Acelerador por hardware", selecciona **GPU T4** (o la GPU disponible).
   - Haz clic en **Guardar**.

3. **Ejecutar el Notebook:**
   - Ve a: **Entorno de ejecución** > **Ejecutar todo** (Ctrl + F9).
   - La primera celda solicitará permiso para conectar tu Google Drive. Haz clic en **Conectar con Google Drive** y autoriza tu cuenta.
   - El cuaderno validará la GPU, cargará los 9 cuerpos y las 68 prendas, compilará las redes `GMM_WarpNet` y `TOM_GeneratorNet`, y comenzará a entrenar.

4. **Tiempos de Entrenamiento Estimados:**
   - En una GPU T4 gratuita de Google Colab:
     - 30 épocas de entrenamiento toman aproximadamente **15 a 20 minutos**.
     - Durante el entrenamiento verás la barra de progreso por época y la disminución de la pérdida (`Loss`).

---

## 📦 5. MODELOS RESULTANTES Y DESCARGA

Al finalizar la última celda del cuaderno, se generarán y guardarán automáticamente en tu Google Drive dentro de `04_checkpoints_modelos/`:

| Archivo | Descripción | Uso en el Sistema |
| :--- | :--- | :--- |
| `gmm_vton_final.pth` | Pesos de la red de deformación geométrica | Deforma y adapta prendas al contorno corporal |
| `tom_vton_final.pth` | Pesos de la red generadora Try-On | Aplica textura fotorrealista y fusión de piel |
| `vton_pipeline.onnx` | Pipeline exportado a formato ONNX estándar | Para inferencia ultra rápida en el backend web/API |
| `comparativas_epoch_*.png` | Muestras visuales generadas durante el entrenamiento | Permite verificar visualmente la calidad del ajuste |

---

## 🛠️ 6. INTEGRACIÓN CON EL BACKEND WEB DE LA TIENDA

Una vez descargados los pesos `.pth` o `.onnx` a tu máquina local:
1. Colócalos en la carpeta `ia_vestidor/modelos/` o `backend/ia_models/`.
2. El script de inferencia del vestidor virtual cargará el modelo preentrenado para realizar el Try-On en menos de 1 segundo por usuario cuando el cliente pulse "Probar prenda" en la tienda.
