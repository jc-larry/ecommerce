# -*- coding: utf-8 -*-
"""
Script de actualización para sincronizar DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md
con los diagramas canónicos del PDF oficial (25 páginas) y los tags del código backend.
Corrige los 15 Casos de Uso que tenían plantillas genéricas.
"""
import re
import shutil

SOURCE_MD = "documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md"
BACKUP_MD = "documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md.bak"

shutil.copyfile(SOURCE_MD, BACKUP_MD)
print(f"Copia de seguridad creada en {BACKUP_MD}")

with open(SOURCE_MD, "r", encoding="utf-8") as f:
    text = f.read()

REPLACEMENTS = {}

# CU12
REPLACEMENTS["CU12"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente / Visitante
    participant IU as IU_BusquedaCatalogo (Web / Móvil)
    participant CTR as CTR_Catalogo (CatalogService)
    participant CE_P as CE_Producto (products)
    participant CE_V as CE_VariantePrenda (product_variants)
    participant CE_I as CE_Inventario (inventory)

    C->>+IU: 1: ingresarCriterios(texto, categoria_id, talla, color, precio_min/max, branch_id)
    IU->>+CTR: 1.1: buscarProductosConStock(filtros)
    CTR->>+CE_P: 1.2: select_active_products(categoria_id, precio_range, texto)
    CE_P-->>-CTR: productos_base[]
    alt Existen productos coincidentes
        CTR->>+CE_V: 1.3: select_variants(product_ids, talla_id, color_id)
        CE_V-->>-CTR: variantes_coincidentes[]
        CTR->>+CE_I: 1.4: select_stock_by_branch(variant_ids, branch_id)
        CE_I-->>-CTR: existencias_por_sucursal[]
        CTR-->>-IU: HTTP 200 OK (items, catalogo_total, paginas, badge_stock)
        IU-->>-C: mostrarResultados(grilla, existencias, badges_disponibilidad)
    else Sin coincidencias (resultado = [])
        CTR-->>IU: HTTP 200 OK (items: [], total: 0)
        IU-->>C: mostrarMensaje("No se encontraron prendas con esos filtros")
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU12[Paso 1: El cliente o visitante ingresa criterios de búsqueda facetada (categoría, rango de precio, color, talla o texto libre) y opcionalmente selecciona una sucursal física en la web o app móvil.]`**
- **`CU12[Paso 1.1: La interfaz despacha la solicitud de búsqueda al servicio del catálogo (GET /api/v1/catalog/products/search).]`**
- **`CU12[Paso 1.2: El controlador consulta los productos activos que cumplen los filtros base en la tabla products (CE_Producto).]`**
- **`CU12[Paso 1.3: [alt: Existen productos] El controlador recupera las variantes disponibles de talla y color en product_variants (CE_VariantePrenda).]`**
- **`CU12[Paso 1.4: El controlador realiza el cruce con la tabla inventory (CE_Inventario) para calcular el stock físico disponible en la sucursal seleccionada.]`**
- **`CU12[Paso 1.5: La API responde con HTTP 200 OK conteniendo la grilla paginada de prendas con sus insignias de stock en tiempo real.]`**
- **`CU12[Paso 1.6: [alt: Sin coincidencias] Si no existen productos, la API devuelve array vacío y la interfaz sugiere relajar los filtros.]`**"""

# CU13
REPLACEMENTS["CU13"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor A as Superadministrador
    participant IU as IU_GestionPromociones
    participant CTR as CTR_Promociones
    participant CE_C as CE_Cupon
    participant CE_B as CE_BitacoraAuditoria

    A->>+IU: 1: crearNuevoCupon(codigo, tipo_descuento, valor, start_date, end_date, max_usos)
    IU->>+CTR: 1.1: POST /api/v1/promotions/coupons (payload)
    CTR->>+CE_C: 1.2: check_code_exists(codigo)
    CE_C-->>-CTR: exists = false
    alt Código único y fechas consistentes (start_date < end_date)
        CTR->>+CE_C: 1.3: insert_coupon(codigo, tipo, valor, start_date, end_date, max_uses, is_active=true)
        CE_C-->>-CTR: coupon_id = 45
        CTR->>+CE_B: 1.4: insert_log(user_id, action="INSERT", table="coupons", row_id=45)
        CE_B-->>-CTR: log_ok
        CTR-->>-IU: HTTP 201 Created (coupon_data)
        IU-->>-A: mostrarAlerta("Promoción programada con éxito en el calendario")
    else Código duplicado o inconsistencia en rango de fechas
        CTR-->>IU: HTTP 400 Bad Request ("El código ya existe o el rango de fechas es inválido")
        IU-->>A: mostrarErrorValidacion()
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU13[Paso 1: El administrador completa el formulario en el panel web definiendo código alfanumérico, tipo de descuento (porcentaje o monto fijo), vigencia y límite de usos.]`**
- **`CU13[Paso 1.1: La interfaz envía la solicitud de creación de cupón (POST /api/v1/promotions/coupons).]`**
- **`CU13[Paso 1.2: El controlador valida que el código no exista previamente en la tabla coupons (CE_Cupon).]`**
- **`CU13[Paso 1.3: [alt: Fechas válidas y código único] Se persiste el cupón activo en la base de datos con su cuota de canjes.]`**
- **`CU13[Paso 1.4: Se asienta el registro de auditoría en audit_logs (CE_BitacoraAuditoria) y la API retorna HTTP 201 Created.]`**
- **`CU13[Paso 1.5: [alt: Error de validación] Si el código ya existe o las fechas son inconsistentes, se responde HTTP 400 Bad Request.]`**"""

# CU15
REPLACEMENTS["CU15"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor EO as Encargado Sucursal Origen
    actor ED as Encargado Sucursal Destino
    participant IU as Interfaz_Gestion_Inventario
    participant CTR as Controlador_Traspasos_Inventario
    participant CE_I as Entidad_Inventario_Sucursal
    participant CE_K as Entidad_Kardex_Movimientos
    participant CE_T as Entidad_Traspaso_Mercaderia

    rect rgb(255, 250, 240)
    Note over EO,CE_T: Fase 1: Solicitud de Traspaso Inter-Sucursal
    EO->>+IU: 1: solicitarTraspaso(sucursal_origen, sucursal_destino, lista_prendas, cantidades)
    IU->>+CTR: 2: registrarSolicitudTraspaso(datos_traspaso)
    CTR->>+CE_I: 3: verificarStockDisponible(sucursal_origen, prendas)
    CE_I-->>-CTR: 4: stock_suficiente_confirmado
    CTR->>+CE_T: 5: crearRegistroTraspaso(estado="SOLICITADA", codigo="TRF-2026-001")
    CE_T-->>-CTR: 6: traspaso_id = 101
    CTR-->>-IU: 7: confirmacionRegistro(traspaso_id=101)
    IU-->>-EO: 8: notificar("Solicitud de traspaso registrada exitosamente")
    end

    rect rgb(240, 255, 240)
    Note over EO,CE_T: Fase 2: Despacho Físico y Salida de Almacén Origen (Transacción en Origen)
    EO->>+IU: 9: despacharPrendasFisicas(traspaso_id=101)
    IU->>+CTR: 10: procesarSalidaMercaderia(traspaso_id=101)
    CTR->>+CE_I: 11: restarStockOrigen(sucursal_origen, prendas, cantidades)
    CE_I-->>-CTR: 12: stock_origen_descontado
    CTR->>+CE_K: 13: asentarMovimientoSalidaKardex(sucursal_origen, tipo="TRASPASO_SALIDA", ref="TRF-101")
    CE_K-->>-CTR: 14: asiento_salida_registrado
    CTR->>+CE_T: 15: actualizarEstadoTraspaso(traspaso_id=101, nuevo_estado="EN_TRANSITO")
    CE_T-->>-CTR: 16: estado_actualizado
    CTR-->>-IU: 17: confirmacionDespacho()
    IU-->>-EO: 18: notificar("Mercadería en camino a sucursal destino")
    end

    rect rgb(240, 248, 255)
    Note over ED,CE_T: Fase 3: Recepción Física e Ingreso en Almacén Destino (Transacción en Destino)
    ED->>+IU: 19: confirmarRecepcionFisica(traspaso_id=101)
    IU->>+CTR: 20: procesarIngresoMercaderia(traspaso_id=101)
    CTR->>+CE_I: 21: sumarStockDestino(sucursal_destino, prendas, cantidades)
    CE_I-->>-CTR: 22: stock_destino_incrementado
    CTR->>+CE_K: 23: asentarMovimientoIngresoKardex(sucursal_destino, tipo="TRASPASO_INGRESO", ref="TRF-101")
    CE_K-->>-CTR: 24: asiento_ingreso_registrado
    CTR->>+CE_T: 25: actualizarEstadoTraspaso(traspaso_id=101, nuevo_estado="COMPLETADA")
    CE_T-->>-CTR: 26: traspaso_finalizado
    CTR-->>-IU: 27: confirmacionRecepcion()
    IU-->>-ED: 28: notificar("Prendas incorporadas al inventario de la sucursal")
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU15[Paso 1: [Fase Solicitud] El Encargado de la Sucursal de Origen crea una solicitud de traspaso indicando la sucursal de origen, la de destino y la lista de prendas con sus cantidades requeridas.]`**
- **`CU15[Paso 1.1: La interfaz envía la solicitud al controlador (POST /api/v1/merchandise/transfers).]`**
- **`CU15[Paso 1.2: El controlador verifica la disponibilidad física de stock en la sucursal de origen (CE_Inventario_Sucursal).]`**
- **`CU15[Paso 1.3: Se crea el registro del traspaso con estado inicial 'SOLICITADA' y código correlativo TRF-AAAA-XXXXXX en CE_Traspaso_Mercaderia.]`**
- **`CU15[Paso 2: [Fase Despacho] El Encargado de Origen embala las prendas y presiona 'Despachar Mercadería'.]`**
- **`CU15[Paso 2.1: El controlador actualiza el estado del traspaso a 'EN_TRANSITO' (PUT /api/v1/merchandise/transfers/{id}/status).]`**
- **`CU15[Paso 2.2: Se descuentan las existencias físicas del almacén de origen en CE_Inventario_Sucursal.]`**
- **`CU15[Paso 2.3: Se registra el asiento contable de salida 'TRANSFERENCIA_SALIDA' en el Kardex (CE_Kardex_Movimientos).]`**
- **`CU15[Paso 3: [Fase Recepción] El Encargado de Destino recibe el paquete físico, verifica las prendas y pulsa 'Confirmar Recepción'.]`**
- **`CU15[Paso 3.1: La interfaz despacha la confirmación de recepción (PUT /api/v1/merchandise/transfers/{id}/receive).]`**
- **`CU15[Paso 3.2: Se incrementa el stock físico de las variantes en la sucursal de destino en CE_Inventario_Sucursal.]`**
- **`CU15[Paso 3.3: Se asienta el ingreso 'TRANSFERENCIA_INGRESO' en CE_Kardex_Movimientos y el traspaso pasa a estado definitivo 'COMPLETADA'.]`**"""

# CU16
REPLACEMENTS["CU16"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor T as Trigger Demonio Sistema
    actor E as Encargado Sucursal
    participant IU as IU_BandejaAlertas
    participant CTR as CTR_AlertasStock
    participant CE_I as CE_Inventario
    participant CE_A as CE_AlertaStock

    rect rgb(255, 250, 240)
    Note over T,CE_A: Detección Automática de Quiebre de Stock tras Venta o Transferencia
    T->>+CTR: 1: verify_inventory_thresholds(branch_id=1, variant_id=5)
    CTR->>+CE_I: 1.1: select(branch_id=1, variant_id=5)
    CE_I-->>-CTR: stock_actual=2, stock_minimo=6, stock_maximo=50
    alt stock_actual <= stock_minimo
        CTR->>+CE_A: 1.2: insert_alert(branch_id=1, variant_id=5, type='STOCK_MINIMO', severity='CRITICA')
        CE_A-->>-CTR: alert_id = 89
        CTR-->>T: notificacion emitida
    end
    end

    rect rgb(240, 248, 255)
    Note over E,CE_A: Gestión y Visualización de Alertas por el Encargado de Tienda
    E->>+IU: abrirPanelNotificacionesBranch()
    IU->>+CTR: 2: GET /api/v1/inventory/alerts?branch_id=1
    CTR->>+CE_A: 2.1: select_unresolved(branch_id=1)
    CE_A-->>-CTR: alerts_list[]
    CTR-->>-IU: HTTP 200 OK (alerts_con_variantes)
    IU-->>-E: renderizarAlerta(insignia_roja, boton_transferencia_o_compra)
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU16[Paso 1: Tras cada venta, merma o despacho de transferencia, el sistema evalúa los umbrales de stock en CE_Inventario.]`**
- **`CU16[Paso 1.1: El controlador consulta si stock_actual <= stock_minimo para la variante y sucursal.]`**
- **`CU16[Paso 1.2: [alt: Stock Crítico] Se genera automáticamente un registro en stock_alerts (CE_AlertaStock) con severidad 'CRITICA'.]`**
- **`CU16[Paso 2: El Encargado de Sucursal abre el panel de alertas en la aplicación web.]`**
- **`CU16[Paso 2.1: La interfaz consulta las alertas activas no resueltas (GET /api/v1/inventory/alerts?branch_id=X).]`**
- **`CU16[Paso 2.2: Se despliega la lista de prendas críticas con botones de acción rápida para solicitar transferencia (CU15) o compra (CU10).]`**"""

# CU17
REPLACEMENTS["CU17"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as Interfaz_Carrito_Compras (Web / Móvil)
    participant CTR as Controlador_Carrito
    participant CE_I as Entidad_Inventario_Sucursal
    participant CE_IC as Entidad_Item_Carrito
    participant CE_C as Entidad_Carrito

    C->>+IU: 1: agregarPrendaAlCarrito(variante_id=22, sucursal_id=1, cantidad=2)
    IU->>+CTR: 2: registrarItemCarrito(usuario_id, variante_id=22, sucursal_id=1, cantidad=2)
    CTR->>+CE_I: 3: consultarStockDisponible(sucursal_id=1, variante_id=22)
    CE_I-->>-CTR: 4: existencias_actuales = 5
    alt Existencias suficientes (stock >= cantidad requerida)
        CTR->>+CE_IC: 5: guardarOActualizarItem(carrito_id, variante_id=22, cantidad=2)
        CE_IC-->>-CTR: 6: item_guardado
        CTR->>+CE_C: 7: recalcularTotales(carrito_id)
        CE_C-->>-CTR: 8: [subtotal: 350.00, descuento: 0.00, total: 350.00]
        CTR-->>-IU: 9: respuestaExitosa(datos_carrito)
        IU-->>-C: 10: actualizarVistaCarrito(articulos, total=Bs 350.00)
    else Existencias agotadas (stock == 0 o insuficiente)
        CTR-->>IU: 5a: errorExistencias("Prenda temporalmente agotada en la sucursal seleccionada")
        IU-->>C: 6a: deshabilitarBotonYMostrarAlerta()
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU17[Paso 1: El cliente pulsa 'Añadir al Carrito' eligiendo talla, color y cantidad desde la ficha de prenda o el vestidor virtual.]`**
- **`CU17[Paso 1.1: La aplicación web o móvil envía la petición al controlador (POST /api/v1/sales/cart/items).]`**
- **`CU17[Paso 1.2: El controlador consulta las existencias físicas disponibles en la sucursal seleccionada en CE_Inventario_Sucursal.]`**
- **`CU17[Paso 1.3: [alt: Stock Suficiente] Se inserta o actualiza el registro en CE_Item_Carrito vinculándolo al carrito del usuario.]`**
- **`CU17[Paso 1.4: El controlador recalcula subtotales, cupones aplicables e impuestos en CE_Carrito y responde con estado 200 OK.]`**
- **`CU17[Paso 1.5: La interfaz actualiza el panel del carrito y el contador de prendas en la barra de navegación.]`**
- **`CU17[Paso 1.6: [alt: Stock Insuficiente/Agotado] Si no hay existencias suficientes, el sistema responde error 400 y bloquea la adición.]`**"""

# CU20
REPLACEMENTS["CU20"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    participant POS as CTR_Ventas / POS
    participant CTR as CTR_Facturacion
    participant CE_O as CE_Orden
    participant CE_F as CE_Factura
    participant PDF as Servicio_GeneradorPDF
    participant IU as IU_VisorComprobantes

    POS->>+CTR: 1: generate_invoice(order_id=450, nit="489123019", name="Comercial SRL")
    CTR->>+CE_O: 1.1: select_total(order_id=450)
    CE_O-->>-CTR: total_amount = 520.00
    Note over CTR: Cálculo Fiscal Boliviano (IVA 13%):<br/>subtotal = 520.00 | tax_rate = 0.130 | tax_amount = round(520.00 * 0.13, 2) = Bs 67.60
    alt Cliente proporciona NIT/CI válido -> FACTURA FISCAL
        Note over CTR: Generación de Código de Control v7 y Cadena para QR Fiscal
        CTR->>CTR: 1.2: compute_control_code(nit, inv_num, date, key)
        CTR->>+CE_F: 1.3: insert_invoice(order_id=450, doc_type="FACTURA", subtotal=520, tax=67.60, total=520, control_code="A4-5B-7C-1D")
        CE_F-->>-CTR: invoice_id = 789
    else Venta sin NIT o interna -> NOTA DE ENTREGA
        CTR->>+CE_F: 1.4: insert_invoice(order_id=450, doc_type="NOTA_ENTREGA", subtotal=520, tax=67.60, total=520, control_code=null)
        CE_F-->>-CTR: invoice_id = 790
    end
    CTR->>+PDF: 1.5: build_pdf(invoice_id, format="CARTA" o "TICKET")
    PDF-->>-CTR: pdf_stream_bytes
    CTR-->>-POS: invoice_record(id, doc_type, pdf_url)
    POS->>+IU: 2: disponibilizarDescarga(pdf_url)
    IU-->>-POS: url_lista_para_visor
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU20[Paso 1: Al confirmarse cualquier venta (checkout digital, POS en caja o cotización convertida), el motor de ventas invoca la emisión de comprobante.]`**
- **`CU20[Paso 1.1: El controlador fiscal consulta el total de la orden en orders (CE_Orden) y calcula el IVA 13% (tax_amount = round(total * 0.13, 2)).]`**
- **`CU20[Paso 1.2: [alt: Con NIT/CI] Se ejecuta el algoritmo de Código de Control v7 en base al NIT, número de autorización y fecha.]`**
- **`CU20[Paso 1.3: Se persiste el comprobante fiscal en la tabla invoices (CE_Factura) con doc_type = 'FACTURA'.]`**
- **`CU20[Paso 1.4: [alt: Sin NIT / Nota de Entrega] Se guarda el documento sin código de control con doc_type = 'NOTA_ENTREGA'.]`**
- **`CU20[Paso 1.5: Se renderiza el comprobante en formato PDF imprimible (tamaño carta o rollo térmico POS) y se pone a disposición del cliente y cajero.]`**"""

# CU23
REPLACEMENTS["CU23"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cajero
    participant IU as IU_ArqueoCaja
    participant CTR as CTR_Arqueo
    participant CE_S as CE_SesionCaja
    participant CE_P as CE_MedioDePago
    participant CE_D as CE_OrdenDevolucion

    rect rgb(255, 250, 240)
    Note over C,CE_D: Fase 1: Apertura de Turno de Caja al Iniciar la Jornada
    C->>+IU: 1: abrirTurno(monto_inicial_efectivo=200.00)
    IU->>+CTR: 1.1: POST /api/v1/sales/shifts/open (user_id, branch_id=1, opening_amount=200.00)
    CTR->>+CE_S: 1.2: check_active_sessions(user_id)
    CE_S-->>-CTR: active_sessions = 0
    CTR->>+CE_S: 1.3: insert(user_id, branch_id=1, opening_amount=200.00, status='ABIERTA')
    CE_S-->>-CTR: session_id = 45
    CTR-->>-IU: HTTP 201 Created (session_id=45)
    IU-->>-C: habilitarModuloPOS()
    end

    Note over C,CE_D: Operación Normal del Turno: Cobros en Mostrador (CU19) y Devoluciones (CU22)

    rect rgb(240, 248, 255)
    Note over C,CE_D: Fase 2: Cierre de Turno y Arqueo Ciego de Gaveta
    C->>+IU: 2: cerrarTurno(session_id=45, monto_declarado_cajero=1450.00)
    IU->>+CTR: 2.1: POST /api/v1/sales/shifts/45/close (declared_amount=1450.00)
    CTR->>+CE_P: 2.2: sum_cash_sales_by_session(session_id=45)
    CE_P-->>-CTR: ventas_efectivo = 1430.00
    CTR->>+CE_D: 2.3: sum_cash_refunds_by_session(session_id=45)
    CE_D-->>-CTR: devoluciones_efectivo = 180.00
    Note over CTR: Cálculo Teórico Esperado:<br/>Esperado = 200.00 (Apertura) + 1430.00 (Ventas) - 180.00 (Devoluciones) = Bs. 1450.00<br/>Diferencia = Declarado (1450.00) - Esperado (1450.00) = Bs. 0.00 (Cuadre Conforme)
    CTR->>+CE_S: 2.4: update(45, declared=1450.00, expected=1450.00, diff=0.00, status='CERRADA')
    CE_S-->>-CTR: session_closed_ok
    CTR-->>-IU: HTTP 200 OK (reporte_arqueo)
    IU-->>-C: imprimirArqueo(diferencia=0.00, status='CUADRADO')
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU23[Paso 1: [Apertura de Caja] El cajero ingresa el fondo de caja inicial en efectivo (ej. Bs. 200.00) al comenzar su turno.]`**
- **`CU23[Paso 1.1: La interfaz envía la apertura (POST /api/v1/sales/shifts/open).]`**
- **`CU23[Paso 1.2: El controlador valida que el usuario no tenga ya un turno abierto en ninguna sucursal.]`**
- **`CU23[Paso 1.3: Se inserta el registro en cash_shifts (CE_SesionCaja) con status = 'ABIERTA' y se habilita el módulo de venta POS.]`**
- **`CU23[Paso 2: [Cierre Ciego] Al concluir la jornada, el cajero cuenta los billetes en gaveta e introduce su monto contado sin ver el sistema.]`**
- **`CU23[Paso 2.1: La interfaz solicita el cierre (POST /api/v1/sales/shifts/{id}/close con declared_amount).]`**
- **`CU23[Paso 2.2: El controlador suma automáticamente las ventas en efectivo del turno en payments (CE_MedioDePago).]`**
- **`CU23[Paso 2.3: El controlador resta las devoluciones en efectivo del turno registradas en order_returns (CE_OrdenDevolucion).]`**
- **`CU23[Paso 2.4: Se calcula el esperado (Apertura + Ventas - Devoluciones) y la diferencia matemática (Declarado - Esperado), guardando el turno como 'CERRADA' e imprimiendo el arqueo.]`**"""

# CU24
REPLACEMENTS["CU24"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as IU_HistorialCompras (Web / Móvil)
    participant CTR as CTR_Historial
    participant CE_O as CE_Orden
    participant CE_IO as CE_ItemOrden
    participant CE_P as CE_MedioDePago
    participant CE_F as CE_Factura (invoices)

    C->>+IU: 1: presionarPestanaMisCompras()
    IU->>+CTR: 1.1: GET /api/v1/sales/orders/my-orders (token_jwt)
    CTR->>+CE_O: 1.2: select_orders_by_user(user_id, order_by_created_at_desc)
    CE_O-->>-CTR: orders_summary[]
    CTR-->>-IU: HTTP 200 OK (orders_list)
    IU-->>-C: renderizarTarjetasPedidos(num_orden, fecha, total_bs, canal)

    C->>+IU: 2: verDetalleOrden(order_id=450)
    IU->>+CTR: 2.1: GET /api/v1/sales/orders/450
    rect rgb(250, 250, 250)
    Note over CTR,CE_F: Carga en Cascada del Detalle de Orden
    CTR->>+CE_IO: 2.2a: select_items_with_product(order_id=450)
    CE_IO-->>-CTR: items[(sku, product_name, color, size, price, qty)]
    CTR->>+CE_P: 2.2b: select_payment_details(order_id=450)
    CE_P-->>-CTR: payment_type: "TARJETA", last4: "4512"
    CTR->>+CE_F: 2.2c: select_invoice(order_id=450)
    CE_F-->>-CTR: doc_type: "FACTURA", total: 520.00, pdf_path: "/pdf/0450.pdf"
    end
    CTR-->>-IU: HTTP 200 OK (order_complete_profile)
    IU-->>-C: mostrarModalDetalle(prendas, desglose_iva, descargar_factura)

    C->>+IU: 3: presionarDescargarFactura()
    IU-->>-C: descargarArchivoPDF(Factura_ORD-450.pdf)
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU24[Paso 1: El cliente autenticado hace clic en 'Mis compras' en la web (/tienda/pedidos) o en la app móvil.]`**
- **`CU24[Paso 1.1: La interfaz consulta la lista de pedidos del usuario (GET /api/v1/sales/orders/my-orders).]`**
- **`CU24[Paso 1.2: El controlador recupera las órdenes ordenadas por fecha en orders (CE_Orden) y las despliega en tarjetas con número y estado.]`**
- **`CU24[Paso 2: El cliente selecciona un pedido para ver el detalle pormenorizado.]`**
- **`CU24[Paso 2.1: La interfaz solicita el detalle completo (GET /api/v1/sales/orders/{id}).]`**
- **`CU24[Paso 2.2: El backend realiza la carga en cascada: ítems adquiridos con fotos y variantes (CE_ItemOrden), comprobante fiscal emitido (CE_Factura) y medios de pago aplicados (CE_MedioDePago).]`**
- **`CU24[Paso 3: El cliente puede pulsar 'Descargar Factura' para abrir o imprimir el archivo PDF oficial generado.]`**"""

# CU28
REPLACEMENTS["CU28"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente / Encargado
    participant IU as IU_Reservas
    participant CTR as CTR_Reservas
    participant CE_R as CE_Reserva
    participant CE_I as CE_Inventario
    participant CE_L as CE_LibroMayor

    Note over C,CE_L: Precondición: Reserva en estado PENDING, PREPARING o READY
    C->>+IU: 1: cancelarReserva(reserva_id=14, motivo)
    IU->>+CTR: 1.1: PUT /api/v1/reservations/14/cancel
    CTR->>+CE_R: 1.2: get_reservation_items(reserva_id=14)
    CE_R-->>-CTR: items = [{variante_id=5, qty=2}, {variante_id=8, qty=1}]
    loop Para cada prenda de la reserva
        CTR->>+CE_I: 1.3: update_stock(branch_id=1, var_id, qty=+cant)
        CE_I-->>-CTR: OK
        CTR->>+CE_L: 1.4: insert_entry(branch_id=1, var_id, qty=+cant, type='CANCELACION_RESERVA')
        CE_L-->>-CTR: OK
    end
    CTR->>+CE_R: 1.5: update_status(14, 'CANCELLED')
    CE_R-->>-CTR: OK
    CTR-->>-IU: HTTP 200 OK (status='CANCELLED')
    IU-->>-C: mostrarAviso("Reserva cancelada y stock liberado")
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU28[Paso 1: El cliente antes de la cita o el encargado por inasistencia (tolerancia 30 min) presiona 'Cancelar Reserva'.]`**
- **`CU28[Paso 1.1: La interfaz envía la solicitud de cancelación (PUT /api/v1/reservations/{id}/cancel).]`**
- **`CU28[Paso 1.2: El controlador recupera las prendas y cantidades apartadas en reservation_items (CE_Reserva).]`**
- **`CU28[Paso 1.3: [loop: Por cada prenda] Se reintegra el stock físico sumando la cantidad en la tabla inventory (CE_Inventario).]`**
- **`CU28[Paso 1.4: Se asienta el asiento de reversión en inventory_ledger (CE_LibroMayor) con movement_type = 'CANCELACION_RESERVA'.]`**
- **`CU28[Paso 1.5: El estado de la reserva se actualiza a 'CANCELLED' o 'NO_SHOW' y se notifica al usuario.]`**"""

# CU30
REPLACEMENTS["CU30"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente / Repartidor
    participant IU as IU_Rastreo
    participant CTR as CTR_Logistica
    participant CE_E as CE_Envio
    participant CE_ET as CE_EventosTracking

    C->>+IU: 1: buscarEnvio(tracking_number="TRK-A1B2C3D4")
    IU->>+CTR: 1.1: track_shipment(tracking_number)
    CTR->>+CE_E: 1.2: select WHERE tracking_number = "TRK-A1B2C3D4"
    CE_E-->>-CTR: shipment (status='EN_CAMINO', address, repartidor_id)
    CTR->>+CE_ET: 1.3: select tracking_events WHERE shipment_id = id
    CE_ET-->>-CTR: [(status, location, description, created_at)]
    CTR-->>-IU: HTTP 200 OK (shipment_timeline[])
    IU-->>-C: Mostrar estado actual, repartidor y línea de tiempo en mapa
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU30[Paso 1: El cliente o repartidor ingresa el código de seguimiento (ej. TRK-A1B2C3D4) en la sección de envíos.]`**
- **`CU30[Paso 1.1: La interfaz realiza la consulta (GET /api/v1/logistics/shipments/track/{tracking_number}).]`**
- **`CU30[Paso 1.2: El controlador consulta los datos generales del despacho en shipments (CE_Envio).]`**
- **`CU30[Paso 1.3: El controlador recupera los hitos cronológicos auditados en tracking_events (CE_EventosTracking).]`**
- **`CU30[Paso 1.4: La interfaz renderiza la barra de progreso (Preparando -> En camino -> Entregado) con coordenadas y hora estimada.]`**"""

# CU31
REPLACEMENTS["CU31"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor S as Superadmin
    participant IU as IU_DeliveryZonas
    participant CTR as CTR_Logistica
    participant CE_DZ as CE_DeliveryZone

    S->>+IU: 1: gestionar_zonas()
    IU->>+CTR: 1.1: GET /api/v1/logistics/zones
    CTR->>+CE_DZ: 1.2: select * FROM delivery_zones
    CE_DZ-->>-CTR: [zones]
    CTR-->>-IU: HTTP 200 OK (zones con mapa Leaflet)
    IU-->>-S: Mostrar mapa y anillos concéntricos

    S->>+IU: 2: crear_zona(name, min_km, max_km, base_rate, estimated_hours)
    IU->>+CTR: 2.1: POST /api/v1/logistics/zones (data)
    CTR->>+CE_DZ: 2.2: insert delivery_zone
    CE_DZ-->>-CTR: zone_id = 4
    CTR-->>-IU: HTTP 201 Created
    IU-->>-S: Zona agregada al mapa

    opt Calcular tarifa según distancia
    S->>+IU: 3: calcular_tarifa(distance_km=12.5)
    IU->>+CTR: 3.1: calculate_rate(distance_km=12.5)
    CTR->>+CE_DZ: 3.2: select WHERE min_km <= 12.5 AND max_km >= 12.5
    alt Distancia supera zona más lejana -> tarifa base + recargo/km
        CE_DZ-->>CTR: null
        CTR->>CTR: tarifa_base + (distancia - max_km) * 5.0
    else Dentro de rango de zona
        CE_DZ-->>CTR: zona (base_rate, estimated_hours)
    end
    CTR-->>-IU: (tarifa=Bs 25.00, horas=24)
    IU-->>-S: Mostrar tarifa calculada en checkout
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU31[Paso 1: El administrador accede a 'Zonas de Envío' en el panel logístico.]`**
- **`CU31[Paso 1.1: La interfaz carga los polígonos y radios de cobertura desde delivery_zones (CE_DeliveryZone).]`**
- **`CU31[Paso 2: El Superadmin define una nueva zona radial (ej. Zona 3: 8 a 15 km, tarifa Bs. 25.00, plazo 24 hrs).]`**
- **`CU31[Paso 2.1: La interfaz persiste la regla en la base de datos (POST /api/v1/logistics/zones).]`**
- **`CU31[Paso 3: [opt: Cotización en Checkout] Durante el pago del cliente, el sistema calcula la distancia y devuelve la tarifa de envío exacta.]`**"""

# CU33
REPLACEMENTS["CU33"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor C as Cliente / Visitante
    participant IU as IU_Chatbot
    participant CTR as CTR_Analitica
    participant CE_C as CE_Conversacion

    C->>+IU: 1: abrir_chatbot()
    IU-->>-C: Widget de chat abierto

    C->>+IU: 2: enviar_mensaje("Busco un vestido elegante para fiesta en Equipetrol")
    IU->>+CTR: 2.1: POST /api/v1/analytics/chatbot/message (session_token, message)
    CTR->>CTR: 2.2: detectar_intencion(message) -> STYLE_RECOMMENDATION
    opt Intención detectada (GREETING / CATALOG_SEARCH / STYLE_RECOMMENDATION / SIZE_ADVICE)
        CTR->>CTR: 2.3: buscar prendas afines con stock activo en sucursal
        CTR->>CTR: 2.4: generar_respuesta(intencion, contexto, sugerencias)
    end
    CTR->>+CE_C: 2.5: insert conversacion(USER + BOT)
    CE_C-->>-CTR: OK
    CTR-->>-IU: HTTP 200 OK (respuesta, prendas_sugeridas[], acciones_rapidas[])
    IU-->>-C: Mostrar respuesta de estilo + prendas interactivas con enlace a probador
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU33[Paso 1: El usuario pulsa la burbuja flotante del Asistente Virtual en la web o app móvil.]`**
- **`CU33[Paso 2: El cliente escribe o dicta una consulta sobre estilo, ocasión, tallas o tiendas físicas.]`**
- **`CU33[Paso 2.1: La interfaz envía el mensaje al motor conversacional (POST /api/v1/analytics/chatbot/message).]`**
- **`CU33[Paso 2.2: El controlador clasifica la intención (GREETING, STYLE_RECOMMENDATION, SIZE_ADVICE, STORE_INFO, ORDER_TRACKING).]`**
- **`CU33[Paso 2.3: [opt: Recomendación] El motor filtra prendas activas con existencias físicas en la tienda consultada.]`**
- **`CU33[Paso 2.4: Se persiste la interacción en chatbot_conversations (CE_Conversacion) y se retorna la respuesta con tarjetas de producto interactivas.]`**"""

# CU35
REPLACEMENTS["CU35"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor S as Superadmin
    participant IU as IU_Reportes
    participant CTR as CTR_Analitica
    participant CE_O as CE_Orden
    participant CE_I as CE_Inventario

    S->>+IU: 1: acceder_reportes(tipo_filtro, fecha_inicio, fecha_fin)
    IU->>+CTR: 1.1: GET /api/v1/analytics/reports/executive
    alt Tipo de reporte = Top Selling / Executive Summary
        CTR->>+CE_O: 1.2: select ventas_agregadas(orders, order_items, payments)
        CE_O-->>-CTR: metricas_ventas[(ingresos, ticket_promedio, mas_vendidos)]
    else Tipo de reporte = Kardex / Stock Summary
        CTR->>+CE_I: 1.3: select inventario_agregado(inventory, inventory_ledger)
        CE_I-->>-CTR: metricas_inventario[(rotacion, valoracion_cpp, alertas)]
    end
    CTR-->>-IU: HTTP 200 OK (reporte_metrico)
    IU-->>-S: Mostrar reporte y gráficas interactivas en dashboard

    S->>+IU: 2: exportar_csv(reporte_id)
    IU->>+CTR: 2.1: GET /api/v1/analytics/reports/export-csv
    CTR-->>-IU: HTTP 200 OK (archivo CSV con cabeceras)
    IU-->>-S: Descarga automática de archivo en navegador

    opt Lectura por voz
    S->>+IU: 3: leer_por_voz(reporte_id)
    IU->>+CTR: 3.1: POST /api/v1/analytics/reports/voice-summary
    CTR-->>-IU: audio_stream (TTS)
    IU-->>-S: La síntesis de voz lee el resumen ejecutivo de ventas e inventario
    end
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU35[Paso 1: El Superadministrador accede al centro de 'Reportes Gerenciales' y selecciona el tipo de informe (Ventas, Kardex, Rendimiento o Cajeros).]`**
- **`CU35[Paso 1.1: La interfaz solicita los indicadores agregados (GET /api/v1/analytics/reports/executive).]`**
- **`CU35[Paso 1.2: [alt: Ventas] El controlador agrega métricas de orders y payments (CE_Orden).]`**
- **`CU35[Paso 1.3: [alt: Kardex] El controlador agrega movimientos y valoración en inventory_ledger (CE_Inventario).]`**
- **`CU35[Paso 2: El administrador puede presionar 'Exportar CSV' para descargar la planilla tabular de datos.]`**
- **`CU35[Paso 3: [opt: Voz] Si activa el lector por voz, el sistema genera la síntesis por voz del resumen ejecutivo.]`**"""

# CU39
REPLACEMENTS["CU39"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor S as Superadmin
    participant IU as IU_Dashboard
    participant CTR as CTR_Analitica
    participant CE_O as CE_Orden
    participant CE_I as CE_Inventario

    S->>+IU: 1: abrir_dashboard()
    IU->>+CTR: 1.1: GET /api/v1/analytics/dashboard/metrics
    CTR->>+CE_O: 1.2: select ventas ONLINE vs POS, ingresos_totales, ordenes_hoy
    CE_O-->>-CTR: [metricas_ventas]
    CTR->>+CE_I: 1.3: select stock_global, alertas_criticas, prendas_agotadas
    CE_I-->>-CTR: [metricas_inventario]
    CTR->>CTR: 1.4: calcular_kpis(ventas, rotacion, alertas)
    CTR-->>-IU: HTTP 200 OK (kpis, series_temporales, graficos_donut)
    IU-->>-S: Mostrar dashboard integral con indicadores en tiempo real
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU39[Paso 1: El Superadministrador ingresa al panel principal (/admin/dashboard).]`**
- **`CU39[Paso 1.1: La interfaz solicita las métricas consolidadas (GET /api/v1/analytics/dashboard/metrics).]`**
- **`CU39[Paso 1.2: El controlador consulta los ingresos de ventas online y ventas POS presenciales en orders (CE_Orden).]`**
- **`CU39[Paso 1.3: El controlador consulta el stock global y las alertas de quiebre en inventory (CE_Inventario).]`**
- **`CU39[Paso 1.4: El controlador calcula la tasa de rotación y salud del inventario, retornando las series para las gráficas.]`**"""

# CU40
REPLACEMENTS["CU40"] = """#### Diagrama de Secuencia (Mermaid):
```mermaid
sequenceDiagram
    actor U as Usuario
    participant IU as IU_Notificaciones
    participant CTR as CTR_Notificaciones
    participant CE_N as CE_NotificacionInApp
    participant SMTP as Servicio_SMTP
    participant CE_DP as CE_DispositivoPush

    Note over U,CE_DP: Precondición: Evento del sistema (Venta PAGADA, Reserva REGISTRADA, Despacho)
    CTR->>+CE_N: 1: create_inapp_notification(user_id, title, message, type)
    CE_N-->>-CTR: notification_id = 120
    opt Evento crítico requiere email (Venta confirmada, Comprobante fiscal, Cita probador)
        CTR->>+SMTP: 1.1: email_dispatch(destinatario, asunto, plantilla_html)
        SMTP-->>-CTR: OK
    end
    opt Dispositivo móvil con token registrado
        CTR->>+CE_DP: 1.2: push_dispatch(token_fcm, title, body)
        CE_DP-->>-CTR: OK
    end

    Note over U,CE_DP: Consulta del Buzón in-app por el Usuario
    U->>+IU: 2: presionarIconoCampana()
    IU->>+CTR: 2.1: GET /api/v1/notifications/my
    CTR->>+CE_N: 2.2: select WHERE user_id = ? ORDER BY created_at DESC
    CE_N-->>-CTR: [notificaciones[], unread_count=3]
    CTR-->>-IU: HTTP 200 OK (notificaciones[], unread=3)
    IU-->>-U: Mostrar lista desplegable con insignia de no leídas

    U->>+IU: 3: marcarNotificacionLeida(notification_id=120)
    IU->>+CTR: 3.1: PUT /api/v1/notifications/120/read
    CTR->>+CE_N: 3.2: update is_read = true WHERE id = 120
    CE_N-->>-CTR: OK
    CTR-->>-IU: HTTP 200 OK
    IU-->>-U: Actualizar insignia y marcar leída
```

#### Desglose Paso a Paso (Nomenclatura Correlativa Formal):
- **`CU40[Paso 1: Ante cualquier evento clave (compra aprobada, cita de reserva, salida de delivery o alerta de stock), el orquestador dispara la notificación.]`**
- **`CU40[Paso 1.1: Se crea el mensaje in-app en user_notifications (CE_NotificacionInApp).]`**
- **`CU40[Paso 1.2: [opt: Correo] Si es un comprobante fiscal o confirmación de compra, el servicio SMTP despacha el email transaccional.]`**
- **`CU40[Paso 1.3: [opt: Push móvil] Si el usuario usa la app Flutter, se envía notificación push al dispositivo.]`**
- **`CU40[Paso 2: El usuario abre la campana de notificaciones en la barra de navegación.]`**
- **`CU40[Paso 2.1: La interfaz consulta la bandeja in-app (GET /api/v1/notifications/my).]`**
- **`CU40[Paso 3: El usuario hace clic en una notificación para marcarla como leída (PUT /api/v1/notifications/{id}/read).]`**"""

# Now replace each in text
pattern_template = r"(### {cu}:[^\n]+(?:\n(?!### CU|\Z)[^\n]*)*?)(#### Diagrama de Secuencia \(Mermaid\):.*?)(?=(?:\n### CU|\Z))"

for cu, repl in REPLACEMENTS.items():
    # find section for cu
    pos = text.find(f"### {cu}:")
    if pos == -1:
        print(f"ERROR: {cu} not found in text")
        continue
    next_cu_pos = text.find("\n### CU", pos + 10)
    section = text[pos:next_cu_pos] if next_cu_pos != -1 else text[pos:]
    
    # replace from "#### Diagrama de Secuencia (Mermaid):" to the end of section
    diag_pos = section.find("#### Diagrama de Secuencia (Mermaid):")
    if diag_pos == -1:
        print(f"ERROR: {cu} has no Diagrama de Secuencia section")
        continue
    
    new_section = section[:diag_pos] + repl + "\n\n---\n"
    if next_cu_pos != -1:
        text = text[:pos] + new_section + text[next_cu_pos+1:]
    else:
        text = text[:pos] + new_section
    print(f"SUCCESS: {cu} updated successfully")

with open(SOURCE_MD, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Documento {SOURCE_MD} actualizado con éxito!")
