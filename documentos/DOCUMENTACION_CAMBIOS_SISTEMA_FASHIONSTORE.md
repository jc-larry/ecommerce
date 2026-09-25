# Documentación Técnica de Cambios Aplicados — FashionStore

**Grupo #29 — Sistemas de Información II (UAGRM - Semestre 2-2026)**  
**Proyecto:** Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual (RA)  
**Fecha:** 19 de Septiembre de 2026  
**Autores:** Condori Diaz & Larrazabal Rojas  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  

---

## 1. Resumen Ejecutivo

En cumplimiento estricto con los requerimientos planteados para el primer parcial y las observaciones de la auditoría de ingeniería de software, se ha efectuado una actualización integral en las tres capas del sistema (Backend FastAPI, Frontend Web Angular y Base de Datos PostgreSQL), orientada a:

1. **Purificación de la Estructura de Paquetes**: Garantizar que tanto en el código fuente (Backend, Web y Móvil) como en la documentación del sistema existan **única y exclusivamente los 8 paquetes lógicos del diseño UML**.
2. **Visualización Gráfica Interactiva en la Bitácora de Auditoría (CU36)**: Incorporación de 4 tarjetas KPI y 3 gráficas analíticas interactivas para análisis de accesos y mutaciones de datos.
3. **Reporte de Demanda Histórica y Decisión de Reposición por Prenda (CU35)**: Nuevo módulo analítico para evaluar la curva de ventas de cualquier prenda a lo largo del tiempo, calcular su velocidad de rotación y generar un dictamen gerencial cuantitativo de reorden a proveedores.
4. **Subsanación de Reglas de Negocio y Auditoría**:
   - Corrección matemática del Costo Promedio Ponderado (CPP) al completar transferencias inter-sucursal.
   - Incorporación de bloqueo pesimista (`with_for_update()`) en checkouts y reservas para evitar condiciones de carrera.
   - Segregación formal de estados de stock (`stock_reservado` y `stock_en_transito`).
   - Adición del modelo de entidad `Collection` (Colecciones de moda) en cumplimiento de RF05 / RF23.

---

## 2. Normalización de Paquetes (Alineación con `PaquetesUML.md`)

### 2.1 Los 8 Paquetes Oficiales del Sistema

De acuerdo a la especificación oficial del documento del proyecto (*Proyecto Sistemas de Información II 1° Parcial Grupo 29.pdf*, Cap. 2.1.1, Págs. 56–58) y `PaquetesUML.md`, el sistema se organiza en exactamente los siguientes 8 subsistemas cohesivos con prefijo explícito `paquete_`:

```
├── 1. paquete_seguridad_usuarios       (CU01–CU05, CU36) [Paquete_Seguridad_Usuarios]
├── 2. paquete_catalogo_y_tiendas         (CU06, CU07, CU09, CU11–CU14) [Paquete_Catálogo_Y_Tiendas]
├── 3. paquete_inventario_y_proveedores   (CU08, CU10, CU15, CU16, CU37, CU38) [Paquete_Inventario_Y_Proveedores]
├── 4. paquete_ventas_y_pagos             (CU17–CU25) [Paquete_Ventas_Y_Pagos]
├── 5. paquete_reservas_y_citas           (CU26–CU28) [Paquete_Reservas_Y_Citas]
├── 6. paquete_envios_y_logistica         (CU29–CU31) [Paquete_Envíos_Y_Logística]
├── 7. paquete_inteligente_y_analitica    (CU32–CU35, CU39) [Paquete_Inteligente_Y_Analítica]
└── 8. paquete_notificaciones             (CU40) [Paquete_Notificaciones]
```

### 2.2 Acciones de Reestructuración Ejecutadas

- **Normalización Estricta 1:1 con la Documentación**:
  - Se ajustó `seguridad_y_usuarios` a `paquete_seguridad_usuarios` eliminando la conjunción "y" intermedia para calzar con el nombre oficial del documento (`Paquete_Seguridad_Usuarios`).
  - Se adoptó el prefijo exacto `paquete_*` en todos los subsistemas en Backend, Frontend Web y Móvil Flutter.
- **Frontend Web (`frontend-web/src/app/packages/`)**:
  - Todas las 8 carpetas siguen la nomenclatura `paquete_*`.
  - Se actualizaron las 44 referencias relativas e importaciones de componentes y servicios. Compilación verificada con `ng build` (código 0).
