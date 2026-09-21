# Diseño Físico y Conceptual de Base de Datos (PostgreSQL)

**Plataforma de Comercio Electrónico para Tienda de Ropa (FashionStore)**  
**Universidad Autónoma Gabriel René Moreno · Sistemas de Información II (Semestre 2-2026)**  
**Grupo #29** | Condori Diaz Marilyn Esther & Larrazabal Rojas Julio Cesar  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  

---

## 1. Validación de Normas Normales (Normalización 3NF)

El esquema relacional de la plataforma **FashionStore** consta de **50 tablas** estructuradas rigurosamente bajo la **Tercera Forma Normal (3NF)**:

* **Primera Forma Normal (1NF)**: Todos los atributos contienen valores atómicos y no existen grupos repetitivos. Las tallas (`sizes`), colores (`colors`), fotos (`product_images`) y roles (`roles`) se modelan como entidades independientes en relaciones normalizadas 1:N o N:N.
* **Segunda Forma Normal (2NF)**: Está en 1NF y todos los atributos no clave dependen en su totalidad de la clave primaria. El inventario real no reside en la entidad producto ni variante, sino en la tabla de cruce `inventory(branch_id, variant_id)` vinculada a una sucursal y variante física.
* **Tercera Forma Normal (3NF)**: Está en 2NF y se eliminan dependencias transitivas. Los datos de empleados de sucursal se desacoplan en `branch_employees`, y los cálculos agregados (calificación promedio de reseñas en CU14, totales derivados en pedidos) se calculan bajo demanda o se sincronizan mediante transacciones atómicas.

---

## 2. Diagramas Disponibles en Draw.io y Guía de Visualización

Para resolver la sobrecarga visual y evitar el cruce de líneas, el sistema provee diagramas organizados modularmente:

1. **`diagrama_bd_fashionstore_ciclos.drawio` (Archivo Maestro Multi-Página con 12 Pestañas):**
   - **Pestaña 1:** *Arquitectura Global (8 Paquetes)*: Vista de alto nivel con las dependencias conceptuales entre subsistemas.
   - **Pestañas 2 a 9:** *Vistas Específicas por Paquete (8 Diagramas Limpios)*: Cada paquete muestra sus tablas con el **100% de atributos completos**, referencias externas en los bordes y **CERO cruces de líneas**.
   - **Pestaña 10:** *Ciclo 1 - Núcleo Base (22 Tablas)* en contenedores visuales de paquete.
   - **Pestaña 11:** *Ciclo 2 - Comercio y POS (39 Tablas)*.
   - **Pestaña 12:** *Ciclo 3 - Consolidado Total (50 Tablas)*.

2. **`diagrama_conceptual_por_paquetes.drawio`**: Archivo enfocado exclusivamente en las 8 pestañas modulares de paquetes para revisión pedagógica directa.
3. **`diagrama_bd_ciclo1.drawio`, `diagrama_bd_ciclo2.drawio`, `diagrama_bd_ciclo3.drawio`**: Archivos individuales para cada entrega curricular.

---

## 3. Esquema Físico y Conceptual Completo de las 50 Tablas (Por Paquetes)

### Paquete 1: Seguridad y Usuarios
> **Descripción:** Autenticación JWT, RBAC multi-rol, sesiones concurrentes y bitácora inmutable de auditoría (CU01-CU05, CU36)
> **Total de Tablas:** 5 tablas físicas en PostgreSQL.

#### Tabla: `roles` (Clase ORM: `Role`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(50)` | UQ, NOT NULL |
| `description` | `VARCHAR(255)` | NULL |

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);
```

#### Tabla: `users` (Clase ORM: `User`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `email` | `VARCHAR(150)` | UQ, NOT NULL |
| `password_hash` | `VARCHAR(255)` | NOT NULL |
| `first_name` | `VARCHAR(100)` | NOT NULL |
| `last_name` | `VARCHAR(100)` | NOT NULL |
| `phone` | `VARCHAR(20)` | NULL |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE;
```

#### Tabla: `user_roles` (Clase ORM: `user_roles (Table N:N)`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `user_id` | `INTEGER` | PK, FK -> users.id |
| `role_id` | `INTEGER` | PK, FK -> roles.id |

```sql
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);
```

