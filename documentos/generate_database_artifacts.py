"""
Script integral que genera:
1. Diagramas Draw.io (multi-página y archivos individuales por ciclo)
2. Scripts DDL SQL (Ciclo 1, Ciclo 2 incremental/acumulado, Ciclo 3 incremental/completo)
3. Documento exhaustivo de Mapeo y Evolución de Base de Datos (Markdown)
"""

import os
import json
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

# Estructura maestra de tablas
TABLES_DATA = {
    # ==================== CICLO 1 ====================
    "roles": {
        "cycle": 1,
        "package": "paquete_seguridad_usuarios",
        "orm_class": "Role",
        "header_fill": "#1e40af",
        "border": "#1e3a8a",
        "col": 0, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(50)", "UQ, NOT NULL"),
            ("description", "VARCHAR(255)", "NULL")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);"""
    },
    "users": {
        "cycle": 1,
        "package": "paquete_seguridad_usuarios",
        "orm_class": "User",
        "header_fill": "#1e40af",
        "border": "#1e3a8a",
        "col": 0, "order": 1,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("email", "VARCHAR(150)", "UQ, NOT NULL"),
            ("password_hash", "VARCHAR(255)", "NOT NULL"),
            ("first_name", "VARCHAR(100)", "NOT NULL"),
            ("last_name", "VARCHAR(100)", "NOT NULL"),
            ("phone", "VARCHAR(20)", "NULL"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE users (
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
CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE;"""
    },
    "user_roles": {
        "cycle": 1,
        "package": "paquete_seguridad_usuarios",
        "orm_class": "user_roles (Table N:N)",
        "header_fill": "#1e40af",
        "border": "#1e3a8a",
        "col": 0, "order": 2,
        "fields": [
            ("user_id", "INTEGER", "PK, FK -> users.id"),
            ("role_id", "INTEGER", "PK, FK -> roles.id")
        ],
        "fks": [
            ("users", "user_id"),
            ("roles", "role_id")
        ],
        "sql_ddl": """CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);"""
    },
    "session_tokens": {
        "cycle": 1,
        "package": "paquete_seguridad_usuarios",
        "orm_class": "SessionToken",
        "header_fill": "#1e40af",
        "border": "#1e3a8a",
        "col": 0, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id"),
            ("token", "VARCHAR(500)", "UQ, NOT NULL"),
            ("expires_at", "TIMESTAMPTZ", "NOT NULL"),
            ("is_revoked", "BOOLEAN", "DEFAULT FALSE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE session_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);"""
    },
    "audit_logs": {
        "cycle": 1,
        "package": "paquete_seguridad_usuarios",
        "orm_class": "AuditLog",
        "header_fill": "#1e40af",
        "border": "#1e3a8a",
        "col": 0, "order": 4,
        "fields": [
            ("id", "BIGSERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id (NULLABLE)"),
            ("action", "VARCHAR(50)", "NOT NULL"),
            ("table_name", "VARCHAR(100)", "NOT NULL"),
            ("row_id", "INTEGER", "NOT NULL"),
            ("old_values", "JSONB", "NULL"),
            ("new_values", "JSONB", "NULL"),
            ("ip_address", "VARCHAR(45)", "NULL"),
            ("timestamp", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE audit_logs (
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
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);"""
    },
    "branches": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Branch",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(100)", "UQ, NOT NULL"),
            ("address", "VARCHAR(255)", "NOT NULL"),
            ("phone", "VARCHAR(20)", "NULL"),
            ("latitude", "DECIMAL(10,8)", "NULL"),
            ("longitude", "DECIMAL(11,8)", "NULL"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);"""
    },
    "branch_employees": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "BranchEmployee",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 1,
        "fields": [
            ("branch_id", "INTEGER", "PK, FK -> branches.id"),
            ("user_id", "INTEGER", "PK, FK -> users.id")
        ],
        "fks": [
            ("branches", "branch_id"),
            ("users", "user_id")
        ],
        "sql_ddl": """CREATE TABLE branch_employees (
    branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (branch_id, user_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);"""
    },
    "categories": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Category",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 2,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(100)", "UQ, NOT NULL"),
            ("description", "VARCHAR(255)", "NULL"),
            ("image_url", "VARCHAR(500)", "NULL")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    image_url VARCHAR(500)
);"""
    },
    "seasons": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Season",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(50)", "UQ, NOT NULL"),
            ("start_date", "DATE", "NOT NULL"),
            ("end_date", "DATE", "NOT NULL")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);"""
    },
    "collections": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Collection",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 4,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(100)", "UQ, NOT NULL"),
            ("description", "VARCHAR(255)", "NULL"),
            ("season_id", "INTEGER", "FK -> seasons.id"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("banner_url", "VARCHAR(500)", "NULL")
        ],
        "fks": [("seasons", "season_id")],
        "sql_ddl": """CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    season_id INTEGER REFERENCES seasons(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    banner_url VARCHAR(500)
);"""
    },
    "colors": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Color",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 5,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(50)", "UQ, NOT NULL"),
            ("hex_code", "VARCHAR(7)", "UQ, NOT NULL")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE colors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    hex_code VARCHAR(7) UNIQUE NOT NULL
);"""
    },
    "sizes": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Size",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 1, "order": 6,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(10)", "UQ, NOT NULL")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE sizes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) UNIQUE NOT NULL
);"""
    },
    "products": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Product",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 2, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(150)", "NOT NULL"),
            ("description", "TEXT", "NULL"),
            ("base_price", "DECIMAL(10,2)", "NOT NULL"),
            ("compare_at_price", "DECIMAL(10,2)", "NULL"),
            ("category_id", "INTEGER", "FK -> categories.id"),
            ("season_id", "INTEGER", "FK -> seasons.id"),
            ("collection_id", "INTEGER", "FK -> collections.id"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("categories", "category_id"),
            ("seasons", "season_id"),
            ("collections", "collection_id")
        ],
        "sql_ddl": """CREATE TABLE products (
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
);"""
    },
    "product_variants": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "ProductVariant",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 2, "order": 1,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("product_id", "INTEGER", "FK -> products.id"),
            ("color_id", "INTEGER", "FK -> colors.id"),
            ("size_id", "INTEGER", "FK -> sizes.id"),
            ("sku", "VARCHAR(50)", "UQ, NOT NULL"),
            ("price_override", "DECIMAL(10,2)", "NULL"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE")
        ],
        "fks": [
            ("products", "product_id"),
            ("colors", "color_id"),
            ("sizes", "size_id")
        ],
        "sql_ddl": """CREATE TABLE product_variants (
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
CREATE INDEX idx_variants_search ON product_variants(product_id, color_id, size_id);"""
    },
    "product_images": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "ProductImage",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 2, "order": 2,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("product_id", "INTEGER", "FK -> products.id"),
            ("color_id", "INTEGER", "FK -> colors.id (NULL)"),
            ("image_url", "VARCHAR(500)", "NOT NULL"),
            ("is_primary", "BOOLEAN", "DEFAULT FALSE")
        ],
        "fks": [
            ("products", "product_id"),
            ("colors", "color_id")
        ],
        "sql_ddl": """CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    color_id INTEGER,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET NULL
);
CREATE INDEX idx_product_images_product ON product_images(product_id);"""
    },
    "product_reviews": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "ProductReview",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 2, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("product_id", "INTEGER", "FK -> products.id"),
            ("user_id", "INTEGER", "FK -> users.id"),
            ("rating", "SMALLINT", "1-5, NOT NULL"),
            ("comment", "TEXT", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("products", "product_id"),
            ("users", "user_id")
        ],
        "sql_ddl": """CREATE TABLE product_reviews (
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
CREATE INDEX idx_reviews_product ON product_reviews(product_id);"""
    },
    "wishlist_items": {
        "cycle": 1,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "WishlistItem",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 2, "order": 4,
        "fields": [
            ("user_id", "INTEGER", "PK, FK -> users.id"),
            ("product_id", "INTEGER", "PK, FK -> products.id"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("users", "user_id"),
            ("products", "product_id")
        ],
        "sql_ddl": """CREATE TABLE wishlist_items (
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX idx_wishlist_user ON wishlist_items(user_id);"""
    },
    "suppliers": {
        "cycle": 1,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "Supplier",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 3, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("nit", "VARCHAR(20)", "UQ, NOT NULL"),
            ("name", "VARCHAR(150)", "NOT NULL"),
            ("email", "VARCHAR(150)", "NULL"),
            ("phone", "VARCHAR(20)", "NULL"),
            ("address", "VARCHAR(255)", "NULL")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    nit VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    address VARCHAR(255)
);"""
    },
    "inventory": {
        "cycle": 1,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "Inventory",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 3, "order": 1,
        "fields": [
            ("branch_id", "INTEGER", "PK, FK -> branches.id"),
            ("variant_id", "INTEGER", "PK, FK -> product_variants.id"),
            ("stock_actual", "INTEGER", "DEFAULT 0"),
            ("avg_cost", "DECIMAL(10,2)", "CPP DEFAULT 0"),
            ("stock_minimo", "INTEGER", "DEFAULT 5"),
            ("stock_maximo", "INTEGER", "DEFAULT 100"),
            ("stock_reservado", "INTEGER", "DEFAULT 0"),
            ("stock_en_transito", "INTEGER", "DEFAULT 0")
        ],
        "fks": [
            ("branches", "branch_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE inventory (
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
CREATE INDEX idx_inventory_stock ON inventory(branch_id, variant_id) INCLUDE (stock_actual);"""
    },
    "inventory_ledger": {
        "cycle": 1,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "InventoryLedger",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 3, "order": 2,
        "fields": [
            ("id", "BIGSERIAL", "PK"),
            ("branch_id", "INTEGER", "FK -> branches.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL (+/-)"),
            ("movement_type", "VARCHAR(20)", "NOT NULL"),
            ("unit_cost", "DECIMAL(10,2)", "NOT NULL"),
            ("reference_id", "VARCHAR(50)", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("branches", "branch_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE inventory_ledger (
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
);"""
    },
    "purchase_orders": {
        "cycle": 1,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "PurchaseOrder",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 3, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("supplier_id", "INTEGER", "FK -> suppliers.id"),
            ("branch_id", "INTEGER", "FK -> branches.id"),
            ("status", "VARCHAR(20)", "DEFAULT 'COMPLETADO'"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("suppliers", "supplier_id"),
            ("branches", "branch_id")
        ],
        "sql_ddl": """CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'COMPLETADO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);"""
    },
    "purchase_details": {
        "cycle": 1,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "PurchaseDetail",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 3, "order": 4,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("purchase_order_id", "INTEGER", "FK -> purchase_orders.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL"),
            ("unit_cost", "DECIMAL(10,2)", "NOT NULL")
        ],
        "fks": [
            ("purchase_orders", "purchase_order_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE purchase_details (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },

    # ==================== CICLO 2 ====================
    "carts": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "Cart",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id (NULLABLE)"),
            ("session_id", "VARCHAR(80)", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(80),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);"""
    },
    "cart_items": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "CartItem",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 1,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("cart_id", "INTEGER", "FK -> carts.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("carts", "cart_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },
    "cash_shifts": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "CashShift",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 2,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("cashier_id", "INTEGER", "FK -> users.id"),
            ("branch_id", "INTEGER", "FK -> branches.id"),
            ("opening_amount", "DECIMAL(10,2)", "NOT NULL"),
            ("closing_amount_declared", "DECIMAL(10,2)", "NULL"),
            ("closing_amount_system", "DECIMAL(10,2)", "NULL"),
            ("difference", "DECIMAL(10,2)", "NULL"),
            ("status", "VARCHAR(20)", "ABIERTO/CERRADO"),
            ("opened_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("closed_at", "TIMESTAMPTZ", "NULL"),
            ("notes", "VARCHAR(255)", "NULL")
        ],
        "fks": [
            ("users", "cashier_id"),
            ("branches", "branch_id")
        ],
        "sql_ddl": """CREATE TABLE cash_shifts (
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
);"""
    },
    "orders": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "Order",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id"),
            ("branch_id", "INTEGER", "FK -> branches.id"),
            ("channel", "VARCHAR(10)", "ONLINE/POS"),
            ("status", "VARCHAR(20)", "PAGADA/PREPARANDO..."),
            ("subtotal", "DECIMAL(10,2)", "NOT NULL"),
            ("discount_amount", "DECIMAL(10,2)", "DEFAULT 0"),
            ("coupon_code", "VARCHAR(30)", "NULL"),
            ("total_amount", "DECIMAL(10,2)", "NOT NULL"),
            ("cash_shift_id", "INTEGER", "FK -> cash_shifts.id"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("users", "user_id"),
            ("branches", "branch_id"),
            ("cash_shifts", "cash_shift_id")
        ],
        "sql_ddl": """CREATE TABLE orders (
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
);"""
    },
    "order_items": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "OrderItem",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 4,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("order_id", "INTEGER", "FK -> orders.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL"),
            ("unit_price", "DECIMAL(10,2)", "NOT NULL")
        ],
        "fks": [
            ("orders", "order_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },
    "payments": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "Payment (STI)",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 5,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("order_id", "INTEGER", "FK -> orders.id"),
            ("payment_type", "VARCHAR(20)", "EFECTIVO/TARJETA/QR/PAYPAL"),
            ("amount", "DECIMAL(10,2)", "NOT NULL"),
            ("status", "VARCHAR(20)", "NOT NULL"),
            ("paid_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("cash_received", "DECIMAL(10,2)", "NULL"),
            ("cash_change", "DECIMAL(10,2)", "NULL"),
            ("card_brand", "VARCHAR(20)", "NULL"),
            ("card_last4", "VARCHAR(4)", "NULL"),
            ("gateway_reference", "VARCHAR(80)", "NULL"),
            ("qr_reference", "VARCHAR(80)", "NULL"),
            ("paypal_payer_id", "VARCHAR(50)", "NULL"),
            ("paypal_payer_email", "VARCHAR(100)", "NULL"),
            ("credit_due_date", "DATE", "NULL")
        ],
        "fks": [("orders", "order_id")],
        "sql_ddl": """CREATE TABLE payments (
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
);"""
    },
    "invoices": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "Invoice",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 4, "order": 6,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("order_id", "INTEGER", "UQ, FK -> orders.id"),
            ("doc_type", "VARCHAR(15)", "FACTURA/NOTA_ENTREGA"),
            ("tax_rate", "DECIMAL(4,3)", "0.130 (IVA 13%)"),
            ("subtotal", "DECIMAL(10,2)", "NOT NULL"),
            ("tax_amount", "DECIMAL(10,2)", "NOT NULL"),
            ("total", "DECIMAL(10,2)", "NOT NULL"),
            ("control_code", "VARCHAR(40)", "NULL"),
            ("customer_nit", "VARCHAR(20)", "NULL"),
            ("customer_name", "VARCHAR(150)", "NULL"),
            ("issued_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("orders", "order_id")],
        "sql_ddl": """CREATE TABLE invoices (
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
);"""
    },
    "quotations": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "Quotation",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 5, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("quotation_number", "VARCHAR(30)", "UQ, NOT NULL"),
            ("customer_name", "VARCHAR(150)", "NOT NULL"),
            ("customer_email", "VARCHAR(100)", "NULL"),
            ("customer_phone", "VARCHAR(30)", "NULL"),
            ("created_by_id", "INTEGER", "FK -> users.id"),
            ("branch_id", "INTEGER", "FK -> branches.id"),
            ("total_amount", "DECIMAL(10,2)", "NOT NULL"),
            ("valid_until", "TIMESTAMPTZ", "NOT NULL"),
            ("status", "VARCHAR(20)", "VIGENTE/CONVERTIDA"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("users", "created_by_id"),
            ("branches", "branch_id")
        ],
        "sql_ddl": """CREATE TABLE quotations (
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
);"""
    },
    "quotation_items": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "QuotationItem",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 5, "order": 1,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("quotation_id", "INTEGER", "FK -> quotations.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL"),
            ("unit_price", "DECIMAL(10,2)", "NOT NULL")
        ],
        "fks": [
            ("quotations", "quotation_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE quotation_items (
    id SERIAL PRIMARY KEY,
    quotation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },
    "order_returns": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "OrderReturn",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 5, "order": 2,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("return_number", "VARCHAR(30)", "UQ, NOT NULL"),
            ("order_id", "INTEGER", "FK -> orders.id"),
            ("processed_by_id", "INTEGER", "FK -> users.id"),
            ("return_type", "VARCHAR(25)", "DEVOLUCION/CAMBIO"),
            ("reason", "VARCHAR(255)", "NOT NULL"),
            ("refund_amount", "DECIMAL(10,2)", "NOT NULL"),
            ("status", "VARCHAR(20)", "APROBADA..."),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("orders", "order_id"),
            ("users", "processed_by_id")
        ],
        "sql_ddl": """CREATE TABLE order_returns (
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
);"""
    },
    "order_return_items": {
        "cycle": 2,
        "package": "paquete_ventas_y_pagos",
        "orm_class": "OrderReturnItem",
        "header_fill": "#b91c1c",
        "border": "#991b1b",
        "col": 5, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("return_id", "INTEGER", "FK -> order_returns.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL"),
            ("replacement_variant_id", "INTEGER", "FK -> product_variants.id (NULL)")
        ],
        "fks": [
            ("order_returns", "return_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE order_return_items (
    id SERIAL PRIMARY KEY,
    return_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    replacement_variant_id INTEGER,
    FOREIGN KEY (return_id) REFERENCES order_returns(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT,
    FOREIGN KEY (replacement_variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },
    "stock_transfers": {
        "cycle": 2,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "StockTransfer",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 5, "order": 4,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("transfer_number", "VARCHAR(30)", "UQ, NOT NULL"),
            ("origin_branch_id", "INTEGER", "FK -> branches.id"),
            ("destination_branch_id", "INTEGER", "FK -> branches.id"),
            ("requested_by_id", "INTEGER", "FK -> users.id"),
            ("received_by_id", "INTEGER", "FK -> users.id (NULL)"),
            ("status", "VARCHAR(20)", "SOLICITADA/EN_TRANSITO..."),
            ("notes", "VARCHAR(255)", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("completed_at", "TIMESTAMPTZ", "NULL")
        ],
        "fks": [
            ("branches", "origin_branch_id"),
            ("branches", "destination_branch_id"),
            ("users", "requested_by_id")
        ],
        "sql_ddl": """CREATE TABLE stock_transfers (
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
);"""
    },
    "stock_transfer_details": {
        "cycle": 2,
        "package": "paquete_inventario_y_proveedores",
        "orm_class": "StockTransferDetail",
        "header_fill": "#b45309",
        "border": "#92400e",
        "col": 5, "order": 5,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("transfer_id", "INTEGER", "FK -> stock_transfers.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "NOT NULL")
        ],
        "fks": [
            ("stock_transfers", "transfer_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE stock_transfer_details (
    id SERIAL PRIMARY KEY,
    transfer_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (transfer_id) REFERENCES stock_transfers(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },
    "coupons": {
        "cycle": 2,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Coupon",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 5, "order": 6,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("code", "VARCHAR(30)", "UQ, NOT NULL"),
            ("discount_type", "VARCHAR(15)", "PORCENTAJE/MONTO_FIJO"),
            ("discount_value", "DECIMAL(10,2)", "NOT NULL"),
            ("min_purchase_amount", "DECIMAL(10,2)", "DEFAULT 0"),
            ("valid_from", "TIMESTAMPTZ", "NOT NULL"),
            ("valid_until", "TIMESTAMPTZ", "NOT NULL"),
            ("max_uses", "INTEGER", "DEFAULT 100"),
            ("used_count", "INTEGER", "DEFAULT 0"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE coupons (
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
);"""
    },
    "seasonal_promotions": {
        "cycle": 2,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "SeasonalPromotion",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 5, "order": 7,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(100)", "NOT NULL"),
            ("description", "TEXT", "NULL"),
            ("discount_percent", "INTEGER", "NOT NULL"),
            ("category_id", "INTEGER", "FK -> categories.id (NULL)"),
            ("start_date", "DATE", "NOT NULL"),
            ("end_date", "DATE", "NOT NULL"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("categories", "category_id")],
        "sql_ddl": """CREATE TABLE seasonal_promotions (
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
);"""
    },
    "wishlists": {
        "cycle": 2,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "Wishlist",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 5, "order": 8,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id"),
            ("name", "VARCHAR(100)", "NOT NULL"),
            ("is_public", "BOOLEAN", "DEFAULT FALSE"),
            ("share_token", "VARCHAR(64)", "UQ, NOT NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE wishlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);"""
    },
    "wishlist_group_items": {
        "cycle": 2,
        "package": "paquete_catalogo_y_tiendas",
        "orm_class": "WishlistGroupItem",
        "header_fill": "#047857",
        "border": "#065f46",
        "col": 5, "order": 9,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("wishlist_id", "INTEGER", "FK -> wishlists.id"),
            ("product_id", "INTEGER", "FK -> products.id"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("wishlists", "wishlist_id"),
            ("products", "product_id")
        ],
        "sql_ddl": """CREATE TABLE wishlist_group_items (
    id SERIAL PRIMARY KEY,
    wishlist_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT uq_wishlist_group_product UNIQUE (wishlist_id, product_id),
    FOREIGN KEY (wishlist_id) REFERENCES wishlists(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);"""
    },

    # ==================== CICLO 3 ====================
    "reservations": {
        "cycle": 3,
        "package": "paquete_reservas_y_citas",
        "orm_class": "Reservation",
        "header_fill": "#6d28d9",
        "border": "#5b21b6",
        "col": 6, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("reservation_code", "VARCHAR(30)", "UQ, NOT NULL"),
            ("customer_id", "INTEGER", "FK -> users.id"),
            ("branch_id", "INTEGER", "FK -> branches.id"),
            ("status", "VARCHAR(20)", "PENDING/READY/LATE..."),
            ("appointment_date", "DATE", "NOT NULL"),
            ("appointment_time", "VARCHAR(10)", "NOT NULL"),
            ("reschedule_count", "INTEGER", "DEFAULT 0"),
            ("grace_period_notified", "BOOLEAN", "DEFAULT FALSE"),
            ("reserved_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("expires_at", "TIMESTAMPTZ", "NOT NULL"),
            ("notes", "VARCHAR(255)", "NULL"),
            ("total_amount", "DECIMAL(10,2)", "NOT NULL"),
            ("deposit_amount", "DECIMAL(10,2)", "50% DEPOSITO"),
            ("payment_method", "VARCHAR(20)", "PAYPAL/QR/TARJETA"),
            ("payment_reference", "VARCHAR(100)", "NULL"),
            ("deposit_paid", "BOOLEAN", "DEFAULT TRUE"),
            ("completed_sale_id", "INTEGER", "FK -> orders.id (NULL)"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("users", "customer_id"),
            ("branches", "branch_id"),
            ("orders", "completed_sale_id")
        ],
        "sql_ddl": """CREATE TABLE reservations (
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
CREATE INDEX ix_reservations_status ON reservations(status);"""
    },
    "reservation_items": {
        "cycle": 3,
        "package": "paquete_reservas_y_citas",
        "orm_class": "ReservationItem",
        "header_fill": "#6d28d9",
        "border": "#5b21b6",
        "col": 6, "order": 1,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("reservation_id", "INTEGER", "FK -> reservations.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id"),
            ("quantity", "INTEGER", "DEFAULT 1"),
            ("unit_price", "DECIMAL(10,2)", "NOT NULL"),
            ("notes", "VARCHAR(100)", "NULL")
        ],
        "fks": [
            ("reservations", "reservation_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE reservation_items (
    id SERIAL PRIMARY KEY,
    reservation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1 NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    notes VARCHAR(100),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);"""
    },
    "delivery_zones": {
        "cycle": 3,
        "package": "paquete_envios_y_logistica",
        "orm_class": "DeliveryZone",
        "header_fill": "#14b8a6",
        "border": "#0f766e",
        "col": 6, "order": 2,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("name", "VARCHAR(100)", "NOT NULL"),
            ("city", "VARCHAR(50)", "NOT NULL"),
            ("min_distance_km", "DECIMAL(5,2)", "NOT NULL"),
            ("max_distance_km", "DECIMAL(5,2)", "NOT NULL"),
            ("base_rate", "DECIMAL(10,2)", "NOT NULL"),
            ("estimated_hours", "INTEGER", "NOT NULL"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [],
        "sql_ddl": """CREATE TABLE delivery_zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    min_distance_km NUMERIC(5, 2) NOT NULL,
    max_distance_km NUMERIC(5, 2) NOT NULL,
    base_rate NUMERIC(10, 2) NOT NULL,
    estimated_hours INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);"""
    },
    "delivery_persons": {
        "cycle": 3,
        "package": "paquete_envios_y_logistica",
        "orm_class": "DeliveryPerson",
        "header_fill": "#14b8a6",
        "border": "#0f766e",
        "col": 6, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "UQ, FK -> users.id"),
            ("vehicle_type", "VARCHAR(50)", "MOTO/AUTO/BICI"),
            ("vehicle_plate", "VARCHAR(20)", "NULL"),
            ("license_number", "VARCHAR(50)", "NULL"),
            ("coverage_zone", "VARCHAR(100)", "NOT NULL"),
            ("phone", "VARCHAR(20)", "NOT NULL"),
            ("is_available", "BOOLEAN", "DEFAULT TRUE"),
            ("rating", "DECIMAL(3,2)", "DEFAULT 5.0"),
            ("total_deliveries", "INTEGER", "DEFAULT 0"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE delivery_persons (
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
);"""
    },
    "shipments": {
        "cycle": 3,
        "package": "paquete_envios_y_logistica",
        "orm_class": "Shipment",
        "header_fill": "#14b8a6",
        "border": "#0f766e",
        "col": 6, "order": 4,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("tracking_number", "VARCHAR(30)", "UQ, NOT NULL"),
            ("order_id", "INTEGER", "FK -> orders.id"),
            ("zone_id", "INTEGER", "FK -> delivery_zones.id (NULL)"),
            ("delivery_person_id", "INTEGER", "FK -> delivery_persons.id (NULL)"),
            ("claimed_at", "TIMESTAMPTZ", "NULL"),
            ("delivery_date", "DATE", "NULL"),
            ("delivery_time", "VARCHAR(20)", "NULL"),
            ("delivery_attempts", "INTEGER", "DEFAULT 0"),
            ("failed_reason", "VARCHAR(255)", "NULL"),
            ("carrier_name", "VARCHAR(100)", "NOT NULL"),
            ("carrier_phone", "VARCHAR(20)", "NULL"),
            ("delivery_address", "VARCHAR(255)", "NOT NULL"),
            ("recipient_name", "VARCHAR(100)", "NOT NULL"),
            ("recipient_phone", "VARCHAR(20)", "NOT NULL"),
            ("shipping_cost", "DECIMAL(10,2)", "NOT NULL"),
            ("status", "VARCHAR(30)", "ASSIGNED/IN_TRANSIT..."),
            ("dispatched_at", "TIMESTAMPTZ", "NULL"),
            ("delivered_at", "TIMESTAMPTZ", "NULL"),
            ("notes", "VARCHAR(255)", "NULL"),
            ("delivery_photo_url", "TEXT", "EVIDENCIA FOTO"),
            ("received_by_name", "VARCHAR(100)", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("updated_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("orders", "order_id"),
            ("delivery_zones", "zone_id"),
            ("delivery_persons", "delivery_person_id")
        ],
        "sql_ddl": """CREATE TABLE shipments (
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
CREATE INDEX ix_shipments_status ON shipments(status);"""
    },
    "shipment_tracking_events": {
        "cycle": 3,
        "package": "paquete_envios_y_logistica",
        "orm_class": "ShipmentTrackingEvent",
        "header_fill": "#14b8a6",
        "border": "#0f766e",
        "col": 6, "order": 5,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("shipment_id", "INTEGER", "FK -> shipments.id"),
            ("status", "VARCHAR(30)", "NOT NULL"),
            ("location", "VARCHAR(100)", "NOT NULL"),
            ("description", "VARCHAR(255)", "NOT NULL"),
            ("photo_url", "TEXT", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("shipments", "shipment_id")],
        "sql_ddl": """CREATE TABLE shipment_tracking_events (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    location VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL,
    photo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE
);"""
    },
    "virtual_tryon_sessions": {
        "cycle": 3,
        "package": "paquete_inteligente_y_analitica",
        "orm_class": "VirtualTryonSession",
        "header_fill": "#4b5563",
        "border": "#374151",
        "col": 7, "order": 0,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id (NULLABLE)"),
            ("session_token", "VARCHAR(100)", "UQ, NOT NULL"),
            ("channel", "VARCHAR(20)", "WEB/MOBILE"),
            ("status", "VARCHAR(20)", "NOT NULL"),
            ("started_at", "TIMESTAMPTZ", "DEFAULT now()"),
            ("finished_at", "TIMESTAMPTZ", "NULL")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE virtual_tryon_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_token VARCHAR(100) UNIQUE NOT NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);"""
    },
    "virtual_tryon_items": {
        "cycle": 3,
        "package": "paquete_inteligente_y_analitica",
        "orm_class": "VirtualTryonItem",
        "header_fill": "#4b5563",
        "border": "#374151",
        "col": 7, "order": 1,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("session_id", "INTEGER", "FK -> virtual_tryon_sessions.id"),
            ("product_id", "INTEGER", "FK -> products.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id (NULL)"),
            ("tested_size", "VARCHAR(20)", "NULL"),
            ("fit_feedback", "VARCHAR(100)", "NULL"),
            ("tested_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("virtual_tryon_sessions", "session_id"),
            ("products", "product_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE virtual_tryon_items (
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
);"""
    },
    "virtual_tryon_captures": {
        "cycle": 3,
        "package": "paquete_inteligente_y_analitica",
        "orm_class": "VirtualTryonCapture",
        "header_fill": "#4b5563",
        "border": "#374151",
        "col": 7, "order": 2,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("session_id", "INTEGER", "FK -> virtual_tryon_sessions.id (NULL)"),
            ("user_id", "INTEGER", "FK -> users.id (NULL)"),
            ("product_id", "INTEGER", "FK -> products.id"),
            ("variant_id", "INTEGER", "FK -> product_variants.id (NULL)"),
            ("photo_url", "TEXT", "NOT NULL"),
            ("original_photo_url", "TEXT", "NULL"),
            ("generation_model", "VARCHAR(100)", "FASHN/IDM/LOCAL"),
            ("confidence_score", "FLOAT", "NULL"),
            ("recommended_size", "VARCHAR(20)", "NULL"),
            ("measurements_json", "TEXT", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [
            ("virtual_tryon_sessions", "session_id"),
            ("users", "user_id"),
            ("products", "product_id"),
            ("product_variants", "variant_id")
        ],
        "sql_ddl": """CREATE TABLE virtual_tryon_captures (
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
);"""
    },
    "chatbot_conversations": {
        "cycle": 3,
        "package": "paquete_inteligente_y_analitica",
        "orm_class": "ChatbotConversation",
        "header_fill": "#4b5563",
        "border": "#374151",
        "col": 7, "order": 3,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id (NULL)"),
            ("session_token", "VARCHAR(100)", "NOT NULL"),
            ("sender", "VARCHAR(10)", "USER/BOT"),
            ("message", "TEXT", "NOT NULL"),
            ("intent", "VARCHAR(50)", "NULL"),
            ("metadata_json", "TEXT", "NULL"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE chatbot_conversations (
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
CREATE INDEX ix_chatbot_conversations_session_token ON chatbot_conversations(session_token);"""
    },
    "in_app_notifications": {
        "cycle": 3,
        "package": "paquete_notificaciones",
        "orm_class": "InAppNotification",
        "header_fill": "#334155",
        "border": "#1e293b",
        "col": 7, "order": 4,
        "fields": [
            ("id", "SERIAL", "PK"),
            ("user_id", "INTEGER", "FK -> users.id"),
            ("title", "VARCHAR(150)", "NOT NULL"),
            ("message", "TEXT", "NOT NULL"),
            ("notification_type", "VARCHAR(30)", "NOT NULL"),
            ("reference_id", "INTEGER", "NULL"),
            ("reference_type", "VARCHAR(30)", "NULL"),
            ("is_read", "BOOLEAN", "DEFAULT FALSE"),
            ("created_at", "TIMESTAMPTZ", "DEFAULT now()")
        ],
        "fks": [("users", "user_id")],
        "sql_ddl": """CREATE TABLE in_app_notifications (
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
CREATE INDEX ix_in_app_notifications_is_read ON in_app_notifications(is_read);"""
    }
}

# =====================================================================
# DEFINICIÓN EXHAUSTIVA DE RELACIONES CONCEPTUALES Y CARDINALIDADES
# =====================================================================

CONCEPTUAL_RELATIONS = [
    # ==================== CICLO 1 (27 Relaciones) ====================
    {"src": "roles", "trg": "user_roles", "src_card": "1..1", "trg_card": "0..*", "verb": "asignado en", "cycle": 1},
    {"src": "users", "trg": "user_roles", "src_card": "1..1", "trg_card": "1..*", "verb": "posee roles", "cycle": 1},
    {"src": "users", "trg": "session_tokens", "src_card": "1..1", "trg_card": "0..*", "verb": "inicia sesión", "cycle": 1},
    {"src": "users", "trg": "audit_logs", "src_card": "0..1", "trg_card": "0..*", "verb": "genera log", "cycle": 1},
    {"src": "branches", "trg": "branch_employees", "src_card": "1..1", "trg_card": "0..*", "verb": "asigna personal", "cycle": 1},
    {"src": "users", "trg": "branch_employees", "src_card": "1..1", "trg_card": "0..1", "verb": "trabaja en", "cycle": 1},
    {"src": "categories", "trg": "products", "src_card": "1..1", "trg_card": "0..*", "verb": "clasifica", "cycle": 1},
    {"src": "seasons", "trg": "products", "src_card": "0..1", "trg_card": "0..*", "verb": "temporada de", "cycle": 1},
    {"src": "seasons", "trg": "collections", "src_card": "0..1", "trg_card": "0..*", "verb": "organiza", "cycle": 1},
    {"src": "collections", "trg": "products", "src_card": "0..1", "trg_card": "0..*", "verb": "incluye", "cycle": 1},
    {"src": "products", "trg": "product_variants", "src_card": "1..1", "trg_card": "1..*", "verb": "tiene variantes", "cycle": 1},
    {"src": "colors", "trg": "product_variants", "src_card": "1..1", "trg_card": "0..*", "verb": "aplica color", "cycle": 1},
    {"src": "sizes", "trg": "product_variants", "src_card": "1..1", "trg_card": "0..*", "verb": "aplica talla", "cycle": 1},
    {"src": "products", "trg": "product_images", "src_card": "1..1", "trg_card": "1..*", "verb": "muestra fotos", "cycle": 1},
    {"src": "colors", "trg": "product_images", "src_card": "0..1", "trg_card": "0..*", "verb": "asocia tono", "cycle": 1},
    {"src": "products", "trg": "product_reviews", "src_card": "1..1", "trg_card": "0..*", "verb": "es calificado", "cycle": 1},
    {"src": "users", "trg": "product_reviews", "src_card": "1..1", "trg_card": "0..*", "verb": "escribe reseña", "cycle": 1},
    {"src": "users", "trg": "wishlist_items", "src_card": "1..1", "trg_card": "0..*", "verb": "marca favorito", "cycle": 1},
    {"src": "products", "trg": "wishlist_items", "src_card": "1..1", "trg_card": "0..*", "verb": "favorito de", "cycle": 1},
    {"src": "suppliers", "trg": "purchase_orders", "src_card": "1..1", "trg_card": "0..*", "verb": "abastece", "cycle": 1},
    {"src": "branches", "trg": "purchase_orders", "src_card": "1..1", "trg_card": "0..*", "verb": "recibe compra", "cycle": 1},
    {"src": "purchase_orders", "trg": "purchase_details", "src_card": "1..1", "trg_card": "1..*", "verb": "contiene lote", "cycle": 1},
    {"src": "product_variants", "trg": "purchase_details", "src_card": "1..1", "trg_card": "0..*", "verb": "comprado en", "cycle": 1},
    {"src": "branches", "trg": "inventory", "src_card": "1..1", "trg_card": "0..*", "verb": "almacena stock", "cycle": 1},
    {"src": "product_variants", "trg": "inventory", "src_card": "1..1", "trg_card": "0..*", "verb": "stockeado en", "cycle": 1},
    {"src": "branches", "trg": "inventory_ledger", "src_card": "1..1", "trg_card": "0..*", "verb": "registra kardex", "cycle": 1},
    {"src": "product_variants", "trg": "inventory_ledger", "src_card": "1..1", "trg_card": "0..*", "verb": "movimiento de", "cycle": 1},

    # ==================== CICLO 2 (+31 Relaciones = 58) ====================
    {"src": "users", "trg": "carts", "src_card": "0..1", "trg_card": "0..1", "verb": "crea carrito", "cycle": 2},
    {"src": "carts", "trg": "cart_items", "src_card": "1..1", "trg_card": "0..*", "verb": "contiene ítems", "cycle": 2},
    {"src": "product_variants", "trg": "cart_items", "src_card": "1..1", "trg_card": "0..*", "verb": "agregado a", "cycle": 2},
    {"src": "users", "trg": "cash_shifts", "src_card": "1..1", "trg_card": "0..*", "verb": "opera turno", "cycle": 2},
    {"src": "branches", "trg": "cash_shifts", "src_card": "1..1", "trg_card": "0..*", "verb": "sede de caja", "cycle": 2},
    {"src": "users", "trg": "orders", "src_card": "1..1", "trg_card": "0..*", "verb": "realiza pedido", "cycle": 2},
    {"src": "branches", "trg": "orders", "src_card": "1..1", "trg_card": "0..*", "verb": "atiende pedido", "cycle": 2},
    {"src": "cash_shifts", "trg": "orders", "src_card": "0..1", "trg_card": "0..*", "verb": "cobra en turno", "cycle": 2},
    {"src": "orders", "trg": "order_items", "src_card": "1..1", "trg_card": "1..*", "verb": "detalla venta", "cycle": 2},
    {"src": "product_variants", "trg": "order_items", "src_card": "1..1", "trg_card": "0..*", "verb": "vendido en", "cycle": 2},
    {"src": "orders", "trg": "payments", "src_card": "1..1", "trg_card": "1..*", "verb": "pagado con", "cycle": 2},
    {"src": "orders", "trg": "invoices", "src_card": "1..1", "trg_card": "1..1", "verb": "facturado en", "cycle": 2},
    {"src": "users", "trg": "quotations", "src_card": "1..1", "trg_card": "0..*", "verb": "elabora", "cycle": 2},
    {"src": "branches", "trg": "quotations", "src_card": "0..1", "trg_card": "0..*", "verb": "emite", "cycle": 2},
    {"src": "quotations", "trg": "quotation_items", "src_card": "1..1", "trg_card": "1..*", "verb": "cotiza ítem", "cycle": 2},
    {"src": "product_variants", "trg": "quotation_items", "src_card": "1..1", "trg_card": "0..*", "verb": "incluido en", "cycle": 2},
    {"src": "orders", "trg": "order_returns", "src_card": "1..1", "trg_card": "0..*", "verb": "objeto de", "cycle": 2},
    {"src": "users", "trg": "order_returns", "src_card": "1..1", "trg_card": "0..*", "verb": "autoriza", "cycle": 2},
    {"src": "order_returns", "trg": "order_return_items", "src_card": "1..1", "trg_card": "1..*", "verb": "detalla", "cycle": 2},
    {"src": "product_variants", "trg": "order_return_items", "src_card": "1..1", "trg_card": "0..*", "verb": "devuelto", "cycle": 2},
    {"src": "product_variants", "trg": "order_return_items", "src_card": "0..1", "trg_card": "0..*", "verb": "reemplazo", "cycle": 2},
    {"src": "branches", "trg": "stock_transfers", "src_card": "1..1", "trg_card": "0..*", "verb": "origen despacho", "cycle": 2},
    {"src": "branches", "trg": "stock_transfers", "src_card": "1..1", "trg_card": "0..*", "verb": "destino recepción", "cycle": 2},
    {"src": "users", "trg": "stock_transfers", "src_card": "1..1", "trg_card": "0..*", "verb": "solicita", "cycle": 2},
    {"src": "users", "trg": "stock_transfers", "src_card": "0..1", "trg_card": "0..*", "verb": "recibe", "cycle": 2},
    {"src": "stock_transfers", "trg": "stock_transfer_details", "src_card": "1..1", "trg_card": "1..*", "verb": "incluye", "cycle": 2},
    {"src": "product_variants", "trg": "stock_transfer_details", "src_card": "1..1", "trg_card": "0..*", "verb": "transferido", "cycle": 2},
    {"src": "categories", "trg": "seasonal_promotions", "src_card": "0..1", "trg_card": "0..*", "verb": "descuento a", "cycle": 2},
    {"src": "users", "trg": "wishlists", "src_card": "1..1", "trg_card": "0..*", "verb": "crea lista", "cycle": 2},
    {"src": "wishlists", "trg": "wishlist_group_items", "src_card": "1..1", "trg_card": "0..*", "verb": "agrupa", "cycle": 2},
    {"src": "products", "trg": "wishlist_group_items", "src_card": "1..1", "trg_card": "0..*", "verb": "listado en", "cycle": 2},

    # ==================== CICLO 3 (+20 Relaciones = 78) ====================
    {"src": "users", "trg": "reservations", "src_card": "1..1", "trg_card": "0..*", "verb": "agenda cita", "cycle": 3},
    {"src": "branches", "trg": "reservations", "src_card": "1..1", "trg_card": "0..*", "verb": "sede de cita", "cycle": 3},
    {"src": "orders", "trg": "reservations", "src_card": "0..1", "trg_card": "0..1", "verb": "cobrado en venta", "cycle": 3},
    {"src": "reservations", "trg": "reservation_items", "src_card": "1..1", "trg_card": "1..*", "verb": "aparta prendas", "cycle": 3},
    {"src": "product_variants", "trg": "reservation_items", "src_card": "1..1", "trg_card": "0..*", "verb": "apartado en", "cycle": 3},
    {"src": "users", "trg": "delivery_persons", "src_card": "1..1", "trg_card": "0..1", "verb": "repartidor", "cycle": 3},
    {"src": "orders", "trg": "shipments", "src_card": "1..1", "trg_card": "0..1", "verb": "despachado en", "cycle": 3},
    {"src": "delivery_zones", "trg": "shipments", "src_card": "0..1", "trg_card": "0..*", "verb": "zona de envío", "cycle": 3},
    {"src": "delivery_persons", "trg": "shipments", "src_card": "0..1", "trg_card": "0..*", "verb": "transporta", "cycle": 3},
    {"src": "shipments", "trg": "shipment_tracking_events", "src_card": "1..1", "trg_card": "1..*", "verb": "historial ruta", "cycle": 3},
    {"src": "users", "trg": "virtual_tryon_sessions", "src_card": "0..1", "trg_card": "0..*", "verb": "sesión vestidor", "cycle": 3},
    {"src": "virtual_tryon_sessions", "trg": "virtual_tryon_items", "src_card": "1..1", "trg_card": "0..*", "verb": "prueba prendas", "cycle": 3},
    {"src": "products", "trg": "virtual_tryon_items", "src_card": "1..1", "trg_card": "0..*", "verb": "simulado en", "cycle": 3},
    {"src": "product_variants", "trg": "virtual_tryon_items", "src_card": "0..1", "trg_card": "0..*", "verb": "variante probada", "cycle": 3},
    {"src": "virtual_tryon_sessions", "trg": "virtual_tryon_captures", "src_card": "0..1", "trg_card": "0..*", "verb": "foto generada", "cycle": 3},
    {"src": "users", "trg": "virtual_tryon_captures", "src_card": "0..1", "trg_card": "0..*", "verb": "retratado", "cycle": 3},
    {"src": "products", "trg": "virtual_tryon_captures", "src_card": "1..1", "trg_card": "0..*", "verb": "prenda IA", "cycle": 3},
    {"src": "product_variants", "trg": "virtual_tryon_captures", "src_card": "0..1", "trg_card": "0..*", "verb": "variante IA", "cycle": 3},
    {"src": "users", "trg": "chatbot_conversations", "src_card": "0..1", "trg_card": "0..*", "verb": "consulta bot", "cycle": 3},
    {"src": "users", "trg": "in_app_notifications", "src_card": "1..1", "trg_card": "0..*", "verb": "notificado", "cycle": 3}
]

# =====================================================================
# GENERADOR DRAW.IO
# =====================================================================

def build_drawio_page(diagram_id, diagram_name, active_cycles):
    """
    Construye una página XML de Draw.io para un ciclo determinado o acumulado.
    """
    col_width = 320
    col_gap = 60
    base_x = 50
    base_y = 60
    
    # Filtrar tablas activas
    active_tables = {k: v for k, v in TABLES_DATA.items() if v["cycle"] in active_cycles}
    
    xml_cells = []
    xml_cells.append('<mxCell id="0" />')
    xml_cells.append('<mxCell id="1" parent="0" />')
    
    # Posicionamiento por columna
    col_heights = {}
    
    for tbl_name, info in active_tables.items():
        col_idx = info["col"]
        # Normalizar col_idx si hay menos columnas en ciclos tempranos
        if max(active_cycles) == 1:
            col_idx = info["col"] # 0 a 3
        elif max(active_cycles) == 2:
            col_idx = info["col"] # 0 a 5
        else:
            col_idx = info["col"] # 0 a 7
            
        cur_y = col_heights.get(col_idx, base_y)
        cur_x = base_x + col_idx * (col_width + col_gap)
        
        num_fields = len(info["fields"])
        tbl_height = 36 + num_fields * 24
        
        # Estilo de cabecera: si es nueva en este ciclo vs heredada
        is_new_in_current_max = (info["cycle"] == max(active_cycles))
        
        header_fill = info["header_fill"]
        border_color = info["border"]
        tbl_title = f"{tbl_name} ({info['orm_class']})"
        if len(active_cycles) > 1 and is_new_in_current_max:
            tbl_title = f"★ {tbl_name} [Nuevo C{max(active_cycles)}]"
            
        swimlane_style = (
            f"swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;"
            f"horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;"
            f"resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;"
            f"fillColor={header_fill};strokeColor={border_color};fontColor=#ffffff;strokeWidth=2;"
        )
        
        tbl_cell_id = f"tbl_{tbl_name}"
        xml_cells.append(
            f'<mxCell id="{tbl_cell_id}" value="{escape(tbl_title)}" style="{swimlane_style}" vertex="1" parent="1">'
            f'<mxGeometry x="{cur_x}" y="{cur_y}" width="{col_width}" height="{tbl_height}" as="geometry" />'
            f'</mxCell>'
        )
        
        # Filas de atributos
        row_y = 30
        for f_name, f_type, f_note in info["fields"]:
            field_id = f"col_{tbl_name}_{f_name}"
            prefix = "+ " if "PK" in f_note else ("# " if "FK" in f_note else "- ")
            field_text = f"{prefix}{f_name} : {f_type}"
            if f_note:
                field_text += f" [{f_note}]"
                
            row_style = (
                "text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
                "spacingLeft=6;spacingRight=6;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];"
                "portConstraint=eastwest;whiteSpace=wrap;html=1;fontColor=#f8fafc;fontSize=11;"
            )
            if "PK" in f_note:
                row_style += "fontStyle=1;fillColor=#1e293b;"
            elif "FK" in f_note:
                row_style += "fontStyle=2;fillColor=#0f172a;"
                
            xml_cells.append(
                f'<mxCell id="{field_id}" value="{escape(field_text)}" style="{row_style}" vertex="1" parent="{tbl_cell_id}">'
                f'<mxGeometry y="{row_y}" width="{col_width}" height="24" as="geometry" />'
                f'</mxCell>'
            )
            row_y += 24
            
        col_heights[col_idx] = cur_y + tbl_height + 40

    # Conectores Conceptuales con Cardinalidades en ambos extremos
    edge_counter = 0
    for rel in CONCEPTUAL_RELATIONS:
        if rel["cycle"] in active_cycles and rel["src"] in active_tables and rel["trg"] in active_tables:
            edge_counter += 1
            edge_id = f"edge_{rel['src']}_{rel['trg']}_{edge_counter}"
            source_id = f"tbl_{rel['src']}"
            target_id = f"tbl_{rel['trg']}"
            
            # Estilo ortogonal con simbología ER
            edge_style = (
                "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;"
                "html=1;strokeColor=#64748b;strokeWidth=1.5;endArrow=ERmany;startArrow=ERmandOne;"
                "fontSize=10;fontColor=#f8fafc;"
            )
            
            verb_str = escape(rel['verb'])
            src_card_str = escape(rel['src_card'])
            trg_card_str = escape(rel['trg_card'])
            
            # Celda principal de la arista con el verbo relacional en el centro
            xml_cells.append(
                f'<mxCell id="{edge_id}" value="{verb_str}" style="{edge_style}" edge="1" parent="1" source="{source_id}" target="{target_id}">'
                f'<mxGeometry relative="1" as="geometry" />'
                f'</mxCell>'
            )
            
            # Cardinalidad en el extremo ORIGEN (source)
            xml_cells.append(
                f'<mxCell id="{edge_id}_src" value="{src_card_str}" style="edgeLabel;html=1;align=left;verticalAlign=bottom;resizable=0;points=[];fontColor=#38bdf8;fontStyle=1;fontSize=11;" vertex="1" connectable="0" parent="{edge_id}">'
                f'<mxGeometry x="-0.75" relative="1" as="geometry"><mxPoint x="5" y="-12" as="offset" /></mxGeometry>'
                f'</mxCell>'
            )
            
            # Cardinalidad en el extremo DESTINO (target)
            xml_cells.append(
                f'<mxCell id="{edge_id}_trg" value="{trg_card_str}" style="edgeLabel;html=1;align=right;verticalAlign=bottom;resizable=0;points=[];fontColor=#f59e0b;fontStyle=1;fontSize=11;" vertex="1" connectable="0" parent="{edge_id}">'
                f'<mxGeometry x="0.75" relative="1" as="geometry"><mxPoint x="-5" y="-12" as="offset" /></mxGeometry>'
                f'</mxCell>'
            )

    inner_xml = "\n    ".join(xml_cells)
    
    diagram_xml = f"""  <diagram id="{diagram_id}" name="{escape(diagram_name)}">
    <mxGraphModel dx="2800" dy="2000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="3600" pageHeight="2800" math="0" shadow="0">
      <root>
        {inner_xml}
      </root>
    </mxGraphModel>
  </diagram>"""
    return diagram_xml

def generate_drawio_files(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Multi-page unified drawio
    p1 = build_drawio_page("page_c1", "Ciclo 1 - Núcleo Base (22 Tablas)", [1])
    p2 = build_drawio_page("page_c2", "Ciclo 2 - Comercio y Ventas (39 Tablas)", [1, 2])
    p3 = build_drawio_page("page_c3", "Ciclo 3 - Final Consolidado (50 Tablas)", [1, 2, 3])
    
    unified_content = f"""<mxfile host="Electron" modified="2026-09-20T12:00:00.000Z" agent="Antigravity-FashionStore" version="21.6.8" type="device">
{p1}
{p2}
{p3}
</mxfile>"""
    
    unified_path = os.path.join(output_dir, "diagrama_bd_fashionstore_ciclos.drawio")
    with open(unified_path, "w", encoding="utf-8") as f:
        f.write(unified_content)
    print(f"Generado archivo Draw.io multi-página: {unified_path}")

    # 2. Archivos individuales por ciclo
    for c_num, (c_name, c_cycles) in enumerate([
        ("Ciclo 1 - Núcleo Base", [1]),
        ("Ciclo 2 - Comercio y Ventas Acumulado", [1, 2]),
        ("Ciclo 3 - Consolidado Total", [1, 2, 3])
    ], start=1):
        page_xml = build_drawio_page(f"page_c{c_num}", c_name, c_cycles)
        single_content = f"""<mxfile host="Electron" modified="2026-09-20T12:00:00.000Z" agent="Antigravity-FashionStore" version="21.6.8" type="device">
{page_xml}
</mxfile>"""
        file_path = os.path.join(output_dir, f"diagrama_bd_ciclo{c_num}.drawio")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(single_content)
        print(f"Generado archivo Draw.io individual: {file_path}")

# =====================================================================
# GENERADOR SCRIPTS SQL
# =====================================================================

def generate_sql_scripts(scripts_dir):
    os.makedirs(scripts_dir, exist_ok=True)
    
    # Encabezado estándar
    header = """-- ============================================================================
-- PLATAFORMA DE COMERCIO ELECTRÓNICO PARA TIENDA DE ROPA (FASHIONSTORE)
-- Universidad Autónoma Gabriel René Moreno - Sistemas de Información II
-- Grupo #29 | Condori Diaz & Larrazabal Rojas
-- Docente: MSc. Ing. Angélica Garzón Cuéllar
-- ============================================================================
"""

    # 1. Ciclo 1 (22 tablas)
    c1_sql = header + "\n-- SCRIPT DDL: CICLO 1 (NÚCLEO BASE)\n-- Paquetes: Seguridad y Usuarios, Catálogo y Tiendas, Inventario y Proveedores (CPP)\n\n"
    for tbl_name, info in TABLES_DATA.items():
        if info["cycle"] == 1:
            c1_sql += f"-- Tabla: {tbl_name} ({info['package']})\n"
            c1_sql += info["sql_ddl"] + "\n\n"
            
    c1_path = os.path.join(scripts_dir, "01_script_bd_ciclo1.sql")
    with open(c1_path, "w", encoding="utf-8") as f:
        f.write(c1_sql)
    print(f"Generado script SQL: {c1_path}")

    # 2. Ciclo 2 Incremental (solo lo nuevo de C2: 17 tablas)
    c2_inc_sql = header + "\n-- SCRIPT DDL: CICLO 2 (INCREMENTAL SOBRE CICLO 1)\n-- Paquetes: Ventas y Pagos, Caja POS, Cotizaciones, Devoluciones, Cupones, Transferencias\n\n"
    for tbl_name, info in TABLES_DATA.items():
        if info["cycle"] == 2:
            c2_inc_sql += f"-- Tabla Nueva C2: {tbl_name} ({info['package']})\n"
            c2_inc_sql += info["sql_ddl"] + "\n\n"
            
    c2_inc_path = os.path.join(scripts_dir, "02_script_bd_ciclo2_incremental.sql")
    with open(c2_inc_path, "w", encoding="utf-8") as f:
        f.write(c2_inc_sql)
    print(f"Generado script SQL: {c2_inc_path}")

    # 3. Ciclo 2 Acumulado (C1 + C2: 39 tablas)
    c2_cum_sql = header + "\n-- SCRIPT DDL: CICLO 2 (ACUMULADO TOTAL CICLO 1 + CICLO 2)\n-- Contiene las 39 tablas operativas del núcleo transaccional y comercial\n\n"
    for tbl_name, info in TABLES_DATA.items():
        if info["cycle"] in [1, 2]:
            c2_cum_sql += f"-- Tabla: {tbl_name} (Ciclo {info['cycle']} - {info['package']})\n"
            c2_cum_sql += info["sql_ddl"] + "\n\n"
            
    c2_cum_path = os.path.join(scripts_dir, "02_script_bd_ciclo2_acumulado.sql")
    with open(c2_cum_path, "w", encoding="utf-8") as f:
        f.write(c2_cum_sql)
    print(f"Generado script SQL: {c2_cum_path}")

    # 4. Ciclo 3 Incremental (solo lo nuevo de C3: 11 tablas)
    c3_inc_sql = header + "\n-- SCRIPT DDL: CICLO 3 (INCREMENTAL SOBRE CICLO 2)\n-- Paquetes: Reservas y Citas, Envíos y Logística, Inteligente y Analítica, Notificaciones\n\n"
    for tbl_name, info in TABLES_DATA.items():
        if info["cycle"] == 3:
            c3_inc_sql += f"-- Tabla Nueva C3: {tbl_name} ({info['package']})\n"
            c3_inc_sql += info["sql_ddl"] + "\n\n"
            
    c3_inc_path = os.path.join(scripts_dir, "03_script_bd_ciclo3_incremental.sql")
    with open(c3_inc_path, "w", encoding="utf-8") as f:
        f.write(c3_inc_sql)
    print(f"Generado script SQL: {c3_inc_path}")

    # 5. Ciclo 3 Completo (Todas las 50 tablas del sistema FashionStore)
    c3_all_sql = header + "\n-- SCRIPT DDL: CICLO 3 (CONSOLIDADO FINAL COMPLETO - 100% TABLAS)\n-- Contiene las 50 tablas de los 8 paquetes de FashionStore para PostgreSQL / pgAdmin 4\n\n"
    for tbl_name, info in TABLES_DATA.items():
        c3_all_sql += f"-- Tabla: {tbl_name} (Ciclo {info['cycle']} - {info['package']})\n"
        c3_all_sql += info["sql_ddl"] + "\n\n"
        
    c3_all_path = os.path.join(scripts_dir, "03_script_bd_ciclo3_completo.sql")
    with open(c3_all_path, "w", encoding="utf-8") as f:
        f.write(c3_all_sql)
    print(f"Generado script SQL: {c3_all_path}")

# =====================================================================
# GENERADOR DOCUMENTO DE MAPEO Y EVOLUCIÓN (MARKDOWN)
# =====================================================================

def generate_mapping_markdown(output_path):
    md = """# Mapeo y Evolución de la Base de Datos por Ciclos (UML 2.5+ / PUDS)

**Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual (FashionStore)**  
**Grupo #29 — Sistemas de Información II (UAGRM - Semestre 2-2026)**  
**Integrantes:** Condori Diaz Marilyn Esther & Larrazabal Rojas Julio Cesar  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  

---

## 1. Resumen Ejecutivo de la Evolución de la Base de Datos

En el marco de trabajo del **Proceso Unificado de Desarrollo de Software (PUDS)**, la arquitectura de persistencia evoluciona de manera iterativa e incremental a lo largo de **tres ciclos de desarrollo**. La base de datos relacional en **PostgreSQL** refleja fielmente la maduración del sistema, pasando desde el núcleo fundacional de seguridad, catálogo e inventario valorado, hasta la consolidación transaccional omnicanal, logística e inteligencia artificial.

### Resumen Cuantitativo por Ciclo:
| Métrica Arquitectónica | Ciclo 1 (Fundacional) | Ciclo 2 (Comercial / Transaccional) | Ciclo 3 (Consolidado Final) |
| :--- | :---: | :---: | :---: |
| **Casos de Uso Cubiertos** | 15 CU (CU01-11, 14, 36, 37, 38) | 13 CU (CU12-24 + ampl. CU14) | 13 CU (CU25-35, 39, 40) |
| **Tablas Nuevas del Ciclo** | **22 tablas** | **17 tablas** | **11 tablas** |
| **Tablas Totales Acumuladas** | **22 tablas** | **39 tablas** | **50 tablas** |
| **Paquetes Lógicos Abordados** | 3 paquetes | 4 paquetes | **8 paquetes (100%)** |
| **Mecanismo de Valoración** | Costo Promedio Ponderado (CPP) | CPP en Transferencias y Devoluciones | CPP global en ventas de reservas |

---

## 2. Detalle de Tablas Incorporadas en Cada Ciclo

### 2.1 CICLO 1: Núcleo de Seguridad, Catálogo e Inventario Valorado (22 Tablas)
*Objetivo:* Proporcionar la infraestructura de usuarios, gestión multisucursal, catálogo jerárquico de prendas con variantes y fotografías, registro de compras a proveedores con **Costo Promedio Ponderado (CU37)**, auditoría rigurosa de mutaciones y libro mayor de inventario.

| # | Tabla | Paquete | Clase ORM (Backend) | Propósito y Regla de Negocio |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `roles` | `paquete_seguridad_usuarios` | `Role` | Catálogo de perfiles autorizados (`SUPERADMIN`, `ENCARGADO`, `CAJERO`, `CLIENTE`, etc.). |
| 2 | `users` | `paquete_seguridad_usuarios` | `User` | Credenciales cifradas con BCrypt, datos personales y estado de actividad. |
| 3 | `user_roles` | `paquete_seguridad_usuarios` | `user_roles` (Tabla N:N) | Asociación relacional muchos a muchos entre usuarios y roles. |
| 4 | `session_tokens` | `paquete_seguridad_usuarios` | `SessionToken` | Control de revocación y expiración de tokens JWT activos. |
| 5 | `audit_logs` | `paquete_seguridad_usuarios` | `AuditLog` | Bitácora inmutable con `JSONB` de valores previos y nuevos (`CU36`). |
| 6 | `branches` | `paquete_catalogo_y_tiendas` | `Branch` | Sucursales físicas con geolocalización (latitud, longitud) y estado. |
| 7 | `branch_employees` | `paquete_catalogo_y_tiendas` | `BranchEmployee` | Vinculación estricta de personal (`ENCARGADO`, `CAJERO`) a una sucursal única. |
| 8 | `categories` | `paquete_catalogo_y_tiendas` | `Category` | Categorías de prendas con URL de imagen circular para la tienda. |
| 9 | `seasons` | `paquete_catalogo_y_tiendas` | `Season` | Temporadas comerciales de moda con rango de fechas. |
| 10 | `collections` | `paquete_catalogo_y_tiendas` | `Collection` | Cápsulas de moda temáticas (`RF05 / RF23`). |
| 11 | `colors` | `paquete_catalogo_y_tiendas` | `Color` | Catálogo de colores con código hexadecimal normalizado. |
| 12 | `sizes` | `paquete_catalogo_y_tiendas` | `Size` | Tallas normalizadas (`S`, `M`, `L`, `XL`). |
| 13 | `products` | `paquete_catalogo_y_tiendas` | `Product` | Ficha técnica base, precio regular y precio tachado de oferta (`CU07`). |
| 14 | `product_variants` | `paquete_catalogo_y_tiendas` | `ProductVariant` | Combinación única Producto + Color + Talla con SKU único. |
| 15 | `product_images` | `paquete_catalogo_y_tiendas` | `ProductImage` | Galería fotográfica (2 a 5 fotos) asociada a producto y opcionalmente a color. |
| 16 | `product_reviews` | `paquete_catalogo_y_tiendas` | `ProductReview` | Calificación 1 a 5 estrellas y opinión (`CU14`, versión ligera). |
| 17 | `wishlist_items` | `paquete_catalogo_y_tiendas` | `WishlistItem` | Favoritos directos del cliente (versión ligera de Ciclo 1). |
| 18 | `suppliers` | `paquete_inventario_y_proveedores` | `Supplier` | Directorio de proveedores de indumentaria con NIT y datos de contacto. |
| 19 | `inventory` | `paquete_inventario_y_proveedores` | `Inventory` | Stock físico, stock reservado, en tránsito y **Costo Promedio Ponderado (`avg_cost`)**. |
| 20 | `inventory_ledger` | `paquete_inventario_y_proveedores` | `InventoryLedger` | Libro mayor valorado: registra cada movimiento físico con su costo unitario exacto. |
| 21 | `purchase_orders` | `paquete_inventario_y_proveedores` | `PurchaseOrder` | Cabecera de compra e ingreso de mercadería desde proveedor (`CU10`). |
| 22 | `purchase_details` | `paquete_inventario_y_proveedores` | `PurchaseDetail` | Detalle de variantes recibidas con el costo unitario de compra del lote. |

---

### 2.2 CICLO 2: Módulo Comercial, Ventas POS, Pagos y Facturación (+17 Tablas = 39 Tablas)
*Objetivo:* Habilitar la compra digital y física en caja: carrito de compras persistente, turnos de caja con arqueo ciego, checkout multicanal con herencia de medios de pago (`MedioDePago` ⭅ `Efectivo` / `Tarjeta` / `QR` / `PayPal`), facturación con IVA 13% y código de control, cotizaciones, devoluciones, cupones de descuento y transferencias de mercadería entre sucursales.

| # | Tabla | Paquete | Clase ORM (Backend) | Propósito y Regla de Negocio |
| :-: | :--- | :--- | :--- | :--- |
| 23 | `carts` | `paquete_ventas_y_pagos` | `Cart` | Carrito de compras web y móvil asociado a usuario o sesión anónima (`CU17`). |
| 24 | `cart_items` | `paquete_ventas_y_pagos` | `CartItem` | Ítems y cantidades seleccionadas en el carrito. |
| 25 | `cash_shifts` | `paquete_ventas_y_pagos` | `CashShift` | Sesión y turno de caja del cajero: apertura, monto esperado, arqueo y cierre (`CU23`). |
| 26 | `orders` | `paquete_ventas_y_pagos` | `Order` | Cabecera del pedido (`ONLINE` o `POS`), estado, montos y descuento (`CU18/19`). |
| 27 | `order_items` | `paquete_ventas_y_pagos` | `OrderItem` | Detalle de prendas vendidas con precio histórico congelado. |
| 28 | `payments` | `paquete_ventas_y_pagos` | `Payment` | Herencia de tabla única (STI): pagos en Efectivo, Tarjeta, QR o PayPal (`CU18`). |
| 29 | `invoices` | `paquete_ventas_y_pagos` | `Invoice` | Emisión legal de Factura (IVA 13%, código de control) o Nota de Entrega (`CU20`). |
| 30 | `quotations` | `paquete_ventas_y_pagos` | `Quotation` | Cotización formal con plazo de vigencia temporal (`CU21`). |
| 31 | `quotation_items` | `paquete_ventas_y_pagos` | `QuotationItem` | Detalle de prendas y precios garantizados en la cotización. |
| 32 | `order_returns` | `paquete_ventas_y_pagos` | `OrderReturn` | Devolución de dinero o cambio de prenda dentro del plazo legal de 30 días (`CU22`). |
| 33 | `order_return_items` | `paquete_ventas_y_pagos` | `OrderReturnItem` | Detalle de ítems devueltos y variante de reposición para cambios físicos. |
| 34 | `stock_transfers` | `paquete_inventario_y_proveedores` | `StockTransfer` | Transferencia entre sucursales: `SOLICITADA` $\\rightarrow$ `EN_TRANSITO` $\\rightarrow$ `COMPLETADA` (`CU15`). |
| 35 | `stock_transfer_details` | `paquete_inventario_y_proveedores` | `StockTransferDetail` | Detalle de variantes y cantidades despachadas entre tiendas. |
| 36 | `coupons` | `paquete_catalogo_y_tiendas` | `Coupon` | Cupones de descuento (porcentaje o monto fijo) con control de usos (`CU13`). |
| 37 | `seasonal_promotions` | `paquete_catalogo_y_tiendas` | `SeasonalPromotion` | Ofertas de temporada programadas por categoría (`CU13`). |
| 38 | `wishlists` | `paquete_catalogo_y_tiendas` | `Wishlist` | Listas de deseos múltiples y personalizadas con token para compartir (`CU14+`). |
| 39 | `wishlist_group_items` | `paquete_catalogo_y_tiendas` | `WishlistGroupItem` | Prendas contenidas en cada lista de deseos compartible. |

---

### 2.3 CICLO 3: Reservas Omnicanal, Envíos, Vestidor IA y Notificaciones (+11 Tablas = 50 Tablas)
*Objetivo:* Culminar el 100% de la visión del sistema: agendamiento de citas y reserva de prendas con seña previa (`CU26-28`), conversión de reserva a venta en POS (`CU25`), gestión de despachos a domicilio con repartidores y evidencia fotográfica (`CU29-31`), motor de inteligencia artificial para el vestidor virtual y chatbot (`CU32-34`), reportes analíticos y buzón de notificaciones push (`CU40`).

| # | Tabla | Paquete | Clase ORM (Backend) | Propósito y Regla de Negocio |
| :-: | :--- | :--- | :--- | :--- |
| 40 | `reservations` | `paquete_reservas_y_citas` | `Reservation` | Cita en probador físico con seña del 50%, código `RES-...` y bloqueo temporal de stock (`CU26`). |
| 41 | `reservation_items` | `paquete_reservas_y_citas` | `ReservationItem` | Prendas apartadas físicamente para la sesión de prueba (hasta 5 prendas). |
| 42 | `delivery_zones` | `paquete_envios_y_logistica` | `DeliveryZone` | Zonificación por kilometraje (anillos) y cálculo tarifario dinámico (`CU31`). |
| 43 | `delivery_persons` | `paquete_envios_y_logistica` | `DeliveryPerson` | Perfil del repartidor: vehículo, placa, zona asignada, calificación y disponibilidad (`CU29`). |
| 44 | `shipments` | `paquete_envios_y_logistica` | `Shipment` | Despacho del pedido, código de rastreo `TRK-...`, intentos y foto de entrega (`CU29/30`). |
| 45 | `shipment_tracking_events`| `paquete_envios_y_logistica` | `ShipmentTrackingEvent` | Hitos cronológicos del envío (`EN_CAMINO`, `LLEGUE`, `ENTREGADO`) con foto de evidencia. |
| 46 | `virtual_tryon_sessions` | `paquete_inteligente_y_analitica` | `VirtualTryonSession` | Registro de sesiones de prueba virtual en web o app móvil (`CU32`). |
| 47 | `virtual_tryon_items` | `paquete_inteligente_y_analitica` | `VirtualTryonItem` | Prendas simuladas en el probador con retroalimentación del calce. |
| 48 | `virtual_tryon_captures`| `paquete_inteligente_y_analitica` | `VirtualTryonCapture` | Foto generada por IA, modelo empleado (`FASHN`/`IDM-VTON`/`LOCAL`) y medidas antropométricas. |
| 49 | `chatbot_conversations` | `paquete_inteligente_y_analitica` | `ChatbotConversation` | Mensajes e intenciones detectadas (NLP) en el asistente de recomendación (`CU33`). |
| 50 | `in_app_notifications` | `paquete_notificaciones` | `InAppNotification` | Notificaciones transaccionales in-app leídas/no leídas para el cliente y personal (`CU40`). |

---

## 3. Matriz de Mapeo: Casos de Uso $\\leftrightarrow$ Entidades Relacionales

Esta matriz garantiza la **trazabilidad bidireccional** entre los requerimientos funcionales y las tablas de base de datos:

```mermaid
graph LR
    subgraph Requisitos [40 Casos de Uso Master]
        CU_Seg[CU01-05, CU36: Seguridad]
        CU_Cat[CU06-07, CU09, CU11-14: Catálogo]
        CU_Inv[CU08, CU10, CU15-16, CU37-38: Inventario y Costos]
        CU_Ven[CU17-25: Ventas, Caja y Pagos]
        CU_Res[CU26-28: Reservas en Tienda]
        CU_Env[CU29-31: Envíos y Logística]
        CU_IA[CU32-35, CU39: IA y BI]
        CU_Not[CU40: Notificaciones]
    end

    subgraph BaseDeDatos [50 Tablas PostgreSQL]
        DB_Seg[(users, roles, user_roles, session_tokens, audit_logs)]
        DB_Cat[(branches, categories, seasons, collections, products, variants, images, reviews, wishlists)]
        DB_Inv[(suppliers, inventory, inventory_ledger, purchase_orders, details, transfers)]
        DB_Ven[(carts, cash_shifts, orders, order_items, payments, invoices, quotations, returns)]
        DB_Res[(reservations, reservation_items)]
        DB_Env[(delivery_zones, delivery_persons, shipments, tracking_events)]
        DB_IA[(virtual_tryon_sessions, items, captures, chatbot_conversations)]
        DB_Not[(in_app_notifications)]
    end

    CU_Seg --> DB_Seg
    CU_Cat --> DB_Cat
    CU_Inv --> DB_Inv
    CU_Ven --> DB_Ven
    CU_Res --> DB_Res
    CU_Env --> DB_Env
    CU_IA --> DB_IA
    CU_Not --> DB_Not
```

---

## 4. Catálogo Exhaustivo de Relaciones Conceptuales y Cardinalidades

A continuación se detalla la semántica relacional modelada en los diagramas conceptuales de **Draw.io**, especificando la cardinalidad en origen y destino para cada ciclo:

| Ciclo | Entidad Origen | Cardinalidad Origen | Verbo / Semántica Relacional | Cardinalidad Destino | Entidad Destino |
| :---: | :--- | :---: | :---: | :---: | :--- |
"""
    for rel in CONCEPTUAL_RELATIONS:
        md += f"| **C{rel['cycle']}** | `{rel['src']}` | **{rel['src_card']}** | *{rel['verb']}* | **{rel['trg_card']}** | `{rel['trg']}` |\n"
        
    md += """
---

## 5. Normalización y Reglas de Negocio Clave

1. **Cumplimiento Estricto de 3FN**:
   - **1FN**: Atomicidad total. No existen arreglos ni cadenas compuestas en las prendas; las variantes residen en `product_variants` normalizadas por `colors` y `sizes`.
   - **2FN**: Toda clave no primaria depende por completo de la clave primaria. El stock no se guarda en el catálogo base sino en la tabla intermedia `inventory(branch_id, variant_id)`.
   - **3FN**: Cero dependencias transitivas. Las calificaciones promedio no se almacenan en `products` para evitar desincronizaciones, calculándose dinámicamente sobre `product_reviews`.
2. **Costo Promedio Ponderado (CPP - CU10, CU15, CU37)**:
   - Al registrar una orden de compra o completar una transferencia entrante, el costo unitario de inventario se recalcula matemáticamente:
     $$\\text{CPP}_{nuevo} = \\frac{(Stock_{actual} \\cdot \\text{CPP}_{anterior}) + (Q_{ingreso} \\cdot Costo_{compra})}{Stock_{actual} + Q_{ingreso}}$$
   - Las salidas (ventas o reservas) nunca alteran el CPP, sino que se valoran al CPP vigente y lo congelan en el `inventory_ledger`.
3. **Bloqueo Concurrente y Transacciones ACID**:
   - Para prevenir sobreventa (*race conditions*) en checkouts y reservas concurrentes, el backend ejecuta bloqueo pesimista en PostgreSQL mediante `SELECT ... FOR UPDATE` sobre la fila correspondiente de la tabla `inventory`.

---

## 5. Instrucciones para Visualizar los Diagramas en Draw.io

Para abrir y visualizar los diagramas generados:
1. Ingrese a **[app.diagrams.net](https://app.diagrams.net)** (o use la extensión Draw.io en VS Code / Antigravity).
2. Seleccione **Archivo** $\\rightarrow$ **Abrir desde** $\\rightarrow$ **Dispositivo**.
3. Seleccione cualquiera de los siguientes archivos generados en la raíz del proyecto:
   - `diagrama_bd_fashionstore_ciclos.drawio`: **Recomendado**. Contiene 3 pestañas inferiores que permiten cambiar dinámicamente entre Ciclo 1, Ciclo 2 y Ciclo 3.
   - `diagrama_bd_ciclo1.drawio`: Visualización exclusiva de las 22 tablas del Ciclo 1.
   - `diagrama_bd_ciclo2.drawio`: Visualización de las 39 tablas acumuladas de Ciclos 1 y 2.
   - `diagrama_bd_ciclo3.drawio`: Visualización completa de las 50 tablas finales del Ciclo 3.
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generado documento de mapeo Markdown: {output_path}")

# =====================================================================
# EJECUCIÓN PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(base_dir, "database", "scripts_sql")
    
    print("Iniciando generación de artefactos...")
    generate_drawio_files(base_dir)
    generate_sql_scripts(scripts_dir)
    
    # También colocamos una copia de los scripts en la raíz para máxima comodidad
    generate_sql_scripts(os.path.join(base_dir, "scripts_sql"))
    
    mapping_path = os.path.join(base_dir, "MAPEO_BASE_DE_DATOS_POR_CICLOS.md")
    generate_mapping_markdown(mapping_path)
    print("¡Todos los artefactos han sido generados exitosamente!")