- **App Móvil Flutter (`mobile/lib/src/packages/`)**:
  - Se renombraron las 8 carpetas a `paquete_*`.
  - Se actualizaron las 27 referencias e importaciones en los archivos `.dart` correspondientes.
- **Backend FastAPI (`backend/app/packages/`)**:
  - Preserva la arquitectura 1:1 con los 8 sub-paquetes Python `paquete_*`.
  - Se actualizaron todos los modelos, routers y tests unitarios. Pruebas de pytest pasando con 100% de éxito.

---

## 3. Bitácora de Auditoría con Visualizaciones Gráficas (CU36)

### 3.1 Ubicación
- **Frontend**: `frontend-web/src/app/packages/seguridad_y_usuarios/audit/`
- **Ruta**: `/admin/audit`
- **Backend**: `GET /api/v1/audit/logs`

### 3.2 Nuevos Componentes Visuales

1. **4 Tarjetas KPI Ejecutivas**:
   - **Total Eventos**: Recuento consolidado de transacciones auditadas.
   - **Seguridad & Accesos**: Eventos de autenticación (`LOGIN`, `LOGOUT`).
   - **Mutaciones DB**: Operaciones sobre registros (`INSERT`, `UPDATE`, `DELETE`).
   - **Operadores Activos**: Total de usuarios únicos con actividad registrada.
2. **Gráfica 1: Distribución por Tipo de Acción**:
   - Barras horizontales proporcionales con porcentaje, conteo, icono temático y código de color según severidad.
   - **Filtro al Clic**: Al pulsar sobre cualquier acción (ej: `DELETE`), la tabla de auditoría se filtra automáticamente.
3. **Gráfica 2: Top Módulos Afectados**:
   - Representación porcentual de las tablas más modificadas (`users`, `orders`, `inventory`, `products`, `branches`, etc.).
4. **Gráfica 3: Actividad Cronológica Reciente**:
   - Gráfico de barras temporales agrupado por fecha para detectar picos de actividad o accesos anómalos.
5. **Barra de Filtros Activos**:
   - Indicadores tipo píldora de los filtros aplicados con enlace de reseteo rápido.

---

## 4. Reporte de Demanda por Prenda y Decisión de Reposición (CU35)

### 4.1 Objetivo de Negocio
Permitir a la gerencia de Casa Matriz seleccionar cualquier prenda del catálogo, evaluar su curva de ventas histórica a lo largo del tiempo (3, 6 o 12 meses) y determinar con base en métricas objetivas **si conviene o es urgente realizar pedidos de reposición a proveedores**, así como la cantidad sugerida de unidades.

### 4.2 Especificación del Endpoint Backend

- **Ruta**: `GET /api/v1/analytics/reports/product-sales-trend`
- **Parámetros**:
  - `product_id` (int, requerido): ID de la prenda a analizar.
  - `months` (int, opcional, defecto 6): Ventana temporal hacia atrás.
- **Lógica Matemática**:
  - **Unidades Vendidas e Ingresos**: Suma agregada sobre `OrderItem` en órdenes `PAGADA`.
  - **Velocidad Semanal**:
    $$\text{Velocidad} = \frac{\text{Unidades Vendidas Totales}}{\text{Meses} \times 4.33}$$
  - **Días de Cobertura de Stock**:
    $$\text{Días de Stock} = \frac{\text{Stock Total en Sucursales}}{\text{Velocidad Semanal} / 7}$$
  - **Algoritmo de Dictamen Gerencial**:
    - **`URGENTE_REORDENAR`** ($\le 10$ días de cobertura con ventas activas): Semáforo Rojo.
    - **`CONVIENE_PEDIR`** ($11 - 25$ días de cobertura): Semáforo Amarillo.
    - **`STOCK_ADECUADO`** ($26 - 60$ días de cobertura): Semáforo Verde.
    - **`BAJA_ROTACION`** ($> 60$ días de cobertura o sin ventas): Semáforo Azul/Gris.
  - **Lote Sugerido de Reposición**:
    $$\text{Lote Sugerido} = \max(10, \lceil (\text{Velocidad Semanal} \times 4.33) - \text{Stock Actual} \rceil)$$

