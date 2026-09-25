# Documentación del Ciclo 2 — Plataforma FashionStore

**Proceso Unificado de Desarrollo de Software (PUDS) + UML 2.5+** · Grupo #29 · Sistemas de Información II

Especificación del **Ciclo 2** tal como está **implementada** en el repositorio: captura de
requisitos, análisis, diseño, datos, implementación y pruebas. Todas las rutas, tablas, estados y
reglas se verificaron contra el código (`backend/app/packages`, `frontend-web`, `mobile`).

**Documentos relacionados:** `Contexto.md` (40 CU), `Ciclo1.md`, `Ciclo3.md`, `BaseDeDatos.md`,
`PaquetesUML.md`.

---

## Índice

- **0. Resumen del Ciclo 2** — alcance, paquetes, alcance por canal, reglas de personal por sucursal
- **1. Captura de Requisitos** — actores, priorización, fichas CU12–CU24 (con la **pasarela PayPal**), modelo de CU
- **2. Análisis** — arquitectura de paquetes, diagramas de comunicación, clases de análisis
- **3. Diseño** — arquitectura, diagramas de secuencia, máquinas de estado
- **4. Diseño de datos** — DDL real
- **5. Implementación** — endpoints, componentes web y pantallas móviles
- **6. Pruebas**
- **7. Trazabilidad**

---

## 0. Resumen del Ciclo 2

### 0.1 Alcance

El Ciclo 2 cubre **13 casos de uso**: **CU12, CU13, CU14+ (ampliación), CU15, CU16, CU17, CU18,
CU19, CU20, CU21, CU22, CU23 y CU24** — el núcleo comercial:

1. **Comercio digital:** búsqueda facetada con stock por sucursal, carrito con control de
   existencias, checkout con **Tarjeta, QR o PayPal real**, cupones, historial de compras.
2. **Tienda física:** POS en caja con turno obligatorio, alistado y entrega de pedidos online de la
   sucursal, arqueo de caja con desglose por medio de pago y origen.
3. **Facturación:** Factura (IVA 13 %, código de control) o Nota de Entrega en cada venta.
4. **Inventario:** transferencias entre sucursales con libro mayor y alertas mínimo/máximo.
5. **Posventa y marketing:** cotizaciones con vigencia, devoluciones y cambios (≤ 30 días),
   cupones, campañas de temporada, wishlists múltiples compartibles y moderación de reseñas.

### 0.2 Paquetes

| Paquete | CU |
| :-- | :-- |
| `catalogo_y_tiendas` | CU12, CU13, CU14+ |
| `inventario_y_proveedores` | CU15, CU16 |
| `ventas_y_pagos` | CU17–CU24 + servicio **PayPal** (`paypal_service.py`, `paypal_routers.py`) |

### 0.3 Alcance por canal

| CU | Web tienda | Web panel | App móvil | Backend |
| :-- | :-: | :-: | :-- | :-: |
| CU12 Buscar/filtrar + stock por sucursal | ✅ filtros facetados y disponibilidad | — | ✅ texto, categoría y voz en el catálogo; **stock por sucursal** en el detalle | ✅ |
| CU13 Cupones y campañas | ✅ aplicar cupón | ✅ `/admin/promotions` | ✅ aplicar cupón en checkout | ✅ |
| CU14+ Wishlist múltiple y moderación | ✅ listas múltiples y enlace compartible | ✅ `/admin/reviews` | ⚠️ una lista de favoritos (la API de listas múltiples existe pero la app no la usa) | ✅ |
| CU15 Transferencias | — | ✅ `/admin/transfers` | — | ✅ |
| CU16 Alertas de stock | — | ✅ `/admin/alerts` | — | ✅ |
| CU17 Carrito | ✅ | — | ✅ | ✅ |
| CU18 Checkout (Tarjeta · PayPal · QR) | ✅ | — | ✅ | ✅ |
| CU19 Venta en caja (POS) | — | ✅ `/admin/pos` | — | ✅ |
| CU20 Factura / Nota de entrega | ✅ ver | ✅ emitir e imprimir | ✅ ver | ✅ |
| CU21 Cotizaciones | — | ✅ `/admin/quotations-returns` | — | ✅ |
| CU22 Devoluciones y cambios | ✅ **consultar** en `/tienda/pedidos` | ✅ `/admin/quotations-returns` | ✅ **consultar** mis devoluciones | ✅ |
| CU23 Arqueo de caja | — | ✅ `/admin/shifts` | — | ✅ |
| CU24 Historial de compras | ✅ `/tienda/pedidos` (pestañas Pedidos / Devoluciones) | — | ✅ Mis compras (pestañas Pedidos / Devoluciones) | ✅ |

### 0.4 Reglas de personal por sucursal (vigentes desde este ciclo)

- Cada **ENCARGADO** y **CAJERO** pertenece a **una sola sucursal** (`branch_employees`); cada
  sucursal tiene **un solo ENCARGADO activo** (409 si se intenta asignar un segundo).
- **Solo `SUPERADMIN` es Casa Matriz** (vista consolidada de todas las sucursales). El backend
  aplica el alcance con `get_branch_scope`: el personal de sucursal solo ve y opera su sucursal.
- **Cajero:** POS, arqueo, dashboard y catálogo en solo lectura.
  **Encargado:** operación completa de su sucursal (mercadería, transferencias, alertas, ajustes,
  cotizaciones, devoluciones, reservas, despachos, recepción de pedidos a proveedores).

---

# 1. Captura de Requisitos

## 1.1 Actores

| Actor | Descripción | CU |
| :-- | :-- | :-- |
| **Visitante** | Sin sesión: busca y filtra el catálogo | CU12 |
| **Cliente** (`CLIENTE`) | Compra en web o app | CU12, CU14+, CU17, CU18, CU20, CU22 (consulta), CU24 |
| **Cajero** (`CAJERO`) | Personal de **una** sucursal | CU19, CU20, CU23, alistado de pedidos online |
| **Encargado** (`ENCARGADO`) | Responsable de **una** sucursal | CU15, CU16, CU19, CU21, CU22, CU23 |
| **Casa Matriz** (`SUPERADMIN`) | Administración central | CU13, CU14+ (moderación), CU15, CU16, CU21, CU22, CU23 (auditoría global) |
| **PayPal** | Pasarela de pagos externa (REST API v2, sandbox o live) | CU18 |
| **Servicio de facturación** | Cálculo de IVA 13 % y código de control (interno) | CU20 |

```mermaid
flowchart LR
    Cliente((Cliente))
    Cajero((Cajero))
    Encargado((Encargado))
    Matriz((Casa Matriz))
    PayPal((PayPal))

    subgraph catalogo_y_tiendas
        CU12([CU12 Buscar y filtrar])
        CU13([CU13 Promociones])
        CU14([CU14+ Wishlists y moderación])
    end
    subgraph inventario_y_proveedores
        CU15([CU15 Transferencias])
        CU16([CU16 Alertas de stock])
    end
    subgraph ventas_y_pagos
        CU17([CU17 Carrito])
        CU18([CU18 Checkout])
        CU19([CU19 POS])
        CU20([CU20 Factura])
        CU21([CU21 Cotización])
        CU22([CU22 Devoluciones])
        CU23([CU23 Arqueo])
        CU24([CU24 Historial])
    end

    Cliente --> CU12 & CU14 & CU17 & CU18 & CU24
    Cajero --> CU19 & CU23
    Encargado --> CU15 & CU16 & CU19 & CU21 & CU22 & CU23
    Matriz --> CU13 & CU14 & CU15 & CU16 & CU21 & CU22 & CU23
    CU18 -.-> PayPal
    CU18 -. «include» .-> CU20
    CU19 -. «include» .-> CU20
```

## 1.2 Priorización

| CU | Prioridad | Tipo |
| :-- | :-: | :-- |
| CU17, CU18, CU19, CU20, CU23 | Alta | Transacciones ACID / control financiero |
| CU12, CU15 | Alta | Consulta indexada / transacción multi-sucursal |
| CU13, CU16, CU22, CU24 | Media | Reglas de negocio / consulta |
| CU14+, CU21 | Baja | Social / documental |

## 1.3 Fichas de casos de uso

### CU12 · Buscar y filtrar catálogo + disponibilidad por sucursal

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Visitante, Cliente. |
| **Tablas** | `products`, `product_variants`, `inventory`, `categories`, `seasons`, `colors`, `sizes`, `branches` |
| **Flujo (web)** | 1. `/tienda` muestra filtros con las opciones de `GET /catalog/filter-options` (rango de precios, categorías, temporadas/ocasión, tallas, colores, sucursales).<br>2. El cliente combina filtros y/o texto (o voz, CU34).<br>3. `GET /catalog/products/search?q&category_id&season_id&min_price&max_price&size_id&color_id&branch_id&sort_by&page&limit` (orden: `newest`, `price_asc`, `price_desc`, `rating`) devuelve resultados **paginados**.<br>4. En el detalle, `GET /catalog/products/{id}/branch-availability` muestra el **stock de la variante elegida en cada sucursal**, separando las que tienen stock, las agotadas y las **cerradas temporalmente**; desde ahí se reserva (CU26). |
| **Flujo (móvil)** | Búsqueda por texto, filtro por categoría y **búsqueda por voz** en el catálogo; el detalle de prenda muestra la sección **"Disponible en tiendas"** con el stock por sucursal de la talla y el color elegidos y el botón *Reservar*. |
| **Excepción** | Sin resultados: mensaje y opción de limpiar filtros. |

### CU13 · Gestionar promociones (cupones y campañas de temporada)

| Campo | Descripción |
| :-- | :-- |
| **Actor** | Casa Matriz (`/admin/promotions`). |
| **Tablas** | `coupons`, `seasonal_promotions`, `audit_logs` |
| **Cupones** | Código único, `discount_type` **`PORCENTAJE` o `MONTO_FIJO`**, valor, compra mínima, `valid_from`/`valid_until`, `max_uses`, `used_count`, activo. CRUD: `GET/POST/PUT/DELETE /catalog/coupons`. |
| **Validación** | `POST /catalog/coupons/validate` (público) con código y total: verifica vigencia, activo, usos y compra mínima y devuelve el descuento. Se usa en el carrito web, el checkout móvil y el POS; el checkout vuelve a aplicarlo en el servidor. |
| **Campañas** | `seasonal_promotions`: nombre, % de descuento, categoría opcional, `start_date`–`end_date`. CRUD: `/catalog/promotions`. |
| **Excepción** | Código duplicado (400). |

