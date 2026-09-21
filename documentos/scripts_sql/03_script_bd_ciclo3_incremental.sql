-- ============================================================================
-- PLATAFORMA DE COMERCIO ELECTRÓNICO PARA TIENDA DE ROPA (FASHIONSTORE)
-- Universidad Autónoma Gabriel René Moreno - Sistemas de Información II
-- Grupo #29 | Condori Diaz & Larrazabal Rojas
-- Docente: MSc. Ing. Angélica Garzón Cuéllar
-- ============================================================================

-- SCRIPT DDL: CICLO 3 (INCREMENTAL SOBRE CICLO 2)
-- Paquetes: Reservas y Citas, Envíos y Logística, Inteligente y Analítica, Notificaciones

-- Tabla Nueva C3: reservations (paquete_reservas_y_citas)
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

-- Tabla Nueva C3: reservation_items (paquete_reservas_y_citas)
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

-- Tabla Nueva C3: delivery_zones (paquete_envios_y_logistica)
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

-- Tabla Nueva C3: delivery_persons (paquete_envios_y_logistica)
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

-- Tabla Nueva C3: shipments (paquete_envios_y_logistica)
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

-- Tabla Nueva C3: shipment_tracking_events (paquete_envios_y_logistica)
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

-- Tabla Nueva C3: virtual_tryon_sessions (paquete_inteligente_y_analitica)
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

-- Tabla Nueva C3: virtual_tryon_items (paquete_inteligente_y_analitica)
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

-- Tabla Nueva C3: virtual_tryon_captures (paquete_inteligente_y_analitica)
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

-- Tabla Nueva C3: chatbot_conversations (paquete_inteligente_y_analitica)
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

-- Tabla Nueva C3: in_app_notifications (paquete_notificaciones)
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