#### Tabla: `session_tokens` (Clase ORM: `SessionToken`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id |
| `token` | `VARCHAR(500)` | UQ, NOT NULL |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL |
| `is_revoked` | `BOOLEAN` | DEFAULT FALSE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE session_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `audit_logs` (Clase ORM: `AuditLog`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `BIGSERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id (NULLABLE) |
| `action` | `VARCHAR(50)` | NOT NULL |
| `table_name` | `VARCHAR(100)` | NOT NULL |
| `row_id` | `INTEGER` | NOT NULL |
| `old_values` | `JSONB` | NULL |
| `new_values` | `JSONB` | NULL |
| `ip_address` | `VARCHAR(45)` | NULL |
| `timestamp` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    row_id INTEGER NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
```

---

### Paquete 2: Catálogo y Tiendas
> **Descripción:** Sucursales, categorización, colecciones, matriz de variantes (color/talla), fotos, reseñas, cupones, promociones y wishlists (CU06, CU07, CU09, CU11-CU14)
> **Total de Tablas:** 16 tablas físicas en PostgreSQL.

#### Tabla: `branches` (Clase ORM: `Branch`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(100)` | UQ, NOT NULL |
| `address` | `VARCHAR(255)` | NOT NULL |
| `phone` | `VARCHAR(20)` | NULL |
| `latitude` | `DECIMAL(10,8)` | NULL |
| `longitude` | `DECIMAL(11,8)` | NULL |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |

```sql
CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);
```

#### Tabla: `branch_employees` (Clase ORM: `BranchEmployee`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `branch_id` | `INTEGER` | PK, FK -> branches.id |
| `user_id` | `INTEGER` | PK, FK -> users.id |

```sql
CREATE TABLE branch_employees (
    branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (branch_id, user_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `categories` (Clase ORM: `Category`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(100)` | UQ, NOT NULL |
| `description` | `VARCHAR(255)` | NULL |
| `image_url` | `VARCHAR(500)` | NULL |

```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    image_url VARCHAR(500)
);
```

#### Tabla: `seasons` (Clase ORM: `Season`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(50)` | UQ, NOT NULL |
| `start_date` | `DATE` | NOT NULL |
| `end_date` | `DATE` | NOT NULL |

```sql
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);
```

#### Tabla: `collections` (Clase ORM: `Collection`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(100)` | UQ, NOT NULL |
| `description` | `VARCHAR(255)` | NULL |
| `season_id` | `INTEGER` | FK -> seasons.id |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `banner_url` | `VARCHAR(500)` | NULL |

```sql
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    season_id INTEGER REFERENCES seasons(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    banner_url VARCHAR(500)
);
```

#### Tabla: `colors` (Clase ORM: `Color`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(50)` | UQ, NOT NULL |
| `hex_code` | `VARCHAR(7)` | UQ, NOT NULL |

```sql
CREATE TABLE colors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    hex_code VARCHAR(7) UNIQUE NOT NULL
);
```

#### Tabla: `sizes` (Clase ORM: `Size`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(10)` | UQ, NOT NULL |

```sql
CREATE TABLE sizes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) UNIQUE NOT NULL
);
```

#### Tabla: `products` (Clase ORM: `Product`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(150)` | NOT NULL |
| `description` | `TEXT` | NULL |
| `base_price` | `DECIMAL(10,2)` | NOT NULL |
| `compare_at_price` | `DECIMAL(10,2)` | NULL |
| `category_id` | `INTEGER` | FK -> categories.id |
| `season_id` | `INTEGER` | FK -> seasons.id |
| `collection_id` | `INTEGER` | FK -> collections.id |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2) NOT NULL,
    compare_at_price DECIMAL(10, 2),
    category_id INTEGER NOT NULL,
    season_id INTEGER,
    collection_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE SET NULL,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE SET NULL
);
```

#### Tabla: `product_variants` (Clase ORM: `ProductVariant`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `product_id` | `INTEGER` | FK -> products.id |
| `color_id` | `INTEGER` | FK -> colors.id |
| `size_id` | `INTEGER` | FK -> sizes.id |
| `sku` | `VARCHAR(50)` | UQ, NOT NULL |
| `price_override` | `DECIMAL(10,2)` | NULL |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |

```sql
CREATE TABLE product_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    color_id INTEGER NOT NULL,
    size_id INTEGER NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    price_override DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE RESTRICT,
    FOREIGN KEY (size_id) REFERENCES sizes(id) ON DELETE RESTRICT,
    CONSTRAINT unique_product_color_size UNIQUE (product_id, color_id, size_id)
);
CREATE INDEX idx_variants_search ON product_variants(product_id, color_id, size_id);
```

#### Tabla: `product_images` (Clase ORM: `ProductImage`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `product_id` | `INTEGER` | FK -> products.id |
| `color_id` | `INTEGER` | FK -> colors.id (NULL) |
| `image_url` | `VARCHAR(500)` | NOT NULL |
| `is_primary` | `BOOLEAN` | DEFAULT FALSE |

```sql
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    color_id INTEGER,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET NULL
);
CREATE INDEX idx_product_images_product ON product_images(product_id);
```

#### Tabla: `product_reviews` (Clase ORM: `ProductReview`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `product_id` | `INTEGER` | FK -> products.id |
| `user_id` | `INTEGER` | FK -> users.id |
| `rating` | `SMALLINT` | 1-5, NOT NULL |
| `comment` | `TEXT` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE product_reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating SMALLINT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_review_product_user UNIQUE (product_id, user_id),
    CONSTRAINT ck_review_rating_range CHECK (rating >= 1 AND rating <= 5)
);
CREATE INDEX idx_reviews_product ON product_reviews(product_id);
```