### CU14+ · Wishlists múltiples y moderación de reseñas

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Cliente (listas), Casa Matriz (moderación). |
| **Tablas** | `wishlists` (`is_public`, `share_token` único), `wishlist_group_items`, `wishlist_items` (favorito simple), `product_reviews` (`status`, `moderated_at`, `moderator_id`) |
| **Listas (web)** | El cliente crea listas con nombre y visibilidad, agrega/quita prendas (`/catalog/wishlists/*`) y comparte la lista pública con su enlace `GET /catalog/wishlists/shared/{share_token}` (sin sesión). |
| **Moderación** | Las reseñas se publican con estado `APPROVED` (moderación **posterior**). Casa Matriz revisa en `/admin/reviews` (`GET /catalog/admin/reviews`) y puede **rechazarlas** (`PUT /catalog/admin/reviews/{id}/moderate` con `APPROVED`/`REJECTED`); la tienda solo muestra las aprobadas (el autor ve la suya). |
| **Móvil** | Mantiene el favorito simple (♥) del Ciclo 1. |

### CU15 · Transferencias entre sucursales

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Encargado (su sucursal), Casa Matriz. Web `/admin/transfers`. |
| **Tablas** | `stock_transfers`, `stock_transfer_details`, `inventory`, `inventory_ledger` |
| **Flujo** | 1. `POST /merchandise/transfers`: origen, destino y variantes/cantidades → estado **`SOLICITADA`** (código `transfer_number`).<br>2. `PUT /merchandise/transfers/{id}/status` → **`EN_TRANSITO`** (solo desde `SOLICITADA`): valida y **descuenta el stock del origen** y asienta `TRANSFERENCIA_SALIDA` en `inventory_ledger`.<br>3. → **`COMPLETADA`**: **suma el stock en el destino** y asienta `TRANSFERENCIA_ENTRADA`; guarda `received_by_id` y `completed_at`.<br>4. → **`CANCELADA`**: si ya estaba `EN_TRANSITO`, **devuelve el stock al origen** (`TRANSFERENCIA_REVERSION`). Una transferencia `COMPLETADA` o `CANCELADA` ya no cambia. |
| **Excepción** | Stock insuficiente en el origen al despachar (400). |
| **Nota** | La actualización del inventario es **lógica de aplicación dentro de la misma transacción** (no hay triggers en la base de datos). |

### CU16 · Alertas de stock (mínimo / máximo)

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Encargado, Casa Matriz (lectura también para Cajero vía API). Web `/admin/alerts`. |
| **Tablas** | `inventory` (`stock_minimo`, `stock_maximo`) — **no hay tabla de alertas**: se calculan al consultar. |
| **Flujo** | `GET /merchandise/inventory/alerts` devuelve las variantes de la sucursal con `stock_actual ≤ stock_minimo` (**`QUIEBRE_STOCK`**) o `stock_actual ≥ stock_maximo` (**`SOBRESTOCK`**). Los umbrales se configuran con `PUT /merchandise/inventory/thresholds/{branch_id}/{variant_id}`. Desde la alerta el encargado puede pedir una transferencia (CU15) o Casa Matriz una reposición al proveedor (CU08/CU10). |

### CU17 · Carrito de compra digital

| Campo | Descripción |
| :-- | :-- |
| **Actor** | Cliente autenticado (web: modal de carrito; móvil: pestaña *Carrito*). |
| **Tablas** | `carts` (uno por usuario), `cart_items` |
| **Flujo** | `GET /sales/cart`, `POST /sales/cart/items`, `PUT/DELETE /sales/cart/items/{id}`, `DELETE /sales/cart/clear`. Al agregar se valida que la variante tenga stock (> 0) en alguna sucursal; la sucursal definitiva se elige en el checkout, donde se revalida el stock de **esa** sucursal. También recibe prendas desde el vestidor virtual (CU32) con la talla recomendada. |
| **Excepción** | "La prenda se encuentra temporalmente agotada en todas las sucursales (stock = 0)". |

### CU18 · Checkout digital con medios de pago (incluye la pasarela PayPal)

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Cliente; **PayPal** (sistema externo). |
| **Tablas** | `orders`, `order_items`, `payments` (herencia de tabla única), `invoices`, `inventory`, `inventory_ledger`, `carts`, `cart_items`, `coupons` |
| **Precondición** | Carrito con ítems; stock en la sucursal elegida. |
| **Flujo** | 1. El cliente elige la **sucursal** de retiro/despacho, tipo de comprobante (**Factura** con NIT/CI y razón social, o **Nota de Entrega**) y, si tiene, un **cupón**.<br>2. Elige el medio de pago del canal online: **Tarjeta**, **PayPal** o **QR** (efectivo y crédito solo existen en el POS).<br>3. **Tarjeta:** titular, número (≥ 13 dígitos), vencimiento MM/AA y CVV; se guardan solo marca y últimos 4 dígitos. **QR:** se registra una referencia. **PayPal:** ver flujo de la pasarela.<br>4. `POST /sales/checkout` (canal `ONLINE`) ejecuta **una transacción**: valida stock por variante en la sucursal, crea la orden en estado **`PAGADA`**, sus ítems, **descuenta el inventario** y asienta `VENTA` en `inventory_ledger`, aplica el cupón, registra el pago con su subtipo, **emite el comprobante** (CU20) y vacía el carrito.<br>5. La web y la app muestran el comprobante (número de pedido, código de control, referencia del pago y total). |
| **Excepciones** | **E1** Stock insuficiente en la sucursal (400, se revierte todo). **E2** Datos de tarjeta inválidos (validación en web y móvil). **E3** PayPal no confirma el cobro (402) o no hay datos de la transacción (400). |

#### Pasarela de pago PayPal (CU18 y seña de CU26)

| Aspecto | Implementación |
| :-- | :-- |
| **API** | PayPal REST v2 (`/v1/oauth2/token`, `/v2/checkout/orders`, `/capture`, consulta de orden). `PAYPAL_MODE=sandbox` → `api-m.sandbox.paypal.com`; `live` → `api-m.paypal.com`. |
| **Credenciales** | `PAYPAL_CLIENT_ID` y `PAYPAL_CLIENT_SECRET` en `backend/.env` (app REST creada en developer.paypal.com). El **Secret nunca sale del backend**; el Client ID es público. |
| **Moneda** | Los montos en Bs se convierten a USD con `PAYPAL_EXCHANGE_RATE_BOB_USD` (6,96). |
| **Endpoints** | `GET /api/v1/payments/paypal/config` (Client ID, modo, `simulated`), `GET …/status` (prueba OAuth real: `connected`), `POST …/create-order`, `POST …/capture-order`. |
| **Web** | `paypal-checkout.service.ts` carga el **SDK oficial de PayPal (Smart Buttons)**: `createOrder` → backend crea la orden; el comprador inicia sesión en la ventana de PayPal y aprueba; `onApprove` → backend captura. |
| **Móvil** | `paypal_checkout.dart`: el backend crea la orden; la **ventana oficial de PayPal** se abre en la app (`webview_flutter`); cuando PayPal redirige a `…/checkout/success` la app pide al backend la captura. Si falla el checkout tras cobrar, se reutiliza el cobro (no se cobra dos veces). |
| **Verificación en servidor** | Antes de registrar el pedido (o la reserva), `verify_completed_order` consulta la orden en PayPal y exige `COMPLETED` y un monto que cubra el total. **Nunca se registra como pagado un pedido solo porque el cliente envió un ID.** |
| **Registro** | Pago de subtipo `PAYPAL` con `gateway_reference = PAYPAL:{orderId}`, `paypal_payer_id` y `paypal_payer_email`. |
| **Modo simulación** | Solo si no hay credenciales: órdenes `PAYPAL-SIM-…`, sin contacto con PayPal, y la pantalla lo indica explícitamente ("no se realiza ningún cobro"). |

#### Alistado y entrega de pedidos online en la sucursal (extensión de CU18/CU19)

El stock del pedido online se descuenta de la sucursal elegida al pagar. El **cajero** (o
encargado) lo atiende desde el POS → pestaña **Alistado**:
`GET /sales/orders-fulfillment` (pedidos `ONLINE` de su sucursal en `PENDIENTE`/`PAGADA`/`PREPARANDO`/`LISTO_PARA_ENTREGA`)
y `PATCH /sales/orders/{id}/fulfillment`:

| Desde | Hacia |
| :-- | :-- |
| `PENDIENTE`, `PAGADA` | `PREPARANDO`, `CANCELADO` |
| `PREPARANDO` | `LISTO_PARA_ENTREGA`, `CANCELADO` |
| `LISTO_PARA_ENTREGA` | `ENTREGADO` |

Requiere **caja abierta** del cajero en esa sucursal (el pedido queda asociado a su turno para el
arqueo). **Cancelar** devuelve las prendas al stock (`DEVOLUCION` en el libro mayor).

### CU19 · Venta presencial en caja (POS)

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Cajero o Encargado de la sucursal (Casa Matriz debe elegir una sucursal). Web `/admin/pos`. |
| **Precondición** | **Turno de caja `ABIERTO`** del mismo usuario en la misma sucursal (CU23). |
| **Flujo** | 1. Búsqueda rápida por nombre o SKU en el **inventario real de la sucursal**.<br>2. El ticket suma ítems; opcionalmente aplica un cupón.<br>3. Medio de pago: **EFECTIVO** (monto recibido → vuelto), **TARJETA** (marca + últimos 4 / voucher), **QR** o **CREDITO** (fecha de vencimiento, 30 días por defecto).<br>4. NIT/CI y razón social → Factura o Nota de Entrega.<br>5. `POST /sales/checkout` con `channel = "POS"`, `cash_shift_id` y `pos_items`: misma transacción que CU18 (orden `PAGADA`, stock, ledger, pago, comprobante) asociada al turno.<br>6. Se muestra el recibo y se **imprime** desde el navegador. |
| **Pestañas del POS** | **Venta directa** (CU19) · **Reservas** (cobro del saldo, CU25) · **Alistado** (pedidos online). |
| **Excepciones** | Sin turno abierto, turno de otro usuario o de otra sucursal (400); efectivo insuficiente (400); stock insuficiente (400). |

### CU20 · Emitir factura y nota de entrega

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Sistema (en cada venta: CU18, CU19, CU21, CU25). |
| **Tabla** | `invoices` (`order_id` único) |
| **Cálculo** | `tax_rate = 0,13`; `tax_amount = round(total × 0,13, 2)` (precios con IVA incluido); `subtotal` y `total` de la orden. |
| **Factura** | `doc_type = FACTURA`, NIT/CI y razón social del cliente y **código de control** hexadecimal (`XX-XX-XX-XX`). |
| **Nota de entrega** | `doc_type = NOTA_ENTREGA`, sin código de control. |
| **Visualización** | En la respuesta del pedido (web, app y POS) y en el historial (CU24); el POS lo imprime con el navegador. No hay generación de PDF en el servidor. |

