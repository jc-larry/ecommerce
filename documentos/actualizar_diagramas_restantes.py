# -*- coding: utf-8 -*-
import re

doc_path = r"documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md"
with open(doc_path, "r", encoding="utf-8") as f:
    content = f.read()

updates = {}

# CU16
updates["CU16"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor T as Trigger / Demonio Sistema
    actor E as Encargado Sucursal
    participant IU as IU_BandejaAlertas
    participant CTR as CTR_AlertasStock
    participant CE_I as CE_Inventario
    participant CE_A as CE_AlertaStock

    rect rgb(255, 250, 240)
    Note over T,CE_A: Fase 1: Detección Automática de Quiebre de Stock tras Venta o Transferencia
    T->>+CTR: 1: verify_inventory_thresholds(branch_id=1, variant_id=5)
    CTR->>+CE_I: 1.1: select(branch_id=1, variant_id=5)
    CE_I-->>-CTR: stock_actual=2, stock_minimo=5, stock_maximo=50
    alt stock_actual <= stock_minimo
        CTR->>+CE_A: 1.2: insert_alert(branch_id=1, variant_id=5, type="STOCK_MINIMO", severity="CRITICA")
        CE_A-->>-CTR: alert_id = 89
        CTR-->>T: notificacion_emitida
    end
    end

    rect rgb(240, 248, 255)
    Note over E,CE_A: Fase 2: Gestión y Visualización de Alertas por el Encargado de Tienda
    E->>+IU: 2: abrirPanelNotificaciones(branch_id=1)
    IU->>+CTR: 2.1: GET /api/v1/inventory/alerts?branch_id=1
    CTR->>+CE_A: 2.2: select_unresolved(branch_id=1)
    CE_A-->>-CTR: alerts_data[]
    CTR-->>-IU: HTTP 200 OK (alertas_con_variantes[])
    IU-->>-E: renderizarAlertas(insignia_roja, boton_transferencia_o_compra)
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU16[Paso 1: El demonio del sistema o evento de inventario invoca verify_inventory_thresholds(branch_id, variant_id) tras una salida o venta.]`**
- **`CU16[Paso 1.1: El controlador consulta los niveles actuales en CE_Inventario (select branch_id, variant_id).]`**
- **`CU16[Paso 1.2: [alt: stock_actual <= stock_minimo] Se genera un registro en CE_AlertaStock con severidad 'CRITICA' y tipo 'STOCK_MINIMO', emitiendo notificación.]`**
- **`CU16[Paso 2: El Encargado de Sucursal abre el panel de notificaciones en la interfaz (IU_BandejaAlertas).]`**
- **`CU16[Paso 2.1: La interfaz solicita las alertas activas no resueltas mediante GET /api/v1/inventory/alerts?branch_id=1.]`**
- **`CU16[Paso 2.2: El controlador consulta en CE_AlertaStock las alertas pendientes de atención y retorna HTTP 200 OK.]`**
- **`CU16[Paso 2.3: La interfaz renderiza las alertas con insignias de urgencia y enlaces de acción rápida a transferencias o compras.]`**"""

# CU18
updates["CU18"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as IU_Checkout (Web / Móvil)
    participant CTR as CTR_Checkout
    participant API as API_PasarelaPagos
    participant CE_I as CE_Inventario
    participant CE_O as CE_Orden
    participant CE_P as CE_MedioDePago
    participant CTR_F as CTR_Facturacion
    participant CE_F as CE_Factura
    participant CE_L as CE_LibroMayor
    participant CE_C as CE_Carrito

    C->>+IU: 1: confirmarCompra(branch_id=1, NIT="489123019", RazonSocial="Pérez SRL", medio="TARJETA", token="tok_123")
    IU->>+CTR: 1.1: POST /api/v1/orders/checkout (user_id, payload)
    rect rgb(255, 250, 240)
    Note over CTR,CE_C: Transacción ACID Crítica de Venta y Facturación
    CTR->>+CE_I: 1.2: select_for_update(branch_id=1, variant_ids)
    CE_I-->>-CTR: stock_bloqueado_ok
    CTR->>+API: 1.3: charge(amount=520.00, token="tok_123")
    API-->>-CTR: charge_success(gateway_ref="ch_stripe_9981")
    CTR->>+CE_O: 1.4: insert_order(user_id, branch_id=1, channel="ONLINE", total=520.00, status="PAGADO")
    CE_O-->>-CTR: order_id = 450
    CTR->>+CE_I: 1.5: deduct_stock(branch_id=1, items)
    CE_I-->>-CTR: ok
    CTR->>+CE_L: 1.6: insert_ledger_entries(branch_id=1, items, movement="VENTA", ref="ORD-450")
    CE_L-->>-CTR: ok
    CTR->>+CE_P: 1.7: insert_payment(order_id=450, type="TARJETA", amount=520.00, card_last4="4242", ref="ch_stripe_9981")
    CE_P-->>-CTR: payment_id = 601
    CTR->>+CTR_F: 1.8: generate_fiscal_invoice(order_id=450, nit="489123019", name="Pérez SRL", total=520.00)
    CTR_F->>+CE_F: 1.8.1: insert_invoice(order_id=450, IVA=13% (Bs. 67.60), control_code="E2-8F-1B", qr_payload)
    CE_F-->>-CTR_F: invoice_id = 310
    CTR_F-->>-CTR: invoice_data
    CTR->>+CE_C: 1.9: clear_cart(user_id)
    CE_C-->>-CTR: cart_empty_ok
    Note over CTR,CE_C: COMMIT Transacción ACID Exitosa
    end
    CTR-->>-IU: HTTP 201 Created (order_id=450, invoice_url="/invoices/310/pdf")
    IU-->>-C: mostrarPantallaExito(resumen_compra, boton_descargar_factura)
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU18[Paso 1: El cliente confirma su compra en IU_Checkout ingresando sucursal, NIT/CI, razón social y datos de pago.]`**
- **`CU18[Paso 1.1: La interfaz envía la solicitud de checkout (POST /api/v1/orders/checkout) al controlador CTR_Checkout.]`**
- **`CU18[Paso 1.2: [ACID] El controlador bloquea con SELECT FOR UPDATE las variantes en CE_Inventario para evitar sobreventas concurrentes.]`**
- **`CU18[Paso 1.3: Se invoca la pasarela de pagos (API_PasarelaPagos) procesando el cobro en tarjeta/QR de forma externa.]`**
- **`CU18[Paso 1.4: Se persiste la orden de venta en estado 'PAGADO' en la entidad CE_Orden.]`**
- **`CU18[Paso 1.5: Se descuenta el stock físico de las variantes involucradas en CE_Inventario.]`**
- **`CU18[Paso 1.6: Se registra el asiento contable de salida de inventario por 'VENTA' en CE_LibroMayor.]`**
- **`CU18[Paso 1.7: Se crea el registro del medio de pago en CE_MedioDePago con el token y referencia de pasarela.]`**
- **`CU18[Paso 1.8: Se invoca a CTR_Facturacion para generar la factura fiscal boliviana (IVA 13 %, código de control) en CE_Factura.]`**
- **`CU18[Paso 1.9: Se vacían los ítems del carrito del cliente en CE_Carrito y se realiza el COMMIT de la transacción.]`**
- **`CU18[Paso 2: Se retorna HTTP 201 Created con el ID de orden y URL de factura, desplegando la confirmación de compra.]`**"""

# CU21
updates["CU21"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cajero / Cliente
    participant IU as IU_GenerarCotizacion
    participant CTR as CTR_Cotizaciones
    participant CE_V as CE_VariantePrenda
    participant CE_Q as CE_Cotizacion
    participant CE_D as CE_DetalleCotizacion
    participant PDF as Servicio_GeneradorPDF

    C->>+IU: 1: iniciarCotizacion(cliente_datos, vigencia_dias=15)
    IU->>+CTR: 1.1: POST /api/v1/sales/quotations (payload)
    loop Por cada prenda cotizada
        CTR->>+CE_V: 1.2: get_variant_info(variant_id)
        CE_V-->>-CTR: precio_base, descuento_vigente
    end
    CTR->>+CE_Q: 1.3: insert_quotation(cliente_datos, vigencia, status='VIGENTE')
    CE_Q-->>-CTR: quotation_id = 72, code = "COT-2026-00072"
    loop Por cada ítem
        CTR->>+CE_D: 1.4: insert_detail(quotation_id=72, variant_id, qty, unit_price)
        CE_D-->>-CTR: ok
    end
    CTR->>+PDF: 1.5: build_quotation_pdf(quotation_id=72)
    PDF-->>-CTR: pdf_bytes, download_url
    CTR-->>-IU: HTTP 201 Created (code="COT-2026-00072", total=750.00, pdf_url)
    IU-->>-C: mostrarCotizacionGenerada(code, pdf_url)
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU21[Paso 1: El cajero o cliente ingresa datos del cliente y prendas a presupuestar con vigencia de hasta 15 días.]`**
- **`CU21[Paso 1.1: La interfaz envía la solicitud de cotización (POST /api/v1/sales/quotations).]`**
- **`CU21[Paso 1.2: [loop: Por cada ítem] El controlador consulta en CE_VariantePrenda el precio unitario y promociones aplicables.]`**
- **`CU21[Paso 1.3: Se crea la cabecera en CE_Cotizacion en estado 'VIGENTE' asignando código correlativo (COT-AAAA-XXXXXX).]`**
- **`CU21[Paso 1.4: [loop: Por cada ítem] Se insertan las líneas en CE_DetalleCotizacion sin reservar ni bloquear stock físico.]`**
- **`CU21[Paso 1.5: Se genera el documento formal en PDF mediante el servicio de reportería Servicio_GeneradorPDF.]`**
- **`CU21[Paso 1.6: Se retorna HTTP 201 Created y se disponibiliza el PDF para descarga o conversión futura a venta (CU19).]`**"""

# CU22
updates["CU22"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cajero
    participant IU as IU_Devoluciones
    participant CTR as CTR_Devoluciones
    participant CE_O as CE_Orden
    participant CE_OD as CE_OrdenDevolucion
    participant CE_I as CE_Inventario
    participant CE_L as CE_LibroMayor
    participant CE_S as CE_SesionCaja

    C->>+IU: 1: buscarOrden(order_id=301)
    IU->>+CTR: 1.1: GET /api/v1/sales/orders/301
    CTR->>+CE_O: 1.2: select_with_items(order_id=301)
    CE_O-->>-CTR: {created_at: "2026-08-20", items: [{var_id: 14, name: "Camisa Lino", qty: 1, price: 180.00}]}
    Note over CTR: Evaluación Regla Garantía Estricta: delta_dias = HOY - created_at
    alt delta_dias <= 30 dias (Garantía Vigente)
        CTR-->>IU: HTTP 200 OK (items_comprados, garantia_valida=true)
        IU-->>C: mostrarInsigniaVerdeYTablaItems()
        C->>+IU: 2: confirmarDevolucion(var_id=14, qty=1, op="REEMBOLSO_EFECTIVO", destino="REINGRESO_INVENTARIO")
        IU->>+CTR: 2.1: POST /api/v1/sales/returns (payload)
        rect rgb(255, 250, 240)
        Note over CTR,CE_S: Transacción Atómica de Devolución, Inventario y Ajuste en Caja
        CTR->>+CE_OD: 2.2: insert(order_id=301, amount=180.00, type="REEMBOLSO")
        CE_OD-->>-CTR: return_id = 55
        alt Destino == "REINGRESO_INVENTARIO"
            CTR->>+CE_I: 2.3: add_stock(branch_id=1, variant_id=14, qty=1)
            CE_I-->>-CTR: ok
            CTR->>+CE_L: 2.4: insert_entry(branch=1, var=14, qty=+1, type="DEVOLUCION_CLIENTE")
            CE_L-->>-CTR: ok
        end
        CTR->>+CE_S: 2.5: deduct_cash_refund(session_id=45, amount=180.00)
        CE_S-->>-CTR: cash_deducted_ok
        end
        CTR-->>-IU: HTTP 200 OK (return_voucher_id=55)
        IU-->>-C: emitirComprobanteYEntregarEfectivo(Bs. 180.00)
    else delta_dias > 30 dias (Plazo Vencido)
        CTR-->>IU: HTTP 400 Bad Request ("Plazo de devolución vencido: han transcurrido más de 30 días")
        IU-->>C: mostrarAlertaRojaBloquearBoton()
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU22[Paso 1: El cajero busca la orden de venta por código o ID (order_id=301).]`**
- **`CU22[Paso 1.1: La interfaz consulta la información de la orden (GET /api/v1/sales/orders/301).]`**
- **`CU22[Paso 1.2: El controlador evalúa la fecha de emisión calculando delta_dias = HOY - created_at.]`**
- **`CU22[Paso 1.3: [alt: Plazo Vencido] Si supera los 30 días reglamentarios, se bloquea el trámite con HTTP 400 Bad Request.]`**
- **`CU22[Paso 2: [alt: Garantía Vigente] El cajero selecciona ítems a devolver, motivo y método de reembolso (Efectivo/Cambio).]`**
- **`CU22[Paso 2.1: La interfaz despacha la solicitud de devolución (POST /api/v1/sales/returns).]`**
- **`CU22[Paso 2.2: Se crea el comprobante en CE_OrdenDevolucion con estado 'APROBADA'.]`**
- **`CU22[Paso 2.3: [alt: Reingreso de Mercadería] Se reintegra el stock a CE_Inventario y se asienta el movimiento en CE_LibroMayor.]`**
- **`CU22[Paso 2.4: Se descuenta el monto de reembolso de la sesión de caja activa (CE_SesionCaja) para el arqueo (CU23).]`**
- **`CU22[Paso 2.5: Se emite el comprobante oficial de devolución y se entrega el dinero o prenda de cambio al cliente.]`**"""

# CU25
updates["CU25"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cajero
    participant IU as IU_POS_Reservas
    participant CTR as CTR_Reservas
    participant CE_TC as CE_TurnoCaja
    participant CE_O as CE_Orden
    participant CE_I as CE_Inventario
    participant CE_R as CE_Reserva

    C->>+IU: 1: seleccionarReserva(reservation_id)
    IU->>+CTR: 1.1: convert_to_pos(reservation_id, items, payment, NIT)
    CTR->>+CE_TC: 1.2: validar_turno_abierto(cashier_id, branch_id)
    CE_TC-->>-CTR: turno (status: ABIERTO)
    opt E1: Caja no abierta o de otro cajero/sucursal
        Note over CTR: HTTP 400 / 403 Sesión Inválida
    end
    CTR->>+CE_R: 1.3: get_reservation(reservation_id)
    CE_R-->>-CTR: reserva (items, deposit_amount)
    opt E2: Stock insuficiente o prendas rechazadas
        CTR->>+CE_I: 1.4: reponer_no_comprados(variant_ids)
        CE_I-->>-CTR: stock_restaurado
    end
    CTR->>+CE_O: 1.5: insert_order(POS, items, turno)
    CE_O-->>-CTR: order_id
    CTR->>+CE_O: 1.6: insert_payment(saldo, medio)
    CTR->>+CE_O: 1.7: insert_invoice(IVA 13%, NIT)
    CE_O-->>-CTR: invoice (control_code)
    CTR->>+CE_R: 1.8: update_status = COMPLETED
    CE_R-->>-CTR: ok
    CTR-->>-IU: OrderResponse (order, invoice)
    IU-->>-C: 2: Mostrar comprobante y reserva completada
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU25[Paso 1: El cajero busca la reserva activa por código (RES-XXXXXX) o cliente al presentarse físicamente en tienda.]`**
- **`CU25[Paso 1.1: La interfaz invoca la conversión a venta POS (POST /api/v1/reservations/{id}/convert).]`**
- **`CU25[Paso 1.2: El controlador valida que el cajero tenga una sesión de caja abierta y activa (CE_TurnoCaja).]`**
- **`CU25[Paso 1.3: Se recuperan las prendas reservadas y el anticipo monetario cobrado previamente (CE_Reserva).]`**
- **`CU25[Paso 1.4: [opt: Prendas no compradas] Las prendas que el cliente probó pero no decidió adquirir reingresan a CE_Inventario.]`**
- **`CU25[Paso 1.5: Se crea la orden formal de venta en CE_Orden descontando el anticipo del total final.]`**
- **`CU25[Paso 1.6: Se asienta el cobro del saldo restante y se emite la factura o nota fiscal boliviana.]`**
- **`CU25[Paso 1.7: La reserva pasa irreversiblemente a estado 'COMPLETADA' (CE_Reserva) y se imprime el ticket de compra.]`**"""

# CU26
updates["CU26"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as IU_ReservarProbador
    participant CTR as CTR_Reservas
    participant CTR_PP as CTR_PayPal
    participant API_PP as PayPal_API
    participant CE_I as CE_Inventario
    participant CE_R as CE_Reserva
    participant CE_L as CE_LibroMayor

    C->>+IU: 1: elegirVariante(color, talla)
    IU->>+CTR: 1.1: get_branch_availability(product_id, variant_id)
    CTR-->>-IU: [(branch_id, stock)]
    C->>+IU: 2: elegirSucursal(fecha, hora, medioPago)
    opt E1: Fuera de horario o E2: Más de 5 prendas
        Note over IU: Bloquea y notifica regla operativa
    end
    IU->>+CTR_PP: 2.1: create_order(app_amount_bs)
    CTR_PP->>+API_PP: POST /v2/checkout/orders
    API_PP-->>-CTR_PP: order_id + approve_url
    CTR_PP-->>IU: approve_url
    IU->>+CTR_PP: capture_order(order_id)
    CTR_PP->>+API_PP: POST /v2/checkout/orders/{id}/capture
    API_PP-->>-CTR_PP: COMPLETED + payer
    CTR_PP-->>-IU: VERIFIED
    IU->>+CTR: 2.2: create_reservation(items, payment_ref)
    CTR->>+CTR_PP: verify_completed_order(order_id)
    CTR_PP-->>-CTR: VERIFIED
    CTR->>+CE_I: 2.3: descontar_stock(variant_ids, qty)
    CE_I-->>-CTR: stock_descontado
    CTR->>+CE_L: 2.4: insert_movimiento(RESERVA)
    CE_L-->>-CTR: ok
    CTR->>+CE_R: 2.5: insert_reservation(PENDING, expires_at)
    CE_R-->>-CTR: reservation_code RES-XXXXXX
    CTR-->>-IU: {reservation_code, total, deposit}
    IU-->>-C: 3: Confirmación y código de reserva
    Note over C,CE_L: La reserva expira a las 48 horas si no se cobra el saldo
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU26[Paso 1: El cliente selecciona tallas y colores de hasta 5 prendas desde la app o web.]`**
- **`CU26[Paso 1.1: La interfaz consulta la disponibilidad física por sucursal en CE_Inventario.]`**
- **`CU26[Paso 2: El cliente selecciona fecha, hora de cita y abona la seña/anticipo de garantía.]`**
- **`CU26[Paso 2.1: El controlador de pasarelas procesa el depósito de anticipo mediante PayPal API retornando estado COMPLETED.]`**
- **`CU26[Paso 2.2: Se invoca la creación formal de la reserva (POST /api/v1/reservations).]`**
- **`CU26[Paso 2.3: Se bloquea el stock físico de las prendas seleccionadas en CE_Inventario.]`**
- **`CU26[Paso 2.4: Se asienta el bloqueo preventivo en el libro mayor contable CE_LibroMayor.]`**
- **`CU26[Paso 2.5: Se persiste la reserva en estado 'PENDING' con código correlativo (RES-AAAA-XXXXXX) y expiración a 48 horas.]`**
- **`CU26[Paso 3: El cliente recibe confirmación en pantalla y comprobante push/correo con su código de atención.]`**"""

# CU27
updates["CU27"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor E as Encargado
    participant IU as IU_KanbanReservas
    participant CTR as CTR_Reservas
    participant CE_R as CE_Reserva
    participant CE_I as CE_Inventario

    E->>+IU: 1: abrir_bandeja()
    IU->>+CTR: 1.1: get_reservations(branch_id)
    CTR->>+CE_R: 1.2: select WHERE branch = ?
    CE_R-->>-CTR: [reservations]
    opt E2: +30 min de la cita sin presentarse -> NO_SHOW y liberar stock
        CTR->>CTR: evaluarTolerancia(reservation)
        CTR->>+CE_I: liberar_stock si CANCELLED / NO_SHOW
        CE_I-->>-CTR: ok
    end
    CTR-->>-IU: [reservas con estado actualizado]
    IU-->>E: Mostrar columnas Kanban (PENDING / PREPARING / READY / COMPLETED)
    E->>+IU: 2: moverTarjeta(reservation_id, nuevo_estado)
    IU->>+CTR: 2.1: update_status(reservation_id, status)
    CTR->>+CE_R: 2.2: update reservation.status
    CE_R-->>-CTR: ok
    opt E3: Estado es CANCELLED o NO_SHOW
        CTR->>+CE_I: 2.3: liberar_stock(variant_ids)
        CE_I-->>-CTR: ok
    end
    CTR-->>-IU: OK
    IU-->>-E: 3: Tablero actualizado
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU27[Paso 1: El encargado de tienda abre el tablero Kanban de reservas de su sucursal.]`**
- **`CU27[Paso 1.1: La interfaz consulta las reservas asignadas a la sucursal (GET /api/v1/reservations?branch_id=X).]`**
- **`CU27[Paso 1.2: El controlador evalúa automáticamente la regla de tolerancia: si pasaron más de 30 min se marca NO_SHOW y se libera stock.]`**
- **`CU27[Paso 1.3: Se visualizan las reservas en columnas: PENDIENTE, EN PREPARACIÓN, LISTO EN PROBADOR y ATENDIDO.]`**
- **`CU27[Paso 2: El encargado mueve la tarjeta de estado (ej: de PENDING a PREPARING o READY).]`**
- **`CU27[Paso 2.1: La interfaz actualiza el estado en el backend (PUT /api/v1/reservations/{id}/status).]`**
- **`CU27[Paso 2.2: Si el estado cambia a CANCELLED o NO_SHOW, el sistema restituye automáticamente el stock a CE_Inventario.]`**
- **`CU27[Paso 3: El tablero Kanban refleja el nuevo estado en tiempo real.]`**"""

# CU29
updates["CU29"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor R as Repartidor
    participant IU as IU_PanelRepartidor
    participant CTR as CTR_Repartidores
    participant CE_R as CE_Repartidor
    participant CE_E as CE_Envio
    participant CE_T as CE_EventoTracking

    R->>+IU: 1: activar_disponibilidad()
    IU->>+CTR: 1.1: update_availability(repartidor_id, true)
    CTR->>+CE_R: 1.2: update is_available = true
    CE_R-->>-CTR: ok
    CTR-->>-IU: ok
    R->>+IU: 2: tomar_pedido(shipment_id)
    IU->>+CTR: 2.1: claim_shipment(shipment_id, repartidor_id)
    opt Repartidor pausado o sin turno
        Note over CTR: HTTP 403 No autorizado
    end
    CTR->>+CE_E: 2.2: update status = ASSIGNED, claimed_at
    CE_E-->>-CTR: ok
    CTR->>+CE_T: 2.3: insert tracking_event(ASSIGNED)
    CE_T-->>-CTR: ok
    CTR-->>-IU: ok
    R->>+IU: 3: avanzar_ruta(PICKED_UP / IN_TRANSIT / OUT_FOR_DELIVERY)
    IU->>+CTR: 3.1: update_route_status(shipment_id, status)
    CTR->>+CE_E: 3.2: update shipment.status
    CE_E-->>-CTR: ok
    CTR->>+CE_T: 3.3: insert tracking_event(status)
    CE_T-->>-CTR: ok
    CTR-->>-IU: ok
    R->>+IU: 4: entregar(foto, received_by_name)
    IU->>+CTR: 4.1: confirm_delivery(shipment_id, photo, name)
    CTR->>+CE_E: 4.2: update status = DELIVERED, foto, delivered_at
    CE_E-->>-CTR: ok
    CTR->>+CE_R: 4.3: total_deliveries + 1
    CE_R-->>-CTR: ok
    CTR->>+CE_T: 4.4: insert tracking_event(DELIVERED)
    CE_T-->>-CTR: ok
    CTR-->>-IU: ok
    IU-->>-R: Entrega confirmada con evidencia
    Note over R,CE_T: La entrega solo puede marcarse DELIVERED con foto obligatoria
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU29[Paso 1: El repartidor activa su turno y disponibilidad geográfica en la aplicación móvil.]`**
- **`CU29[Paso 1.1: El controlador actualiza is_available = true en la entidad CE_Repartidor.]`**
- **`CU29[Paso 2: El repartidor toma un envío pendiente de la bandeja de despachos (claim_shipment).]`**
- **`CU29[Paso 2.1: El envío pasa a estado 'ASSIGNED' y se registra el hito en CE_EventoTracking.]`**
- **`CU29[Paso 3: Durante el recorrido, el repartidor actualiza los estados operativos (PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY).]`**
- **`CU29[Paso 4: Al arribar a destino, el repartidor captura obligatoriamente la fotografía de entrega y firma/nombre del receptor.]`**
- **`CU29[Paso 4.1: El envío se sella como 'DELIVERED', se incrementa el contador de entregas del repartidor y se registra el evento final.]`**"""

# CU32
updates["CU32"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as IU_Vestidor
    participant CTR as CTR_Analitica
    participant VTON as VirtualTryonAI
    participant HF as FASHN_HF
    participant CE_P as CE_Prenda

    C->>+IU: 1: elegir_prenda(product_id)
    C->>+IU: 2: subir_foto(person_image)
    IU->>+CTR: 3: remove_background(photo)
    CTR->>+VTON: 3.1: segmentar_persona(rembg u2net)
    VTON-->>-CTR: imagen_sin_fondo
    CTR-->>-IU: imagen_sin_fondo
    C->>+IU: 4: ingresar_medidas(estatura, peso, pecho, cintura)
    IU->>+CTR: 4.1: simulate_talla(medidas, product_id)
    CTR->>+CE_P: 4.2: get_product(product_id)
    CE_P-->>-CTR: producto (sizes, measurements)
    CTR-->>-IU: {talla_recomendada, calce_por_zona}
    C->>+IU: 5: generate_vton(persona, prenda)
    IU->>+CTR: 5.1: generar_imagen(persona, prenda)
    CTR->>+VTON: 5.2: ejecutar_pipeline(persona, prenda)
    alt Motor de generacion (cascada nube)
        VTON->>+HF: 5.2a: FASHN.ai tryon
        HF-->>-VTON: imagen_fotorrealista
    else Motor local fallback
        VTON->>VTON: 5.2b: pose + amoldado anatomico
    end
    VTON-->>-CTR: imagen_resultado + modelo_usado
    CTR-->>-IU: {imagen_vestida, modelo}
    IU-->>-C: 6: Mostrar imagen probada en pantalla
    C->>+IU: 7: agregar_al_carrito / reservar_en_tienda
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU32[Paso 1: El cliente selecciona una prenda del catálogo y sube su fotografía de cuerpo completo.]`**
- **`CU32[Paso 2: El sistema remueve automáticamente el fondo de la fotografía mediante el modelo u2net / rembg.]`**
- **`CU32[Paso 3: El cliente ingresa sus parámetros antropométricos (estatura, peso, pecho, cintura y cadera).]`**
- **`CU32[Paso 4: El motor de sizing compara las medidas con la tabla de tallas oficial de CE_Prenda recomendando la talla ideal.]`**
- **`CU32[Paso 5: Se dispara el renderizado virtual de la prenda sobre la fotografía del cliente (Virtual Try-On / VTON).]`**
- **`CU32[Paso 5.1: [alt: FASHN.ai / Local Fallback] El pipeline ejecuta el modelo generativo de ropa o amoldado anatómico.]`**
- **`CU32[Paso 6: El cliente visualiza el resultado fotorrealista con controles de rotación y zoom.]`**
- **`CU32[Paso 7: El cliente procede a añadir la prenda y talla recomendada directamente al carrito (CU17) o a reservarla (CU26).]`**"""

# CU34
updates["CU34"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as IU_Catalogo
    participant REC as Reconocedor_Voz
    participant CTR as CTR_NLP
    participant CE_P as CE_Prenda

    C->>+IU: 1: tocar_microfono()
    IU->>+REC: 1.1: listen(idioma es-*)
    REC-->>-IU: transcripcion: 'vestido rojo hasta 200'
    IU-->>C: Mostrar texto transcrito
    IU->>+CTR: 2: voice_nlp(query_text)
    opt E1: No se reconocen entidades -> búsqueda de texto plano
        Note over CTR: Aplica búsqueda ILIKE en catálogo
    end
    CTR->>CTR: 2.1: extraer_entidades(texto) -> {prenda, color, genero, precio_max}
    CTR->>+CE_P: 2.2: buscar(prenda, precio_max)
    CE_P-->>-CTR: [hasta 10 productos]
    CTR-->>-IU: {productos[], entidades}
    IU-->>-C: 3: Grilla filtrada + chip 'Voz: ...'
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU34[Paso 1: El cliente presiona el icono de micrófono en la barra de búsqueda de la tienda.]`**
- **`CU34[Paso 1.1: El componente web/móvil captura el flujo de audio mediante la API de voz del navegador/dispositivo.]`**
- **`CU34[Paso 1.2: Se transcribe el audio a texto en español y se muestra visualmente al usuario.]`**
- **`CU34[Paso 2: La interfaz envía la cadena transcrita al controlador de procesamiento de lenguaje natural (POST /api/v1/voice/parse).]`**
- **`CU34[Paso 2.1: El controlador extrae entidades clave: tipo de prenda ('vestido'), color ('rojo'), género y tope de precio ('200').]`**
- **`CU34[Paso 2.2: Se consulta el catálogo en CE_Prenda filtrando por las entidades reconocidas y stock disponible.]`**
- **`CU34[Paso 3: La interfaz presenta la grilla de prendas coincidentes con chips interactivos de los filtros aplicados.]`**"""

for cu_id, replacement in updates.items():
    pattern = rf'(### {cu_id}:.*?)(\n#### Diagrama de Secuencia.*?)(\n---\n|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        header = match.group(1)
        trailer = match.group(3)
        content = content[:match.start()] + header + '\n\n' + replacement + '\n' + trailer + content[match.end():]
        print(f"Successfully updated {cu_id}")
    else:
        print(f"Could NOT find pattern for {cu_id}")

with open(doc_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Saved updated documentation successfully!")