### 4.3 Vista Frontend Web (`/admin/reports` → Pestaña "Demanda y Pedidos por Prenda")
- Selector desplegable de prendas con buscador de texto en tiempo real.
- Botonera para conmutar rango (3 meses, 6 meses, 1 año).
- **Banner Ejecutivo de Semáforo**: Alerta de alto impacto con recomendación y lote sugerido.
- **4 Tarjetas KPI**: Stock Actual en Tiendas, Unidades Vendidas, Velocidad Semanal y Días de Cobertura.
- **Gráfica de Barras Cronológicas**: Comportamiento semanal/mensual con alturas proporcionales.
- **Existencias por Sucursal**: Cuadro de existencias en cada punto físico.
- **Tabla de Variantes (Talla y Color)**: Desglose por SKU con existencias, ventas y badge de acción recomendada (`Reponer`, `Bajo`, `OK`).

---

## 5. Subsanaciones de Negocio, Inventarios y Base de Datos

### 5.1 Recálculo de Costo Promedio Ponderado en Transferencias
- **Archivo**: `backend/app/packages/inventario_y_proveedores/merchandise/routers.py`
- **Corrección**: Al completar una transferencia inter-sucursal (`status == 'COMPLETADA'`), si la sucursal de destino ya tenía existencias, se recalcula el costo promedio ponderado en vez de únicamente sumar el stock escalar:
  ```python
  prev_stock = dest_inv.stock_actual
  prev_cost = float(dest_inv.avg_cost or 0.0)
  new_stock = prev_stock + d.quantity
  if new_stock > 0:
      dest_inv.avg_cost = round(((prev_stock * prev_cost) + (d.quantity * unit_cost)) / new_stock, 2)
  dest_inv.stock_actual = new_stock
  ```

### 5.2 Bloqueo Pesimista en Concurrencia Transaccional
- **Archivos**:
  - `backend/app/packages/ventas_y_pagos/routers.py` (Líneas 365, 417, 1095)
  - `backend/app/packages/reservas_y_citas/routers.py` (Línea 254)
- **Corrección**: Se incorporó `.with_for_update()` en las consultas de `Inventory` durante el checkout, la conversión de cotizaciones y la creación de reservas de probador. Esto bloquea a nivel de fila en PostgreSQL para evitar carreras que resulten en sobreventa o stock negativo.

### 5.3 Segregación de Estados de Stock
- **Archivo**: `backend/app/packages/inventario_y_proveedores/merchandise/models.py`
- **Campos incorporados**:
  - `stock_reservado`: Prendas apartadas para citas físicas de vestidor (CU26).
  - `stock_en_transito`: Mercadería en tránsito entre sucursales.
- **Migración registrada en `main.py`**:
  ```sql
  ALTER TABLE inventory ADD COLUMN IF NOT EXISTS stock_reservado INT NOT NULL DEFAULT 0;
  ALTER TABLE inventory ADD COLUMN IF NOT EXISTS stock_en_transito INT NOT NULL DEFAULT 0;
  ```

### 5.4 Modelo `Collection` (Colecciones y Cápsulas de Moda)
- **Archivo**: `backend/app/packages/catalogo_y_tiendas/models.py`
- **Requisito Cátedra**: RF05 / RF23 ("temporadas y colecciones").
- **Estructura**:
  ```python
  class Collection(Base):
      __tablename__ = "collections"
      id: Mapped[int] = mapped_column(primary_key=True)
      name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
      description: Mapped[Optional[str]] = mapped_column(String(255))
      season_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True)
      is_active: Mapped[bool] = mapped_column(Boolean, default=True)
      banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
  ```
- **Relación**: `Product.collection_id` vinculado con `ON DELETE SET NULL`.
- **Migración registrada en `main.py`**:
  ```sql
  ALTER TABLE products ADD COLUMN IF NOT EXISTS collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL;
  ```

---

## 6. Validación Técnica y Compilación

| Capa / Módulo | Comando de Validación | Resultado |
|:---|:---|:---:|
| **Backend (Python)** | `python -m py_compile backend/app/main.py ...` | **Exitoso (Code 0)** |
| **Frontend Web (Angular)** | `npx ng build --configuration development` | **Exitoso (Code 0)** |
| **Trazabilidad de Paquetes** | Inspección de `backend/`, `frontend-web/` y `mobile/` | **8 paquetes exactos en todas las capas** |

---

## 7. Conclusión

Con estas adecuaciones, la plataforma **FashionStore** perfecciona su correspondencia arquitectónica con el diseño UML, enriquece sustancialmente la experiencia analítica para la toma de decisiones de inventario y compras, y eleva la robustez contable y transaccional del sistema a los estándares más exigentes de la cátedra de Sistemas de Información II.


---