### CU21 · Generar y convertir cotización

| Campo | Descripción |
| :-- | :-- |
| **Actores** | **Encargado** y Casa Matriz (`POST` y conversión restringidos a `SUPERADMIN`/`ENCARGADO`; el cajero solo puede consultar vía API). Web `/admin/quotations-returns`. |
| **Tablas** | `quotations` (`quotation_number` único, `valid_until`), `quotation_items` |
| **Flujo** | 1. `POST /sales/quotations` con cliente, ítems y días de vigencia → estado **`VIGENTE`**.<br>2. `GET /sales/quotations` marca como **`EXPIRADA`** las vencidas al consultar.<br>3. `POST /sales/quotations/{id}/convert` (solo `VIGENTE`): valida stock, crea la venta con pago y **factura** (CU20), descuenta stock y deja la cotización **`CONVERTIDA`**. |
| **Excepciones** | Cotización expirada (400); stock insuficiente en la sucursal (400). |

### CU22 · Devoluciones y cambios de prendas

| Campo | Descripción |
| :-- | :-- |
| **Actores** | **Encargado** y Casa Matriz (`POST /sales/returns`); el **cliente consulta** sus devoluciones (`GET /sales/returns/my`: web `/tienda/pedidos` → pestaña *Devoluciones y cambios*; app móvil → *Mis compras* → *Devoluciones*). |
| **Tablas** | `order_returns` (`return_number` `DEV-AAAA-XXXXXX`, `refund_amount`, `status`), `order_return_items` (`replacement_variant_id`) |
| **Reglas** | Plazo máximo **30 días** desde la compra (validado en web y backend). Solo prendas de esa orden y hasta la cantidad comprada. |
| **Tipos** | **`DEVOLUCION_DINERO`** (reembolso del precio facturado) o **`CAMBIO_PRENDA`** (con variante de reemplazo; se valida y descuenta su stock). |
| **Efecto** | La prenda devuelta **siempre reingresa** al stock de la sucursal de la orden (`DEVOLUCION_CLIENTE` en el libro mayor); la de cambio se descuenta como `VENTA`. La devolución queda `APROBADA` y se audita. |
| **Excepciones** | Plazo vencido (400); prenda ajena a la orden o cantidad excedida (400); sin stock para el cambio (400). |

### CU23 · Arqueo de caja

| Campo | Descripción |
| :-- | :-- |
| **Actores** | Cajero, Encargado; Casa Matriz ve la **auditoría global** de cajas. Web `/admin/shifts`. |
| **Tabla** | `cash_shifts` (`cashier_id`, `branch_id`, `opening_amount`, `closing_amount_declared`, `closing_amount_system`, `difference`, `status`) |
| **Apertura** | `POST /sales/shifts/open` con monto inicial → **`ABIERTO`**. Un usuario no puede tener dos turnos abiertos (aviso si está abierto en otra sucursal). |
| **Turno en curso** | `GET /sales/shifts/current` con ventas del turno y **desglose**: efectivo, tarjeta, QR y por origen (presencial, reservas, pedidos online/delivery). |
| **Cierre ciego** | `POST /sales/shifts/{id}/close` con el efectivo contado: **esperado = apertura + ventas en efectivo del turno**; **diferencia = declarado − esperado** (0 cuadra, > 0 sobrante, < 0 faltante) → **`CERRADO`**. |
| **Historial** | `GET /sales/shifts` (por sucursal; global para Casa Matriz). |

### CU24 · Historial de compras (cliente)

`GET /sales/orders/my-orders` y `GET /sales/orders/{id}`: número (`ORD-AAAA-NNNNNN`), fecha,
sucursal/canal, estado (`PAGADA`, `PREPARANDO`, `LISTO_PARA_ENTREGA`, `ENTREGADO`, `CANCELADO`),
ítems (prenda, talla, color, cantidad, subtotal), pagos (medio y referencia) y comprobante (tipo,
código de control, NIT). Web `/tienda/pedidos` y móvil *Mis compras*, ambos con las pestañas
**Pedidos** y **Devoluciones** (CU22). Cada compra online, cambio de alistado y devolución genera
además un aviso en el buzón del cliente (CU40, ver `Ciclo3.md`).

## 1.4 Prototipos de navegación

```
Tienda (web/app) ─► Catálogo + filtros (CU12) ─► Detalle (stock por sucursal) ─► Añadir al carrito (CU17)
      ─► Checkout (CU18): sucursal · Factura/Nota · cupón · [Tarjeta | PayPal | QR]
            └─ PayPal: ventana oficial ─► aprobar ─► captura en servidor
      ─► Comprobante (CU20) ─► Mis compras (CU24: Pedidos · Devoluciones)

Panel (cajero) ─► Abrir caja (CU23) ─► POS: [Venta directa (CU19) | Reservas (CU25) | Alistado]
      ─► Recibo impreso ─► Cierre ciego de caja (CU23)
```

## 1.5 Modelo de casos de uso (estereotipos)

```mermaid
flowchart TD
    CU17([CU17 Carrito]) --> CU18([CU18 Checkout])
    CU18 -->|«include»| CU20([CU20 Factura])
    CU19([CU19 POS]) -->|«include»| CU20
    CU19 -->|«include»| CU23([CU23 Caja abierta])
    CU21([CU21 Cotización]) -->|«extend» convertir| CU20
    CU18 -.->|«extend» cupón| CU13([CU13 Promociones])
    CU19 -.->|«extend» cupón| CU13
    CU22([CU22 Devolución]) -->|«include»| CU24([CU24 Orden original])
    CU18 -.->|«extend» PayPal| PP((PayPal))
```

---

# 2. Análisis

## 2.1 Arquitectura de paquetes

```mermaid
graph TD
    SEG[seguridad_y_usuarios<br/>JWT · roles · branch scope · auditoría]
    CAT[catalogo_y_tiendas<br/>catálogo · búsqueda · cupones · wishlists · sucursales]
    INV[inventario_y_proveedores<br/>inventario · ledger · transferencias · alertas]
    VEN[ventas_y_pagos<br/>carrito · checkout · POS · factura · caja · cotizaciones · devoluciones · PayPal]
    PP((PayPal REST v2))

    VEN -->|usuario y alcance de sucursal| SEG
    VEN -->|variantes, precios, cupones| CAT
    VEN -->|stock y libro mayor| INV
    INV -->|sucursales y variantes| CAT
    VEN -->|crear/capturar/verificar orden| PP
```

## 2.2 Diagramas de comunicación

Notación **Mermaid (flowchart LR)**: Actor (`:Actor`) · Interfaz (`<<boundary>> :IU_*`) · Control (`<<control>> :CTR_*`) · Entidad (`<<entity>> :CE_*`) y Servicios Externos (`<<external>>`); correspondencia 1:1 con la secuencia real de ventas, pagos, transferencias y cotizaciones.

### CU12: Buscar y filtrar catálogo avanzado + disponibilidad por sucursal

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cliente / Visitante")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_BusquedaCatalogo</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Catalogo</b>"]:::controlStyle
    CE_P["&laquo;entity&raquo;<br/><b>:CE_Producto</b>"]:::entityStyle
    CE_V["&laquo;entity&raquo;<br/><b>:CE_VariantePrenda</b>"]:::entityStyle
    CE_I["&laquo;entity&raquo;<br/><b>:CE_Inventario</b>"]:::entityStyle

    C -- "1: ingresarCriterios(texto, categoria_id, talla, color, precio_min/max, branch_id)" --> IU
    IU -- "2: buscarProductosConStock(filtros)" --> CTR
    CTR -- "3: select_active_products(categoria_id, precio_range, texto)" --> CE_P
    CE_P -. "4: productos_base[]" .-> CTR
    CTR -- "5: select_variants(product_ids, talla_id, color_id)" --> CE_V
    CE_V -. "6: variantes_coincidentes[]" .-> CTR
    CTR -- "7: select_stock_by_branch(variant_ids, branch_id)" --> CE_I
    CE_I -. "8: existencias_por_sucursal[]" .-> CTR
    CTR -. "9: HTTP 200 OK (items, catalogo_total, paginas, badge_stock)" .-> IU
    IU -. "10: mostrarResultados(grilla, existencias, badges_disponibilidad)" .-> C
    CTR -. "5a: HTTP 200 OK (items: [], total: 0)" .-> IU
    IU -. "6a: mostrarMensaje('No se encontraron prendas con esos filtros')" .-> C
```

### CU13: Gestionar promociones: cupones y ofertas de temporada

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    A(("👤 :Superadministrador")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_GestionPromociones</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Promociones</b>"]:::controlStyle
    CE_C["&laquo;entity&raquo;<br/><b>:CE_Cupon</b>"]:::entityStyle
    CE_B["&laquo;entity&raquo;<br/><b>:CE_BitacoraAuditoria</b>"]:::entityStyle

    A -- "1: crearNuevoCupon(codigo, tipo_descuento, valor, start_date, end_date, max_usos)" --> IU
    IU -- "2: POST /api/v1/promotions/coupons (payload)" --> CTR
    CTR -- "3: check_code_exists(codigo)" --> CE_C
    CE_C -. "4: exists = false" .-> CTR
    CTR -- "5: insert_coupon(codigo, tipo, valor, start_date, end_date, max_uses, is_active=true)" --> CE_C
    CE_C -. "6: coupon_id = 45" .-> CTR
    CTR -- "7: insert_log(user_id, action='INSERT', table='coupons', row_id=45)" --> CE_B
    CE_B -. "8: log_ok" .-> CTR
    CTR -. "9: HTTP 201 Created (coupon_data)" .-> IU
    IU -. "10: mostrarAlerta('Promoción programada con éxito en el calendario')" .-> A
    CTR -. "5a: HTTP 400 Bad Request ('El código ya existe o el rango de fechas es inválido')" .-> IU
    IU -. "6a: mostrarErrorValidacion()" .-> A
```