#### Tabla: `wishlist_items` (Clase ORM: `WishlistItem`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `user_id` | `INTEGER` | PK, FK -> users.id |
| `product_id` | `INTEGER` | PK, FK -> products.id |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE wishlist_items (
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX idx_wishlist_user ON wishlist_items(user_id);
```

#### Tabla: `coupons` (Clase ORM: `Coupon`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `code` | `VARCHAR(30)` | UQ, NOT NULL |
| `discount_type` | `VARCHAR(15)` | PORCENTAJE/MONTO_FIJO |
| `discount_value` | `DECIMAL(10,2)` | NOT NULL |
| `min_purchase_amount` | `DECIMAL(10,2)` | DEFAULT 0 |
| `valid_from` | `TIMESTAMPTZ` | NOT NULL |
| `valid_until` | `TIMESTAMPTZ` | NOT NULL |
| `max_uses` | `INTEGER` | DEFAULT 100 |
| `used_count` | `INTEGER` | DEFAULT 0 |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    discount_type VARCHAR(15) NOT NULL,
    discount_value NUMERIC(10, 2) NOT NULL,
    min_purchase_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    max_uses INTEGER NOT NULL,
    used_count INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
```

#### Tabla: `seasonal_promotions` (Clase ORM: `SeasonalPromotion`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(100)` | NOT NULL |
| `description` | `TEXT` | NULL |
| `discount_percent` | `INTEGER` | NOT NULL |
| `category_id` | `INTEGER` | FK -> categories.id (NULL) |
| `start_date` | `DATE` | NOT NULL |
| `end_date` | `DATE` | NOT NULL |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE seasonal_promotions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_percent INTEGER NOT NULL,
    category_id INTEGER,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);
