# Plan V5 — Colab T4 sin cortes + vestidor en vivo que no pierde la prenda

> Revisión hecha el 2026-09-21 sobre: `PLAN_MAESTRO_ENTRENAMIENTO_VTON_V4.md`, el cuaderno
> `VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb`, `live-garment-engine.ts`, `virtual-tryon.component.ts`,
> `verificar_mediapipe_colab.py`, tus 4 capturas y el video `video_prueba/WhatsApp Video ...mp4`
> (12 fotogramas muestreados de 35 s).
>
> **Este plan reemplaza a V4 en tres puntos** (ver §1): V4 da por muerto el enfoque de destilación y
> pide un dataset pareado de 500 pares que no existe; el cuaderno vivo ya resuelve eso con
> destilación, pero tiene fallos concretos que se listan abajo.

---

## 1. Diagnóstico

### 1.1 Por qué salió la foto (agnóstica gris → recuadro marrón → "objetivo" de malla)

Lo que se ve en tu primera captura, de izquierda a derecha, y su causa:

| Panel | Qué se ve | Causa |
|---|---|---|
| agnóstica | bloque gris rectangular con hombros cuadrados que se come brazos y torso | `mascara_agnostica_por_prenda` (celda 5) para una **chaqueta** fuerza `cuello=0.80, manga=0.85`: borra casi todo el tronco y los brazos con un polígono de esquinas rectas |
| prenda | la chaqueta guinda **cortada por el borde derecho** | el recorte del catálogo (`letterbox`/`mascara_prenda_plana`) no comprueba que la prenda toque el borde de la imagen |
| objetivo (modo foto) | camiseta corta **marrón y semitransparente**, no la chaqueta guinda de manga larga | el *teacher* (CatVTON) falló y **nadie lo filtró**: se guarda tal cual como verdad de terreno |
| modo cámara | recuadro con bordes duros, manchas y fantasmas de manga | el alumno (1,9 M parámetros, 192×256) aprende del teacher malo y **rellena todo el recuadro gris** sin fundirlo con la persona |

Resumen: **verdad de terreno mala + recuadro que no se funde + sin control de calidad**. Es el mismo tipo de error
que el CP-VTON descartado (aprender de algo que no es la prenda real).

### 1.2 Fallos de Colab que hay que corregir (verificados leyendo el código)

1. **`mp` machacado (celda 17).** `for rp, mp in prendas_dest[...]` y `rp, mp = rnd.choice(...)` reasignan `mp`,
   que la celda 4 usa como `import mediapipe as mp`. Da `AttributeError: 'dict' object has no attribute 'Image'`
   lejos de la causa. Renombrar metadatos a `mt` y el módulo a `mpipe` en **todas** las celdas.
2. **Dependencias de 2024 en un Colab de 2026.** La celda 2 fija `onnx==1.16.2`, `transformers==4.44.2`,
   `peft==0.13.2`. Colab trae Python 3.13 / numpy 2.1: `onnx 1.16.2` no tiene rueda cp313 y CatVTON necesita
   `transformers` 4.57.6. Además `raise SystemExit` **no detiene "Ejecutar todo"**: el fallo reaparece 20 min después.
3. **MediaPipe.** (a) `requirements_colab.txt` pide `mediapipe<0.11` y `numpy<2`, imposible en Python 3.13;
   (b) la celda 4 **descarga** el `.task` en vez de usar `00_modelos_base/pose_landmarker_lite.task`;
   (c) el respaldo por segmentación tiene ~20 % de error en hombros y ~0,4 anchos en codo, así que **degrada en silencio**;
   (d) en Colab no hay GPU/OpenGL para el delegado GPU de MediaPipe: solo CPU.
4. **El ZIP para Drive deja fuera las 1735 personas vestidas.** Excluye `04_checkpoints_modelos/`, y ahí está
   `resultados_vton_previos/cache/` (**solo 59 MB**, 5708 archivos). Sin ellas la celda 17 falla su `assert`
   (`>= 80` vestidas) y el modelo solo sabría vestir bodysuits.
5. **No hay reanudación.** La celda 26 solo guarda `mejor.pth` (sin optimizador, sin época, sin scaler). Si Colab
   corta a la época 30, se pierde todo.
6. **El cuaderno obsoleto sigue en la carpeta** (`ENTRENAMIENTO_VTON_COLAB.ipynb`): moverlo a `_obsoletos/`.