### CU15: Gestionar inventario general y transferencias entre sucursales

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    EO(("👤 :Encargado Sucursal Origen")):::actorStyle
    ED(("👤 :Encargado Sucursal Destino")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:Interfaz_Gestion_Inventario</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:Controlador_Traspasos_Inventario</b>"]:::controlStyle
    CE_I["&laquo;entity&raquo;<br/><b>:Entidad_Inventario_Sucursal</b>"]:::entityStyle
    CE_K["&laquo;entity&raquo;<br/><b>:Entidad_Kardex_Movimientos</b>"]:::entityStyle
    CE_T["&laquo;entity&raquo;<br/><b>:Entidad_Traspaso_Mercaderia</b>"]:::entityStyle

    EO -- "1: solicitarTraspaso(sucursal_origen, sucursal_destino, lista_prendas, cantidades)" --> IU
    IU -- "2: registrarSolicitudTraspaso(datos_traspaso)" --> CTR
    CTR -- "3: verificarStockDisponible(sucursal_origen, prendas)" --> CE_I
    CE_I -. "4: stock_suficiente_confirmado" .-> CTR
    CTR -- "5: crearRegistroTraspaso(estado='SOLICITADA', codigo='TRF-2026-001')" --> CE_T
    CE_T -. "6: traspaso_id = 101" .-> CTR
    CTR -. "7: confirmacionRegistro(traspaso_id=101)" .-> IU
    IU -. "8: notificar('Solicitud de traspaso registrada exitosamente')" .-> EO
    EO -- "9: despacharPrendasFisicas(traspaso_id=101)" --> IU
    IU -- "10: procesarSalidaMercaderia(traspaso_id=101)" --> CTR
    CTR -- "11: restarStockOrigen(sucursal_origen, prendas, cantidades)" --> CE_I
    CE_I -. "12: stock_origen_descontado" .-> CTR
    CTR -- "13: asentarMovimientoSalidaKardex(sucursal_origen, tipo='TRASPASO_SALIDA', ref='TRF-101')" --> CE_K
    CE_K -. "14: asiento_salida_registrado" .-> CTR
    CTR -- "15: actualizarEstadoTraspaso(traspaso_id=101, nuevo_estado='EN_TRANSITO')" --> CE_T
    CE_T -. "16: estado_actualizado" .-> CTR
    CTR -. "17: confirmacionDespacho()" .-> IU
    IU -. "18: notificar('Mercadería en camino a sucursal destino')" .-> EO
    ED -- "19: confirmarRecepcionFisica(traspaso_id=101)" --> IU
    IU -- "20: procesarIngresoMercaderia(traspaso_id=101)" --> CTR
    CTR -- "21: sumarStockDestino(sucursal_destino, prendas, cantidades)" --> CE_I
    CE_I -. "22: stock_destino_incrementado" .-> CTR
    CTR -- "23: asentarMovimientoIngresoKardex(sucursal_destino, tipo='TRASPASO_INGRESO', ref='TRF-101')" --> CE_K
    CE_K -. "24: asiento_ingreso_registrado" .-> CTR
    CTR -- "25: actualizarEstadoTraspaso(traspaso_id=101, nuevo_estado='COMPLETADA')" --> CE_T
    CE_T -. "26: traspaso_finalizado" .-> CTR
    CTR -. "27: confirmacionRecepcion()" .-> IU
    IU -. "28: notificar('Prendas incorporadas al inventario de la sucursal')" .-> ED
```

### CU16: Configurar y notificar alertas de stock (mínimo/máximo)

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    T(("👤 :Trigger / Demonio Sistema")):::actorStyle
    E(("👤 :Encargado Sucursal")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_BandejaAlertas</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_AlertasStock</b>"]:::controlStyle
    CE_I["&laquo;entity&raquo;<br/><b>:CE_Inventario</b>"]:::entityStyle
    CE_A["&laquo;entity&raquo;<br/><b>:CE_AlertaStock</b>"]:::entityStyle

    T -- "1: verify_inventory_thresholds(branch_id=1, variant_id=5)" --> CTR
    CTR -- "2: select(branch_id=1, variant_id=5)" --> CE_I
    CE_I -. "3: stock_actual=2, stock_minimo=5, stock_maximo=50" .-> CTR
    CTR -- "4: insert_alert(branch_id=1, variant_id=5, type='STOCK_MINIMO', severity='CRITICA')" --> CE_A
    CE_A -. "5: alert_id = 89" .-> CTR
    CTR -. "6: notificacion_emitida" .-> T
    E -- "7: abrirPanelNotificaciones(branch_id=1)" --> IU
    IU -- "8: GET /api/v1/inventory/alerts?branch_id=1" --> CTR
    CTR -- "9: select_unresolved(branch_id=1)" --> CE_A
    CE_A -. "10: alerts_data[]" .-> CTR
    CTR -. "11: HTTP 200 OK (alertas_con_variantes[])" .-> IU
    IU -. "12: renderizarAlertas(insignia_roja, boton_transferencia_o_compra)" .-> E
```

### CU17: Gestionar carrito de compra digital

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cliente")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:Interfaz_Carrito_Compras</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:Controlador_Carrito</b>"]:::controlStyle
    CE_I["&laquo;entity&raquo;<br/><b>:Entidad_Inventario_Sucursal</b>"]:::entityStyle
    CE_IC["&laquo;entity&raquo;<br/><b>:Entidad_Item_Carrito</b>"]:::entityStyle
    CE_C["&laquo;entity&raquo;<br/><b>:Entidad_Carrito</b>"]:::entityStyle

    C -- "1: agregarPrendaAlCarrito(variante_id=22, sucursal_id=1, cantidad=2)" --> IU
    IU -- "2: registrarItemCarrito(usuario_id, variante_id=22, sucursal_id=1, cantidad=2)" --> CTR
    CTR -- "3: consultarStockDisponible(sucursal_id=1, variante_id=22)" --> CE_I
    CE_I -. "4: existencias_actuales = 5" .-> CTR
    CTR -- "5: guardarOActualizarItem(carrito_id, variante_id=22, cantidad=2)" --> CE_IC
    CE_IC -. "6: item_guardado" .-> CTR
    CTR -- "7: recalcularTotales(carrito_id)" --> CE_C
    CE_C -. "8: [subtotal: 350.00, descuento: 0.00, total: 350.00]" .-> CTR
    CTR -. "9: respuestaExitosa(datos_carrito)" .-> IU
    IU -. "10: actualizarVistaCarrito(articulos, total=Bs 350.00)" .-> C
    CTR -. "5a: errorExistencias('Prenda temporalmente agotada en la sucursal seleccionada')" .-> IU
    IU -. "6a: deshabilitarBotonYMostrarAlerta()" .-> C
```

### CU18: Procesar venta omnicanal (E-commerce / App Móvil)

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cliente")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:Interfaz_Checkout</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:Controlador_Ventas</b>"]:::controlStyle
    PAS["&laquo;external&raquo;<br/><b>:Pasarela_De_Pagos</b>"]:::externalStyle
    CE_I["&laquo;entity&raquo;<br/><b>:Entidad_Inventario</b>"]:::entityStyle
    CE_O["&laquo;entity&raquo;<br/><b>:Entidad_Orden_Venta</b>"]:::entityStyle
    CE_P["&laquo;entity&raquo;<br/><b>:Entidad_Registro_Pago</b>"]:::entityStyle
    CTR_F["&laquo;control&raquo;<br/><b>:Controlador_Facturacion</b>"]:::controlStyle
    CE_F["&laquo;entity&raquo;<br/><b>:Entidad_Factura_Fiscal</b>"]:::entityStyle
    CE_NC["&laquo;entity&raquo;<br/><b>:Entidad_Nota_Credito</b>"]:::entityStyle
    NOTIF["&laquo;control&raquo;<br/><b>:Servicio_Notificaciones_Push</b>"]:::controlStyle

    C -- "1: confirmarCompra(modalidad_entrega, sucursal_id, direccion, medio_pago, nit_ci)" --> IU
    IU -- "1.1a: fijarCostoEnvio(Bs 0.00) y fijarPlazoCustodia(48 horas)" --> IU
    IU -- "1.1b: calcularTarifaEnvioPorZona(direccion) -> costo_envio = Bs 15.00" --> IU
    IU -- "2: iniciarCheckoutConReserva(datos_checkout)" --> CTR
    CTR -- "3: bloquearStockTemporal(sucursal_id, variantes, cantidades)" --> CE_I
    CE_I -. "4: stock_bloqueado_ok" .-> CTR
    CTR -- "5: registrarOrdenPendiente(estado='PENDIENTE_PAGO', session_timeout=300s)" --> CE_O
    CE_O -. "6: orden_id = 450, expires_at = now + 5min" .-> CTR
    CTR -. "7: sesionIniciada(orden_id=450, tiempo_restante=300s)" .-> IU
    IU -- "8a: notificarExpiracionOVerificarTimeout(orden_id=450)" --> CTR
    CTR -- "9a: liberarStockBloqueado(sucursal_id, variantes, cantidades)" --> CE_I
    CE_I -. "10a: stock_liberado_a_disponible" .-> CTR
    CTR -- "11a: anularOrden(estado='CANCELADA_TIMEOUT')" --> CE_O
    CE_O -. "12a: orden_anulada" .-> CTR
    CTR -- "13a: despacharAlertaPush('Sesión de pago expiró. No se realizó ningún cargo. Prendas liberadas.')" --> NOTIF
    NOTIF -. "14a: alerta_enviada" .-> CTR
    CTR -. "15a: ordenCanceladaPorTiempo()" .-> IU
    IU -. "16a: mostrarPantallaExpiracionConBotonReintentar()" .-> C
    IU -- "8b: procesarCobroPasarela(monto_total, token_autorizacion)" --> PAS
    PAS -. "9b: cobro_confirmado(ref_pasarela)" .-> IU
    IU -- "10b: confirmarPagoOrden(orden_id=450, ref_pasarela)" --> CTR
    CTR -- "11b: descontarDefinitivamenteStock(sucursal_id, variantes)" --> CE_I
    CE_I -. "12b: stock_descontado" .-> CTR
    CTR -- "13b: registrarComprobantePago(orden_id=450, ref_pasarela, estado='CONFIRMADO')" --> CE_P
    CE_P -. "14b: pago_registrado" .-> CTR
    CTR -- "15b: emitirFacturaFiscal(orden_id=450, nit_ci, total, iva_13)" --> CTR_F
    CTR_F -- "16b: persistirFactura(codigo_control, qr)" --> CE_F
    CE_F -. "17b: factura_id = 310" .-> CTR_F
    CTR_F -. "18b: factura_generada" .-> CTR
    CTR -- "19b: fijarPlazoRetiro(pickup_deadline = now + 48h, estado='LISTO_RETIRO')" --> CE_O
    CTR -- "20b: notificarCliente('Tu pedido está listo para recoger en sucursal. Plazo máximo: 48 horas.')" --> NOTIF
    CTR -- "21b: reingresarStockASucursal(sucursal_id, variantes)" --> CE_I
    CE_I -. "22b: stock_retornado_a_exhibicion" .-> CTR
    CTR -- "23b: emitirNotaDeCredito(cliente_id, monto_total, motivo='EXPIRACION_RETIRO_48H')" --> CE_NC
    CE_NC -. "24b: nota_credito_code = 'NC-2026-9812'" .-> CTR
    CTR -- "25b: notificarCliente('Plazo de 48h vencido. Prenda reingresada a stock y se generó tu Nota de Crédito NC-2026-9812.')" --> NOTIF
    CTR -- "19c: generarGuiaDespacho(direccion, tarifa_envio, estado='PREPARANDO_DESPACHO')" --> CE_O
    CTR -. "26b: respuestaExitosa(orden_id=450, factura_id=310, modalidad_entrega)" .-> IU
    IU -. "27b: mostrarPantallaExito(resumen_compra, boton_descargar_factura)" .-> C
```