## 8. Revisión Septiembre 2026: Refinamiento de Reglas de Negocio en Ventas (CU18) y Cambios/Devoluciones (CU22)

En atención a los requerimientos operacionales y de experiencia del cliente del negocio de retail de moda, se implementaron reglas de negocio críticas en los paquetes paquete_ventas_y_pagos e paquete_inventario_y_proveedores:

### 8.1. CU22 (Cambios y Devoluciones):
1. **Garantía Estricta de 14 Días (2 Semanas):**
   - El plazo reglamentario máximo para cualquier cambio o devolución se fijó en exactamente **14 días calendario** a partir de la fecha de emisión de la orden de compra (created_at).
   - Si delta_dias > 14, el sistema deniega el trámite con código HTTP 400 Bad Request y advertencia explicativa.
2. **Búsqueda por Código de Factura:**
   - Se habilitó el endpoint GET /api/v1/sales/invoices/by-code/{invoice_code} para que el cajero o encargado busque la compra ingresando el número de factura o código de control fiscal, desplegando el desglose de prendas compradas, precios unitarios y el indicador booleano warranty_valid (delta_dias <= 14).
3. **Subflujos de Cambio por Talla vs. Cambio por Modelo:**
   - **Cambio por Talla (CAMBIO_TALLA):** El cliente cambia la prenda por el mismo modelo en otra talla disponible. No genera diferencia de costo (diferencia = Bs. 0.00). Se reingresa la talla devuelta al stock de la sucursal y se descuenta la nueva talla.
   - **Cambio por Modelo (CAMBIO_MODELO):**
     * *Nuevo modelo más costoso:* Se calcula la diferencia a favor de la tienda (precio_nuevo - precio_antiguo) y se exige su cobro en caja antes de entregar la prenda.
     * *Nuevo modelo más económico:* Por política financiera de tienda, no se realiza devolución en efectivo; el sistema genera automáticamente una **Nota de Crédito** (CreditNote, código correlativo NC-2026-XXXX) por el saldo a favor para que el cliente lo descuente en su próxima compra.
   - **Devolución Definitiva (DEVOLUCION_DINERO / DEVOLUCION_NOTA_CREDITO):** Se reingresa el stock a la sucursal y se emite la Nota de Crédito o comprobante de caja correspondiente.

### 8.2. CU18 (Checkout Omnicanal con Timeout de Pasarela y Custodia 48h):
1. **Modalidad de Entrega con Custodia Máxima de 48 Horas:**
   - Si el comprador elige **Retiro en Sucursal** (RETIRO_TIENDA), el costo de envío es Bs. 0.00 y se calcula un plazo límite de retiro: pickup_deadline = created_at + 48 horas.
   - Si el cliente no retira la prenda en 48 horas, se ejecuta el proceso de expiración: la prenda retorna a inventario para exhibición y venta, y se emite una Nota de Crédito para no acumular paquetes en el mostrador.
2. **Pasarela de Pago con Timeout Estricto de 5 Minutos (300 segundos):**
   - Al iniciar la sesión de pago digital, la orden se registra en estado PENDIENTE_PAGO con payment_session_expires_at = created_at + 5 minutos y las prendas quedan bloqueadas preventivamente.
   - Si no se recibe la confirmación de la pasarela dentro de los 300 segundos, la orden pasa a CANCELADA_TIMEOUT, el stock bloqueado se libera de inmediato devolviendo la disponibilidad de la prenda a la tienda, y el sistema despacha una notificación push urgente al comprador notificándole que el tiempo expiró y no se le cobró nada.

### 8.3. Entidades y Esquemas Incorporados:
- **CreditNote (credit_notes):** id, credit_note_code, user_id, order_id, 
eturn_id, mount, status, 
eason, created_at, expires_at.
- **Columnas añadidas a orders:** delivery_type, pickup_deadline, payment_session_expires_at.
- **Nuevos endpoints:**
  * GET /api/v1/sales/invoices/by-code/{invoice_code}: Búsqueda de factura, evaluación de 14 días y desglose de prendas.
  * POST /api/v1/sales/orders/{id}/check-payment-timeout: Verificación y cancelación por timeout de 5 minutos con liberación de prendas.
  * POST /api/v1/sales/orders/{id}/expire-uncollected-pickup: Expiración de custodia de 48 horas con reingreso a stock y Nota de Crédito.
  * GET /api/v1/sales/credit-notes/my-credit-notes: Consulta de notas de crédito vigentes del cliente.