### 1.3 Por qué se pierde la prenda en cámara (código web actual)

Causas reales, ordenadas por probabilidad:

1. **`hasUsableBody` exige caderas visibles** (`visibility > 0.5` en 11, 12, 23, 24). Con la persona cerca de la
   webcam (tu video: fotogramas 1, 5 y 8, cartel *"Necesito ver hombros y cadera"*) las caderas quedan fuera de
   cuadro y la prenda se apaga aunque los hombros estén perfectos.
2. **El recorte contra la silueta puede borrarla entera.** En `render()`, `destination-in` con la máscara: si la
   máscara sale vacía o parcial en un fotograma (persona muy cerca, contraluz, movimiento), todo lo que cae fuera se
   descarta y la prenda desaparece sin que la pose haya fallado.
3. **Sin histéresis:** el umbral de entrada y el de salida son el mismo (0,5), así que una visibilidad de 0,49↔0,51
   hace parpadear.
4. **Delegado GPU:** el `try/catch` solo cubre el *crear*; hay GPU que crea bien y luego devuelve vacío o pierde
   contexto WebGL. Hoy no hay reintento en CPU en ese caso.
5. La ventana de gracia (750 ms + 350 ms) ya existe y es correcta; solo protege de pérdidas de pose, no de 1 y 2.

### 1.4 Lo que muestra tu video (importante: es tu propio prototipo)

El video es una grabación de **tu app con camisetas de color plano** (Polera roja, azul, Musculosa, Manga larga; casillas
Landmarks/Esqueleto), no un video de referencia de otra herramienta. Extraje de él estos requisitos:

- La prenda **sí sigue** el torso y se estira con los brazos abiertos (buen punto de partida).
- **Manchas oscuras en el cuello** (elipse gris/negra): el escote se pinta como prenda opaca en vez de dejar ver el cuello.
- **Círculo blanco** en el pecho de la polera azul: marcador o artefacto de la malla; no debe verse.
- Con brazos en alto/abiertos las mangas son **bultos redondeados** que no siguen la dirección del brazo.
- Borde inferior **recto y rígido**, sin caída ni balanceo; el color es **plano** (sin luz ni sombra de la escena).
- Cuando la persona se acerca: la prenda **desaparece** (ver 1.3-1).

Si tienes otro video que sea la referencia "así debe moverse", súbelo y lo comparo fotograma a fotograma; con este solo
puedo afirmar lo anterior.

---

## 2. Plan Colab T4 (sesiones cortas, reanudables)

### 2.1 Límites de la T4 y cómo se respetan

| Límite | Consecuencia | Medida |
|---|---|---|
| ~15 GB VRAM | CatVTON 384×512 + SegFormer + VGG juntos revientan | cargar **un modelo a la vez**; `torch.cuda.empty_cache()` entre etapas; CatVTON en fp16 |
| Sin bf16 | bf16 falla o va lento | usar **fp16 + GradScaler** (ya está) |
| ~12,7 GB RAM | `DataLoader` con muchos workers se cae | `num_workers=2`, `persistent_workers=True` |
| Disco `/content` efímero | se pierde al desconectar | resultados y checkpoints **directo a Drive** |
| Drive por FUSE lento | leer 5000 archivos pequeños es lento | copiar datos a `/content` al inicio (tar/`copytree`), escribir a Drive solo pares y checkpoints |
| Sesión finita / desconexión por inactividad | corta a mitad | **todo reanudable** (§2.4). No usar scripts "anti-inactividad": incumplen los términos de Colab; se resuelve con reanudación |
| OOM ocasional | aborta la celda | envolver el paso en `try/except torch.cuda.OutOfMemoryError` → vaciar caché, reintentar con lote/2 |

### 2.2 Qué subir a Drive (`Mi unidad/entrenamiento_ia_ropa/`)

```
00_modelos_base/pose_landmarker_lite.task      (local, sin descargar)
01_cuerpos/            9 fotos
02_prendas/            68 prendas + manifiesto
03_notebooks_colab/    VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb  (corregido)
04_checkpoints_modelos/resultados_vton_previos/cache/   <- 59 MB, IMPRESCINDIBLE
06_poses_precalculadas/   <- se genera en tu PC (§2.3)
```

No subir `etapa*/`, `onnx/`, `tensorboard/` (≈1,8 GB, no sirven: el `.onnx` salió vacío y `last.pth` pesa 0 bytes).