### CU19: Procesar venta presencial en caja

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    Cajero(("👤 :Cajero")):::actorStyle
    UI["&laquo;external&raquo;<br/><b>:U_PuntoDeVentaPOS</b>"]:::externalStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_POS</b>"]:::controlStyle
    SC["&laquo;entity&raquo;<br/><b>:CE_SesionCaja</b>"]:::entityStyle
    INV["&laquo;entity&raquo;<br/><b>:CE_Inventario</b>"]:::entityStyle
    ORD["&laquo;entity&raquo;<br/><b>:CE_Orden</b>"]:::entityStyle
    MP["&laquo;entity&raquo;<br/><b>:CE_MedioDePago</b>"]:::entityStyle
    FAC_CTR["&laquo;external&raquo;<br/><b>:CTR_Facturacion</b>"]:::externalStyle
    FAC["&laquo;entity&raquo;<br/><b>:CE_Factura</b>"]:::entityStyle
    PRN["&laquo;external&raquo;<br/><b>:Dispositivo_Impresora</b>"]:::externalStyle

    Cajero -- "1: ingresarCobro(session_id=45, items, total=200.00, medio='EFECTIVO', recibido=250.00, NIT='1029384')" --> UI
    UI -- "1.1: POST /api/v1/pos/orders (payload)" --> CTR
    CTR -- "1.2: get_session(session_id=45)" --> SC
    SC -. "1.2a: session_status = 'ABIERTA'" .-> CTR
    CTR -- "1.3: insert_order(branch_id=1, channel='POS', total=200.00, status='COMPLETADO')" --> ORD
    ORD -. "1.3a: order_id = 880" .-> CTR
    CTR -- "1.4: deduct_stock(branch_id=1, items)" --> INV
    INV -. "1.4a: stock_deducted_ok" .-> CTR
    CTR -- "1.5: insert_payment(order_id=880, type='EFECTIVO', amount=200.00, cash_received=250.00, cash_change=50.00)" --> MP
    MP -. "1.5a: pay_ok" .-> CTR
    CTR -- "1.6: issue_invoice(order_id=880, nit='1029384', total=200.00)" --> FAC_CTR
    FAC_CTR -- "1.6.1: insert(order_id=880, doc_type='FACTURA', subtotal=200.00, tax_amount=26.00)" --> FAC
    FAC -. "1.6.1a: invoice_id = 512" .-> FAC_CTR
    FAC_CTR -. "1.6.1b: invoice_data" .-> CTR
    CTR -- "1.7: print_receipt(raw_thermal_data, width=80mm)" --> PRN
    PRN -. "1.7a: print_ok" .-> CTR
    CTR -. "1.8: HTTP 200 OK (order_id=880, change=50.00)" .-> UI
    UI -. "1.9: mostrarCambioYConfirmacion(vuelto=Bs. 50.00, gaveta_abierta)" .-> Cajero
```

### CU20: Emitir factura y nota de entrega (IVA 13 %, código de control)

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    POS["&laquo;external&raquo;<br/><b>:CTR_Ventas / POS</b>"]:::externalStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Facturacion</b>"]:::controlStyle
    CE_O["&laquo;entity&raquo;<br/><b>:CE_Orden</b>"]:::entityStyle
    CE_F["&laquo;entity&raquo;<br/><b>:CE_Factura</b>"]:::entityStyle
    PDF["&laquo;control&raquo;<br/><b>:Servicio_GeneradorPDF</b>"]:::controlStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_VisorComprobantes</b>"]:::boundaryStyle

    POS -- "1: generate_invoice(order_id=450, nit='489123019', name='Comercial SRL')" --> CTR
    CTR -- "2: select_total(order_id=450)" --> CE_O
    CE_O -. "3: total_amount = 520.00" .-> CTR
    CTR -- "4: compute_control_code(nit, inv_num, date, key)" --> CTR
    CTR -- "5: insert_invoice(order_id=450, doc_type='FACTURA', subtotal=520, tax=67.60, total=520, control_code='A4-5B-7C-1D')" --> CE_F
    CE_F -. "6: invoice_id = 789" .-> CTR
    CTR -- "4a: insert_invoice(order_id=450, doc_type='NOTA_ENTREGA', subtotal=520, tax=67.60, total=520, control_code=null)" --> CE_F
    CE_F -. "5a: invoice_id = 790" .-> CTR
    CTR -- "7: build_pdf(invoice_id, format='CARTA' o 'TICKET')" --> PDF
    PDF -. "8: pdf_stream_bytes" .-> CTR
    CTR -. "9: invoice_record(id, doc_type, pdf_url)" .-> POS
    POS -- "10: disponibilizarDescarga(pdf_url)" --> IU
    IU -. "11: url_lista_para_visor" .-> POS
```

### CU21: Generar y convertir cotización comercial

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cajero / Cliente")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_GenerarCotizacion</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Cotizaciones</b>"]:::controlStyle
    CE_V["&laquo;entity&raquo;<br/><b>:CE_VariantePrenda</b>"]:::entityStyle
    CE_Q["&laquo;entity&raquo;<br/><b>:CE_Cotizacion</b>"]:::entityStyle
    CE_D["&laquo;entity&raquo;<br/><b>:CE_DetalleCotizacion</b>"]:::entityStyle
    PDF["&laquo;control&raquo;<br/><b>:Servicio_GeneradorPDF</b>"]:::controlStyle

    C -- "1: iniciarCotizacion(cliente_datos, vigencia_dias=15)" --> IU
    IU -- "2: POST /api/v1/sales/quotations (payload)" --> CTR
    CTR -- "3: get_variant_info(variant_id)" --> CE_V
    CE_V -. "4: precio_base, descuento_vigente" .-> CTR
    CTR -- "5: insert_quotation(cliente_datos, vigencia, status='VIGENTE')" --> CE_Q
    CE_Q -. "6: quotation_id = 72, code = 'COT-2026-00072'" .-> CTR
    CTR -- "7: insert_detail(quotation_id=72, variant_id, qty, unit_price)" --> CE_D
    CE_D -. "8: ok" .-> CTR
    CTR -- "9: build_quotation_pdf(quotation_id=72)" --> PDF
    PDF -. "10: pdf_bytes, download_url" .-> CTR
    CTR -. "11: HTTP 201 Created (code='COT-2026-00072', total=750.00, pdf_url)" .-> IU
    IU -. "12: mostrarCotizacionGenerada(code, pdf_url)" .-> C
```

### CU22: Gestionar devoluciones y cambios de prendas

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cajero_Encargado")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_Gestion_Devoluciones</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Devoluciones_Y_Cambios</b>"]:::controlStyle
    CE_F["&laquo;entity&raquo;<br/><b>:Entidad_Factura</b>"]:::entityStyle
    CE_O["&laquo;entity&raquo;<br/><b>:Entidad_Orden</b>"]:::entityStyle
    CE_I["&laquo;entity&raquo;<br/><b>:Entidad_Inventario</b>"]:::entityStyle
    CE_OD["&laquo;entity&raquo;<br/><b>:Entidad_OrdenDevolucion</b>"]:::entityStyle
    CE_NC["&laquo;entity&raquo;<br/><b>:Entidad_NotaCredito</b>"]:::entityStyle
    CE_S["&laquo;entity&raquo;<br/><b>:Entidad_SesionCaja</b>"]:::entityStyle

    C -- "1: ingresarCodigoFactura(codigo_factura='FAC-10024')" --> IU
    IU -- "2: GET /api/v1/sales/invoices/by-code/FAC-10024" --> CTR
    CTR -- "3: buscarFacturaConItems(codigo_factura)" --> CE_F
    CE_F -. "4: {factura_id: 85, orden_id: 301, fecha: '2026-09-15', items: [{var_id: 14, nombre: 'Blusa Seda', precio: 220.00}]}" .-> CTR
    CTR -. "5a: HTTP 400 Bad Request ('Plazo vencido: Han pasado más de 14 días (2 semanas) desde la compra')" .-> IU
    IU -. "6a: mostrarInsigniaRojaBloqueo('Garantía Expirada - No procede devolución ni cambio')" .-> C
    CTR -. "5b: HTTP 200 OK (items_factura, garantia_valida=true, dias_restantes)" .-> IU
    IU -. "6b: mostrarPrendasCompradas(tabla_prendas, selector_accion)" .-> C
    C -- "7a: solicitarCambioTalla(var_id_origen=14, talla_nueva='M')" --> IU
    IU -- "8a: POST /api/v1/sales/returns (tipo='CAMBIO_TALLA', var_id=14, rep_id=18)" --> CTR
    CTR -- "9a: reingresarStock(var_id=14, qty=+1) y descontarStock(var_id=18, qty=-1)" --> CE_I
    CE_I -. "10a: inventario_actualizado_ok" .-> CTR
    CTR -- "11a: registrarComprobante(tipo='CAMBIO_TALLA', diferencia=0.00)" --> CE_OD
    CE_OD -. "12a: return_id = 91" .-> CTR
    CTR -. "13a: cambioExitoso(return_id=91, diferencia=0.00)" .-> IU
    IU -. "14a: emitirComprobanteCambioEntregaPrenda()" .-> C
    C -- "7b: solicitarCambioModelo(var_id_origen=14, modelo_nuevo_var_id=32)" --> IU
    IU -- "8b: POST /api/v1/sales/returns (tipo='CAMBIO_MODELO', var_id=14, rep_id=32)" --> CTR
    CTR -- "9b: intercambiarStock(var_devuelta=+1, var_nueva=-1)" --> CE_I
    CE_I -. "10b: stock_ajustado" .-> CTR
    CTR -- "11b: cobrarDiferenciaEnCaja(monto_diferencia = Bs 50.00)" --> CE_S
    CE_S -. "12b: cobro_asentado" .-> CTR
    CTR -- "13b: registrarCambio(diferencia_cobrada = Bs 50.00)" --> CE_OD
    CE_OD -. "14b: return_id = 92" .-> CTR
    CTR -. "15b: cambioConfirmado(monto_a_cobrar=50.00)" .-> IU
    IU -. "16b: cobrarDiferenciaYEntregarNuevaPrenda()" .-> C
    CTR -- "11c: emitirNotaCredito(cliente_id, saldo_a_favor = Bs 40.00, motivo='CAMBIO_MODELO_MENOR_VALOR')" --> CE_NC
    CE_NC -. "12c: codigo_nc = 'NC-2026-0045'" .-> CTR
    CTR -- "13c: registrarCambio(nota_credito_id=45, saldo_a_favor=40.00)" --> CE_OD
    CE_OD -. "14c: return_id = 93" .-> CTR
    CTR -. "15c: cambioConfirmadoConNotaCredito(codigo_nc='NC-2026-0045', saldo=40.00)" .-> IU
    IU -. "16c: imprimirNotaCreditoParaProximaCompraYEntregarPrenda()" .-> C
    C -- "7c: solicitarDevolucion(var_id=14, motivo='Falla técnica')" --> IU
    IU -- "8c: POST /api/v1/sales/returns (tipo='DEVOLUCION_DINERO', var_id=14)" --> CTR
    CTR -- "9c: reingresarStockAInventario(var_id=14, qty=+1)" --> CE_I
    CE_I -. "10c: stock_reingresado" .-> CTR
    CTR -- "11d: generarNotaCreditoOReembolso(cliente_id, monto=220.00)" --> CE_NC
    CE_NC -. "12d: comprobante_emitido" .-> CTR
    CTR -. "13d: devolucionProcesada()" .-> IU
    IU -. "14d: comprobanteFinalizado()" .-> C
```

