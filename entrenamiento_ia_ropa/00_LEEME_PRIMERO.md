# entrenamiento_ia_ropa — empieza aquí

1. **Elige tu plataforma de entrenamiento en la nube:**
   - **Kaggle (Recomendado):** Sigue [`GUIA_ENTRENAMIENTO_KAGGLE_VTON.md`](file:///c:/Users/MARILYN/Documents/Carpeta%20Esther/Semestre%202-2026/SI%202/Primer_parcial/entrenamiento_ia_ropa/GUIA_ENTRENAMIENTO_KAGGLE_VTON.md). Sube `entrenamiento_ia_ropa_PARA_DRIVE_V5.zip` a Kaggle Datasets y ejecuta [`03_notebooks_kaggle/VESTIDOR_VIRTUAL_ENTRENAMIENTO_KAGGLE.ipynb`](file:///c:/Users/MARILYN/Documents/Carpeta%20Esther/Semestre%202-2026/SI%202/Primer_parcial/entrenamiento_ia_ropa/03_notebooks_kaggle/VESTIDOR_VIRTUAL_ENTRENAMIENTO_KAGGLE.ipynb) con GPU T4 x2 o P100 e **Internet ON**.
   - **Google Colab:** Lee [`GUIA_ENTRENAMIENTO_COLAB_VTON.md`](file:///c:/Users/MARILYN/Documents/Carpeta%20Esther/Semestre%202-2026/SI%202/Primer_parcial/entrenamiento_ia_ropa/GUIA_ENTRENAMIENTO_COLAB_VTON.md) y usa [`03_notebooks_colab/VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb`](file:///c:/Users/MARILYN/Documents/Carpeta%20Esther/Semestre%202-2026/SI%202/Primer_parcial/entrenamiento_ia_ropa/03_notebooks_colab/VESTIDOR_VIRTUAL_ENTRENAMIENTO.ipynb).

2. **Dataset listo:**
   - El archivo `entrenamiento_ia_ropa_PARA_DRIVE_V5.zip` (en la raíz del proyecto, ~60 MB) contiene los 9 cuerpos HD, las 68 prendas clasificadas, las 1735 personas vestidas con máscaras y las poses precalculadas (`06_poses_precalculadas/`, 99.3%).

3. **Reanudación automática:**
   - Si la sesión se interrumpe, vuelve a ejecutar: cada celda retoma exactamente donde quedó gracias al sistema de caché por pasos.

4. **Puertas de calidad:**
   - Puerta A (tasa de aceptación del profesor CatVTON) y Puerta B (calidad y similitud de textura del alumno) garantizan que solo se exporte un modelo si no hay recuadros rígidos ni deformaciones.

Obsoleto: `_obsoletos/ENTRENAMIENTO_VTON_COLAB.ipynb` y `PLAN_MAESTRO_ENTRENAMIENTO_VTON_V4.md`.
`pruebas_camara/` = prueba de que la prenda no se pierde en cámara (ver su LEEME).
