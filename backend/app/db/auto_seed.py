import json
import os
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

SEED_FILE_PATH = os.path.join(os.path.dirname(__file__), "catalog_seed_data.json")

def auto_seed_catalog_if_needed(engine):
    """
    Inicialización Segura y No Destructiva del Catálogo Maestro.
    - Si la tabla 'products' tiene al menos 1 producto: NO HACE NADA.
      Esto garantiza que NINGÚN dato de producción o despliegue sea sobrescrito ni borrado.
    - Si la tabla 'products' está completamente vacía (0 productos):
      Puebla automáticamente las 16 tablas maestras (roles, usuarios, sucursales,
      categorías, temporadas, colores, tallas, 89 productos, variantes, inventario, etc.)
      a partir de 'catalog_seed_data.json'.
    - Al terminar, actualiza las secuencias autoincrementales de PostgreSQL para evitar colisiones.
    """
    if not os.path.exists(SEED_FILE_PATH):
        logger.warning(f"[AUTO-SEED] Archivo no encontrado: {SEED_FILE_PATH}. Omitiendo inicialización.")
        return

    try:
        with engine.begin() as conn:
            # 1. Comprobar si la tabla products existe y cuántos registros tiene
            res = conn.execute(text("SELECT count(*) FROM products")).scalar()
            if res is not None and res > 0:
                print(f"[AUTO-SEED] Base de datos contiene {res} productos. Preservando datos existentes intactos.")
                return

            print("[AUTO-SEED] Base de datos vacía (0 productos detectados). Iniciando población de catálogo maestro...")
            with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
                seed_data = json.load(f)

            table_order = [
                'roles',
                'users',
                'user_roles',
                'branches',
                'branch_employees',
                'categories',
                'seasons',
                'colors',
                'sizes',
                'products',
                'product_images',
                'product_variants',
                'inventory',
                'suppliers',
                'coupons',
                'seasonal_promotions'
            ]

            for tbl in table_order:
                rows = seed_data.get(tbl, [])
                if not rows:
                    continue

                # En categories, insertar primero aquellas con parent_id IS NULL para respetar la clave foránea
                if tbl == 'categories':
                    rows = sorted(rows, key=lambda r: (r.get('parent_id') is not None, r.get('id', 0)))

                cols = list(rows[0].keys())
                col_names = ", ".join(f'"{c}"' for c in cols)
                col_params = ", ".join(f":{c}" for c in cols)
                insert_sql = f'INSERT INTO "{tbl}" ({col_names}) VALUES ({col_params}) ON CONFLICT DO NOTHING'

                conn.execute(text(insert_sql), rows)
                print(f"[AUTO-SEED] Tabla '{tbl}' procesada ({len(rows)} registros).")

            # 2. Sincronizar secuencias serial de PostgreSQL
            serial_tables = [
                'roles', 'users', 'branches', 'categories', 'seasons',
                'colors', 'sizes', 'products', 'product_images',
                'product_variants', 'suppliers', 'coupons', 'seasonal_promotions'
            ]
            for st in serial_tables:
                try:
                    conn.execute(text(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{st}', 'id'),
                            COALESCE((SELECT MAX(id) FROM "{st}"), 1)
                        );
                    """))
                except Exception:
                    pass

            print("[AUTO-SEED] ¡Catálogo maestro de 89 productos inicializado exitosamente en la base de datos!")

    except Exception as e:
        print(f"[AUTO-SEED] Advertencia o error durante la verificación del catálogo: {e}")