### CU23: Gestionar arqueo de caja (apertura y cierre ciego)

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cajero")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_ArqueoCaja</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Arqueo</b>"]:::controlStyle
    CE_S["&laquo;entity&raquo;<br/><b>:CE_SesionCaja</b>"]:::entityStyle
    CE_P["&laquo;entity&raquo;<br/><b>:CE_MedioDePago</b>"]:::entityStyle
    CE_D["&laquo;entity&raquo;<br/><b>:CE_OrdenDevolucion</b>"]:::entityStyle

    C -- "1: abrirTurno(monto_inicial_efectivo=200.00)" --> IU
    IU -- "2: POST /api/v1/sales/shifts/open (user_id, branch_id=1, opening_amount=200.00)" --> CTR
    CTR -- "3: check_active_sessions(user_id)" --> CE_S
    CE_S -. "4: active_sessions = 0" .-> CTR
    CTR -- "5: insert(user_id, branch_id=1, opening_amount=200.00, status='ABIERTA')" --> CE_S
    CE_S -. "6: session_id = 45" .-> CTR
    CTR -. "7: HTTP 201 Created (session_id=45)" .-> IU
    IU -. "8: habilitarModuloPOS()" .-> C
    C -- "9: cerrarTurno(session_id=45, monto_declarado_cajero=1450.00)" --> IU
    IU -- "10: POST /api/v1/sales/shifts/45/close (declared_amount=1450.00)" --> CTR
    CTR -- "11: sum_cash_sales_by_session(session_id=45)" --> CE_P
    CE_P -. "12: ventas_efectivo = 1430.00" .-> CTR
    CTR -- "13: sum_cash_refunds_by_session(session_id=45)" --> CE_D
    CE_D -. "14: devoluciones_efectivo = 180.00" .-> CTR
    CTR -- "15: update(45, declared=1450.00, expected=1450.00, diff=0.00, status='CERRADA')" --> CE_S
    CE_S -. "16: session_closed_ok" .-> CTR
    CTR -. "17: HTTP 200 OK (reporte_arqueo)" .-> IU
    IU -. "18: imprimirArqueo(diferencia=0.00, status='CUADRADO')" .-> C
```

### CU24: Consultar historial de compras

```mermaid
flowchart LR
    classDef actorStyle fill:#ffffff,stroke:#111827,stroke-width:1.5px,color:#111827;
    classDef boundaryStyle fill:#f9fafb,stroke:#2563eb,stroke-width:1.5px,color:#1e3a8a;
    classDef controlStyle fill:#f9fafb,stroke:#7c3aed,stroke-width:1.5px,color:#5b21b6;
    classDef entityStyle fill:#f9fafb,stroke:#059669,stroke-width:1.5px,color:#065f46;
    classDef externalStyle fill:#f9fafb,stroke:#d97706,stroke-width:1.5px,color:#92400e;

    C(("👤 :Cliente")):::actorStyle
    IU["&laquo;boundary&raquo;<br/><b>:IU_HistorialCompras</b>"]:::boundaryStyle
    CTR["&laquo;control&raquo;<br/><b>:CTR_Historial</b>"]:::controlStyle
    CE_O["&laquo;entity&raquo;<br/><b>:CE_Orden</b>"]:::entityStyle
    CE_IO["&laquo;entity&raquo;<br/><b>:CE_ItemOrden</b>"]:::entityStyle
    CE_P["&laquo;entity&raquo;<br/><b>:CE_MedioDePago</b>"]:::entityStyle
    CE_F["&laquo;entity&raquo;<br/><b>:CE_Factura</b>"]:::entityStyle

    C -- "1: presionarPestanaMisCompras()" --> IU
    IU -- "2: GET /api/v1/sales/orders/my-orders (token_jwt)" --> CTR
    CTR -- "3: select_orders_by_user(user_id, order_by_created_at_desc)" --> CE_O
    CE_O -. "4: orders_summary[]" .-> CTR
    CTR -. "5: HTTP 200 OK (orders_list)" .-> IU
    IU -. "6: renderizarTarjetasPedidos(num_orden, fecha, total_bs, canal)" .-> C
    C -- "7: verDetalleOrden(order_id=450)" --> IU
    IU -- "8: GET /api/v1/sales/orders/450" --> CTR
    CTR -- "9: select_items_with_product(order_id=450)" --> CE_IO
    CE_IO -. "10: items[(sku, product_name, color, size, price, qty)]" .-> CTR
    CTR -- "11: select_payment_details(order_id=450)" --> CE_P
    CE_P -. "12: payment_type: 'TARJETA', last4: '4512'" .-> CTR
    CTR -- "13: select_invoice(order_id=450)" --> CE_F
    CE_F -. "14: doc_type: 'FACTURA', total: 520.00, pdf_path: '/pdf/0450.pdf'" .-> CTR
    CTR -. "15: HTTP 200 OK (order_complete_profile)" .-> IU
    IU -. "16: mostrarModalDetalle(prendas, desglose_iva, descargar_factura)" .-> C
    C -- "17: presionarDescargarFactura()" --> IU
    IU -. "18: descargarArchivoPDF(Factura_ORD-450.pdf)" .-> C
```


## 2.3 Clases de análisis

| Paquete | Boundary | Control | Entity |
| :-- | :-- | :-- | :-- |
| `ventas_y_pagos` | `CartModalComponent`, `PosComponent`, `CashShiftComponent`, `QuotationsReturnsComponent`, `CustomerOrdersComponent` · móvil `CartView`/`CheckoutSheet`, `CustomerOrdersView`, `PayPalApprovalPage` | `ventas_y_pagos/routers.py`, `paypal_routers.py`, `PayPalService`, `PayPalCheckoutService` (web) | `Cart`, `CartItem`, `Order`, `OrderItem`, `Payment` (`Efectivo`/`Tarjeta`/`QR`/`PayPal`/`Credito`), `Invoice`, `CashShift`, `Quotation`, `QuotationItem`, `OrderReturn`, `OrderReturnItem` |
| `inventario_y_proveedores` | `TransfersComponent`, `StockAlertsComponent` | `merchandise/routers.py` | `StockTransfer`, `StockTransferDetail`, `Inventory`, `InventoryLedger` |
| `catalogo_y_tiendas` | `StoreHomeComponent`, `ProductDetailComponent`, `WishlistComponent`, `PromotionsComponent`, `ReviewsModerationComponent` · `CatalogoView`, `ProductDetailView` | `catalogo_y_tiendas/routers.py` | `Coupon`, `SeasonalPromotion`, `Wishlist`, `WishlistGroupItem`, `ProductReview` |

## 2.4 Acoplamiento y cohesión

- `ventas_y_pagos` concentra toda la lógica comercial y fiscal; consume `catalogo_y_tiendas`
  (precios, cupones) e `inventario_y_proveedores` (stock y ledger) y **aísla la pasarela externa**
  en `PayPalService`.
- El polimorfismo de pagos se persiste en **una sola tabla** (`payments`, discriminador
  `payment_type`: `EFECTIVO`, `TARJETA`, `QR`, `PAYPAL`, `CREDITO`).
- El alcance por sucursal se resuelve en una sola dependencia (`get_branch_scope`) reutilizada por
  ventas, caja, inventario y transferencias.

---

# 3. Diseño

## 3.1 Arquitectura

| Capa | Tecnología |
| :-- | :-- |
| Presentación | **Angular 16** + Bootstrap 5 (web) · **Flutter** (app; `http`, `shared_preferences`, `webview_flutter`, `speech_to_text`, `image_picker`, `camera`) |
| Servicios | **FastAPI** (routers por paquete, `Depends` para JWT, roles y alcance de sucursal) |
| Dominio | Reglas en los routers y servicios del paquete (`paypal_service.py`, `vton_service.py`), transacciones SQLAlchemy |
| Datos | **SQLAlchemy 2** sobre **PostgreSQL**; tablas por `create_all` + migraciones ligeras en `main.py` |
| Externos | PayPal REST v2 · SMTP |

## 3.2 Diagramas de secuencia

**DSC018 — Checkout digital con PayPal y factura**

```mermaid
sequenceDiagram
    actor C as Cliente
    participant UI as Web / App
    participant API as FastAPI /api/v1
    participant PPS as PayPalService
    participant PP as PayPal
    participant DB as PostgreSQL

    C->>UI: 1: sucursal, comprobante, cupón, PayPal
    UI->>API: 2: POST /payments/paypal/create-order
    API->>PPS: 3: create_order(total Bs)
    PPS->>PP: 4: OAuth + POST /v2/checkout/orders
    PP-->>UI: 5: orden (id) / approve_url
    C->>PP: 6: login comprador y aprobar
    UI->>API: 7: POST /payments/paypal/capture-order
    API->>PP: 8: capture
    PP-->>API: 9: COMPLETED + payer
    UI->>API: 10: POST /sales/checkout {payment_type: PAYPAL, paypal_payment}
    API->>PPS: 11: verify_completed_order(orderId, total)
    PPS->>PP: 12: GET orden
    API->>DB: 13: validar stock sucursal
    API->>DB: 14: INSERT orders (PAGADA) + order_items
    API->>DB: 15: UPDATE inventory − qty · INSERT inventory_ledger (VENTA)
    API->>DB: 16: INSERT payments (PAYPAL) + invoices (IVA 13 %)
    API->>DB: 17: vaciar carrito · COMMIT
    API-->>UI: 18: 201 OrderResponse
    UI-->>C: 19: comprobante