```

#### Tabla: `wishlists` (Clase ORM: `Wishlist`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id |
| `name` | `VARCHAR(100)` | NOT NULL |
| `is_public` | `BOOLEAN` | DEFAULT FALSE |
| `share_token` | `VARCHAR(64)` | UQ, NOT NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE wishlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `wishlist_group_items` (Clase ORM: `WishlistGroupItem`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `wishlist_id` | `INTEGER` | FK -> wishlists.id |
| `product_id` | `INTEGER` | FK -> products.id |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE wishlist_group_items (
    id SERIAL PRIMARY KEY,
    wishlist_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT uq_wishlist_group_product UNIQUE (wishlist_id, product_id),
    FOREIGN KEY (wishlist_id) REFERENCES wishlists(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

---

### Paquete 3: Inventario y Proveedores
> **Descripción:** Proveedores, órdenes de compra por sucursal, kardex valorado (CPP), stock multi-sucursal y transferencias entre tiendas (CU08, CU10, CU15, CU16, CU37, CU38)
> **Total de Tablas:** 7 tablas físicas en PostgreSQL.

#### Tabla: `suppliers` (Clase ORM: `Supplier`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `nit` | `VARCHAR(20)` | UQ, NOT NULL |
| `name` | `VARCHAR(150)` | NOT NULL |
| `email` | `VARCHAR(150)` | NULL |
| `phone` | `VARCHAR(20)` | NULL |
| `address` | `VARCHAR(255)` | NULL |

```sql
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    nit VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    address VARCHAR(255)
);
```

#### Tabla: `inventory` (Clase ORM: `Inventory`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `branch_id` | `INTEGER` | PK, FK -> branches.id |
| `variant_id` | `INTEGER` | PK, FK -> product_variants.id |
| `stock_actual` | `INTEGER` | DEFAULT 0 |
| `avg_cost` | `DECIMAL(10,2)` | CPP DEFAULT 0 |
| `stock_minimo` | `INTEGER` | DEFAULT 5 |
| `stock_maximo` | `INTEGER` | DEFAULT 100 |
| `stock_reservado` | `INTEGER` | DEFAULT 0 |
| `stock_en_transito` | `INTEGER` | DEFAULT 0 |

```sql
CREATE TABLE inventory (
    branch_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    stock_actual INTEGER DEFAULT 0 NOT NULL,
    avg_cost DECIMAL(10, 2) DEFAULT 0 NOT NULL,
    stock_minimo INTEGER DEFAULT 5 NOT NULL,
    stock_maximo INTEGER DEFAULT 100 NOT NULL,
    stock_reservado INTEGER DEFAULT 0 NOT NULL,
    stock_en_transito INTEGER DEFAULT 0 NOT NULL,
    PRIMARY KEY (branch_id, variant_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);
CREATE INDEX idx_inventory_stock ON inventory(branch_id, variant_id) INCLUDE (stock_actual);
```

#### Tabla: `inventory_ledger` (Clase ORM: `InventoryLedger`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `BIGSERIAL` | PK |
| `branch_id` | `INTEGER` | FK -> branches.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL (+/-) |
| `movement_type` | `VARCHAR(20)` | NOT NULL |
| `unit_cost` | `DECIMAL(10,2)` | NOT NULL |
| `reference_id` | `VARCHAR(50)` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE inventory_ledger (
    id BIGSERIAL PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    reference_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);
```

#### Tabla: `purchase_orders` (Clase ORM: `PurchaseOrder`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `supplier_id` | `INTEGER` | FK -> suppliers.id |
| `branch_id` | `INTEGER` | FK -> branches.id |
| `status` | `VARCHAR(20)` | DEFAULT 'COMPLETADO' |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'COMPLETADO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);
```

#### Tabla: `purchase_details` (Clase ORM: `PurchaseDetail`) — *Ciclo 1*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `purchase_order_id` | `INTEGER` | FK -> purchase_orders.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL |
| `unit_cost` | `DECIMAL(10,2)` | NOT NULL |

```sql
CREATE TABLE purchase_details (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

#### Tabla: `stock_transfers` (Clase ORM: `StockTransfer`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `transfer_number` | `VARCHAR(30)` | UQ, NOT NULL |
| `origin_branch_id` | `INTEGER` | FK -> branches.id |
| `destination_branch_id` | `INTEGER` | FK -> branches.id |
| `requested_by_id` | `INTEGER` | FK -> users.id |
| `received_by_id` | `INTEGER` | FK -> users.id (NULL) |
| `status` | `VARCHAR(20)` | SOLICITADA/EN_TRANSITO... |
| `notes` | `VARCHAR(255)` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `completed_at` | `TIMESTAMPTZ` | NULL |

```sql
CREATE TABLE stock_transfers (
    id SERIAL PRIMARY KEY,
    transfer_number VARCHAR(30) UNIQUE NOT NULL,
    origin_branch_id INTEGER NOT NULL,
    destination_branch_id INTEGER NOT NULL,
    requested_by_id INTEGER NOT NULL,
    received_by_id INTEGER,
    status VARCHAR(20) NOT NULL,
    notes VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (origin_branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (destination_branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (requested_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (received_by_id) REFERENCES users(id) ON DELETE SET NULL
);
```

#### Tabla: `stock_transfer_details` (Clase ORM: `StockTransferDetail`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `transfer_id` | `INTEGER` | FK -> stock_transfers.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL |

```sql
CREATE TABLE stock_transfer_details (
    id SERIAL PRIMARY KEY,
    transfer_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (transfer_id) REFERENCES stock_transfers(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

---

### Paquete 4: Ventas y Pagos
> **Descripción:** Carrito, arqueo POS, pedidos omnicanal, pagos polimórficos STI (Efectivo/Tarjeta/QR/PayPal/Crédito), facturación IVA 13%, cotizaciones y devoluciones (CU17-CU25)
> **Total de Tablas:** 11 tablas físicas en PostgreSQL.

#### Tabla: `carts` (Clase ORM: `Cart`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id (NULLABLE) |
| `session_id` | `VARCHAR(80)` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(80),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `cart_items` (Clase ORM: `CartItem`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `cart_id` | `INTEGER` | FK -> carts.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

#### Tabla: `cash_shifts` (Clase ORM: `CashShift`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `cashier_id` | `INTEGER` | FK -> users.id |
| `branch_id` | `INTEGER` | FK -> branches.id |
| `opening_amount` | `DECIMAL(10,2)` | NOT NULL |
| `closing_amount_declared` | `DECIMAL(10,2)` | NULL |
| `closing_amount_system` | `DECIMAL(10,2)` | NULL |
| `difference` | `DECIMAL(10,2)` | NULL |
| `status` | `VARCHAR(20)` | ABIERTO/CERRADO |
| `opened_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `closed_at` | `TIMESTAMPTZ` | NULL |
| `notes` | `VARCHAR(255)` | NULL |

```sql
CREATE TABLE cash_shifts (
    id SERIAL PRIMARY KEY,
    cashier_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    opening_amount NUMERIC(10, 2) NOT NULL,
    closing_amount_declared NUMERIC(10, 2),
    closing_amount_system NUMERIC(10, 2),
    difference NUMERIC(10, 2),
    status VARCHAR(20) NOT NULL,
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    notes VARCHAR(255),
    FOREIGN KEY (cashier_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);
```

#### Tabla: `orders` (Clase ORM: `Order`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id |
| `branch_id` | `INTEGER` | FK -> branches.id |
| `channel` | `VARCHAR(10)` | ONLINE/POS |
| `status` | `VARCHAR(20)` | PAGADA/PREPARANDO... |
| `subtotal` | `DECIMAL(10,2)` | NOT NULL |
| `discount_amount` | `DECIMAL(10,2)` | DEFAULT 0 |
| `coupon_code` | `VARCHAR(30)` | NULL |
| `total_amount` | `DECIMAL(10,2)` | NOT NULL |
| `cash_shift_id` | `INTEGER` | FK -> cash_shifts.id |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    channel VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    discount_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    coupon_code VARCHAR(30),
    total_amount NUMERIC(10, 2) NOT NULL,
    cash_shift_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (cash_shift_id) REFERENCES cash_shifts(id) ON DELETE SET NULL
);
```

#### Tabla: `order_items` (Clase ORM: `OrderItem`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `order_id` | `INTEGER` | FK -> orders.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL |
| `unit_price` | `DECIMAL(10,2)` | NOT NULL |

```sql
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

#### Tabla: `payments` (Clase ORM: `Payment (STI)`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `order_id` | `INTEGER` | FK -> orders.id |
| `payment_type` | `VARCHAR(20)` | EFECTIVO/TARJETA/QR/PAYPAL |
| `amount` | `DECIMAL(10,2)` | NOT NULL |
| `status` | `VARCHAR(20)` | NOT NULL |
| `paid_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `cash_received` | `DECIMAL(10,2)` | NULL |
| `cash_change` | `DECIMAL(10,2)` | NULL |
| `card_brand` | `VARCHAR(20)` | NULL |
| `card_last4` | `VARCHAR(4)` | NULL |
| `gateway_reference` | `VARCHAR(80)` | NULL |
| `qr_reference` | `VARCHAR(80)` | NULL |
| `paypal_payer_id` | `VARCHAR(50)` | NULL |
| `paypal_payer_email` | `VARCHAR(100)` | NULL |
| `credit_due_date` | `DATE` | NULL |

```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    paid_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    cash_received NUMERIC(10, 2),
    cash_change NUMERIC(10, 2),
    card_brand VARCHAR(20),
    card_last4 VARCHAR(4),
    gateway_reference VARCHAR(80),
    qr_reference VARCHAR(80),
    paypal_payer_id VARCHAR(50),
    paypal_payer_email VARCHAR(100),
    credit_due_date DATE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
```

#### Tabla: `invoices` (Clase ORM: `Invoice`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `order_id` | `INTEGER` | UQ, FK -> orders.id |
| `doc_type` | `VARCHAR(15)` | FACTURA/NOTA_ENTREGA |
| `tax_rate` | `DECIMAL(4,3)` | 0.130 (IVA 13%) |
| `subtotal` | `DECIMAL(10,2)` | NOT NULL |
| `tax_amount` | `DECIMAL(10,2)` | NOT NULL |
| `total` | `DECIMAL(10,2)` | NOT NULL |
| `control_code` | `VARCHAR(40)` | NULL |
| `customer_nit` | `VARCHAR(20)` | NULL |
| `customer_name` | `VARCHAR(150)` | NULL |
| `issued_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL UNIQUE,
    doc_type VARCHAR(15) NOT NULL,
    tax_rate NUMERIC(4, 3) DEFAULT 0.130 NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    tax_amount NUMERIC(10, 2) NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    control_code VARCHAR(40),
    customer_nit VARCHAR(20),
    customer_name VARCHAR(150),
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT
);
```

#### Tabla: `quotations` (Clase ORM: `Quotation`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `quotation_number` | `VARCHAR(30)` | UQ, NOT NULL |
| `customer_name` | `VARCHAR(150)` | NOT NULL |
| `customer_email` | `VARCHAR(100)` | NULL |
| `customer_phone` | `VARCHAR(30)` | NULL |
| `created_by_id` | `INTEGER` | FK -> users.id |
| `branch_id` | `INTEGER` | FK -> branches.id |
| `total_amount` | `DECIMAL(10,2)` | NOT NULL |
| `valid_until` | `TIMESTAMPTZ` | NOT NULL |
| `status` | `VARCHAR(20)` | VIGENTE/CONVERTIDA |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE quotations (
    id SERIAL PRIMARY KEY,
    quotation_number VARCHAR(30) UNIQUE NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(100),
    customer_phone VARCHAR(30),
    created_by_id INTEGER NOT NULL,
    branch_id INTEGER,
    total_amount NUMERIC(10, 2) NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
);
```

