# Carga de Datos Iniciales - Setup Producción

**Objetivo:** Asegurar que la BD de producción tenga datos listos sin perder información en updates

---

## 📦 Datos Que Necesita Producción

### 1. **Roles del Sistema** (CRÍTICO)
```
- SUPERADMIN (acceso total)
- ENCARGADO (gerente de sucursal)
- CAJERO (operador POS)
- CLIENTE (comprador)
- REPARTIDOR (delivery)
```

### 2. **Usuario Admin Default**
```
Email: admin@fashionstore.local
Contraseña: (cambiar después del primer login)
Rol: SUPERADMIN
```

### 3. **Sucursales** (CU39)
```
- Sucursal Central (Casa Matriz)
- Sucursal (opcional: agregar más en admin)
```

### 4. **Categorías de Productos** (CU07)
```
- Blusas
- Camisas
- Camisetas
- Jeans
- Vestidos
- Etc.
```

### 5. **Productos de Catálogo** (CU11)
```
- Nombre, descripción, precio
- Imágenes por color
- Tallas disponibles
- Stock inicial por sucursal
```

---

## 🚀 Procedimiento: Cargar Datos en Producción

### Opción A: Automático (Recomendado)

#### 1. Crear Script `seed_production.py`

```python
# backend/seed_production.py
"""Script para cargar datos iniciales en producción (idempotente)."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.packages.paquete_seguridad_usuarios.models import User, Role
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import Category, Product
from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory
from app.config import settings
from app.packages.paquete_seguridad_usuarios.utils import hash_password

def seed_roles(db: Session):
    """Crea roles si no existen."""
    roles_data = [
        {"name": "SUPERADMIN", "description": "Acceso total al sistema"},
        {"name": "ENCARGADO", "description": "Gerente de sucursal"},
        {"name": "CAJERO", "description": "Operador de POS"},
        {"name": "CLIENTE", "description": "Cliente comprador"},
        {"name": "REPARTIDOR", "description": "Personal de delivery"},
    ]
    
    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            print(f"✅ Rol creado: {role_data['name']}")
        else:
            print(f"⏭️  Rol ya existe: {role_data['name']}")
    
    db.commit()

def seed_admin_user(db: Session):
    """Crea usuario admin si no existe."""
    admin_email = "admin@fashionstore.local"
    existing = db.query(User).filter(User.email == admin_email).first()
    
    if not existing:
        superadmin_role = db.query(Role).filter(Role.name == "SUPERADMIN").first()
        admin = User(
            email=admin_email,
            hashed_password=hash_password("admin123"),
            first_name="Admin",
            last_name="FashionStore",
            phone="0-0000000",
            is_active=True,
        )
        admin.roles.append(superadmin_role)
        db.add(admin)
        db.commit()
        print(f"✅ Usuario admin creado: {admin_email}")
    else:
        print(f"⏭️  Admin ya existe: {admin_email}")

def seed_branches(db: Session):
    """Crea sucursales si no existen."""
    branches_data = [
        {
            "name": "Casa Matriz",
            "address": "Av. Principal, La Paz",
            "phone": "2-2000000",
            "email": "central@fashionstore.local",
            "is_central": True,
        },
    ]
    
    for branch_data in branches_data:
        existing = db.query(Branch).filter(Branch.name == branch_data["name"]).first()
        if not existing:
            branch = Branch(**branch_data)
            db.add(branch)
            db.commit()
            print(f"✅ Sucursal creada: {branch_data['name']}")
        else:
            print(f"⏭️  Sucursal ya existe: {branch_data['name']}")

def seed_categories(db: Session):
    """Crea categorías de productos si no existen."""
    categories = [
        "Blusas", "Camisas", "Camisetas", "Chaquetas",
        "Jeans", "Pantalones", "Vestidos", "Faldas",
        "Accesorios", "Zapatos"
    ]
    
    for cat_name in categories:
        existing = db.query(Category).filter(Category.name == cat_name).first()
        if not existing:
            category = Category(name=cat_name)
            db.add(category)
            db.commit()
            print(f"✅ Categoría creada: {cat_name}")
        else:
            print(f"⏭️  Categoría ya existe: {cat_name}")

def main():
    """Ejecuta todos los seeds."""
    print("\n" + "="*80)
    print("🌱 CARGANDO DATOS INICIALES EN PRODUCCIÓN")
    print("="*80 + "\n")
    
    db = SessionLocal()
    try:
        seed_roles(db)
        print()
        seed_admin_user(db)
        print()
        seed_branches(db)
        print()
        seed_categories(db)
        
        print("\n" + "="*80)
        print("✅ DATOS INICIALES CARGADOS CORRECTAMENTE")
        print("="*80)
        print("\n⚠️  IMPORTANTE:")
        print("   1. Cambiar contraseña del admin (admin123) después del login")
        print("   2. Agregar productos desde el panel de admin")
        print("   3. Configurar inventario inicial por sucursal\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

#### 2. Ejecutar Script Después del Primer Deploy

En Render, via SSH Console:

```bash
cd /opt/render/project/backend
python seed_production.py
```

O agregar a **Build Command** en Render:

```bash
cd backend && pip install -r requirements.txt && python seed_production.py && python preload_models.py
```

---

### Opción B: Manual (Via Admin Panel)

Si prefieres cargar datos manualmente:

1. **Accede al panel de admin:** `https://tu-frontend.onrender.com/admin`
2. **Login:** admin@fashionstore.local / admin123
3. **Agrega:**
   - Sucursales (si necesitas más)
   - Categorías
   - Productos
   - Inventario

