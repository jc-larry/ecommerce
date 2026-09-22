# Guía de Deployment - Preservación de Base de Datos

**Fecha:** 21/09/2026  
**Importante:** Leer ANTES de hacer deploy en Render

---

## 📌 RESUMEN CRÍTICO

**NO ejecutar `CREATE_ALL` o `DROP TABLE` en producción**

La BD de producción debe:
- ✅ Persister datos entre deployments
- ✅ Tener datos iniciales (roles, admin, productos)
- ✅ Mantener historial de órdenes, usuarios, inventario
- ❌ NO borrar datos al redeploy

---

## 🗄️ Configuración Actual de BD

### En Desarrollo (localhost)
```python
# backend/app/main.py
Base.metadata.create_all(bind=engine)  # Crea tablas si no existen
```

**Comportamiento:** 
- Crea tablas automáticamente
- NO elimina datos
- Idempotente (seguro ejecutar múltiples veces)

### En Producción (Render)
```
DATABASE_URL=postgresql://user:pass@host:port/fashionstore
```

**Base de datos: PostgreSQL en Render (persistente)**

---

## 🚀 Deployment en Render - Procedimiento Correcto

### PASO 1: Antes de Conectar BD a Render

1. **Ve a Render Dashboard**
   - https://dashboard.render.com
   
2. **Crea PostgreSQL Database:**
   - Name: `fashionstore-db`
   - Plan: Standard (mínimo recomendado)
   - PostgreSQL Version: 14+
   
3. **Copia la connection string:**
   ```
   postgresql://user:pass@host:5432/fashionstore
   ```

### PASO 2: Configurar Variables de Entorno en Render

En tu deploy de FastAPI en Render, agrega estas variables en **Settings → Environment:**

```env
# Base de Datos (PostgreSQL de Render)
DATABASE_URL=postgresql://[USER]:[PASSWORD]@[HOST]:[PORT]/fashionstore

# PayPal (ver PAYPAL_FIX_CHANGELOG.md)
PAYPAL_CLIENT_ID=xxxxx
PAYPAL_CLIENT_SECRET=xxxxx
PAYPAL_MODE=sandbox

# Otros
SECRET_KEY=tu_clave_secreta_super_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

BACKEND_CORS_ORIGINS=https://tu-frontend.onrender.com

FRONTEND_URL=https://tu-frontend.onrender.com

# SMTP (opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com

# Hugging Face
HUGGINGFACE_API_TOKEN=hf_xxxxx
```

### PASO 3: Build Command (Render)

En Render, en la sección **Build Command**, coloca:

```bash
cd backend && pip install -r requirements.txt && python preload_models.py
```

**Explicación:**
- `pip install -r requirements.txt` → instala dependencias
- `python preload_models.py` → descarga modelos de IA (solo primera vez)
- NO ejecuta `CREATE_ALL` aquí (se ejecuta en Start)

### PASO 4: Start Command (Render)

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Lo que sucede:**
1. `app.main` carga `Base.metadata.create_all(bind=engine)`
2. Crea tablas si NO existen
3. NO borra datos existentes (SEGURO)
4. Ejecuta migraciones ligeras en `main.py`

---

## 📊 Datos Iniciales - Seeds

Para que producción tenga datos listos:

### 1. Roles y Admin (Automático)
```python
# backend/seed_admin.py
python seed_admin.py
```

**Crea:**
- Roles: SUPERADMIN, ENCARGADO, CAJERO, CLIENTE, REPARTIDOR
- Usuario admin default:
  - Email: `admin@fashionstore.local`
  - Password: `admin123` (cambiar en producción)

**Ejecutar en Render:** 
- Via SSH Console o en el build (antes del start)
- O ejecutar manualmente después del primer deploy

### 2. Categorías y Productos (CU07)
- Se cargan desde el frontend (admin panel)
- O ejecutar `seed_products.py` si existe