#### Tabla: `quotation_items` (Clase ORM: `QuotationItem`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `quotation_id` | `INTEGER` | FK -> quotations.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL |
| `unit_price` | `DECIMAL(10,2)` | NOT NULL |

```sql
CREATE TABLE quotation_items (
    id SERIAL PRIMARY KEY,
    quotation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

#### Tabla: `order_returns` (Clase ORM: `OrderReturn`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `return_number` | `VARCHAR(30)` | UQ, NOT NULL |
| `order_id` | `INTEGER` | FK -> orders.id |
| `processed_by_id` | `INTEGER` | FK -> users.id |
| `return_type` | `VARCHAR(25)` | DEVOLUCION/CAMBIO |
| `reason` | `VARCHAR(255)` | NOT NULL |
| `refund_amount` | `DECIMAL(10,2)` | NOT NULL |
| `status` | `VARCHAR(20)` | APROBADA... |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE order_returns (
    id SERIAL PRIMARY KEY,
    return_number VARCHAR(30) UNIQUE NOT NULL,
    order_id INTEGER NOT NULL,
    processed_by_id INTEGER NOT NULL,
    return_type VARCHAR(25) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    refund_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
    FOREIGN KEY (processed_by_id) REFERENCES users(id) ON DELETE RESTRICT
);
```