---

## 🔄 Idempotencia - Datos Seguros

Los scripts de seed verifican antes de crear:

```python
existing = db.query(User).filter(User.email == admin_email).first()
if not existing:
    # Crear solo si NO existe
    db.add(new_user)
```

**Resultado:** 
- ✅ Puedes ejecutar múltiples veces sin duplicar
- ✅ Seguro re-ejecutar en cada deploy
- ✅ Datos nuevos no se pierden

---

## 📊 Schema BD - Tablas Principales

```sql
-- Usuarios y Seguridad
users (id, email, hashed_password, first_name, last_name, phone, is_active, created_at)
roles (id, name, description)
user_roles (user_id, role_id)

-- Catálogo
categories (id, name, description)
products (id, name, description, base_price, category_id, is_active, created_at)
product_images (id, product_id, image_url, color)
product_reviews (id, product_id, user_id, rating, comment, created_at)

-- Sucursales
branches (id, name, address, phone, email, is_central)
inventory (id, branch_id, variant_id, stock_actual, avg_cost)

-- Ventas
orders (id, user_id, branch_id, channel, status, total_amount, created_at)
order_items (id, order_id, variant_id, quantity, unit_price)
payments (id, order_id, payment_type, amount, status, paid_at)
invoices (id, order_id, doc_type, subtotal, tax_amount, total, issued_at)
```

---

## 🎯 Checklist: Antes de Deploy Producción

```
☑️ Crear script seed_production.py
☑️ Probar seed localmente
☑️ PostgreSQL BD creada en Render
☑️ DATABASE_URL configurada en Render Settings
☑️ Build Command incluye seeds
☑️ Roles creados
☑️ Admin user creado
☑️ Sucursales creadas
☑️ Categorías creadas
☑️ Productos agregados (admin panel o seed adicional)
☑️ Inventario configurado
☑️ Backup de datos antes del deploy
```

---

## 🚨 Recuperar Datos si Algo Falla

### 1. Si se ejecutó `DROP_ALL` accidentalmente

```bash
# Render Dashboard → PostgreSQL → Backups → Restore
# Selecciona snapshot anterior al error
```

### 2. Desde pgAdmin

```bash
# Conexión local a BD Render
psql -h your-render-host -U postgres fashionstore

# Restaurar desde backup .sql
\i backup.sql
```

---

## 📝 Ejemplo: Agregar Productos Iniciales

```python
def seed_products(db: Session):
    """Agrega productos iniciales."""
    category = db.query(Category).filter(Category.name == "Camisetas").first()
    
    if category:
        product = Product(
            name="Camiseta Básica Azul",
            description="Camiseta 100% algodón",
            base_price=150.0,
            category_id=category.id,
            is_active=True,
        )
        db.add(product)
        db.commit()
        print(f"✅ Producto creado: {product.name}")
```

---

## 🎬 Flujo Completo de Deploy

```
1. Push código a GitHub
   ↓
2. Render Redeploy automático
   ↓
3. Build: pip install + seed_production.py + preload_models.py
   ↓
4. Start: uvicorn (crea_all + migraciones ligeras)
   ↓
5. Base de datos lista con datos iniciales ✅
   ↓
6. Usuarios pueden hacer checkout, admin puede actualizar catálogo
```

---

**Próximo paso:** Ver [DEPLOYMENT_DATABASE_GUIDE.md](DEPLOYMENT_DATABASE_GUIDE.md) para configuración completa de Render.