### 2.3 MediaPipe: que no dependa de Colab (la solución de fondo)

En tu PC MediaPipe **ya funciona** (es el mismo modelo que usa la web). Entonces:

1. En tu PC, script `precalcular_poses.py` recorre `01_cuerpos/` + `cache/*.jpg` y guarda por imagen
   `<id>_pose.npy` (33×3: x, y, visibilidad) con `PoseLandmarker` **CPU**, `.task` local, umbral 0,3.
2. Registra en `06_poses_precalculadas/reporte.json` cuántas detectó y cuáles **no** (esas se excluyen o se marcan).
3. En Colab, la celda 4 **lee primero el `.npy`**; solo si falta, intenta MediaPipe CPU; solo si falla, el respaldo por
   segmentación y **lo anota en el reporte** (nunca en silencio).
4. Regla de parada: si más del 15 % de las poses usadas vienen del respaldo, la celda se detiene con mensaje claro.

Resultado: Colab pasa a no necesitar MediaPipe para entrenar y el problema de "no lo detecta en Colab" desaparece.

### 2.4 Celdas nuevas / cambiadas (en orden)

**Celda 0 — entorno (nueva, primera).** Comprueba, detiene con `assert` real y *reinicia* si hace falta:

```python
import sys, torch, importlib, subprocess
print("Python", sys.version.split()[0], "| torch", torch.__version__)
assert torch.cuda.is_available(), "Activa GPU: Entorno de ejecución > Cambiar tipo > T4"
print(torch.cuda.get_device_name(0), f"{torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")

PIN = ["diffusers==0.31.0", "transformers==4.57.6", "accelerate", "huggingface_hub",
       "peft", "safetensors", "opencv-python-headless", "onnx>=1.18", "onnxruntime"]
r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", *PIN],
                   capture_output=True, text=True)
assert r.returncode == 0, r.stderr[-1500:]        # AssertionError SÍ frena la cadena; no SystemExit
```

- **No** instalar `mediapipe` aquí. Bloque opcional aparte, dentro de `try/except`, que solo lo usa como respaldo.
- Comprobar que `CLIPImageProcessor`, `AutoencoderKL`, `UNet2DConditionModel`, `DDIMScheduler` importan (la celda 1 actual ya lo hace).

**Celda 2 (Drive).** Montar, `copytree` de `cache/` y `02_prendas/` a `/content`, y verificar `cache` con ≥ 1500 imágenes.

**Celda 4 (pose).** Orden: `.npy` precalculado → MediaPipe CPU con `.task` local (`Delegate.CPU`) → respaldo. Renombrar
`mp`→`mpipe`. Contador de origen de pose (§2.3).

**Celdas 17-18 (destilación) — con filtro de calidad, la corrección principal:**

Por cada par generado por CatVTON, aceptar solo si pasa **las cinco** pruebas; si no, reintentar hasta 3 semillas:

| Prueba | Criterio | Detecta en tu captura |
|---|---|---|
| Sin filtración | `mean|res − persona|` fuera de `zona` dilatada 3 px ≤ 3/255 | fantasmas fuera del recuadro |
| Color | ΔE (Lab) entre mediana de la prenda del catálogo y de la ropa nueva (SegFormer sobre `res`) ≤ 25 | guinda → marrón |
| Manga | brazo desnudo esperado por `sleeve_length` (larga ⇒ ≤ 12 % de piel en el brazo; corta ⇒ 25-70 %) | chaqueta de manga larga → camiseta corta |
| Cobertura | área de ropa superior nueva ≥ 0,6 × área de la zona de torso | prenda que no llena el tronco |
| Opacidad | píxeles "piel" dentro de la prenda ≤ 15 % | malla semitransparente |

Guardar `reporte_filtro.json` (aceptados/rechazados por causa y por categoría). **Parar si acepta < 60 %**: significa
que hay que arreglar el teacher, no entrenar el alumno. Antes de destilar: rechazar prendas de catálogo cuyo recorte
toque el borde de la imagen (la chaqueta cortada) o recortarlas con margen.

**Celda 5 (zona agnóstica).** Para chaquetas y abrigos, no usar el polígono con esquinas rectas: usar unión de
`parse(ropa previa)` dilatada + cápsulas de brazo + torso **con hombros redondeados** (`GaussianBlur` sobre la zona,
umbral 0,5). Menos "caja", mismos píxeles borrados.

