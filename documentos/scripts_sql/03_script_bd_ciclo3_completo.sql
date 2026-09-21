-- ============================================================================
-- PLATAFORMA DE COMERCIO ELECTRÓNICO PARA TIENDA DE ROPA (FASHIONSTORE)
-- Universidad Autónoma Gabriel René Moreno - Sistemas de Información II
-- Grupo #29 | Condori Diaz & Larrazabal Rojas
-- Docente: MSc. Ing. Angélica Garzón Cuéllar
-- ============================================================================

-- SCRIPT DDL: CICLO 3 (CONSOLIDADO FINAL COMPLETO - 100% TABLAS)
-- Contiene las 50 tablas de los 8 paquetes de FashionStore para PostgreSQL / pgAdmin 4

-- Tabla: roles (Ciclo 1 - paquete_seguridad_usuarios)
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

-- Tabla: users (Ciclo 1 - paquete_seguridad_usuarios)
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

-- Tabla: user_roles (Ciclo 1 - paquete_seguridad_usuarios)
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Tabla: session_tokens (Ciclo 1 - paquete_seguridad_usuarios)
CREATE TABLE session_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla: audit_logs (Ciclo 1 - paquete_seguridad_usuarios)
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

-- Tabla: branches (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- Tabla: branch_employees (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE branch_employees (
    branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (branch_id, user_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla: categories (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    image_url VARCHAR(500)
);

-- Tabla: seasons (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

-- Tabla: collections (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    season_id INTEGER REFERENCES seasons(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    banner_url VARCHAR(500)
);

-- Tabla: colors (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE colors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    hex_code VARCHAR(7) UNIQUE NOT NULL
);

-- Tabla: sizes (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE sizes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) UNIQUE NOT NULL
);

-- Tabla: products (Ciclo 1 - paquete_catalogo_y_tiendas)
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

-- Tabla: product_variants (Ciclo 1 - paquete_catalogo_y_tiendas)
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

-- Tabla: product_images (Ciclo 1 - paquete_catalogo_y_tiendas)
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

-- Tabla: product_reviews (Ciclo 1 - paquete_catalogo_y_tiendas)
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

-- Tabla: wishlist_items (Ciclo 1 - paquete_catalogo_y_tiendas)
CREATE TABLE wishlist_items (
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX idx_wishlist_user ON wishlist_items(user_id);

-- Tabla: suppliers (Ciclo 1 - paquete_inventario_y_proveedores)
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    nit VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    address VARCHAR(255)
);

-- Tabla: inventory (Ciclo 1 - paquete_inventario_y_proveedores)
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

-- Tabla: inventory_ledger (Ciclo 1 - paquete_inventario_y_proveedores)
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

-- Tabla: purchase_orders (Ciclo 1 - paquete_inventario_y_proveedores)
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'COMPLETADO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);

-- Tabla: purchase_details (Ciclo 1 - paquete_inventario_y_proveedores)
CREATE TABLE purchase_details (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);

-- Tabla: carts (Ciclo 2 - paquete_ventas_y_pagos)
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(80),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla: cart_items (Ciclo 2 - paquete_ventas_y_pagos)
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);

-- Tabla: cash_shifts (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: orders (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: order_items (Ciclo 2 - paquete_ventas_y_pagos)
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);

-- Tabla: payments (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: invoices (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: quotations (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: quotation_items (Ciclo 2 - paquete_ventas_y_pagos)
CREATE TABLE quotation_items (
    id SERIAL PRIMARY KEY,
    quotation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);

-- Tabla: order_returns (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: order_return_items (Ciclo 2 - paquete_ventas_y_pagos)
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

-- Tabla: stock_transfers (Ciclo 2 - paquete_inventario_y_proveedores)
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

-- Tabla: stock_transfer_details (Ciclo 2 - paquete_inventario_y_proveedores)
CREATE TABLE stock_transfer_details (
    id SERIAL PRIMARY KEY,
    transfer_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (transfer_id) REFERENCES stock_transfers(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);

-- Tabla: coupons (Ciclo 2 - paquete_catalogo_y_tiendas)
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

-- Tabla: seasonal_promotions (Ciclo 2 - paquete_catalogo_y_tiendas)
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

-- Tabla: wishlists (Ciclo 2 - paquete_catalogo_y_tiendas)
CREATE TABLE wishlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla: wishlist_group_items (Ciclo 2 - paquete_catalogo_y_tiendas)
CREATE TABLE wishlist_group_items (
    id SERIAL PRIMARY KEY,
    wishlist_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT uq_wishlist_group_product UNIQUE (wishlist_id, product_id),
    FOREIGN KEY (wishlist_id) REFERENCES wishlists(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Tabla: reservations (Ciclo 3 - paquete_reservas_y_citas)
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

-- Tabla: reservation_items (Ciclo 3 - paquete_reservas_y_citas)
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

-- Tabla: delivery_zones (Ciclo 3 - paquete_envios_y_logistica)
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

-- Tabla: delivery_persons (Ciclo 3 - paquete_envios_y_logistica)
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

-- Tabla: shipments (Ciclo 3 - paquete_envios_y_logistica)
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

-- Tabla: shipment_tracking_events (Ciclo 3 - paquete_envios_y_logistica)
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

-- Tabla: virtual_tryon_sessions (Ciclo 3 - paquete_inteligente_y_analitica)
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

-- Tabla: virtual_tryon_items (Ciclo 3 - paquete_inteligente_y_analitica)
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

-- Tabla: virtual_tryon_captures (Ciclo 3 - paquete_inteligente_y_analitica)
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

-- Tabla: chatbot_conversations (Ciclo 3 - paquete_inteligente_y_analitica)
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

-- Tabla: in_app_notifications (Ciclo 3 - paquete_notificaciones)
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

