# GUÍA DE PERSISTENCIA Y PROTECCIÓN DE DATOS EN EL DESPLIEGUE
## Sistema FashionStore — Comercio Electrónico con Vestidor Virtual (RA)

---

## 1. DIAGNÓSTICO: ¿POR QUÉ NO SE MANTENÍAN LOS DATOS AL DESPLEGAR?

Para comprender el comportamiento del sistema y evitar cualquier pérdida de información, es fundamental distinguir la diferencia entre el **Código Fuente** y el **Motor de Base de Datos**:

```
               TU COMPUTADORA (Localhost)                         SERVIDOR EN LA NUBE (Despliegue)
 ┌───────────────────────────────────────────────────┐    ┌──────────────────────────────────────────────────┐
 │ • Código Fuente (Python, Angular, Flutter, etc.)  │    │ • Código Fuente desplegado                       │
 │ • PostgreSQL Local (localhost:5432)               │    │ • PostgreSQL Remoto / Cloud SQL / Docker         │
 │    └─> 89 Productos, 27 Categorías, 426 Inventario│    │    └─> Base de datos SEPARADA e INDEPENDIENTE   │
 └─────────────────────────┬─────────────────────────┘    └────────────────────────▲─────────────────────────┘
                           │                                                       │
                           │  git push                  git pull / docker build    │
                           └─────────────────> GITHUB ─────────────────────────────┘
                                   (Git SOLO transporta ARCHIVOS DE CÓDIGO,
                                    NUNCA transporta filas de PostgreSQL)
```

### Causas identificadas del problema anterior:
1. **Git solo versiona archivos de código:** Al ejecutar `git push`, Git traslada archivos `.py`, `.ts`, `.html`, imágenes y configuraciones. **Git no extrae ni traslada registros o filas de la base de datos local**.
2. **Base de datos remota vacía:** El servidor desplegado se conecta a una base de datos PostgreSQL distinta e independiente en la nube. Al arrancar el backend por primera vez, SQLAlchemy ejecuta `Base.metadata.create_all()`, lo que crea las **tablas vacías**. Como el catálogo de 89 productos residía en el PostgreSQL local de tu máquina, la página web desplegada no mostraba productos.
3. **Almacenamiento efímero en Docker (Pérdida de datos al reiniciar):** Si en el servidor remoto levantaban PostgreSQL en un contenedor Docker sin un **volumen persistente** montado en el disco del host, cada vez que el contenedor se detenía, reiniciaba o redesplegaba, la base de datos se destruía y volvía a crearse completamente en blanco.
4. **Scripts de prueba con TRUNCATE:** Existían scripts de limpieza antiguos (`TRUNCATE TABLE ... CASCADE`) que, si eran ejecutados en el servidor, borraban inmediatamente todas las tablas.

---

## 2. ARQUITECTURA DE PROTECCIÓN DE DATOS IMPLEMENTADA (ZERO DATA LOSS)

Se implementó una solución de **3 capas** para garantizar que los datos estén siempre disponibles y que **NUNCA se borre ni sobrescriba la información existente**:

```
                                      ARRANQUE DE FASTAPI (main.py)
                                                    │
                                                    ▼
                                    ¿SELECT count(*) FROM products?
                                                   / \
                                     (count == 0) /   \ (count > 0)
                                                 /     \
                                                ▼       ▼
                       ┌───────────────────────────┐   ┌──────────────────────────────────────────────┐
                       │  BASE DE DATOS EN BLANCO  │   │        BASE DE DATOS CON INFORMACIÓN         │
                       ├───────────────────────────┤   ├──────────────────────────────────────────────┤
                       │ Auto-puebla los 89        │   │ NO TOCA NADA. Preserva al 100% todos los     │
                       │ productos, categorías,    │   │ productos, usuarios, pedidos y ventas        │
                       │ variantes e inventario    │   │ existentes en la nube sin riesgo de pérdida. │
                       └───────────────────────────┘   └──────────────────────────────────────────────┘
```

### Capa 1: Semilla Maestra Portátil (`catalog_seed_data.json`)
* **Ubicación:** `backend/app/db/catalog_seed_data.json` (276 KB).
* **Contenido exportado desde localhost:**
  * **89 Productos** activos con precios, descripciones y materiales.
  * **27 Categorías** organizadas jerárquicamente.
  * **241 Variantes de productos** (combinaciones de tallas y colores).
  * **426 Registros de inventario** con stock distribuido entre sucursales.
  * **72 Imágenes de productos**.
  * **2 Sucursales físicas** con horarios, geolocalización y servicios.
  * **25 Usuarios y roles** del sistema.
  * **15 Colores y 17 Tallas**.
  * **5 Proveedores** y promociones de temporada.