#### Tabla: `order_return_items` (Clase ORM: `OrderReturnItem`) — *Ciclo 2*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `return_id` | `INTEGER` | FK -> order_returns.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | NOT NULL |
| `replacement_variant_id` | `INTEGER` | FK -> product_variants.id (NULL) |

```sql
CREATE TABLE order_return_items (
    id SERIAL PRIMARY KEY,
    return_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    replacement_variant_id INTEGER,
    FOREIGN KEY (return_id) REFERENCES order_returns(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT,
    FOREIGN KEY (replacement_variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

---

### Paquete 5: Reservas y Citas
> **Descripción:** Citas en probadores de sucursal con seña obligatoria (50%), bloqueo de stock, tolerancia 15/30 min y conversión directa a venta (CU26-CU28, CU25)
> **Total de Tablas:** 2 tablas físicas en PostgreSQL.

#### Tabla: `reservations` (Clase ORM: `Reservation`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `reservation_code` | `VARCHAR(30)` | UQ, NOT NULL |
| `customer_id` | `INTEGER` | FK -> users.id |
| `branch_id` | `INTEGER` | FK -> branches.id |
| `status` | `VARCHAR(20)` | PENDING/READY/LATE... |
| `appointment_date` | `DATE` | NOT NULL |
| `appointment_time` | `VARCHAR(10)` | NOT NULL |
| `reschedule_count` | `INTEGER` | DEFAULT 0 |
| `grace_period_notified` | `BOOLEAN` | DEFAULT FALSE |
| `reserved_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL |
| `notes` | `VARCHAR(255)` | NULL |
| `total_amount` | `DECIMAL(10,2)` | NOT NULL |
| `deposit_amount` | `DECIMAL(10,2)` | 50% DEPOSITO |
| `payment_method` | `VARCHAR(20)` | PAYPAL/QR/TARJETA |
| `payment_reference` | `VARCHAR(100)` | NULL |
| `deposit_paid` | `BOOLEAN` | DEFAULT TRUE |
| `completed_sale_id` | `INTEGER` | FK -> orders.id (NULL) |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    reservation_code VARCHAR(30) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(10) NOT NULL,
    reschedule_count INTEGER DEFAULT 0 NOT NULL,
    grace_period_notified BOOLEAN DEFAULT FALSE NOT NULL,
    reserved_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    notes VARCHAR(255),
    total_amount NUMERIC(10, 2) NOT NULL,
    deposit_amount NUMERIC(10, 2) NOT NULL,
    payment_method VARCHAR(20),
    payment_reference VARCHAR(100),
    deposit_paid BOOLEAN DEFAULT TRUE NOT NULL,
    completed_sale_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (completed_sale_id) REFERENCES orders(id) ON DELETE SET NULL
);
CREATE INDEX ix_reservations_status ON reservations(status);
```

#### Tabla: `reservation_items` (Clase ORM: `ReservationItem`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `reservation_id` | `INTEGER` | FK -> reservations.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id |
| `quantity` | `INTEGER` | DEFAULT 1 |
| `unit_price` | `DECIMAL(10,2)` | NOT NULL |
| `notes` | `VARCHAR(100)` | NULL |

```sql
CREATE TABLE reservation_items (
    id SERIAL PRIMARY KEY,
    reservation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1 NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    notes VARCHAR(100),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

---

### Paquete 6: Envíos y Logística
> **Descripción:** Zonas y tarifas por distancia, repartidores (bolsa), tracking en tiempo real de ruta y entrega con foto obligatoria (CU29-CU31)
> **Total de Tablas:** 4 tablas físicas en PostgreSQL.

#### Tabla: `delivery_zones` (Clase ORM: `DeliveryZone`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `name` | `VARCHAR(100)` | NOT NULL |
| `city` | `VARCHAR(50)` | NOT NULL |
| `min_distance_km` | `DECIMAL(5,2)` | NOT NULL |
| `max_distance_km` | `DECIMAL(5,2)` | NOT NULL |
| `base_rate` | `DECIMAL(10,2)` | NOT NULL |
| `estimated_hours` | `INTEGER` | NOT NULL |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE delivery_zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    min_distance_km NUMERIC(5, 2) NOT NULL,
    max_distance_km NUMERIC(5, 2) NOT NULL,
    base_rate NUMERIC(10, 2) NOT NULL,
    estimated_hours INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
```

#### Tabla: `delivery_persons` (Clase ORM: `DeliveryPerson`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | UQ, FK -> users.id |
| `vehicle_type` | `VARCHAR(50)` | MOTO/AUTO/BICI |
| `vehicle_plate` | `VARCHAR(20)` | NULL |
| `license_number` | `VARCHAR(50)` | NULL |
| `coverage_zone` | `VARCHAR(100)` | NOT NULL |
| `phone` | `VARCHAR(20)` | NOT NULL |
| `is_available` | `BOOLEAN` | DEFAULT TRUE |
| `rating` | `DECIMAL(3,2)` | DEFAULT 5.0 |
| `total_deliveries` | `INTEGER` | DEFAULT 0 |
| `is_active` | `BOOLEAN` | DEFAULT TRUE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE delivery_persons (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    vehicle_plate VARCHAR(20),
    license_number VARCHAR(50),
    coverage_zone VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE NOT NULL,
    rating NUMERIC(3, 2) DEFAULT 5.0 NOT NULL,
    total_deliveries INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `shipments` (Clase ORM: `Shipment`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `tracking_number` | `VARCHAR(30)` | UQ, NOT NULL |
| `order_id` | `INTEGER` | FK -> orders.id |
| `zone_id` | `INTEGER` | FK -> delivery_zones.id (NULL) |
| `delivery_person_id` | `INTEGER` | FK -> delivery_persons.id (NULL) |
| `claimed_at` | `TIMESTAMPTZ` | NULL |
| `delivery_date` | `DATE` | NULL |
| `delivery_time` | `VARCHAR(20)` | NULL |
| `delivery_attempts` | `INTEGER` | DEFAULT 0 |
| `failed_reason` | `VARCHAR(255)` | NULL |
| `carrier_name` | `VARCHAR(100)` | NOT NULL |
| `carrier_phone` | `VARCHAR(20)` | NULL |
| `delivery_address` | `VARCHAR(255)` | NOT NULL |
| `recipient_name` | `VARCHAR(100)` | NOT NULL |
| `recipient_phone` | `VARCHAR(20)` | NOT NULL |
| `shipping_cost` | `DECIMAL(10,2)` | NOT NULL |
| `status` | `VARCHAR(30)` | ASSIGNED/IN_TRANSIT... |
| `dispatched_at` | `TIMESTAMPTZ` | NULL |
| `delivered_at` | `TIMESTAMPTZ` | NULL |
| `notes` | `VARCHAR(255)` | NULL |
| `delivery_photo_url` | `TEXT` | EVIDENCIA FOTO |
| `received_by_name` | `VARCHAR(100)` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE shipments (
    id SERIAL PRIMARY KEY,
    tracking_number VARCHAR(30) UNIQUE NOT NULL,
    order_id INTEGER NOT NULL,
    zone_id INTEGER,
    delivery_person_id INTEGER,
    claimed_at TIMESTAMP WITH TIME ZONE,
    delivery_date DATE,
    delivery_time VARCHAR(20),
    delivery_attempts INTEGER DEFAULT 0 NOT NULL,
    failed_reason VARCHAR(255),
    carrier_name VARCHAR(100) NOT NULL,
    carrier_phone VARCHAR(20),
    delivery_address VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(100) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    shipping_cost NUMERIC(10, 2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    dispatched_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    notes VARCHAR(255),
    delivery_photo_url TEXT,
    received_by_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
    FOREIGN KEY (zone_id) REFERENCES delivery_zones(id) ON DELETE SET NULL,
    FOREIGN KEY (delivery_person_id) REFERENCES delivery_persons(id) ON DELETE SET NULL
);
CREATE INDEX ix_shipments_status ON shipments(status);
```

#### Tabla: `shipment_tracking_events` (Clase ORM: `ShipmentTrackingEvent`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `shipment_id` | `INTEGER` | FK -> shipments.id |
| `status` | `VARCHAR(30)` | NOT NULL |
| `location` | `VARCHAR(100)` | NOT NULL |
| `description` | `VARCHAR(255)` | NOT NULL |
| `photo_url` | `TEXT` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE shipment_tracking_events (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    location VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL,
    photo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE
);
```

---

### Paquete 7: Inteligencia Artificial y Analítica
> **Descripción:** Probador virtual con simulación de ajuste (VTON/FASHN.ai), capturas fotorrealistas con recomendación de talla y chatbot con detección de intenciones (CU32-CU35, CU39)
> **Total de Tablas:** 4 tablas físicas en PostgreSQL.

#### Tabla: `virtual_tryon_sessions` (Clase ORM: `VirtualTryonSession`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id (NULLABLE) |
| `session_token` | `VARCHAR(100)` | UQ, NOT NULL |
| `channel` | `VARCHAR(20)` | WEB/MOBILE |
| `status` | `VARCHAR(20)` | NOT NULL |
| `started_at` | `TIMESTAMPTZ` | DEFAULT now() |
| `finished_at` | `TIMESTAMPTZ` | NULL |

```sql
CREATE TABLE virtual_tryon_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_token VARCHAR(100) UNIQUE NOT NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

#### Tabla: `virtual_tryon_items` (Clase ORM: `VirtualTryonItem`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `session_id` | `INTEGER` | FK -> virtual_tryon_sessions.id |
| `product_id` | `INTEGER` | FK -> products.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id (NULL) |
| `tested_size` | `VARCHAR(20)` | NULL |
| `fit_feedback` | `VARCHAR(100)` | NULL |
| `tested_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE virtual_tryon_items (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    tested_size VARCHAR(20),
    fit_feedback VARCHAR(100),
    tested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (session_id) REFERENCES virtual_tryon_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE SET NULL
);
```

#### Tabla: `virtual_tryon_captures` (Clase ORM: `VirtualTryonCapture`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `session_id` | `INTEGER` | FK -> virtual_tryon_sessions.id (NULL) |
| `user_id` | `INTEGER` | FK -> users.id (NULL) |
| `product_id` | `INTEGER` | FK -> products.id |
| `variant_id` | `INTEGER` | FK -> product_variants.id (NULL) |
| `photo_url` | `TEXT` | NOT NULL |
| `original_photo_url` | `TEXT` | NULL |
| `generation_model` | `VARCHAR(100)` | FASHN/IDM/LOCAL |
| `confidence_score` | `FLOAT` | NULL |
| `recommended_size` | `VARCHAR(20)` | NULL |
| `measurements_json` | `TEXT` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE virtual_tryon_captures (
    id SERIAL PRIMARY KEY,
    session_id INTEGER,
    user_id INTEGER,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    photo_url TEXT NOT NULL,
    original_photo_url TEXT,
    generation_model VARCHAR(100) NOT NULL,
    confidence_score FLOAT,
    recommended_size VARCHAR(20),
    measurements_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (session_id) REFERENCES virtual_tryon_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE SET NULL
);
```

#### Tabla: `chatbot_conversations` (Clase ORM: `ChatbotConversation`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id (NULL) |
| `session_token` | `VARCHAR(100)` | NOT NULL |
| `sender` | `VARCHAR(10)` | USER/BOT |
| `message` | `TEXT` | NOT NULL |
| `intent` | `VARCHAR(50)` | NULL |
| `metadata_json` | `TEXT` | NULL |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE chatbot_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_token VARCHAR(100) NOT NULL,
    sender VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    intent VARCHAR(50),
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX ix_chatbot_conversations_session_token ON chatbot_conversations(session_token);
```

---

### Paquete 8: Notificaciones
> **Descripción:** Bandeja de notificaciones in-app y alertas push en tiempo real sobre pedidos, citas, stock y envíos (CU40)
> **Total de Tablas:** 1 tablas físicas en PostgreSQL.

#### Tabla: `in_app_notifications` (Clase ORM: `InAppNotification`) — *Ciclo 3*
| Atributo | Tipo de Dato | Restricción / Propósito |
| :--- | :--- | :--- |
| `id` | `SERIAL` | PK |
| `user_id` | `INTEGER` | FK -> users.id |
| `title` | `VARCHAR(150)` | NOT NULL |
| `message` | `TEXT` | NOT NULL |
| `notification_type` | `VARCHAR(30)` | NOT NULL |
| `reference_id` | `INTEGER` | NULL |
| `reference_type` | `VARCHAR(30)` | NULL |
| `is_read` | `BOOLEAN` | DEFAULT FALSE |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() |

```sql
CREATE TABLE in_app_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(30) NOT NULL,
    reference_id INTEGER,
    reference_type VARCHAR(30),
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX ix_in_app_notifications_user_id ON in_app_notifications(user_id);
CREATE INDEX ix_in_app_notifications_is_read ON in_app_notifications(is_read);
```

---

## 4. Índices de Rendimiento y Optimización

Para garantizar tiempos de respuesta sub-segundo en la aplicación móvil Flutter y la SPA Angular:

1. **Autenticación:** `CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE;`
2. **Búsqueda de Variantes:** `CREATE INDEX idx_variants_search ON product_variants(product_id, color_id, size_id);`
3. **Control de Stock Concurrente:** `CREATE INDEX idx_inventory_stock ON inventory(branch_id, variant_id) INCLUDE (stock_actual);`
4. **Auditoría Inmutable:** `CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);`
5. **Bandeja de Reservas:** `CREATE INDEX ix_reservations_status ON reservations(status);`
6. **Despacho y Envíos:** `CREATE INDEX ix_shipments_status ON shipments(status);`
7. **Notificaciones sin Leer:** `CREATE INDEX ix_in_app_notifications_user_id ON in_app_notifications(user_id);`