**Celda 24 (pérdidas) — cerrar el recuadro:**

1. `final = persona·(1 − Mf) + salida·Mf`, con `Mf` = `zona` **suavizada** (blur σ≈2 px). Fuera de la zona, la
   salida es la persona, bit a bit.
2. `L1_fuera` sobre `(1 − zona)`, peso alto (≥ 5): la red no puede tocar lo que no es prenda.
3. `L_costura`: coincidencia de gradientes en el anillo de 6 px alrededor del borde de la zona.
4. Mantener las penalizaciones actuales (escote, mangas, forma vieja).

**Celda 26 (entrenamiento) — reanudable:**

```python
def guardar_estado(ep):
    estado = dict(modelo=modelo.state_dict(), disc=disc.state_dict(),
                  opt_g=opt_g.state_dict(), opt_d=opt_d.state_dict(),
                  sched=sched.state_dict(), esc_g=esc_g.state_dict(), esc_d=esc_d.state_dict(),
                  epoca=ep, hist=dict(hist), mejor=mejor,
                  rng=dict(py=random.getstate(), np=np.random.get_state(), torch=torch.get_rng_state()))
    guardar(DIR_CKPT / "ultimo.pth", estado)          # atómico (.tmp -> replace) y con tamaño > 1 MB

ini = 1
if (DIR_CKPT / "ultimo.pth").exists():
    ck = torch.load(DIR_CKPT / "ultimo.pth", map_location=DEV)
    # cargar todos los estados ... ; ini = ck["epoca"] + 1
for ep in range(ini, EPOCAS + 1):
    ...
    guardar_estado(ep)                                # cada época (cuestan ~30 s)
```

Añadir: guardado de emergencia cada 200 pasos dentro de la época, y `try/except OutOfMemoryError` por lote.

**Celda 28 (ONNX).** Ya verifica tamaño; añadir comparación PyTorch↔ONNX (`max|Δ| < 1e-3`) y **falla si el archivo pesa < 5 MB**.

### 2.5 Reparto en sesiones (cada una termina sola y se puede repetir)

| Sesión | Contenido | Tiempo T4 | Salida en Drive |
|---|---|---|---|
| A | Celda 0-4 + poses + prueba de humo (20 muestras) | ~15 min | `reporte_entorno.json` |
| B | Destilación con filtro (≈426 pares aceptados) | 60-100 min; **se reanuda sola** (`hechos`) | `pares/` + `reporte_filtro.json` |
| C | Entrenar alumno (40 épocas) | ~25-40 min | `ultimo.pth`, `mejor.pth` |
| D | Evaluación + ONNX + panel de control | ~10 min | `vestidor_camara.onnx`, `panel.png` |

Regla: **no empezar C si B no cumple los criterios de §2.6.**

### 2.6 Puertas de calidad (para que no se repita la foto)

Antes de dar por bueno el modelo, panel fijo de 12 casos (3 chaquetas de manga larga, 3 tops, 2 vestidos, 2 crop,
2 personas vestidas con jeans+sudadera) y estos umbrales sobre el conjunto de validación:

- Fuera de la zona: diferencia media con la persona ≤ 1/255 (debe ser 0 con el composite).
- Color de prenda: ΔE mediano ≤ 25 frente al catálogo.
- Concordancia de manga con `sleeve_length` ≥ 90 %.
- Sin recuadro: la prueba de borde (gradiente en el anillo) no supera 1,5× el de la foto original.
- **Revisión visual obligatoria** del panel; si una chaqueta de manga larga sale corta, no se avanza.

> Nota honesta: el alumno de 192×256 con 1,9 M parámetros **no** va a igualar a la difusión. Su rol es un aspecto
> "creíble" a 30 fps; lo que garantiza que la prenda no se pierda es el motor geométrico (§3), no el modelo.

---

## 3. Vestidor en vivo: que la prenda no se pierda + mejor colocación

**Regla de oro:** la cámara nunca depende del entrenamiento. El modelo corporal MediaPipe ya entrenado se conserva
y el motor geométrico es siempre el respaldo.

### 3.1 No perder la prenda (web `live-garment-engine.ts` / `virtual-tryon.component.ts`; misma lógica en `live_garment_engine.dart`)

