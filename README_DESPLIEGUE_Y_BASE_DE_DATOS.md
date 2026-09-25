# FASHIONSTORE — GUÍA RÁPIDA DE DESPLIEGUE Y PERSISTENCIA DE DATOS

> **AVISO IMPORTANTE PARA EL DESPLIEGUE:**  
> Este repositorio incluye una arquitectura de **Protección de Datos (Zero Data Loss)** para garantizar que el catálogo maestro de **89 productos, variantes e inventario** se mantenga disponible y que **ningún dato se pierda ni se borre** al desplegar en servidores remotos o en la nube.

---

## 🚀 ¿CÓMO FUNCIONA EL CATÁLOGO EN PRODUCCIÓN?

1. **Auto-Semilla No Destructiva (`auto_seed.py`):**
   * Al arrancar el backend (`app.main:app`), el sistema verifica si la tabla de productos contiene registros.
   * **Si la base de datos está vacía (0 productos):** Se auto-puebla automáticamente desde `backend/app/db/catalog_seed_data.json` con los 89 productos, categorías, tallas, colores e inventario.
   * **Si la base de datos ya tiene datos:** El backend detecta los productos existentes y **NO HACE NADA**, preservando al 100% todos los pedidos, usuarios, ventas y datos previos.

2. **Carga Manual Alternativa vía SQL:**
   * Si prefieres inicializar la base de datos por consola o pgAdmin, puedes ejecutar el script:
     `documentos/scripts_sql/backup_catalogo_maestro_89_productos.sql`
   * Utiliza sentencias `INSERT INTO ... VALUES (...) ON CONFLICT DO NOTHING;` por lo que es completamente seguro y no duplicará datos.

---

## ⚠️ REGLAS OBLIGATORIAS PARA EL DESPLIEGUE EN DOCKER

Si despliegas la base de datos en Docker, asegúrate de utilizar **volúmenes persistentes**:

```yaml
services:
  db:
    image: postgres:15
    volumes:
      - pgdata_fashionstore:/var/lib/postgresql/data  # <-- OBLIGATORIO para no perder datos

volumes:
  pgdata_fashionstore:
```

* **NUNCA** ejecutes `docker-compose down -v` en el servidor de producción (el flag `-v` destruye los volúmenes de datos).
* Para actualizar el código en el servidor, usa únicamente:
  ```bash
  git pull origin main
  docker-compose up -d --build
  ```

---

## 📖 DOCUMENTACIÓN DETALLADA

Para consultar la explicación técnica completa sobre el funcionamiento de Git vs. Base de Datos, prevención de pérdida de datos y diagramas de flujo, revisa el archivo:
* [`documentos/GUIA_PERSISTENCIA_Y_DESPLIEGUE_BASE_DE_DATOS.md`](documentos/GUIA_PERSISTENCIA_Y_DESPLIEGUE_BASE_DE_DATOS.md)