```

**DSC019/023 — Turno de caja, venta POS y cierre ciego**

```mermaid
sequenceDiagram
    actor Cj as Cajero
    participant POS as IU_POS / IU_Arqueo
    participant API as /api/v1/sales
    participant DB as PostgreSQL

    Cj->>POS: 1: abrir caja (Bs 200)
    POS->>API: 2: POST /shifts/open {branch_id, opening_amount}
    API->>DB: 3: INSERT cash_shifts (ABIERTO)
    loop ventas del turno
        Cj->>POS: 4: ítems + medio de pago
        POS->>API: 5: POST /checkout {channel: POS, cash_shift_id, pos_items}
        API->>DB: 6: orden + stock + pago + factura (turno)
    end
    Cj->>POS: 7: contar efectivo (cierre ciego)
    POS->>API: 8: POST /shifts/{id}/close {closing_amount_declared}
    API->>DB: 9: esperado = apertura + Σ efectivo · diferencia
    API->>DB: 10: UPDATE cash_shifts (CERRADO)
    API-->>POS: 11: cuadre / sobrante / faltante + desglose
```

**DSC-Alistado — Pedido online en la sucursal**

```mermaid
sequenceDiagram
    actor Cj as Cajero
    participant POS as IU_POS (Alistado)
    participant API as /api/v1/sales
    participant DB as PostgreSQL

    POS->>API: 1: GET /orders-fulfillment
    API-->>POS: 2: pedidos ONLINE de la sucursal
    Cj->>POS: 3: Preparar
    POS->>API: 4: PATCH /orders/{id}/fulfillment {PREPARANDO}
    API->>DB: 5: asociar al turno ABIERTO del cajero
    Cj->>POS: 6: Listo → Entregado (o Cancelar)
    POS->>API: 7: PATCH …/fulfillment
    API->>DB: 8: estado (+ reponer stock si CANCELADO)
```

**DSC021 — Convertir cotización**

```mermaid
sequenceDiagram
    actor E as Encargado
    participant UI as IU_Cotizaciones
    participant API as /api/v1/sales
    participant DB as PostgreSQL

    E->>UI: 1: [Cobrar / Facturar] cotización
    UI->>API: 2: POST /quotations/{id}/convert
    API->>DB: 3: VIGENTE y valid_until ≥ hoy
    API->>DB: 4: validar stock
    API->>DB: 5: orden + stock + pago + factura
    API->>DB: 6: quotations.status = CONVERTIDA
    API-->>UI: 7: comprobante
```

**DSC022 — Devolución o cambio (≤ 30 días)**

```mermaid
sequenceDiagram
    actor E as Encargado
    participant UI as IU_Devoluciones
    participant API as /api/v1/sales
    participant DB as PostgreSQL

    E->>UI: 1: buscar orden
    UI->>API: 2: GET /orders/{id}
    UI-->>E: 3: días transcurridos + prendas compradas
    E->>UI: 4: prendas, tipo, motivo
    UI->>API: 5: POST /returns
    API->>DB: 6: validar plazo y pertenencia
    API->>DB: 7: INSERT order_returns (APROBADA) + items
    API->>DB: 8: stock + devuelto (− cambio) · ledger
    API-->>UI: 9: DEV-AAAA-XXXXXX
```

## 3.3 Máquinas de estado

**Orden (`orders.status`)**

```mermaid
stateDiagram-v2
    [*] --> PAGADA: checkout ONLINE / POS
    PAGADA --> PREPARANDO: alistado (pedido online)
    PAGADA --> CANCELADO: stock repuesto
    PREPARANDO --> LISTO_PARA_ENTREGA
    PREPARANDO --> CANCELADO
    LISTO_PARA_ENTREGA --> ENTREGADO
    ENTREGADO --> [*]
    CANCELADO --> [*]
```

(`PENDIENTE` también se acepta como estado de origen en el alistado.)

**Transferencia (`stock_transfers.status`)**

```mermaid
stateDiagram-v2
    [*] --> SOLICITADA
    SOLICITADA --> EN_TRANSITO: despacho (− stock origen)
    EN_TRANSITO --> COMPLETADA: recepción (+ stock destino)
    SOLICITADA --> CANCELADA
    EN_TRANSITO --> CANCELADA
    COMPLETADA --> [*]
    CANCELADA --> [*]