1. **Caderas virtuales.** `hasUsableBody` pasa a exigir **solo hombros** (visibilidad > 0,5). Si las caderas no se
   ven, se estiman: `cadera = punto medio de hombros + down · (1,35 × ancho de hombros)` (con `down` tomado de la
   inclinación de hombros), y el largo de prenda se calcula igual que ahora. La prenda sigue puesta y "Necesito ver
   hombros y cadera" pasa a ser solo un aviso suave.
2. **Histéresis.** Entrar a "seguido" con visibilidad > 0,5 y salir solo por debajo de 0,25.
3. **Máscara con seguro.** Aplicar el recorte `destination-in` solo si la máscara cubre ≥ 55 % del rectángulo del
   torso estimado; si no, se omite ese fotograma y se conserva la última máscara buena (hasta 750 ms). Dilatar la
   máscara 6-8 px para no morder bordes.
4. **Fallo silencioso del delegado GPU.** Si tras 30 fotogramas con persona delante `landmarks` sigue vacío,
   destruir el landmarker y recrearlo con `delegate: 'CPU'` (una sola vez); guardar la decisión en `sessionStorage`.
5. **Recuperación por máscara.** Si la pose se pierde pero hay silueta, ubicar la prenda con la caja del torso de la
   máscara durante la ventana de gracia.
6. **Ventana de gracia** se mantiene (750 ms + 350 ms de desvanecido, borrar a 1,1 s).

**Prueba de aceptación automática** (script Node/Python sobre `video_prueba/*.mp4`, sin abrir la app):
inyectar pérdidas de pose de 1, 5, 15 y 30 fotogramas y caídas de las caderas; medir % de fotogramas con prenda visible.
Criterio: **0 desapariciones en pérdidas ≤ 750 ms** y prenda visible ≥ 98 % del video mientras la persona esté en cuadro.

### 3.2 Colocación más natural (a partir del video)

Orden por impacto/coste:

1. **Escote transparente:** el rig ya recorta con rembg; aplicar la máscara del recorte también a la zona del cuello
   (hoy sale una elipse oscura). Quitar cualquier círculo/marcador de depuración del pecho.
2. **Mangas que siguen al brazo:** afinar el ancho con `halfWidth` decreciente hombro→codo→muñeca y añadir 3 segmentos
   por brazo en vez de 2; recorte de la manga contra el brazo real usando la máscara. Con brazos levantados las mangas
   deben cambiar de dirección, no quedarse horizontales.
3. **Giro del cuerpo (yaw):** estimar con `z` de hombros; comprimir el ancho de la prenda por `cos(yaw)` y mover el
   centro hacia el hombro que avanza. Con giro ≥ 60° reducir opacidad progresivamente en vez de deformar.
4. **Malla más rica:** pasar de 18 filas × 1 columna a 18 × 5 columnas, con desplazamiento lateral extra en sisa y
   cintura para que la prenda se curve al inclinarse.
5. **Caída y balanceo del bajo:** resorte amortiguado sobre las filas inferiores (retardo ~80-120 ms) para dar
   sensación de tela; nada de bajo rígido.
6. **Luz de la escena:** medir brillo y temperatura medios del torso del video (16 px de muestra) y aplicar ese tono a la
   prenda; sombra suave de 2-3 px bajo el bajo y en el cuello.
7. **Oclusión:** ya existe para antebrazos cruzados (`restoreForearms`); verificar con brazos cruzados y mano en cintura.
8. **Talla automática:** ajustar `fitScaleFactor` con el ancho de la silueta a la altura del pecho, no solo con los
   hombros (los hombros de MediaPipe caen en el acromion, ya se compensa con 0,92).

Cambios deben aplicarse en **web y móvil a la vez** (misma geometría, `live_mirror_view.dart`).

---

## 4. Orden de trabajo recomendado

**Hoy, en tu PC (sin Colab):**
1. Aplicar §3.1 (caderas virtuales, histéresis, máscara con seguro, reintento CPU) y correr la prueba de aceptación.
2. Ejecutar `precalcular_poses.py` y revisar `reporte.json`.
3. Corregir el cuaderno: `mp`→`mpipe`/`mt`, celda 0 nueva, `.task` local, lectura de poses, filtro de calidad,
   composite + pérdidas de costura, reanudación.
4. Reempaquetar el ZIP **incluyendo** `cache/` (59 MB) y `06_poses_precalculadas/`; mover el cuaderno obsoleto.