### Capa 2: Auto-Seed Idempotente en el Arranque (`auto_seed.py`)
* **Ubicación:** `backend/app/db/auto_seed.py`
* **Integración:** Ejecutado automáticamente en `backend/app/main.py` durante el ciclo de vida del servidor.
* **Mecanismo de seguridad:**
  1. Consulta `SELECT count(*) FROM products`.
  2. **Si `count > 0`:** El sistema detecta que la base de datos ya está en producción o contiene datos de trabajo. Muestra en el log:
     ```
     [AUTO-SEED] Base de datos contiene {count} productos. Preservando datos existentes intactos.
     ```
     **No ejecuta ninguna modificación, asegurando que ningún pedido, usuario, producto o venta se pierda.**
  3. **Si `count == 0`:** Detecta que es un despliegue nuevo o una base de datos recién creada, e inserta ordenadamente todo el catálogo maestro utilizando:
     ```sql
     INSERT INTO "tabla" (...) VALUES (...) ON CONFLICT DO NOTHING;
     ```
  4. **Sincronización de secuencias seriales:** Actualiza automáticamente `setval(pg_get_serial_sequence('...', 'id'), MAX(id))` para que nuevas inserciones manuales desde la web o el móvil no generen conflictos de clave primaria.

### Capa 3: Respaldo SQL Puro (`backup_catalogo_maestro_89_productos.sql`)
* **Ubicación:** `documentos/scripts_sql/backup_catalogo_maestro_89_productos.sql` (268 KB).
* Contiene sentencias SQL estándar listas para ser ejecutadas en pgAdmin, DBeaver o consola terminal `psql`.
* Puede utilizarse si el administrador del servidor desea realizar la carga manualmente antes de iniciar los contenedores.

---

## 3. CHECKLIST OBLIGATORIO PARA QUIEN DESPLIEGA EN EL SERVIDOR (AMIGO / DEVOPS)

Para asegurar que el despliegue en la nube mantenga los datos de forma permanente:

### A. Si se utiliza Docker Compose (Recomendado)
Asegurar que el servicio de base de datos tenga un volumen persistente nombrado:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: fashionstore_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: tu_password_seguro
      POSTGRES_DB: fashionstore_db
    volumes:
      # OBLIGATORIO: Este volumen evita que los datos se borren al reiniciar
      - pgdata_fashionstore:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    container_name: fashionstore_backend
    restart: always
    environment:
      DATABASE_URL: postgresql://postgres:tu_password_seguro@db:5432/fashionstore_db
    depends_on:
      - db
    ports:
      - "8000:8000"

volumes:
  pgdata_fashionstore:
    driver: local
```

> **IMPORTANTE:** Al actualizar el código en el servidor, **NUNCA** usar `docker-compose down -v` (la opción `-v` borra los volúmenes). Usar simplemente:
> ```bash
> git pull origin main
> docker-compose up -d --build
> ```

### B. Si se utiliza PostgreSQL administrado (Google Cloud SQL, Supabase, Neon, RDS)
1. Solo configurar la variable de entorno `DATABASE_URL` en el archivo `.env` del servidor.
2. Al iniciar el backend, FastAPI detectará si la base de datos está vacía y cargará los 89 productos automáticamente.
3. Si la base ya tiene datos, no alterará nada.

### C. Carga manual mediante SQL (Opcional)
Si se desea poblar la base de datos manualmente vía consola:
```bash
psql -U postgres -d fashionstore_db -f documentos/scripts_sql/backup_catalogo_maestro_89_productos.sql
```

---

## 4. INSTRUCCIONES PARA HACER PUSH CON TOTAL SEGURIDAD

Ejecuta los siguientes comandos desde tu terminal de PowerShell en la raíz del proyecto:

```powershell
# 1. Comprobar el estado del repositorio
git status -s

# 2. Agregar los componentes verificados
git add backend/ frontend-web/ mobile/ documentos/ README_DESPLIEGUE_Y_BASE_DE_DATOS.md .gitignore

# 3. Registrar el commit descriptivo
git commit -m "feat: integracion de auto-seed de catalogo maestro (89 productos), diagramas UML canonicos y guia de persistencia"

# 4. Enviar los cambios a la rama principal
git push origin main
```

---

## 5. RESUMEN DE ARCHIVOS CLAVE DE PERSISTENCIA

| Archivo | Propósito | Comportamiento |
|---|---|---|
| `backend/app/db/catalog_seed_data.json` | Snapshot del catálogo maestro (89 productos). | Solo lectura para inicializaciones. |
| `backend/app/db/auto_seed.py` | Lógica de auto-población en FastAPI. | Solo actúa si `products == 0`. Idempotente. |
| `backend/app/main.py` | Punto de entrada del backend. | Invoca de forma segura a `auto_seed.py` al arrancar. |
| `documentos/scripts_sql/backup_catalogo_maestro_89_productos.sql` | Script SQL con sentencias `INSERT ... ON CONFLICT DO NOTHING`. | Compatible con cualquier cliente PostgreSQL. |
| `.gitignore` | Exclusión de volcados temporales y scripts locales. | Protege el repositorio de archivos temporales. |
