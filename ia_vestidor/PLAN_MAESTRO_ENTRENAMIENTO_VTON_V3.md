# Plan maestro de entrenamiento VTON v4.0

> Proyecto: FashionStore - Vestidor virtual (CU32)  
> Estado revisado: **datos de catalogo listos; entrenamiento VTON supervisado aun no listo**  
> Entorno objetivo: Google Colab con GPU T4 o superior

## 1. Conclusion de la revision

El material actual contiene 9 fotografias de cuerpos y 68 fotografias de prendas. Es util para probar segmentacion, composicion geometrica e integracion con el sistema, pero **no es un dataset pareado de virtual try-on**: no hay una imagen objetivo real de cada persona usando la prenda que se entrega al modelo.

El entrenamiento v3 empareja cuerpos y prendas al azar y calcula parte de la perdida contra la propia foto de la prenda. Por eso una perdida baja no demuestra que el resultado vista correctamente a la persona. Tampoco implementa las promesas del plan anterior sobre MediaPipe, anclaje por categoria o suavizado temporal. No se recomienda gastar otra sesion larga de GPU con ese script sin corregir primero los datos y el protocolo de evaluacion.

Los resultados anteriores confirman esta limitacion: varias salidas reconstruyen o deforman la prenda sobre fondo blanco, pero no producen una persona vestida evaluable.

## 2. Objetivo realista del sistema

Se separan dos modos con necesidades distintas:

1. **Camara en vivo:** usar MediaPipe y el motor geometrico local para mantener la prenda estable a velocidad interactiva. La estabilidad temporal se resuelve en inferencia con seguimiento y suavizado entre fotogramas, no con imagenes independientes.
2. **Foto de alta calidad:** usar un modelo VTON preentrenado y, cuando exista un dataset pareado suficiente, realizar fine-tuning. Este modo puede tardar segundos y prioriza realismo.

No se promete conservar el 100% de los pixeles ni inferencia de 25 ms hasta medirlo en el equipo de destino. La textura puede preservarse en gran parte mediante warping, pero escotes, mangas, oclusiones y pliegues requieren sintesis y pueden cambiar detalles.

### Requisito obligatorio: la prenda no desaparece en camara

El modelo corporal MediaPipe ya existente se conserva. La aplicacion debe cumplir estas reglas independientemente del entrenamiento de la prenda:

- Cargar `pose_landmarker_lite.task` desde los archivos locales, sin depender de una descarga al iniciar.
- Intentar el delegado GPU y cambiar automaticamente a CPU si WebGL/GPU no puede inicializar MediaPipe.
- Usar umbrales de deteccion, presencia y seguimiento de 0.55.
- No borrar la prenda por un unico fotograma perdido.
- Mantener la ultima pose confiable durante 750 ms y desvanecerla durante 350 ms adicionales.
- Suavizar landmarks con One Euro Filter y conservar la ultima mascara corporal durante la ventana de recuperacion.
- Borrar la prenda despues de 1.1 segundos sin pose para evitar que quede congelada cuando la persona sale de escena.

Criterio de aceptacion: en una prueba de video con giros y movimiento normal, ninguna perdida de pose menor o igual a 750 ms puede hacer desaparecer la prenda. Si el delegado GPU falla, la camara debe continuar con CPU.

## 3. Alcance de la primera version entrenable

La primera fase debe limitarse a ropa superior:

- Blusas
- Camisas
- Camisetas
- Tops y crop tops
- Sueteres
- Chaquetas

Vestidos, enterizos, pantalones, jeans, pijamas y conjuntos quedan para fases posteriores porque necesitan mascaras objetivo, longitudes y reglas de oclusion diferentes.

## 4. Datos requeridos

### 4.1 Datos disponibles

- 9 cuerpos diversos para pruebas cualitativas.
- 68 prendas de catalogo en 11 categorias.
- Metadatos de prendas y cuerpos.
- Checkpoints anteriores conservados solo como evidencia y posible comparacion.

### 4.2 Datos faltantes para entrenar

Cada muestra supervisada debe incluir, como minimo:

```text
sample_id/
|- person.jpg          # persona con una prenda real
|- cloth.jpg           # imagen aislada de esa misma prenda
|- target.jpg          # verdad terreno; normalmente coincide con person.jpg
|- cloth_mask.png
|- human_parse.png
|- pose.json
`- metadata.json       # categoria, identidad, prenda y licencia/origen
```

Meta minima para un piloto: 500 pares de ropa superior para entrenamiento, 50 para validacion y 50 para prueba. Para una mejora solida conviene usar miles de pares de un dataset VTON licenciado. Las 9 personas propias se reservan para prueba final y no deben repetirse entre train, validacion y test.

El split se realiza por identidad de persona y, de ser posible, por prenda. Esto evita que el modelo memorice la misma foto y reporte metricas artificialmente altas.

## 5. Plan por fases

### Fase 0 - Preflight y linea base

1. Ejecutar `python validar_dataset.py`.
2. Ejecutar `python verificar_mediapipe_colab.py --strict` para cargar el modelo local y comprobar los cuerpos.
3. Corregir imagenes ilegibles, metadatos ausentes y duplicados.
4. Medir el motor actual con las 9 personas y una seleccion fija de ropa superior.
5. Probar caidas artificiales de pose de 1, 5, 15 y 30 fotogramas.
6. Guardar ejemplos de exito y fallo: cuello, mangas, torso, bodi negro, movimiento y fondo complejo.

Salida: reporte reproducible y conjunto fijo de casos de prueba.

### Fase 1 - Preparar dataset pareado

1. Obtener un dataset VTON con permiso de uso y estructura pareada.
2. Normalizar orientacion, color RGB y resolucion sin deformar la relacion de aspecto.
3. Generar o verificar `cloth_mask`, `human_parse` y pose.
4. Crear manifiestos `train.csv`, `val.csv` y `test.csv` con IDs sin filtraciones.
5. Mantener el catalogo FashionStore como conjunto externo de inferencia, no como verdad terreno.

Salida: al menos 600 pares validos para el piloto y cero cruces de identidad entre particiones.

### Fase 2 - Piloto de fine-tuning

1. Partir de pesos VTON preentrenados; no entrenar una red generativa desde cero con 9 cuerpos.
2. Entrenar primero solo ropa superior a 256x192 o 384x288.
3. Usar precision mixta, checkpoints reanudables y semilla fija.
4. Hacer una corrida corta de 1 epoca y 20 muestras antes de la corrida completa.
5. Revisar visualmente el mismo panel fijo cada epoca.

Salida: checkpoint piloto y registro completo de configuracion, versiones, semilla y metricas.

### Fase 3 - Evaluacion

Las metricas se calculan contra la imagen objetivo pareada, nunca contra una prenda no relacionada:

- LPIPS y SSIM sobre el resultado completo.
- IoU/Dice de la region de prenda contra la region objetivo.
- Error de bordes en cuello, hombros, mangas y cintura.
- Fidelidad de color dentro de la mascara de prenda.
- Tasa de fallos por categoria y tipo corporal.
- En video: jitter de landmarks y porcentaje de fotogramas donde la prenda desaparece.

El modelo solo avanza si mejora la linea base en el conjunto de prueba y no empeora de forma visible los casos de bodi negro, brazos cruzados y tallas diversas.

### Fase 4 - Integracion

1. Exportar a ONNX solo las operaciones compatibles y comparar salida PyTorch/ONNX.
2. Medir latencia real en CPU y GPU con 50 ejecuciones.
3. Integrar primero detras de una bandera de configuracion.
4. Mantener el motor geometrico como fallback cuando falle pose, segmentacion o modelo.
5. Agregar pruebas de contrato para nombres, formas, rangos y resolucion de entradas.

## 6. Estructura para Google Drive

```text
entrenamiento_ia_ropa/
|- 00_LEEME_PRIMERO.md
|- PLAN_MAESTRO_ENTRENAMIENTO_VTON_V4.md
|- validar_dataset.py
|- verificar_mediapipe_colab.py
|- requirements_colab.txt
|- 00_modelos_base/
|  `- pose_landmarker_lite.task
|- dataset_manifest.json
|- dataset_metadata.csv
|- 01_cuerpos/
|- 02_prendas/
|- 03_notebooks_colab/
|  `- 00_VALIDAR_ANTES_DE_ENTRENAR.ipynb
|- 05_reportes/
`- dataset_pareado/                # se agrega antes del fine-tuning
   |- train/
   |- val/
   `- test/
```

La carpeta `04_checkpoints_modelos` no se incluye en la subida inicial: pesa cerca de 1.9 GB y contiene resultados anteriores. Debe conservarse localmente como respaldo.

## 7. Criterio para comenzar

Se puede comenzar ahora con la validacion, la linea base y la preparacion del dataset. El fine-tuning supervisado comienza cuando el validador informe:

- todas las imagenes legibles;
- MediaPipe importa correctamente y detecta al menos 70% de los cuerpos de prueba;
- la camara supera la prueba de perdida breve sin borrar la prenda;
- metadatos consistentes;
- al menos 500 pares de entrenamiento;
- al menos 50 pares de validacion y 50 de prueba;
- splits sin identidades repetidas;
- una corrida de humo de 20 muestras completada.

Hasta cumplir esas condiciones, ejecutar 80 epocas del script v3 produciria un artefacto experimental, no un modelo confiable para produccion.