**Después, en Colab:** sesiones A → B → C → D (§2.5), sin saltar la puerta de §2.6.

**Último:** mejoras de §3.2 en el orden listado, midiendo cada una contra el video.

## 5. Criterios de "listo"

- [ ] Prenda visible ≥ 98 % del video de prueba; 0 desapariciones en pérdidas ≤ 750 ms; sigue con GPU forzada a fallar.
- [ ] Sesión A sin errores; pose del respaldo ≤ 15 %.
- [ ] Sesión B: ≥ 60 % de pares aceptados, ≥ 300 vestidas + 126 HD, `reporte_filtro.json` guardado.
- [ ] Sesión C: reanuda tras cortar a propósito (probar cortando en la época 3).
- [ ] Panel de 12 casos aprobado a ojo, incluida la chaqueta guinda de manga larga.
- [ ] `.onnx` > 5 MB y PyTorch↔ONNX coinciden.

## 6. Riesgos abiertos

- Si el teacher (CatVTON) rechaza > 40 % de los pares, hay que revisar la zona agnóstica o cambiar de teacher antes de entrenar.
- El video enviado es de tu prototipo; sin un video de referencia externo, el objetivo de "cómo debe moverse" se
  basa en §1.4 y en estándares habituales de probadores AR.
- Las cifras de tiempo de T4 (§2.5) son estimaciones a partir del propio cuaderno (8-15 s por par en CatVTON, ~22 min de
  entrenamiento); hay que medirlas en la sesión A.

---

## 7. Estado de implementación (2026-09-21)

**Hecho y verificado**

| Qué | Dónde | Verificación |
|---|---|---|
| Prenda no se pierde: solo hombros obligatorios, caderas estimadas, histéresis 0.5/0.25 | `live-garment-engine.ts`, `live_garment_engine.dart` | `pruebas_camara/`: sobre tu video la regla vieja mostraba la prenda en el 93.1 % de los fotogramas; la nueva, 100 % (0 parpadeos). Con caderas fuera de cuadro: 0 % → 100 %. Con visibilidad oscilando en 0.5: 1292 parpadeos → 1 |
| Cadera estimada calibrada con datos | mismas | torso = 1.55 anchos de hombro (medido en 737 personas + el video), no 1.3; corregido también el efecto de la proporción del vídeo. Error mediano 0.16 anchos de hombro (p90 0.30) |
| Silueta con seguro (cobertura ≥ 55 % del torso, última buena 750 ms, dilatada) | `virtual-tryon.component.ts` | máscara vacía → no se usa; llena → se usa |
| Reintento en CPU si la GPU no detecta | `virtual-tryon.component.ts` (`watchPoseHealth`) | **solo revisado por tipos, no probado en un equipo con GPU defectuosa** |
| Poses precalculadas (2821/2842 = 99.3 %) | `precalcular_poses.py` → `06_poses_precalculadas/` | remapeo al letterbox 384×512 vs detección directa: error 1.3 % del ancho de hombros |
| Cuaderno: `mp`→`mpipe`/`mt`, dependencias 3.13, poses precalculadas, caché atómico, filtro de calidad, composite, banda de costura, entrenamiento reanudable, puertas A y B, panel de progreso | `VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb` | sintaxis y nombres (pyflakes) OK; **reanudación probada con torch en 5 escenarios** (incl. checkpoint cortado a mitad); pérdidas ejecutadas con tensores sintéticos; filtro del profesor probado con casos sintéticos (acepta el bueno; rechaza color, manga y malla) |
| ZIP para Drive con el caché de 1735+ personas y las poses | `../entrenamiento_ia_ropa_PARA_DRIVE_V5.zip` (60 MB) | contenido comprobado |

**No verificado (no se puede sin Colab/GPU)**: la ejecución de punta a punta en la T4, la descarga de CatVTON, los tiempos
de §2.5 y **los umbrales del filtro** (`U` en la celda de destilación: fuga 12, color 30, etc.). Son valores iniciales; el
informe de la Puerta A muestra las distribuciones para ajustarlos.

**Pendiente de §3.2 (colocación más natural)**: escote transparente, mangas que siguen al brazo con brazos en alto, giro del
cuerpo (yaw), malla 18×5, balanceo del bajo, luz de la escena. Recuperación por máscara (§3.1-5) tampoco se implementó. La
paridad de la máscara segura en móvil no aplica (el motor Dart no usa máscara).
