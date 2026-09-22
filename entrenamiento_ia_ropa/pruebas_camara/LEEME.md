# Prueba de aceptación de la cámara (la prenda no debe perderse)

Compara la regla **vieja** (hombros + caderas > 0.5) con el motor **nuevo** (`resolveBody`) sobre los
landmarks de un video real, en 4 escenarios: video tal cual, caderas fuera de cuadro, visibilidad
oscilando en 0.5 y una comprobación de la máscara. Además mide el error de la cadera estimada.

```bash
# 1) landmarks del video (desde entrenamiento_ia_ropa/)
python pruebas_camara/extraer_landmarks_video.py "C:/ruta/video.mp4" pruebas_camara/video_landmarks.json

# 2) compilar el motor (desde frontend-web/) a una carpeta eng/ junto al script
npx tsc src/app/packages/paquete_inteligente_y_analitica/virtual-tryon/live-garment-engine.ts \
  --outDir ../entrenamiento_ia_ropa/pruebas_camara/eng --target es2020 --module commonjs --lib es2020,dom --skipLibCheck

# 3) ejecutar (desde entrenamiento_ia_ropa/pruebas_camara/)
node prueba_motor.js
```

Resultado esperado: escenarios A, B y C ≥ 98 % (sale con código 0), y cadera estimada con
mediana ≤ 0.3 anchos de hombro. Con el video de prueba: A 100 % (la regla vieja 93.1 %),
B 100 % (vieja 0 %), C 99.9 % con 1 parpadeo (vieja 1292).