### 3. Inventario por Sucursal
- Se configura desde admin
- Or seeding en `seed_inventory.py`

---

## 🔄 Workflow de Updates Sin Pérdida de BD

### Escenario: Cambios en el código (NO en BD)

```bash
# 1. En tu PC: hacer cambios en Python/Angular/etc
# 2. Push a GitHub
git push origin main

# 3. Render redeploy automático:
# - Ejecuta Build Command (pip install + preload_models)
# - Ejecuta Start Command (uvicorn + create_all)
# - BD PERMANECE INTACTA ✅
# - Datos históricos están disponibles ✅
```

### Escenario: Cambios en esquema BD (nuevas columnas)

```python
# En backend/app/main.py, al final de create_all():

_COLUMN_UPGRADES = [
    # Formato: (table_name, column_name, column_def)
    ("products", "new_column_name", "VARCHAR(255) DEFAULT NULL"),
]

async def run_migrations():
    for table, col, col_def in _COLUMN_UPGRADES:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}")
            await db.commit()
            logger.info(f"✅ Migración: {table}.{col} creada")
        except Exception as e:
            logger.warning(f"⚠️ {table}.{col} ya existe o error: {e}")
```

**Resultado:** 
- Agrega columnas SIN borrar datos
- Idempotente (seguro re-ejecutar)
- Backward compatible

---

## ⚠️ Lo Que NUNCA Hacer en Producción

❌ `Base.metadata.drop_all(bind=engine)` - BORRA TODO
❌ `DELETE FROM users` - BORRA datos
❌ `DROP TABLE orders` - BORRA historial
❌ Cambiar connection string sin backup - PIERDE acceso a BD

---

## 🔐 Seguridad - Credenciales en Render

**Variables de entorno en Render (NUNCA en .env committeado):**

1. `.env` está en `.gitignore` ✅
2. Credenciales sensibles van en Render Settings:
   - `DATABASE_URL`
   - `PAYPAL_CLIENT_ID`
   - `PAYPAL_CLIENT_SECRET`
   - `SMTP_PASSWORD`
   - `SECRET_KEY`

3. Render encripta variables en tránsito y reposo ✅

---

## 📋 Checklist Antes de Deploy en Render

- [ ] PostgreSQL database creada en Render
- [ ] `DATABASE_URL` copiada correctamente
- [ ] Variables de entorno agregadas en Render Settings
- [ ] Build Command configurado: `cd backend && pip install -r requirements.txt && python preload_models.py`
- [ ] Start Command configurado: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] `.env` NO committeado (verificar .gitignore)
- [ ] `requirements.txt` actualizado con todas las dependencias
- [ ] Probado localmente con `DATABASE_URL` de Render (opcional pero recomendado)

---

## 🚨 En Caso de Emergencia (Restore BD)

Si accidentalmente se borra data:

### Opción 1: Restore de Backup Render
```
Render Dashboard → PostgreSQL → Backups → Restore
```

### Opción 2: Dump/Restore Manual
```bash
# Dump BD local
pg_dump fashionstore > backup.sql

# Restore a Render
psql -h render-host -U user fashionstore < backup.sql
```

---

## 📞 Contacts / Support

- **Render Docs:** https://render.com/docs/databases
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/

---

## 🎯 Resumen Final

| Aspecto | Desarrollo | Producción (Render) |
|--------|-----------|-------------------|
| BD | SQLite/PostgreSQL local | PostgreSQL Render |
| Create Tables | Automático en `main.py` | Automático en `main.py` |
| Datos | Persisten entre restarts | Persisten entre deployments ✅ |
| Credenciales | `.env` (local) | Render Settings (seguro) |
| Backups | Manual | Automático en Render |
| URL | `http://localhost:8000` | `https://fashionstore.onrender.com` |

**IMPORTANTE:** La BD en producción es independiente del código. Cambios de código NO afectan datos existentes.