```

**Cotización (`quotations.status`)** — `VIGENTE → CONVERTIDA` (cobro) · `VIGENTE → EXPIRADA` (vencida al consultar).

**Turno de caja (`cash_shifts.status`)** — `ABIERTO → CERRADO` (cierre ciego).

---

# 4. Diseño de datos (DDL real)

Generado desde los modelos SQLAlchemy (dialecto PostgreSQL); coincide con la base de datos.
No hay triggers: la actualización de inventario y libro mayor ocurre en la aplicación, dentro de
la misma transacción que la venta, la transferencia o la devolución.

```sql
CREATE TABLE carts (
    id SERIAL NOT NULL,
    user_id INTEGER,
    session_id VARCHAR(80),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE cart_items (
    id SERIAL NOT NULL,
    cart_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(cart_id) REFERENCES carts (id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
);

CREATE TABLE cash_shifts (
    id SERIAL NOT NULL,
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
    PRIMARY KEY (id),
    FOREIGN KEY(cashier_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY(branch_id) REFERENCES branches (id) ON DELETE RESTRICT
);

CREATE TABLE orders (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    channel VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    discount_amount NUMERIC(10, 2) NOT NULL,
    coupon_code VARCHAR(30),
    total_amount NUMERIC(10, 2) NOT NULL,
    cash_shift_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY(branch_id) REFERENCES branches (id) ON DELETE RESTRICT,
    FOREIGN KEY(cash_shift_id) REFERENCES cash_shifts (id) ON DELETE SET NULL
);

CREATE TABLE order_items (
    id SERIAL NOT NULL,
    order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
);

CREATE TABLE payments (
    id SERIAL NOT NULL,
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
    PRIMARY KEY (id),
    FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE
);

CREATE TABLE invoices (
    id SERIAL NOT NULL,
    order_id INTEGER NOT NULL,
    doc_type VARCHAR(15) NOT NULL,
    tax_rate NUMERIC(4, 3) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    tax_amount NUMERIC(10, 2) NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    control_code VARCHAR(40),
    customer_nit VARCHAR(20),
    customer_name VARCHAR(150),
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (order_id),
    FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT
);

CREATE TABLE quotations (
    id SERIAL NOT NULL,
    quotation_number VARCHAR(30) NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(100),
    customer_phone VARCHAR(30),
    created_by_id INTEGER NOT NULL,
    branch_id INTEGER,
    total_amount NUMERIC(10, 2) NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (quotation_number),
    FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY(branch_id) REFERENCES branches (id) ON DELETE SET NULL
);

CREATE TABLE quotation_items (
    id SERIAL NOT NULL,
    quotation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(quotation_id) REFERENCES quotations (id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
);

CREATE TABLE order_returns (
    id SERIAL NOT NULL,
    return_number VARCHAR(30) NOT NULL,
    order_id INTEGER NOT NULL,
    processed_by_id INTEGER NOT NULL,
    return_type VARCHAR(25) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    refund_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (return_number),
    FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
    FOREIGN KEY(processed_by_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE order_return_items (
    id SERIAL NOT NULL,
    return_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    replacement_variant_id INTEGER,
    PRIMARY KEY (id),
    FOREIGN KEY(return_id) REFERENCES order_returns (id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT,
    FOREIGN KEY(replacement_variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
);

CREATE TABLE stock_transfers (
    id SERIAL NOT NULL,
    transfer_number VARCHAR(30) NOT NULL,
    origin_branch_id INTEGER NOT NULL,
    destination_branch_id INTEGER NOT NULL,
    requested_by_id INTEGER NOT NULL,
    received_by_id INTEGER,
    status VARCHAR(20) NOT NULL,
    notes VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    UNIQUE (transfer_number),
    FOREIGN KEY(origin_branch_id) REFERENCES branches (id) ON DELETE RESTRICT,
    FOREIGN KEY(destination_branch_id) REFERENCES branches (id) ON DELETE RESTRICT,
    FOREIGN KEY(requested_by_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY(received_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE stock_transfer_details (
    id SERIAL NOT NULL,
    transfer_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(transfer_id) REFERENCES stock_transfers (id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
);

CREATE TABLE inventory (
    branch_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    stock_actual INTEGER NOT NULL,
    avg_cost NUMERIC(10, 2) NOT NULL,
    stock_minimo INTEGER NOT NULL,
    stock_maximo INTEGER NOT NULL,
    PRIMARY KEY (branch_id, variant_id),
    FOREIGN KEY(branch_id) REFERENCES branches (id) ON DELETE RESTRICT,
    FOREIGN KEY(variant_id) REFERENCES product_variants (id) ON DELETE CASCADE
);

CREATE TABLE coupons (
    id SERIAL NOT NULL,
    code VARCHAR(30) NOT NULL,
    discount_type VARCHAR(15) NOT NULL,
    discount_value NUMERIC(10, 2) NOT NULL,
    min_purchase_amount NUMERIC(10, 2) NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    max_uses INTEGER NOT NULL,
    used_count INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (code)
);

CREATE TABLE seasonal_promotions (
    id SERIAL NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_percent INTEGER NOT NULL,
    category_id INTEGER,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE TABLE wishlists (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_public BOOLEAN NOT NULL,
    share_token VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE (share_token)
);

CREATE TABLE wishlist_group_items (
    id SERIAL NOT NULL,
    wishlist_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_wishlist_group_product UNIQUE (wishlist_id, product_id),
    FOREIGN KEY(wishlist_id) REFERENCES wishlists (id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
);
```

| Columna | Valores usados |
| :-- | :-- |
| `orders.channel` | `ONLINE`, `POS` |
| `orders.status` | `PAGADA`, `PENDIENTE`, `PREPARANDO`, `LISTO_PARA_ENTREGA`, `ENTREGADO`, `CANCELADO` |
| `payments.payment_type` | `EFECTIVO`, `TARJETA`, `QR`, `PAYPAL`, `CREDITO` |
| `payments.status` | `CONFIRMADO` |
| `invoices.doc_type` | `FACTURA`, `NOTA_ENTREGA` |
| `cash_shifts.status` | `ABIERTO`, `CERRADO` |
| `quotations.status` | `VIGENTE`, `CONVERTIDA`, `EXPIRADA` |
| `order_returns.return_type` | `DEVOLUCION_DINERO`, `CAMBIO_PRENDA` |
| `stock_transfers.status` | `SOLICITADA`, `EN_TRANSITO`, `COMPLETADA`, `CANCELADA` |
| `coupons.discount_type` | `PORCENTAJE`, `MONTO_FIJO` |
| `product_reviews.status` | `APPROVED`, `REJECTED` |
| `inventory_ledger.movement_type` (Ciclo 2) | `VENTA`, `DEVOLUCION` (pedido cancelado), `DEVOLUCION_CLIENTE`, `TRANSFERENCIA_SALIDA`, `TRANSFERENCIA_ENTRADA`, `TRANSFERENCIA_REVERSION` |

---

# 5. Implementación

## 5.1 Endpoints (prefijo `/api/v1`)

**`ventas_y_pagos` (`/sales`)**

| Método y ruta | Permiso | CU |
| :-- | :-- | :-- |
| `GET /sales/cart` · `POST /sales/cart/items` · `PUT/DELETE /sales/cart/items/{id}` · `DELETE /sales/cart/clear` | Autenticado | CU17 |
| `POST /sales/checkout` | Autenticado (canal `POS` solo personal de tienda) | CU18 / CU19 / CU20 |
| `GET /sales/orders/my-orders` · `GET /sales/orders/{id}` | Cliente / personal de la sucursal | CU24 |
| `GET /sales/orders` | Personal (su sucursal) | — |
| `GET /sales/orders-fulfillment` · `PATCH /sales/orders/{id}/fulfillment` | SUPERADMIN, ENCARGADO, CAJERO | Alistado |
| `POST /sales/shifts/open` · `GET /sales/shifts/current` · `GET /sales/shifts` · `POST /sales/shifts/{id}/close` | SUPERADMIN, ENCARGADO, CAJERO | CU23 |
| `POST /sales/quotations` · `POST /sales/quotations/{id}/convert` | SUPERADMIN, ENCARGADO | CU21 |
| `GET /sales/quotations` | SUPERADMIN, ENCARGADO, CAJERO | CU21 |
| `POST /sales/returns` | SUPERADMIN, ENCARGADO | CU22 |
| `GET /sales/returns/my` | Cliente | CU22 / CU24 |

**Pasarela PayPal (`/payments/paypal`)**

| Método y ruta | Permiso |
| :-- | :-- |
| `GET /payments/paypal/config` · `GET /payments/paypal/status` | Público |
| `POST /payments/paypal/create-order` · `POST /payments/paypal/capture-order` | Autenticado |

**`inventario_y_proveedores` (`/merchandise`)**

| Método y ruta | Permiso | CU |
| :-- | :-- | :-- |
| `POST /merchandise/transfers` · `PUT /merchandise/transfers/{id}/status` | SUPERADMIN, ENCARGADO | CU15 |
| `GET /merchandise/transfers` · `GET /merchandise/transfers/{id}` | + CAJERO | CU15 |
| `GET /merchandise/inventory/alerts` | SUPERADMIN, ENCARGADO, CAJERO | CU16 |
| `PUT /merchandise/inventory/thresholds/{branch_id}/{variant_id}` | SUPERADMIN, ENCARGADO | CU16 |

**`catalogo_y_tiendas` (`/catalog`)**

| Método y ruta | Permiso | CU |
| :-- | :-- | :-- |
| `GET /catalog/filter-options` · `GET /catalog/products/search` · `GET /catalog/products/{id}/branch-availability` | Público | CU12 |
| `GET/POST/PUT/DELETE /catalog/coupons` · `/catalog/promotions` (escritura) | SUPERADMIN | CU13 |
| `POST /catalog/coupons/validate` · `GET /catalog/promotions` | Público | CU13 |
| `GET/POST/PUT/DELETE /catalog/wishlists…` · `POST/DELETE /catalog/wishlists/{id}/items/{product_id}` | Autenticado | CU14+ |
| `GET /catalog/wishlists/shared/{share_token}` | Público | CU14+ |
| `GET /catalog/admin/reviews` · `PUT /catalog/admin/reviews/{id}/moderate` | SUPERADMIN | CU14+ |

## 5.2 Web (`frontend-web/src/app/packages/`)

| Componente | Ruta | CU |
| :-- | :-- | :-- |
| `catalogo_y_tiendas/store/store-home` | `/tienda` | CU12 (+ CU34 voz) |
| `catalogo_y_tiendas/store/product-detail` | `/tienda/producto/:id` | CU12 (stock por sucursal), CU26 |
| `catalogo_y_tiendas/store/wishlist` | `/tienda/favoritos` | CU14+ |
| `catalogo_y_tiendas/promotions` | `/admin/promotions` | CU13 |
| `catalogo_y_tiendas/reviews-moderation` | `/admin/reviews` | CU14+ |
| `inventario_y_proveedores/transfers` | `/admin/transfers` | CU15 |
| `inventario_y_proveedores/stock-alerts` | `/admin/alerts` | CU16 |
| `ventas_y_pagos/cart/cart-modal` | modal de la tienda | CU17, CU18 (Tarjeta / PayPal / QR) |
| `ventas_y_pagos/paypal-checkout.service.ts` | — | PayPal Smart Buttons |
| `ventas_y_pagos/pos` | `/admin/pos` | CU19, CU25, alistado |
| `ventas_y_pagos/cash-shift` | `/admin/shifts` | CU23 |
| `ventas_y_pagos/quotations-returns` | `/admin/quotations-returns` | CU21, CU22 |
| `ventas_y_pagos/orders/customer-orders` | `/tienda/pedidos` (Pedidos · Devoluciones) | CU24, CU22 |

## 5.3 Móvil (`mobile/lib/src/packages/`)

| Archivo | CU |
| :-- | :-- |
| `catalogo_y_tiendas/catalogo_view.dart` | CU12 (texto, categoría, voz) |
| `catalogo_y_tiendas/product_detail_view.dart` | CU12 (stock por sucursal), CU17 (añadir al carrito) |
| `ventas_y_pagos/cart_view.dart` (`CartView` + `CheckoutSheet`) | CU17, CU18, CU20, CU13 (cupón) |
| `ventas_y_pagos/paypal_checkout.dart` | PayPal (ventana oficial en WebView) |
| `ventas_y_pagos/customer_orders_view.dart` | CU24 + CU22 (pestaña Devoluciones) |
| `ventas_y_pagos/ventas_api.dart` | Cliente HTTP de ventas |

---

# 6. Pruebas

| Archivo | Pruebas | Escenarios |
| :-- | :-: | :-- |
| `test_cu12.py` | 4 | opciones de filtro, búsqueda básica, búsqueda con filtros, disponibilidad inexistente |
| `test_cu13.py` | 2 | CRUD y validación de cupones, campañas de temporada |
| `test_cu14.py` | 2 | reseña y moderación, wishlists múltiples y enlace compartido |
| `test_cu15_cu16.py` | 2 | ciclo de vida de transferencias, alertas y umbrales |
| `test_cu17_cu24.py` | 5 | carrito; checkout online + factura + historial; POS + turno; cotización; devolución y cambio + **consulta de devoluciones del cliente** |
| `test_paypal_payments.py` | 4 | config, **status OAuth**, crear y capturar orden, reserva con seña PayPal |
| `test_nuevas_operaciones_caja_proveedor.py` | 3 | alistado de pedidos de la sucursal, desglose del arqueo, reposición bloqueada |

Suite completa del backend: **72 pruebas aprobadas**. Móvil: `flutter analyze` sin errores y
`flutter test` 4/4. Web: `ng build` sin errores.

---

# 7. Trazabilidad

| CU | Endpoint principal | Backend | Web | Móvil | Tablas |
| :-- | :-- | :-- | :-- | :-- | :-- |
| CU12 | `GET /catalog/products/search`, `…/branch-availability` | `catalogo_y_tiendas/routers.py` | `store-home`, `product-detail` | `catalogo_view`, `product_detail_view` | `products`, `product_variants`, `inventory` |
| CU13 | `/catalog/coupons`, `/catalog/promotions` | idem | `promotions` | checkout (cupón) | `coupons`, `seasonal_promotions` |
| CU14+ | `/catalog/wishlists`, `/catalog/admin/reviews` | idem | `wishlist`, `reviews-moderation` | favoritos simples | `wishlists`, `wishlist_group_items`, `product_reviews` |
| CU15 | `/merchandise/transfers` | `merchandise/routers.py` | `transfers` | — | `stock_transfers`, `stock_transfer_details`, `inventory_ledger` |
| CU16 | `/merchandise/inventory/alerts` | idem | `stock-alerts` | — | `inventory` |
| CU17 | `/sales/cart` | `ventas_y_pagos/routers.py` | `cart-modal` | `cart_view` | `carts`, `cart_items` |
| CU18 | `POST /sales/checkout` + `/payments/paypal/*` | `routers.py`, `paypal_service.py` | `cart-modal`, `paypal-checkout.service` | `cart_view`, `paypal_checkout` | `orders`, `order_items`, `payments`, `invoices` |
| CU19 | `POST /sales/checkout` (POS) | idem | `pos` | — | idem + `cash_shifts` |
| CU20 | (dentro del checkout) | idem | `cart-modal`, `pos` | `cart_view` | `invoices` |
| CU21 | `/sales/quotations` | idem | `quotations-returns` | — | `quotations`, `quotation_items` |
| CU22 | `POST /sales/returns`, `GET /sales/returns/my` | idem | `quotations-returns`, `customer-orders` | `customer_orders_view` | `order_returns`, `order_return_items` |
| CU23 | `/sales/shifts` | idem | `cash-shift` | — | `cash_shifts` |
| CU24 | `/sales/orders/my-orders` | idem | `customer-orders` | `customer_orders_view` | `orders`, `invoices`, `payments` |

**Pendientes conocidos del Ciclo 2:** pagos con **tarjeta y QR simulados** (sin pasarela bancaria;
PayPal sí es real); la app móvil no usa las listas de deseos múltiples (solo favoritos); no hay PDF de factura
en el servidor (el POS imprime desde el navegador).
