import uuid
from datetime import datetime, timedelta, timezone, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db

from app.packages.paquete_ventas_y_pagos.models import (
    Order, OrderItem, Payment, EfectivoPayment, TarjetaPayment, QRPayment, PayPalPayment, CreditoPayment,
    Invoice, Cart, CartItem, CashShift, Quotation, QuotationItem, OrderReturn, OrderReturnItem, CreditNote,
)
from app.packages.paquete_ventas_y_pagos.schemas import (
    CartItemAdd, CartItemUpdate, CartItemResponse, CartResponse,
    CheckoutRequest, OrderResponse, OrderItemResponse, PaymentResponse, InvoiceResponse,
    CashShiftOpen, CashShiftClose, CashShiftResponse, BranchOrderFulfillmentUpdate,
    QuotationCreate, QuotationResponse, QuotationConvertRequest,
    OrderReturnCreate, OrderReturnResponse, CustomerReturnResponse, CustomerReturnItemResponse,
    InvoiceItemDetail, InvoiceLookupResponse, CreditNoteResponse,
)
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import Product, ProductVariant, Color, Size, Coupon, SeasonalPromotion
from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger
from app.packages.paquete_reservas_y_citas.models import Reservation
from app.packages.paquete_seguridad_usuarios import User, RoleChecker, log_event, get_current_user, get_branch_scope, BranchScope
from app.packages.paquete_ventas_y_pagos.paypal_service import paypal_service
from app.packages.paquete_notificaciones.service import notificar, TIPO_PEDIDO

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])

staff_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO", "CAJERO"])
# Cotizaciones, conversión y devoluciones son decisiones del encargado de sucursal (no del cajero).
manager_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO"])


def _get_product_effective_price(db: Session, prod: Optional[Product]) -> float:
    """[CU13] Devuelve el precio unitario efectivo de una prenda considerando promociones estacionales activas."""
    if not prod:
        return 0.0
    base = float(prod.base_price or 0.0)
    today = date.today()
    if prod.season_id:
        active_promo = (
            db.query(SeasonalPromotion)
            .filter(
                SeasonalPromotion.season_id == prod.season_id,
                SeasonalPromotion.is_active == True,
                SeasonalPromotion.start_date <= today,
                SeasonalPromotion.end_date >= today,
            )
            .order_by(SeasonalPromotion.discount_percent.desc())
            .first()
        )
        if active_promo:
            disc = round(base * (active_promo.discount_percent / 100.0), 2)
            return max(0.0, round(base - disc, 2))
    return base


# ===================================================================
# Diagnóstico PayPal
# ===================================================================

@router.get("/health/paypal-status")
async def paypal_status_check():
    """Diagnóstico de conexión con PayPal y validez de credenciales."""
    return await paypal_service.check_connection()


@router.post("/debug/paypal-test-order")
async def paypal_test_order_creation(
    amount_bob: float = 100.0,
    reference_id: str = "TEST-ORDER-DEBUG",
):
    """[DEBUG] Crea una orden de prueba en PayPal y devuelve la respuesta completa.

    Esto te permite ver exactamente qué está rechazando PayPal.
    Parámetros:
    - amount_bob: cantidad en Bolivianos (default 100.0)
    - reference_id: ID de referencia (default TEST-ORDER-DEBUG)
    """
    try:
        result = await paypal_service.create_order(
            amount_bob=amount_bob,
            reference_id=reference_id,
            description=f"Test Order - {reference_id}",
        )
        return {
            "success": True,
            "order": result,
            "message": "Orden de prueba creada exitosamente en PayPal",
        }
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code,
            "message": "PayPal rechazó la orden de prueba",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error inesperado",
        }


@router.post("/paypal/capture-order")
async def capture_paypal_order(paypal_order_id: str):
    """Captura una orden de PayPal después de que el usuario la apruebe.

    Se llama desde el frontend cuando vuelve de PayPal (return_url).
    """
    try:
        result = await paypal_service.capture_order(paypal_order_id)
        return {
            "success": True,
            "capture": result,
            "message": "Orden capturada exitosamente",
        }
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code,
            "message": "PayPal no pudo capturar la orden",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error inesperado",
        }


# ===================================================================
# CU17 — Carrito de Compras Digital
# ===================================================================

def _get_or_create_cart(db: Session, user: Optional[User], session_id: Optional[str] = None) -> Cart:
    cart = None
    if user:
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    elif session_id:
        cart = db.query(Cart).filter(Cart.session_id == session_id).first()

    if not cart:
        cart = Cart(
            user_id=user.id if user else None,
            session_id=session_id if not user else None,
        )
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _build_cart_response(db: Session, cart: Cart) -> CartResponse:
    items_resp = []
    subtotal = 0.0

    for item in cart.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            continue
        prod = db.query(Product).filter(Product.id == variant.product_id).first()
        size = db.query(Size).filter(Size.id == variant.size_id).first()
        color = db.query(Color).filter(Color.id == variant.color_id).first()

        unit_price = _get_product_effective_price(db, prod)
        item_subtotal = round(unit_price * item.quantity, 2)
        subtotal += item_subtotal

        # Stock total disponible entre todas las sucursales
        stock_sum = (
            db.query(func.sum(Inventory.stock_actual))
            .filter(Inventory.variant_id == item.variant_id)
            .scalar() or 0
        )

        items_resp.append(
            CartItemResponse(
                id=item.id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=item_subtotal,
                sku=variant.sku,
                product_name=prod.name if prod else "Prenda",
                size=size.name if size else "Única",
                color=color.name if color else "Estándar",
                image_url=prod.images[0].image_url if (prod and prod.images) else None,
                stock_available=int(stock_sum),
            )
        )

    return CartResponse(
        id=cart.id,
        items=items_resp,
        subtotal=round(subtotal, 2),
        items_count=sum(i.quantity for i in items_resp),
    )


@router.get("/cart", response_model=CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Consulta el carrito de compras digital del usuario autenticado."""
    # [CU17 - Op: Consultar Carrito] +1. get_cart(user_id)
    cart = _get_or_create_cart(db, current_user)
    return _build_cart_response(db, cart)


# [CU17 - Paso 1] (IU) El cliente añade una variante de prenda al carrito en IU_Catalogo
@router.post("/cart/items", response_model=CartResponse)
# [CU17 - Paso 2] / [DSC017 - Paso 2] +1. add_to_cart(variant_id, quantity)
def add_to_cart(
    item_in: CartItemAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Agrega una prenda al carrito con control estricto de existencias (bloqueo stock = 0)."""
    variant = db.query(ProductVariant).filter(ProductVariant.id == item_in.variant_id).first()
    if not variant or not variant.is_active:
        raise HTTPException(status_code=404, detail="Variante de prenda no encontrada o inactiva.")

    # [CU17 - Paso 3] / [DSC017 - Paso 3] +2. get_stock(branch_id, variant_id) / stock_actual
    stock_total = (
        db.query(func.sum(Inventory.stock_actual))
        .filter(Inventory.variant_id == item_in.variant_id)
        .scalar() or 0
    )
    # [CU17 - Paso 1.6] / [DSC017 - Paso 1.6] [alt: stock_actual == 0 (Agotado)]
    if stock_total <= 0:
        raise HTTPException(
            status_code=400,
            detail="La prenda se encuentra temporalmente agotada en todas las sucursales (stock = 0)."
        )

    cart = _get_or_create_cart(db, current_user)
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.variant_id == item_in.variant_id
    ).first()

    desired_qty = item_in.quantity + (existing_item.quantity if existing_item else 0)
    if desired_qty > stock_total:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Solo quedan {stock_total} unidades disponibles."
        )

    # [CU17 - Paso 5] / [DSC017 - Paso 5] +3. upsert_cart_item(cart_id, variant_id, quantity)
    if existing_item:
        existing_item.quantity = desired_qty
    else:
        db.add(CartItem(cart_id=cart.id, variant_id=item_in.variant_id, quantity=item_in.quantity))

    db.commit()
    # [CU17 - Paso 7] / [DSC017 - Paso 7] +4. recalculate_totals(cart_id) y retornar drawer carrito actualizado
    return _build_cart_response(db, cart)


@router.put("/cart/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    item_in: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Actualiza la cantidad de un ítem en el carrito (0 lo elimina)."""
    # [CU17 - Op: Actualizar Cantidad] +1. update_cart_item(item_id, quantity)
    cart = _get_or_create_cart(db, current_user)
    cart_item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado en el carrito.")

    if item_in.quantity <= 0:
        db.delete(cart_item)
    else:
        stock_total = (
            db.query(func.sum(Inventory.stock_actual))
            .filter(Inventory.variant_id == cart_item.variant_id)
            .scalar() or 0
        )
        if item_in.quantity > stock_total:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente. Solo quedan {stock_total} unidades disponibles."
            )
        cart_item.quantity = item_in.quantity

    db.commit()
    return _build_cart_response(db, cart)


@router.delete("/cart/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Quita un producto del carrito digital."""
    # [CU17 - Op: Eliminar Ítem] +1. remove_cart_item(item_id)
    cart = _get_or_create_cart(db, current_user)
    db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).delete()
    db.commit()
    return _build_cart_response(db, cart)


@router.delete("/cart/clear", response_model=CartResponse)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Vacía completamente el carrito digital."""
    # [CU17 - Op: Vaciar Carrito] +1. clear_cart(cart_id)
    cart = _get_or_create_cart(db, current_user)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return _build_cart_response(db, cart)


# ===================================================================
# CU18, CU19, CU20 — Checkout Polimórfico, POS y Facturación IVA 13%
# ===================================================================

def _build_order_response(db: Session, order: Order) -> OrderResponse:
    items_resp = []
    for it in order.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == it.variant_id).first()
        prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
        size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
        color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None

        items_resp.append(
            OrderItemResponse(
                id=it.id,
                variant_id=it.variant_id,
                quantity=it.quantity,
                unit_price=float(it.unit_price),
                subtotal=round(float(it.unit_price) * it.quantity, 2),
                product_name=prod.name if prod else "Prenda",
                sku=variant.sku if variant else "N/A",
                size=size.name if size else "Única",
                color=color.name if color else "Estándar",
            )
        )

    payments_resp = [
        PaymentResponse(
            id=p.id,
            payment_type=p.payment_type,
            amount=float(p.amount),
            status=p.status,
            paid_at=p.paid_at,
            cash_received=float(p.cash_received) if p.cash_received is not None else None,
            cash_change=float(p.cash_change) if p.cash_change is not None else None,
            card_brand=p.card_brand,
            card_last4=p.card_last4,
            gateway_reference=p.gateway_reference,
            qr_reference=p.qr_reference,
            paypal_payer_id=p.paypal_payer_id,
            paypal_payer_email=p.paypal_payer_email,
        )
        for p in order.payments
    ]

    inv_resp = None
    if order.invoice:
        inv = order.invoice
        qr_payload = f"NIT:{inv.customer_nit or '0'}|FAC:{inv.id}|AUT:18273645|TOTAL:{inv.total}|IVA:{inv.tax_amount}|FECHA:{inv.issued_at.isoformat()}|COD:{inv.control_code or 'N/A'}"
        inv_resp = InvoiceResponse(
            id=inv.id,
            doc_type=inv.doc_type,
            subtotal=float(inv.subtotal),
            tax_rate=float(inv.tax_rate),
            tax_amount=float(inv.tax_amount),
            total=float(inv.total),
            control_code=inv.control_code,
            customer_nit=inv.customer_nit,
            customer_name=inv.customer_name,
            issued_at=inv.issued_at,
            qr_payload=qr_payload,
        )

    order_num = f"ORD-{order.created_at.year}-{order.id:06d}"

    # Buscar despacho/envío asociado (CU29, CU30)
    from app.packages.paquete_envios_y_logistica.models import Shipment
    ship = db.query(Shipment).filter(Shipment.order_id == order.id).first()

    return OrderResponse(
        id=order.id,
        order_number=order_num,
        channel=order.channel,
        status=order.status,
        subtotal=float(order.subtotal),
        discount_amount=float(order.discount_amount),
        coupon_code=order.coupon_code,
        total_amount=float(order.total_amount),
        created_at=order.created_at,
        items=items_resp,
        payments=payments_resp,
        invoice=inv_resp,
        tracking_number=ship.tracking_number if ship else None,
        delivery_address=ship.delivery_address if ship else None,
        shipping_method="DELIVERY" if ship else ("PICKUP" if order.channel == "ONLINE" else "PRESENCIAL"),
        delivery_type=getattr(order, "delivery_type", "ENVIO_DOMICILIO"),
        pickup_deadline=getattr(order, "pickup_deadline", None),
        payment_session_expires_at=getattr(order, "payment_session_expires_at", None),
    )


# [DSC019 - Mensaje 1] Cajero -> IU_POS: 1: ingresarVentaDirecta(sesion_id, items, efectivo_recibido, nit_ci)
# [DSC018 - Mensaje 1] Cliente -> IU_Checkout: 1: iniciarCheckout(sucursal_id, delivery_type, medio_pago, nit_ci, coupon_code)
# [DSC019 - Mensaje 2] IU_POS -> CTR_POS: 2: POST /api/v1/pos/orders (PosCheckoutDTO)
@router.post("/pos/orders", response_model=OrderResponse, status_code=201)
# [DSC018 - Mensaje 2] IU_Checkout -> CTR_Ventas: 2: POST /api/v1/sales/checkout (CheckoutRequest)
@router.post("/checkout", response_model=OrderResponse, status_code=201)
def process_checkout(
    data: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU18 / CU19 / CU20] Procesa una compra omnicanal (E-commerce / POS) con facturación IVA 13% y control transaccional ACID."""
    # CU18[Paso 1] / CU19[Paso 1.1]: Validación de canal de atención y contexto de sucursal
    # [Separación por sucursal] Una venta POS es una operación de personal de tienda: exige
    # rol de staff y fuerza la sucursal real del usuario (ignora branch_id del cliente).
    if data.channel == "POS" or request.url.path.endswith("/pos/orders"):
        data.channel = "POS"
        user_roles = [r.name for r in current_user.roles]
        if not any(r in user_roles for r in ("SUPERADMIN", "ENCARGADO", "CAJERO")):
            raise HTTPException(status_code=403, detail="Solo el personal de tienda puede registrar ventas en POS.")
        scope = get_branch_scope(current_user, db)
        if not scope.is_central:
            data.branch_id = scope.branch_id

    branch = db.query(Branch).filter(Branch.id == data.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    # Se consulta la entidad CE_SesionCaja y se verifica que session_status == "ABIERTA" y pertenezca al cajero
    if data.channel == "POS":
        if not data.cash_shift_id:
            raise HTTPException(status_code=400, detail="Ventas en POS requieren un turno de caja activo (cash_shift_id).")
        # [DSC019 - Mensaje 3] CTR_POS -> CE_SesionCaja: 3: get_active_shift(sesion_id)
        shift = db.query(CashShift).filter(
            CashShift.id == data.cash_shift_id,
            CashShift.status == "ABIERTO"
        ).first()
        # [DSC019 - Mensaje 4] CE_SesionCaja -->> CTR_POS: 4: shift CashShift(id=45, estado=ABIERTA)
        if not shift:
            raise HTTPException(status_code=400, detail="El turno de caja especificado no existe o ya está cerrado (session_status != 'ABIERTA').")
        if shift.cashier_id != current_user.id:
            raise HTTPException(status_code=400, detail="El turno de caja especificado no pertenece a tu usuario.")
        if shift.branch_id != data.branch_id:
            raise HTTPException(
                status_code=400,
                detail=f"Inconsistencia multi-sucursal: El turno de caja #{shift.id} pertenece a otra sucursal, no a la sucursal seleccionada (#{data.branch_id})."
            )

    # 1. Determinar ítems comprados
    checkout_items: List[tuple[int, int, float]] = []  # (variant_id, quantity, unit_price)

    if data.channel == "POS":
        if not data.pos_items or len(data.pos_items) == 0:
            raise HTTPException(status_code=400, detail="Debes ingresar al menos una prenda en el POS.")
        for item in data.pos_items:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
            if not variant:
                raise HTTPException(status_code=404, detail=f"Variante {item.variant_id} no encontrada.")
            prod = db.query(Product).filter(Product.id == variant.product_id).first()
            unit_price = _get_product_effective_price(db, prod)
            checkout_items.append((item.variant_id, item.quantity, unit_price))
    else:
        # [DSC018 - Mensaje 3] CTR_Ventas -> CE_Carrito: 3: get_cart_items(user_id)
        cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="El carrito de compras está vacío.")
        # [DSC018 - Mensaje 4] CE_Carrito -->> CTR_Ventas: 4: cart_items[(variant_id, qty)]
        for item in cart.items:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
            if not variant:
                continue
            prod = db.query(Product).filter(Product.id == variant.product_id).first()
            unit_price = _get_product_effective_price(db, prod)
            checkout_items.append((item.variant_id, item.quantity, unit_price))

    # [DSC018 - Mensaje 5] [loop: Por cada variante] CTR_Ventas -> CE_Inventario: 5: select_for_update(branch_id, variant_id)
    # [DSC019 - Mensaje 5] [loop: Por cada variante] CTR_POS -> CE_Inventario: 5: select_for_update(branch_id, variant_id)
    subtotal = 0.0
    for var_id, qty, unit_price in checkout_items:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == var_id
        ).with_for_update().first()
        # [DSC018 - Mensaje 6] CE_Inventario -->> CTR_Ventas: 6: stock_ok, unit_price
        # [DSC019 - Mensaje 6] CE_Inventario -->> CTR_POS: 6: stock_disponible, unit_price
        current_stock = inv.stock_actual if inv else 0
        if current_stock < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente en la sucursal para la prenda con ID variante {var_id} (Disponible: {current_stock}, Requerido: {qty})."
            )
        subtotal += unit_price * qty

    subtotal = round(subtotal, 2)

    # [CU18 - Paso 4] / [DSC018 - Paso 4] +3. aplicar_cupon_descuento_si_existe(discount_code)
    # [DSC018 - Mensaje 7] [opt: Cupón] CTR_Ventas -> CE_Cupon: 7: validar_cupon(code, min_purchase)
    discount_amount = 0.0
    if data.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == data.coupon_code.strip().upper(),
            Coupon.is_active == True,
            Coupon.valid_from <= func.now(),
            Coupon.valid_until >= func.now(),
        ).first()
        if coupon and subtotal >= float(coupon.min_purchase_amount) and coupon.used_count < coupon.max_uses:
            if coupon.discount_type == "PORCENTAJE":
                discount_amount = round(subtotal * (float(coupon.discount_value) / 100.0), 2)
            else:
                discount_amount = round(min(subtotal, float(coupon.discount_value)), 2)
            coupon.used_count += 1
            # [DSC018 - Mensaje 8] CE_Cupon -->> CTR_Ventas: 8: discount_amount

    total_amount = max(0.0, round(subtotal - discount_amount, 2))

    # [DSC018 - Mensaje 9] CTR_Ventas -> CE_Orden: 9: insert_order(user_id, branch_id, channel="ONLINE", status="PAGADA", total, delivery_type, pickup_deadline)
    # [DSC019 - Mensaje 7] [Transacción ACID] CTR_POS -> CE_Orden: 7: insert_order(sucursal_id, canal=POS, total, estado=COMPLETADO)
    order_initial_status = "COMPLETADO" if data.channel == "POS" else "PAGADA"
    deliv_type = data.delivery_type or ("RETIRO_TIENDA" if data.shipping_method == "PICKUP" else "ENVIO_DOMICILIO")
    now_utc = datetime.now(timezone.utc)
    p_deadline = (now_utc + timedelta(hours=48)) if deliv_type == "RETIRO_TIENDA" else None
    p_timeout = now_utc + timedelta(minutes=5)
    
    order = Order(
        user_id=current_user.id,
        branch_id=data.branch_id,
        channel=data.channel,
        status=order_initial_status,
        subtotal=subtotal,
        discount_amount=discount_amount,
        coupon_code=data.coupon_code.strip().upper() if data.coupon_code else None,
        total_amount=total_amount,
        cash_shift_id=data.cash_shift_id if data.channel == "POS" else None,
        delivery_type=deliv_type,
        pickup_deadline=p_deadline,
        payment_session_expires_at=p_timeout,
    )
    db.add(order)
    db.flush()
    # [DSC018 - Mensaje 10] CE_Orden -->> CTR_Ventas: 10: order_id
    # [DSC019 - Mensaje 8] CE_Orden -->> CTR_POS: 8: orden Order(id=880)

    order_ref = f"ORD-{order.id}"
    for var_id, qty, unit_price in checkout_items:
        db.add(OrderItem(order_id=order.id, variant_id=var_id, quantity=qty, unit_price=unit_price))

        # [DSC018 - Mensaje 11] CTR_Ventas -> CE_Inventario: 11: deduct_stock(branch_id, variant_id, qty)
        # [DSC019 - Mensaje 9] CTR_POS -> CE_Inventario: 9: deduct_stock(sucursal_id, variante_id, cantidad)
        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == var_id
        ).with_for_update().first()
        inv.stock_actual -= qty
        # [DSC018 - Mensaje 12] CE_Inventario -->> CTR_Ventas: 12: stock_descontado
        # [DSC019 - Mensaje 10] CE_Inventario -->> CTR_POS: 10: stock_descontado

        # [DSC018 - Mensaje 13] CTR_Ventas -> CE_Kardex: 13: insert_ledger(tipo="VENTA", cantidad=-qty, ref="ORD-id")
        # [DSC019 - Mensaje 11] CTR_POS -> CE_Inventario: 11: insert_ledger(tipo=VENTA, cantidad=-N, ref=ORD-880)
        db.add(InventoryLedger(
            branch_id=data.branch_id,
            variant_id=var_id,
            quantity=-qty,
            movement_type="VENTA",
            unit_cost=float(inv.avg_cost or 0),
            reference_id=order_ref,
        ))
        # [DSC018 - Mensaje 14] CE_Kardex -->> CTR_Ventas: 14: asiento_registrado
        # [DSC019 - Mensaje 12] CE_Inventario -->> CTR_POS: 12: asiento_kardex_registrado

    # [DSC019 - Mensaje 13] CTR_POS -> CTR_POS: 13: calcularCambio(recibido=250.00, total=200.00) -> vuelto=50.00
    # [DSC019 - Mensaje 14] CTR_POS -> CE_Pago: 14: insert_payment(orden_id=880, metodo="EFECTIVO", recibido, cambio)
    # [DSC018 - Mensaje 15] CTR_Ventas -> CE_Pago: 15: insert_payment(order_id, metodo_pago, monto, status="CONFIRMADO")
    p_type = data.payment_type
    if p_type == "EFECTIVO":
        cash_rec = data.cash_payment.cash_received if data.cash_payment else total_amount
        if cash_rec < total_amount:
            raise HTTPException(status_code=400, detail=f"El efectivo recibido (Bs. {cash_rec}) no cubre el total (Bs. {total_amount}).")
        change = round(cash_rec - total_amount, 2)
        payment = EfectivoPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            cash_received=cash_rec,
            cash_change=change,
        )
    elif p_type == "TARJETA":
        if not data.card_payment:
            raise HTTPException(status_code=400, detail="Faltan datos de la tarjeta bancaria.")
        payment = TarjetaPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            card_brand=data.card_payment.card_brand,
            card_last4=data.card_payment.card_last4,
            gateway_reference=data.card_payment.gateway_reference or f"TX-{uuid.uuid4().hex[:8].upper()}",
        )
    elif p_type == "QR":
        qr_ref = data.qr_payment.qr_reference if data.qr_payment else f"QR-{uuid.uuid4().hex[:8].upper()}"
        payment = QRPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            qr_reference=qr_ref,
        )
    elif p_type == "PAYPAL":
        if not data.paypal_payment:
            raise HTTPException(status_code=400, detail="Faltan los datos de la transacción de PayPal.")
        # [DSC018 - Mensaje 15a] CTR_Ventas -> PAS_PayPal: 15a: verify_completed_order(paypal_order_id, total)
        paypal_service.verify_completed_order(data.paypal_payment.paypal_order_id, float(total_amount))
        # [DSC018 - Mensaje 15b] PAS_PayPal -->> CTR_Ventas: 15b: pago_verificado
        paypal_ref = f"PAYPAL:{data.paypal_payment.paypal_order_id}"
        payment = PayPalPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            gateway_reference=paypal_ref,
            paypal_payer_id=data.paypal_payment.paypal_payer_id,
            paypal_payer_email=data.paypal_payment.paypal_payer_email,
        )
    elif p_type == "CREDITO":
        due_date = data.credit_payment.credit_due_date if data.credit_payment else (date.today() + timedelta(days=30))
        payment = CreditoPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            credit_due_date=due_date,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Medio de pago {p_type} no soportado.")

    db.add(payment)
    # [DSC019 - Mensaje 15] CE_Pago -->> CTR_POS: 15: pago_id = 741
    # [DSC018 - Mensaje 16] CE_Pago -->> CTR_Ventas: 16: payment_id

    tax_rate = 0.130
    # [CU20 - Paso 2] / [DSC020 - Paso 2] +7. calculate_tax_iva_13(total_amount)
    tax_amount = round(total_amount * tax_rate, 2)
    control_code = None
    # [CU20 - Paso 3] / [DSC020 - Paso 3] [alt: Cliente con NIT/CI válido -> Código de Control v7]
    if data.doc_type == "FACTURA":
        control_code = f"{uuid.uuid4().hex[:2]}-{uuid.uuid4().hex[2:4]}-{uuid.uuid4().hex[4:6]}-{uuid.uuid4().hex[6:8]}".upper()
    # [CU20 - alt: Venta sin NIT o interna -> NOTA DE ENTREGA sin código de control]

    # [DSC019 - Mensaje 16] CTR_POS -> CE_Factura: 16: insert_invoice(orden_id=880, doc_type=FACTURA, nit_ci, total=200.00, iva_13=26.00)
    # [DSC018 - Mensaje 17] CTR_Ventas -> CE_Factura: 17: insert_invoice(order_id, doc_type, subtotal, iva_13, control_code)
    # [CU20 - Paso 4] insert(Invoice)
    invoice = Invoice(
        order_id=order.id,
        doc_type=data.doc_type,
        tax_rate=tax_rate,
        subtotal=total_amount,
        tax_amount=tax_amount,
        total=total_amount,
        control_code=control_code,
        customer_nit=data.customer_nit.strip() if data.customer_nit else "0",
        customer_name=data.customer_name.strip() if data.customer_name else f"{current_user.first_name} {current_user.last_name}".strip(),
    )
    db.add(invoice)
    # [DSC019 - Mensaje 17] CE_Factura -->> CTR_POS: 17: factura Invoice(id=512, codigo_control)
    # [DSC018 - Mensaje 18] CE_Factura -->> CTR_Ventas: 18: invoice_id

    if data.channel == "ONLINE":
        # [DSC018 - Mensaje 19] CTR_Ventas -> CE_Carrito: 19: clear_cart_items(user_id)
        cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
        if cart:
            db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        # [DSC018 - Mensaje 20] CTR_Ventas -> CTR_Notificaciones: 20: notificar(user_id, "Compra confirmada", order_id)
        notificar(
            db, current_user.id,
            f"Compra confirmada {_numero_orden(order)}",
            f"Recibimos tu pago de Bs. {total_amount:.2f} ({p_type}). Tu pedido se preparará en {branch.name}.",
            TIPO_PEDIDO, order.id, "ORDER",
        )
        # [DSC018 - Mensaje 21] CTR_Notificaciones -->> CTR_Ventas: 21: notificacion_enviada

        if data.shipping_method != "PICKUP":
            from app.packages.paquete_envios_y_logistica.models import Shipment, ShipmentTrackingEvent
            from app.packages.paquete_envios_y_logistica.routers import avisar_envio

            # [DSC018 - Mensaje 22] [opt: DELIVERY] CTR_Ventas -> CE_Envio: 22: insert_shipment(order_id, tracking_number, status="PENDING_DISPATCH")
            tracking_num = f"TRK-{uuid.uuid4().hex[:8].upper()}"
            address = (data.delivery_address or "Dirección indicada por el cliente").strip()
            rec_name = (data.recipient_name or data.customer_name or f"{current_user.first_name} {current_user.last_name}").strip()
            rec_phone = (data.recipient_phone or current_user.phone or "S/N").strip()
            cost = float(data.shipping_cost or 15.0)

            shipment = Shipment(
                tracking_number=tracking_num,
                order_id=order.id,
                zone_id=data.zone_id,
                carrier_name="Moto Express",
                carrier_phone=None,
                delivery_address=address,
                delivery_latitude=data.delivery_latitude,
                delivery_longitude=data.delivery_longitude,
                recipient_name=rec_name,
                recipient_phone=rec_phone,
                shipping_cost=cost,
                status="PENDING_DISPATCH",
                notes=data.delivery_notes.strip() if data.delivery_notes else None,
            )
            db.add(shipment)
            db.flush()
            # [DSC018 - Mensaje 23] CE_Envio -->> CTR_Ventas: 23: shipment_id

            initial_event = ShipmentTrackingEvent(
                shipment_id=shipment.id,
                status="PENDING_DISPATCH",
                location=f"Sucursal {branch.name}",
                description=f"Pedido ONLINE con envío a domicilio ({address}). Disponible en bolsa de repartidores.",
            )
            db.add(initial_event)
            try:
                avisar_envio(db, shipment, "CREADO")
            except Exception:
                pass

    db.commit()
    db.refresh(order)

    # [Auditoría transaccional] log_event
    log_event(db, current_user.id, "INSERT", "orders", order.id,
              {"channel": data.channel, "total": total_amount, "doc_type": data.doc_type},
              request.client.host)

    # [DSC019 - Mensaje 18] CTR_POS -->> IU_POS: 18: HTTP 201 Created OrderResponse(orden_id=880, factura_id=512, cambio=50.00)
    # [DSC019 - Mensaje 19] IU_POS -->> Cajero: 19: mostrarResumenVuelto(vuelto=50.00)
    # [DSC018 - Mensaje 24] CTR_Ventas -->> IU_Checkout: 24: HTTP 201 Created OrderResponse(order_id, invoice, delivery_type, pickup_deadline)
    # [DSC018 - Mensaje 25] IU_Checkout -->> Cliente: 25: renderizarConfirmacionPedido()
    return _build_order_response(db, order)


# [CU24 - Paso 1] (IU) El cliente abre su historial de compras en IU_HistorialCompras
@router.get("/orders/my-orders", response_model=List[OrderResponse])
# [CU24 - Paso 2] / [DSC024 - Paso 2] +1. get_my_orders(user_id)
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU24] Historial de compras y pedidos del cliente en sesión."""
    # [CU24 - Paso 3] / [DSC024 - Paso 3] +2. select_orders_where(user_id)
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    # [CU24 - Paso 4] / [DSC024 - Paso 4] +3. Retornar historial de compras
    return [_build_order_response(db, o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU24] Detalle de una compra con sus ítems, comprobante y pago."""
    # [CU24 - Paso 5] / [DSC024 - Paso 5] +1. get_order_detail(order_id)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    is_owner = order.user_id == current_user.id
    is_staff_same_branch = not scope.is_central and order.branch_id == scope.branch_id
    if not (is_owner or scope.is_central or is_staff_same_branch):
        # 404 en vez de 403: no confirmar a terceros que el pedido existe.
        raise HTTPException(status_code=404, detail="Orden no encontrada.")
    # [CU24 - Paso 6] / [DSC024 - Paso 6] +2. Retornar detalle con ítems, factura y tracking
    return _build_order_response(db, order)


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    branch_id: Optional[int] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[Separación por sucursal] Lista los pedidos de la sucursal del usuario (o consolidado si es central)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(Order)
    if effective_branch_id:
        query = query.filter(Order.branch_id == effective_branch_id)
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    return [_build_order_response(db, o) for o in orders]


def _numero_orden(order: Order) -> str:
    """Número visible del pedido (mismo formato que OrderResponse.order_number)."""
    anio = order.created_at.year if order.created_at else datetime.now().year
    return f"ORD-{anio}-{order.id:06d}"


# Mensajes al cliente por cada cambio de estado del alistado (CU40).
AVISOS_ALISTADO = {
    "PREPARANDO": ("Estamos preparando tu pedido", "La sucursal {sucursal} está alistando tu pedido {numero}."),
    "LISTO_PARA_ENTREGA": ("Tu pedido está listo", "Tu pedido {numero} ya está listo para entrega o retiro en {sucursal}."),
    "ENTREGADO": ("Pedido entregado", "Tu pedido {numero} fue entregado. ¡Gracias por comprar en FashionStore!"),
    "CANCELADO": ("Pedido cancelado", "Tu pedido {numero} fue cancelado por la sucursal {sucursal}."),
}


# Flujo de alistado de un pedido online en la sucursal.
FULFILLMENT_TRANSITIONS = {
    "PENDIENTE": {"PREPARANDO", "CANCELADO"},
    "PAGADA": {"PREPARANDO", "CANCELADO"},
    "PREPARANDO": {"LISTO_PARA_ENTREGA", "CANCELADO"},
    "LISTO_PARA_ENTREGA": {"ENTREGADO"},
}


@router.get("/orders-fulfillment", response_model=List[OrderResponse])
def list_branch_fulfillment_orders(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[Alistado y Despacho en Tienda] Pedidos online (retiro en tienda o delivery) de la sucursal del cajero para alistar y entregar.

    El stock de estos pedidos ya se descontó de la sucursal elegida al pagar.
    """
    # Consulta de pedidos pendientes de entrega física en sucursal
    query = db.query(Order).filter(Order.channel == "ONLINE")
    if not scope.is_central:
        query = query.filter(Order.branch_id == scope.branch_id)

    if status_filter:
        query = query.filter(Order.status == status_filter.upper())
    else:
        # Por defecto muestra pedidos que el cajero debe alistar o despachar
        query = query.filter(Order.status.in_(["PAGADA", "PREPARANDO", "LISTO_PARA_ENTREGA", "PENDIENTE"]))

    orders = query.order_by(Order.created_at.desc()).all()
    return [_build_order_response(db, o) for o in orders]


@router.patch("/orders/{order_id}/fulfillment", response_model=OrderResponse)
def update_order_fulfillment(
    order_id: int,
    data: BranchOrderFulfillmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[Alistado y Despacho en Tienda] Permite al cajero / encargado alistar y marcar como despachado/entregado un pedido online de su sucursal."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if not scope.is_central and order.branch_id != scope.branch_id:
        raise HTTPException(status_code=403, detail="No puedes gestionar pedidos de otra sucursal.")

    if order.channel != "ONLINE":
        raise HTTPException(status_code=400, detail="Solo los pedidos online se alistan desde esta bandeja.")

    new_status = data.status.upper()
    allowed = FULFILLMENT_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede pasar el pedido de {order.status} a {new_status}.",
        )

    # El pedido queda en la caja del cajero que lo atiende, para que cuadre en su arqueo.
    if order.cash_shift_id is None and new_status != "CANCELADO":
        shift = db.query(CashShift).filter(
            CashShift.cashier_id == current_user.id,
            CashShift.status == "ABIERTO",
            CashShift.branch_id == order.branch_id,
        ).first()
        if not shift:
            raise HTTPException(status_code=400, detail="Abre tu caja en esta sucursal antes de atender pedidos.")
        order.cash_shift_id = shift.id

    if new_status == "CANCELADO":
        # Devolver al stock de la sucursal las prendas del pedido cancelado.
        for item in order.items:
            inv = db.query(Inventory).filter(
                Inventory.branch_id == order.branch_id,
                Inventory.variant_id == item.variant_id,
            ).with_for_update().first()
            if inv:
                inv.stock_actual += item.quantity
                db.add(InventoryLedger(
                    branch_id=order.branch_id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    movement_type="DEVOLUCION",
                    unit_cost=float(inv.avg_cost or 0),
                    reference_id=f"CANCEL-ORD-{order.id}",
                ))

    old_status = order.status
    order.status = new_status
    if new_status in AVISOS_ALISTADO:
        titulo, plantilla = AVISOS_ALISTADO[new_status]
        sucursal = db.query(Branch).filter(Branch.id == order.branch_id).first()
        notificar(
            db, order.user_id, titulo,
            plantilla.format(numero=_numero_orden(order), sucursal=sucursal.name if sucursal else "la sucursal"),
            TIPO_PEDIDO, order.id, "ORDER",
        )
    db.commit()
    db.refresh(order)

    log_event(
        db, current_user.id, "UPDATE", "orders", order.id,
        {"from_status": old_status, "to_status": new_status, "notes": data.notes},
        request.client.host
    )
    return _build_order_response(db, order)


# ===================================================================
# CU23 — Arqueo de Caja (Apertura y Cierre de Turno)
# ===================================================================

def _build_cash_shift_response(db: Session, shift: CashShift) -> CashShiftResponse:
    cashier = db.query(User).filter(User.id == shift.cashier_id).first()
    branch = db.query(Branch).filter(Branch.id == shift.branch_id).first()

    # Ventas y cobros asentados durante el turno
    orders_in_shift = db.query(Order).filter(Order.cash_shift_id == shift.id).all()
    cash_total = 0.0
    card_total = 0.0
    qr_total = 0.0
    reservation_total = 0.0
    delivery_total = 0.0
    presencial_total = 0.0

    for ord in orders_in_shift:
        for p in ord.payments:
            amt = float(p.amount)
            if p.payment_type == "EFECTIVO":
                cash_total += amt
            elif p.payment_type == "TARJETA":
                card_total += amt
            elif p.payment_type in ("QR", "QR_PAGO"):
                qr_total += amt

        is_res = db.query(Reservation).filter(Reservation.completed_sale_id == ord.id).first() is not None
        if is_res:
            reservation_total += float(ord.total_amount)
        elif ord.channel in ("DELIVERY", "ONLINE"):
            delivery_total += float(ord.total_amount)
        else:
            presencial_total += float(ord.total_amount)

    return CashShiftResponse(
        id=shift.id,
        cashier_id=shift.cashier_id,
        cashier_name=f"{cashier.first_name} {cashier.last_name}".strip() if cashier else "Cajero",
        branch_id=shift.branch_id,
        branch_name=branch.name if branch else "Sucursal",
        opening_amount=float(shift.opening_amount),
        closing_amount_declared=float(shift.closing_amount_declared) if shift.closing_amount_declared is not None else None,
        closing_amount_system=float(shift.closing_amount_system) if shift.closing_amount_system is not None else None,
        difference=float(shift.difference) if shift.difference is not None else None,
        status=shift.status,
        opened_at=shift.opened_at,
        closed_at=shift.closed_at,
        notes=shift.notes,
        total_sales_count=len(orders_in_shift),
        total_cash_sales=round(cash_total, 2),
        total_card_sales=round(card_total, 2),
        total_qr_sales=round(qr_total, 2),
        total_reservation_sales=round(reservation_total, 2),
        total_delivery_sales=round(delivery_total, 2),
        total_presencial_sales=round(presencial_total, 2),
    )


# [CU23 - Paso 1] (IU) El cajero inicia apertura de turno de caja en U_PuntoDeVentaPOS
@router.post("/shifts/open", response_model=CashShiftResponse, status_code=201)
# [CU23 - Paso 2] / [DSC023 - Paso 2] +1. open_shift(cajero_id, sucursal_id, monto_inicial)
def open_cash_shift(
    data: CashShiftOpen,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Apertura de turno de caja con fondo inicial."""
    if not scope.is_central:
        data.branch_id = scope.branch_id

    # [CU23 - Paso 3] / [DSC023 - Paso 3] +2. check_active_shift(cajero_id)
    active_shift = db.query(CashShift).filter(
        CashShift.cashier_id == current_user.id,
        CashShift.status == "ABIERTO"
    ).first()
    if active_shift:
        from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
        shift_branch = db.query(Branch).filter(Branch.id == active_shift.branch_id).first()
        branch_desc = f"'{shift_branch.name}'" if shift_branch else f"sucursal #{active_shift.branch_id}"
        raise HTTPException(
            status_code=400, 
            detail=f"Ya tienes el Turno #{active_shift.id} ABIERTO en la sucursal {branch_desc}. Debes cerrarlo o hacer el arqueo en esa sucursal antes de abrir una nueva caja aquí."
        )

    # [CU23 - Paso 4] / [DSC023 - Paso 4] +3. insert(cash_shift, status='ABIERTO')
    shift = CashShift(
        cashier_id=current_user.id,
        branch_id=data.branch_id,
        opening_amount=data.opening_amount,
        status="ABIERTO",
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    # [CU23 - Paso 5] / [DSC023 - Paso 5] +4. log_event(apertura_caja)
    log_event(db, current_user.id, "INSERT", "cash_shifts", shift.id,
              {"opening_amount": data.opening_amount, "branch_id": data.branch_id},
              request.client.host)

    return _build_cash_shift_response(db, shift)


@router.get("/shifts/current", response_model=Optional[CashShiftResponse])
def get_current_cash_shift(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Obtiene el turno de caja abierto del usuario actual (opcionalmente filtrado por sucursal)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(CashShift).filter(
        CashShift.cashier_id == current_user.id,
        CashShift.status == "ABIERTO"
    )
    if effective_branch_id is not None:
        query = query.filter(CashShift.branch_id == effective_branch_id)
    shift = query.first()
    if not shift:
        return None
    return _build_cash_shift_response(db, shift)


@router.get("/shifts", response_model=List[CashShiftResponse])
def get_cash_shifts(
    branch_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Historial de turnos y arqueos de caja por sucursal o consolidado global (Casa Matriz)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(CashShift)
    if effective_branch_id is not None:
        query = query.filter(CashShift.branch_id == effective_branch_id)
    if status:
        query = query.filter(CashShift.status == status)
    shifts = query.order_by(CashShift.id.desc()).limit(limit).all()
    return [_build_cash_shift_response(db, s) for s in shifts]


@router.post("/shifts/{shift_id}/close", response_model=CashShiftResponse)
def close_cash_shift(
    shift_id: int,
    data: CashShiftClose,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Cierre ciego de turno de caja y balance con ventas del sistema."""
    # [CU23 - Paso 6] / [DSC023 - Paso 6] +1. close_shift(shift_id, monto_declarado)
    shift = db.query(CashShift).filter(CashShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Turno de caja no encontrado.")
    if not scope.is_central and shift.branch_id != scope.branch_id:
        raise HTTPException(status_code=404, detail="Turno de caja no encontrado.")
    if shift.status == "CERRADO":
        raise HTTPException(status_code=400, detail="El turno de caja ya se encuentra cerrado.")

    # [CU23 - Paso 7] / [DSC023 - Paso 7] +2. calculate_system_sales(shift_id)
    orders_in_shift = db.query(Order).filter(Order.cash_shift_id == shift.id).all()
    cash_sales = 0.0
    for ord in orders_in_shift:
        for p in ord.payments:
            if p.payment_type == "EFECTIVO":
                cash_sales += float(p.amount)

    system_total = round(float(shift.opening_amount) + cash_sales, 2)
    difference = round(data.closing_amount_declared - system_total, 2)

    # [CU23 - Paso 8] / [DSC023 - Paso 8] +3. update(cash_shift, status='CERRADO', diff)
    shift.closing_amount_declared = data.closing_amount_declared
    shift.closing_amount_system = system_total
    shift.difference = difference
    shift.status = "CERRADO"
    shift.closed_at = func.now()
    if data.notes:
        shift.notes = data.notes

    db.commit()
    db.refresh(shift)

    # [CU23 - Paso 9] / [DSC023 - Paso 9] +4. log_event(cierre_caja) y confirmación
    log_event(db, current_user.id, "UPDATE", "cash_shifts", shift.id,
              {"declared": data.closing_amount_declared, "system": system_total, "diff": difference},
              request.client.host)

    return _build_cash_shift_response(db, shift)


# ===================================================================
# CU21 — Generación de Cotizaciones
# ===================================================================

# [CU21 - Paso 1] (IU) El cliente o asesor ingresa los ítems de la cotización
@router.post("/quotations", response_model=QuotationResponse, status_code=201)
# [CU21 - Paso 2] / [DSC021 - Paso 2] +1. create_quotation(cliente, items, vigencia)
def create_quotation(
    data: QuotationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(manager_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU21] Genera una cotización comercial con período de validez."""
    if not data.details:
        raise HTTPException(status_code=400, detail="La cotización debe incluir al menos una prenda.")

    # [CU21 - Paso 3] / [DSC021 - Paso 3] +2. calcular_totales_y_fecha_vencimiento()
    total = 0.0
    q_items: List[tuple[int, int, float]] = []

    for item in data.details:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variante {item.variant_id} no encontrada.")
        prod = db.query(Product).filter(Product.id == variant.product_id).first()
        u_price = float(prod.base_price if prod else 0.0)
        total += u_price * item.quantity
        q_items.append((item.variant_id, item.quantity, u_price))

    q_num = f"COT-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    valid_until = datetime.now(timezone.utc) + timedelta(days=data.valid_days)

    # [CU21 - Paso 4] / [DSC021 - Paso 4] +3. insert(quotation, status='VIGENTE')
    quotation = Quotation(
        quotation_number=q_num,
        customer_name=data.customer_name.strip(),
        customer_email=data.customer_email.strip() if data.customer_email else None,
        customer_phone=data.customer_phone.strip() if data.customer_phone else None,
        created_by_id=current_user.id,
        branch_id=scope.branch_id if not scope.is_central else None,
        total_amount=round(total, 2),
        valid_until=valid_until,
        status="VIGENTE",
    )
    db.add(quotation)
    db.flush()

    created_items = []
    for var_id, qty, u_price in q_items:
        qi = QuotationItem(quotation_id=quotation.id, variant_id=var_id, quantity=qty, unit_price=u_price)
        db.add(qi)
        created_items.append((qi, var_id, qty, u_price))
    db.flush()

    items_resp = []
    for qi, var_id, qty, u_price in created_items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == var_id).first()
        prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
        size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
        color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None

        items_resp.append(
            OrderItemResponse(
                id=qi.id,
                variant_id=var_id,
                quantity=qty,
                unit_price=u_price,
                subtotal=round(u_price * qty, 2),
                product_name=prod.name if prod else "Prenda",
                sku=variant.sku if variant else "N/A",
                size=size.name if size else "Única",
                color=color.name if color else "Estándar",
            )
        )

    db.commit()
    db.refresh(quotation)

    # [CU21 - Paso 5] / [DSC021 - Paso 5] +4. log_event(cotizacion) y confirmación
    log_event(db, current_user.id, "INSERT", "quotations", quotation.id,
              {"quotation_number": quotation.quotation_number, "total": float(quotation.total_amount)},
              request.client.host)

    branch = db.query(Branch).filter(Branch.id == quotation.branch_id).first() if quotation.branch_id else None
    return QuotationResponse(
        id=quotation.id,
        quotation_number=quotation.quotation_number,
        customer_name=quotation.customer_name,
        customer_email=quotation.customer_email,
        customer_phone=quotation.customer_phone,
        total_amount=float(quotation.total_amount),
        valid_until=quotation.valid_until,
        status=quotation.status,
        created_at=quotation.created_at,
        items=items_resp,
        branch_id=quotation.branch_id,
        branch_name=branch.name if branch else None,
    )


@router.get("/quotations", response_model=List[QuotationResponse])
def list_quotations(
    branch_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU21] Lista el historial de cotizaciones comerciales generadas (scoped por sucursal)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(Quotation)
    if effective_branch_id:
        query = query.filter(Quotation.branch_id == effective_branch_id)
    quotes = query.order_by(Quotation.id.desc()).limit(limit).all()
    branches_by_id = {b.id: b.name for b in db.query(Branch.id, Branch.name).all()}
    results = []
    now_utc = datetime.now(timezone.utc)
    for q in quotes:
        v_until = q.valid_until
        if v_until.tzinfo is None:
            v_until = v_until.replace(tzinfo=timezone.utc)
        if q.status == "VIGENTE" and now_utc > v_until:
            q.status = "EXPIRADA"
            db.commit()

        items_resp = []
        for qi in q.items:
            variant = db.query(ProductVariant).filter(ProductVariant.id == qi.variant_id).first()
            prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
            size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
            color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None
            items_resp.append(
                OrderItemResponse(
                    id=qi.id,
                    variant_id=qi.variant_id,
                    quantity=qi.quantity,
                    unit_price=float(qi.unit_price),
                    subtotal=round(float(qi.unit_price) * qi.quantity, 2),
                    product_name=prod.name if prod else "Prenda",
                    sku=variant.sku if variant else "N/A",
                    size=size.name if size else "Única",
                    color=color.name if color else "Estándar",
                )
            )
        results.append(
            QuotationResponse(
                id=q.id,
                quotation_number=q.quotation_number,
                customer_name=q.customer_name,
                customer_email=q.customer_email,
                customer_phone=q.customer_phone,
                total_amount=float(q.total_amount),
                valid_until=q.valid_until,
                status=q.status,
                created_at=q.created_at,
                items=items_resp,
                branch_id=q.branch_id,
                branch_name=branches_by_id.get(q.branch_id) if q.branch_id else None,
            )
        )
    return results


@router.post("/quotations/{quotation_id}/convert", response_model=OrderResponse)
def convert_quotation_to_order(
    quotation_id: int,
    data: QuotationConvertRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(manager_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU21 -> CU18/CU20] Convierte una cotización vigente en venta formal con emisión de factura."""
    # [CU21 - Paso 6] / [DSC021 - Paso 6] +1. convert_quotation(quotation_id, sucursal_id)
    if not scope.is_central:
        data.branch_id = scope.branch_id

    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Cotización no encontrada.")

    if quotation.status == "CONVERTIDA":
        raise HTTPException(status_code=400, detail="Esta cotización ya fue convertida en una venta anteriormente.")

    # [CU21 - Paso 7] / [DSC021 - Paso 7] +2. check_expiration_and_stock()
    now_utc = datetime.now(timezone.utc)
    v_until = quotation.valid_until
    if v_until.tzinfo is None:
        v_until = v_until.replace(tzinfo=timezone.utc)
    if now_utc > v_until:
        quotation.status = "EXPIRADA"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"La cotización {quotation.quotation_number} ha vencido el {quotation.valid_until.strftime('%d/%m/%Y')}. La validez de la oferta expiró y los precios no son vinculantes; debe generarse una nueva cotización."
        )

    # Validar stock en la sucursal seleccionada
    for qi in quotation.items:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == qi.variant_id
        ).with_for_update().first()
        avail = inv.stock_actual if inv else 0
        if avail < qi.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente en la sucursal para la prenda variante #{qi.variant_id} (Disponible: {avail}, Requerido: {qi.quantity})."
            )

    # [CU21 - Paso 8] / [DSC021 - Paso 8] +3. process_checkout(channel='POS')
    pos_items = [CartItemAdd(variant_id=qi.variant_id, quantity=qi.quantity) for qi in quotation.items]
    checkout_payload = CheckoutRequest(
        channel="POS",
        branch_id=data.branch_id,
        cash_shift_id=data.cash_shift_id,
        payment_method=data.payment_method,
        pos_items=pos_items,
        customer_nit=data.customer_nit or "0",
        customer_business_name=data.customer_business_name or quotation.customer_name,
    )
    order_res = process_checkout(checkout_payload, request, db, current_user)
    # [CU21 - Paso 9] / [DSC021 - Paso 9] +4. update(quotation, status='CONVERTIDA')
    quotation.status = "CONVERTIDA"
    db.commit()
    return order_res


# ===================================================================
# CU22 — Devoluciones y Cambios de Prendas
# ===================================================================

@router.get("/returns/my", response_model=List[CustomerReturnResponse])
def get_my_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU22 / CU24] Devoluciones y cambios registrados sobre las compras del cliente en sesión.

    Solo lectura: las devoluciones las procesa el encargado de sucursal; aquí el cliente
    consulta su estado, el monto reembolsado y qué prendas se devolvieron o cambiaron.
    """
    returns = (
        db.query(OrderReturn)
        .join(Order, Order.id == OrderReturn.order_id)
        .filter(Order.user_id == current_user.id)
        .options(selectinload(OrderReturn.items))
        .order_by(OrderReturn.created_at.desc())
        .all()
    )

    def _variant_parts(v):
        if v is None:
            return None, None, None
        return (
            v.product.name if v.product else "Prenda",
            v.size.name if v.size else "-",
            v.color.name if v.color else "-",
        )

    result = []
    for r in returns:
        items = []
        for it in r.items:
            name, size, color = _variant_parts(it.variant)
            r_name, r_size, r_color = _variant_parts(it.replacement_variant)
            items.append(CustomerReturnItemResponse(
                product_name=name or "Prenda",
                size=size or "-",
                color=color or "-",
                quantity=it.quantity,
                replacement_product_name=r_name,
                replacement_size=r_size,
                replacement_color=r_color,
            ))
        order = r.order
        result.append(CustomerReturnResponse(
            id=r.id,
            return_number=r.return_number,
            order_id=r.order_id,
            order_number=f"ORD-{order.created_at.year}-{order.id:06d}",
            return_type=r.return_type,
            reason=r.reason,
            refund_amount=float(r.refund_amount),
            status=r.status,
            created_at=r.created_at,
            items=items,
        ))
    return result


# =========================================================================================================
# CU22 / DSC022: GESTIÓN DE DEVOLUCIONES Y CAMBIOS DE PRENDAS (UML 2.5)
# Diagrama de Secuencia Canónico: Búsqueda de Factura, Validación de Garantía y 3 Acciones Posibles
# Participantes:
#   - Cajero_Encargado (Actor)
#   - IU_Gestion_Devoluciones (IU)
#   - CTR_Devoluciones_Y_Cambios (CTR)
#   - Entidad_Factura (CE_F)
#   - Entidad_Orden (CE_O)
#   - Entidad_Inventario (CE_I)
#   - Entidad_OrdenDevolucion (CE_OD)
#   - Entidad_NotaCredito (CE_NC)
#   - Entidad_Sesion (CE_S)
# =========================================================================================================

# ---------------------------------------------------------------------------------------------------------
# FASE 2: Procesamiento de la Devolución o Cambio según Acción Seleccionada (Mensajes 7 al 16)
# ---------------------------------------------------------------------------------------------------------
# [DSC022 - Mensaje 8] IU_Gestion_Devoluciones -> CTR_Devoluciones_Y_Cambios: POST /api/v1/sales/returns
@router.post("/returns", response_model=OrderReturnResponse, status_code=201)
def process_order_return(
    data: OrderReturnCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(manager_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """
    [CU22 / DSC022: Procesar Cambios y Devoluciones de Prendas]
    
    Diagrama de Secuencia y Arquitectura BCE:
      - Actor: Cajero_Encargado
      - Boundary: IU_Gestion_Devoluciones (Formulario de Cambios y Devoluciones)
      - Control: CTR_Devoluciones_Y_Cambios (POST /api/v1/sales/returns)
      - Entity: Entidad_Orden (Orden original de compra facturada)
      - Entity: Entidad_OrdenDevolucion (Modelo OrderReturn y OrderReturnItem)
      - Entity: Entidad_Inventario (Ajuste de existencias: reingreso y salida)
      - Entity: Entidad_NotaCredito (Modelo CreditNote - Emisión de saldo a favor, cero efectivo)
      - Entity: Entidad_Sesion (Cobro de diferencia en caja cuando la prenda nueva es de mayor valor)

    Reglas de Negocio Estrictas:
      1. Plazo Máximo de Garantía de 14 Días (2 Semanas):
         - delta_dias = NOW - fecha_compra. Si delta_dias > 14 -> Rechazo con HTTP 400 Bad Request.
      2. Acciones Seleccionadas:
         - CAMBIO POR TALLA (Mismo Modelo / Mismo SKU): Diferencia financiera Bs. 0.00.
         - CAMBIO POR MODELO:
             * Prenda más cara: Cobro de la diferencia en caja (diff_total > 0).
             * Prenda más barata: Emisión obligatoria de Nota de Crédito (cero devolución en efectivo).
         - DEVOLUCIÓN DEFINITIVA: Reingreso a inventario y emisión de Nota de Crédito por el monto total.
    """
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")
    if not scope.is_central and order.branch_id != scope.branch_id:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    # Validación de Plazo Derecho: delta_dias = NOW - fecha_compra
    if order.created_at:
        now_utc = datetime.now(timezone.utc)
        order_time = order.created_at
        if order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)
        diff_days = (now_utc - order_time).days
        # [DSC022 - Mensaje 5a / 6a] [alt: delta_dias > 14 dias (2 Semanas Vencidas)]
        if diff_days > 14:
            raise HTTPException(
                status_code=400,
                detail=f"Plazo vencido: Han pasado más de 14 días (2 semanas) desde la compra (hace {diff_days} días). Garantía Expirada - No procede devolución ni cambio."
            )

    refund_total = 0.0
    diff_total = 0.0
    credit_note_obj = None
    price_diff_msg = None

    for it in data.items:
        order_it = db.query(OrderItem).filter(
            OrderItem.order_id == order.id, OrderItem.variant_id == it.variant_id
        ).first()
        if not order_it:
            raise HTTPException(status_code=400, detail=f"La prenda con ID variante {it.variant_id} no pertenece a esta orden.")
        if it.quantity > order_it.quantity:
            raise HTTPException(status_code=400, detail="La cantidad a devolver no puede superar la cantidad comprada.")

        # =================================================================================================
        # ACCIÓN C: DEVOLUCIÓN DEFINITIVA (Mensajes 7d y 8d)
        # =================================================================================================
        # [DSC022 - Mensaje 7d] Cajero_Encargado -> IU_Gestion_Devoluciones: solicitarDevolucion(var_id=14, motivo='Falla Fabrica')
        # [DSC022 - Mensaje 8d] IU_Gestion_Devoluciones -> CTR_Devoluciones_Y_Cambios: POST /api/v1/sales/returns (tipo='DEVOLUCION_DINERO', var_id=14)
        if data.return_type == "DEVOLUCION_DINERO":
            refund_total += float(order_it.unit_price) * it.quantity

        # =================================================================================================
        # ACCIÓN A y B: CAMBIO POR TALLA / CAMBIO POR MODELO (Mensajes 7a/8a y 7b/8b)
        # =================================================================================================
        elif data.return_type in ["CAMBIO_PRENDA", "CAMBIO_TALLA", "CAMBIO_MODELO"] and it.replacement_variant_id:
            orig_var = db.query(ProductVariant).filter(ProductVariant.id == it.variant_id).first()
            repl_var = db.query(ProductVariant).filter(ProductVariant.id == it.replacement_variant_id).first()
            if not repl_var:
                raise HTTPException(status_code=404, detail=f"Variante de reemplazo {it.replacement_variant_id} no encontrada.")

            orig_p = db.query(Product).filter(Product.id == orig_var.product_id).first()
            repl_p = db.query(Product).filter(Product.id == repl_var.product_id).first()

            orig_price = _get_product_effective_price(db, orig_p)
            repl_price = _get_product_effective_price(db, repl_p)

            # [DSC022 - Mensaje 7a / 8a] Acción Seleccionada: CAMBIO POR TALLA (Mismo Modelo / Mismo SKU) -> diferencia = 0.00
            if data.return_type == "CAMBIO_TALLA" or orig_p.id == repl_p.id:
                pass
            else:
                # [DSC022 - Mensaje 7b / 8b] Acción Seleccionada: CAMBIO POR MODELO (Diferente Prenda / Diferencia de Precio)
                diff_unit = round(repl_price - orig_price, 2)
                diff_total += round(diff_unit * it.quantity, 2)

    # -----------------------------------------------------------------------------------------------------
    # SUBFLUJO B.2: Precio Nuevo < Precio Antiguo (Prenda más barata - Emisión Obligatoria de Nota de Crédito)
    # -----------------------------------------------------------------------------------------------------
    # [DSC022 - Mensaje 11c] CTR_Devoluciones_Y_Cambios -> Entidad_NotaCredito: emitirNotaCredito(cliente_id, saldo_a_favor, motivo='CAMBIO_MODELO_MENOR_VALOR')
    if diff_total < 0:
        saldo_a_favor = round(abs(diff_total), 2)
        nc_code = f"NC-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        credit_note_obj = CreditNote(
            credit_note_code=nc_code,
            user_id=order.user_id,
            order_id=order.id,
            amount=saldo_a_favor,
            status="VIGENTE",
            reason=f"Saldo a favor por cambio de modelo en orden {_numero_orden(order)}",
        )
        db.add(credit_note_obj)
        db.flush()
        # [DSC022 - Mensaje 12c] Entidad_NotaCredito --> CTR_Devoluciones_Y_Cambios: codigo_nc = 'NC-2026-0045'
        price_diff_msg = f"Se emitio la Nota de Credito {nc_code} por Bs. {saldo_a_favor:.2f} a favor del cliente para su proxima compra."

    # -----------------------------------------------------------------------------------------------------
    # SUBFLUJO B.1: Precio Nuevo > Precio Antiguo (Prenda más cara - Cobro de Diferencia en Caja)
    # -----------------------------------------------------------------------------------------------------
    # [DSC022 - Mensaje 11b] CTR_Devoluciones_Y_Cambios -> Entidad_Sesion: cobrarDiferenciaVentaCaja(monto_diferencia)
    # [DSC022 - Mensaje 12b] Entidad_Sesion --> CTR_Devoluciones_Y_Cambios: cobro_asentado
    elif diff_total > 0:
        price_diff_msg = f"Diferencia a cobrar en caja/pasarela: Bs. {diff_total:.2f}."

    # -----------------------------------------------------------------------------------------------------
    # SUBFLUJO C: DEVOLUCIÓN DEFINITIVA (Emisión de Nota de Crédito por el Valor Total)
    # -----------------------------------------------------------------------------------------------------
    elif data.return_type == "DEVOLUCION_DINERO":
        # [DSC022 - Mensaje 11d] CTR_Devoluciones_Y_Cambios -> Entidad_NotaCredito: generarNotaCreditoDevolucion(datos.id, monto)
        nc_code = f"NC-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        credit_note_obj = CreditNote(
            credit_note_code=nc_code,
            user_id=order.user_id,
            order_id=order.id,
            amount=round(refund_total, 2),
            status="VIGENTE",
            reason=f"Reembolso por devolución definitiva de orden {_numero_orden(order)}",
        )
        db.add(credit_note_obj)
        db.flush()
        # [DSC022 - Mensaje 12d] Entidad_NotaCredito --> CTR_Devoluciones_Y_Cambios: comprobante_emitido

    # -----------------------------------------------------------------------------------------------------
    # Registro en Entidad_OrdenDevolucion
    # -----------------------------------------------------------------------------------------------------
    # [DSC022 - Mensaje 11a / 13b / 13c] CTR_Devoluciones_Y_Cambios -> Entidad_OrdenDevolucion: registrarCambioDevolucion(...)
    ret_num = f"DEV-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    order_ret = OrderReturn(
        return_number=ret_num,
        order_id=order.id,
        processed_by_id=current_user.id,
        return_type=data.return_type,
        reason=data.reason,
        refund_amount=round(refund_total, 2),
        difference_amount=round(diff_total, 2),
        credit_note_id=credit_note_obj.id if credit_note_obj else None,
        status="APROBADA",
    )
    db.add(order_ret)
    db.flush()
    # [DSC022 - Mensaje 12a / 14b / 14c] Entidad_OrdenDevolucion --> CTR_Devoluciones_Y_Cambios: return_id = order_ret.id

    for it in data.items:
        db.add(OrderReturnItem(
            return_id=order_ret.id,
            variant_id=it.variant_id,
            quantity=it.quantity,
            replacement_variant_id=it.replacement_variant_id,
        ))

        # [DSC022 - Mensaje 9a / 9b / 9d] CTR_Devoluciones_Y_Cambios -> Entidad_Inventario: reingresarStock(var_id, qty=+1)
        inv = db.query(Inventory).filter(
            Inventory.branch_id == order.branch_id,
            Inventory.variant_id == it.variant_id
        ).first()
        if inv:
            inv.stock_actual += it.quantity
            db.add(InventoryLedger(
                branch_id=order.branch_id,
                variant_id=it.variant_id,
                quantity=it.quantity,
                movement_type="DEVOLUCION_CLIENTE",
                unit_cost=float(inv.avg_cost or 0),
                reference_id=ret_num,
            ))

        # [DSC022 - Mensaje 9a / 9b] CTR_Devoluciones_Y_Cambios -> Entidad_Inventario: descontarStock(var_nuevo, qty=-1)
        if data.return_type in ["CAMBIO_PRENDA", "CAMBIO_TALLA", "CAMBIO_MODELO"] and it.replacement_variant_id:
            repl_inv = db.query(Inventory).filter(
                Inventory.branch_id == order.branch_id,
                Inventory.variant_id == it.replacement_variant_id
            ).first()
            if not repl_inv or repl_inv.stock_actual < it.quantity:
                raise HTTPException(status_code=400, detail="Stock insuficiente para la prenda de cambio.")
            repl_inv.stock_actual -= it.quantity
            db.add(InventoryLedger(
                branch_id=order.branch_id,
                variant_id=it.replacement_variant_id,
                quantity=-it.quantity,
                movement_type="VENTA",
                unit_cost=float(repl_inv.avg_cost or 0),
                reference_id=ret_num,
            ))

    # [DSC022 - Mensaje 10a / 10b / 10d] Entidad_Inventario --> CTR_Devoluciones_Y_Cambios: inventario_actualizado_ok / stock_ajustado
    tipo_texto = "Devolucion de dinero" if data.return_type == "DEVOLUCION_DINERO" else ("Cambio por talla" if data.return_type == "CAMBIO_TALLA" else ("Cambio por modelo" if data.return_type == "CAMBIO_MODELO" else "Cambio de prenda"))
    detalle = f" Reembolso: Bs. {refund_total:.2f}." if data.return_type == "DEVOLUCION_DINERO" else (f" {price_diff_msg}" if price_diff_msg else "")
    notificar(
        db, order.user_id, f"{tipo_texto} registrada",
        f"Se registro {ret_num} sobre tu pedido {_numero_orden(order)}.{detalle}",
        TIPO_PEDIDO, order.id, "ORDER",
    )
    db.commit()
    db.refresh(order_ret)

    log_event(db, current_user.id, "INSERT", "order_returns", order_ret.id,
              {"return_number": order_ret.return_number, "order_id": order.id, "type": data.return_type},
              request.client.host)

    # [DSC022 - Mensaje 13a / 15b / 15c / 13d] CTR_Devoluciones_Y_Cambios --> IU_Gestion_Devoluciones: confirmación / respuesta
    # [DSC022 - Mensaje 14a / 16b / 16c / 14d] IU_Gestion_Devoluciones --> Cajero_Encargado: comprobante finalizado / entrega de prenda / nota de crédito
    return OrderReturnResponse(
        id=order_ret.id,
        return_number=order_ret.return_number,
        order_id=order_ret.order_id,
        return_type=order_ret.return_type,
        reason=order_ret.reason,
        refund_amount=float(order_ret.refund_amount),
        status=order_ret.status,
        created_at=order_ret.created_at,
        credit_note_code=credit_note_obj.credit_note_code if credit_note_obj else None,
        difference_amount=float(diff_total),
        price_difference_message=price_diff_msg,
    )


# ==============================================================================================
# FASE 1: BÚSQUEDA Y VALIDACIÓN DE FACTURA (14 DÍAS DE GARANTÍA) [Mensajes 1 al 6]
# ==============================================================================================

# [DSC022 - Mensaje 1] Cajero_Encargado -> IU_Gestion_Devoluciones: ingresarCodigoFactura(codigo_factura='FAC-10024')
# [DSC022 - Mensaje 2] IU_Gestion_Devoluciones -> CTR_Devoluciones_Y_Cambios: GET /api/v1/sales/returns/lookup-invoice?codigo=FAC-10024
@router.get("/returns/lookup-invoice", response_model=InvoiceLookupResponse)
def lookup_invoice_query(
    codigo: str = Query(..., description="Código de factura o número de orden"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU22 / DSC022 - Mensaje 2] Búsqueda de factura por parámetro query 'codigo'."""
    return lookup_invoice_by_code(codigo, db, current_user)


# [DSC022 - Mensaje 2 (variante REST de ruta)] GET /api/v1/sales/invoices/by-code/{invoice_code}
@router.get("/invoices/by-code/{invoice_code}", response_model=InvoiceLookupResponse)
def lookup_invoice_by_code(
    invoice_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [CU22 / DSC022 - Mensajes 1 al 6: Búsqueda y Validación de Factura para Devolución o Cambio]
    """
    code_clean = invoice_code.strip()
    invoice = None
    if code_clean.isdigit():
        invoice = db.query(Invoice).filter(Invoice.id == int(code_clean)).first()
        if not invoice:
            invoice = db.query(Invoice).filter(Invoice.order_id == int(code_clean)).first()
    elif code_clean.upper().startswith("FAC-"):
        raw_id = code_clean.upper().replace("FAC-", "")
        if raw_id.isdigit():
            invoice = db.query(Invoice).filter(Invoice.id == int(raw_id)).first()
    elif code_clean.upper().startswith("ORD-"):
        raw_oid = code_clean.upper().replace("ORD-", "")
        if raw_oid.isdigit():
            invoice = db.query(Invoice).filter(Invoice.order_id == int(raw_oid)).first()

    if not invoice:
        invoice = db.query(Invoice).filter(Invoice.control_code.ilike(code_clean)).first()

    if not invoice:
        raise HTTPException(status_code=404, detail=f"No se encontro factura con el codigo '{invoice_code}'.")

    # [DSC022 - Mensaje 3] CTR_Devoluciones_Y_Cambios -> Entidad_Factura / Entidad_Orden: buscarFacturaConItems(codigo_factura)
    order = db.query(Order).filter(Order.id == invoice.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden asociada a la factura no encontrada.")

    branch = db.query(Branch).filter(Branch.id == order.branch_id).first()
    branch_name = branch.name if branch else f"Sucursal #{order.branch_id}"

    # [DSC022 - Mensaje 4] Entidad_Factura --> CTR_Devoluciones_Y_Cambios: {factura_id, orden_id, fecha, items}
    # Validación de Plazo Derecho: delta_dias = NOW - fecha_compra
    now_utc = datetime.now(timezone.utc)
    order_time = order.created_at
    if order_time.tzinfo is None:
        order_time = order_time.replace(tzinfo=timezone.utc)
    days_diff = (now_utc - order_time).days

    warranty_limit = 14
    warranty_valid = days_diff <= warranty_limit

    # [DSC022 - Mensaje 5a / 6a] [alt: delta_dias > 14 dias (2 Semanas Vencidas)]
    #   CTR -->> IU: Plazo vencido (Garantía Expirada - No procede devolución ni cambio)
    # [DSC022 - Mensaje 5b / 6b] [else: delta_dias <= 14 dias (Garantía Vigente 2 Semanas)]
    #   CTR -->> IU: HTTP 200 OK con items_factura, garantia_valida=true y dias_restantes
    if warranty_valid:
        days_left = warranty_limit - days_diff
        warranty_msg = f"Garantia vigente. Quedan {days_left} dias de los 14 permitidos (2 semanas) para cambios o devoluciones."
    else:
        warranty_msg = f"Plazo vencido. Han transcurrido {days_diff} dias desde la compra. El limite estricto de garantia es de 14 dias (2 semanas)."

    items_res = []
    for oi in order.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == oi.variant_id).first()
        p_name = "Prenda"
        size_name = "Unica"
        color_name = "Estandar"
        sku = None
        if variant:
            sku = variant.sku
            if variant.size:
                size_name = variant.size.name
            if variant.color:
                color_name = variant.color.name
            if variant.product:
                p_name = variant.product.name

        items_res.append(InvoiceItemDetail(
            variant_id=oi.variant_id,
            product_name=p_name,
            sku=sku,
            size=size_name,
            color=color_name,
            quantity=oi.quantity,
            unit_price=float(oi.unit_price),
            subtotal=round(float(oi.unit_price) * oi.quantity, 2),
        ))

    inv_display_code = f"FAC-{invoice.id:05d}" if not invoice.control_code else f"FAC-{invoice.id:05d} ({invoice.control_code})"

    return InvoiceLookupResponse(
        invoice_id=invoice.id,
        invoice_code=inv_display_code,
        order_id=order.id,
        order_number=_numero_orden(order),
        branch_id=order.branch_id,
        branch_name=branch_name,
        customer_name=invoice.customer_name or (f"{order.user.first_name} {order.user.last_name}" if order.user else None),
        customer_nit=invoice.customer_nit,
        total=float(invoice.total),
        issued_at=invoice.issued_at,
        days_since_purchase=days_diff,
        warranty_valid=warranty_valid,
        warranty_days_limit=warranty_limit,
        warranty_message=warranty_msg,
        items=items_res,
    )


# [CU18 - Flujo Alterno A - Paso 1] (IU) Temporizador detecta 5 minutos cumplidos en pasarela (300s)
# [CU18 - Flujo Alterno A - Paso 2] / [DSC018 - Flujo Alterno A - Paso 2] +1. check_payment_timeout(order_id)
@router.post("/orders/{order_id}/check-payment-timeout")
def check_payment_timeout(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [CU18 - Flujo Alterno A: Timeout de Pasarela de Pagos (5 Minutos / 300 Segundos)]
    
    Diagrama de Secuencia y Análisis BCE:
      - Boundary: IU_CheckoutOnline (Temporizador en frontend) / Job Cron de Expiración
      - Control: CTR_Ventas (POST /api/v1/sales/orders/{order_id}/check-payment-timeout)
      - Entity: CE_Orden (Transición de estado a 'CANCELADA_TIMEOUT')
      - Entity: CE_Inventario (Reingreso de existencias reservadas al stock disponible de la sucursal)
      - Entity: CE_InventoryLedger (Registro de auditoría tipo 'LIBERACION_TIMEOUT' en Kardex)
      - Entity: CE_NotificacionPush (Alerta push inmediata al cliente informando cancelación sin costo)
      
    Regla de Negocio:
      Si now >= payment_session_expires_at (5 minutos tras la creación de la orden pendiente):
      1. Se cancela la orden sin ningún cargo financiero al cliente.
      2. El stock bloqueado se libera en tiempo real para que otros clientes puedan adquirirlo.
      3. Se despacha una notificación push informando la cancelación por inactividad.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    now = datetime.now(timezone.utc)
    order_time = order.created_at
    if order_time.tzinfo is None:
        order_time = order_time.replace(tzinfo=timezone.utc)

    expires_at = order.payment_session_expires_at or (order_time + timedelta(minutes=5))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if order.status in ["PENDIENTE", "PENDIENTE_PAGO"]:
        if now >= expires_at:
            # [CU18 - Flujo Alterno A - Paso 3] / [DSC018 - Flujo Alterno A - Paso 3] +2. cancelar_orden_y_liberar_stock_a_disponible()
            order.status = "CANCELADA_TIMEOUT"
            for item in order.items:
                inv = db.query(Inventory).filter(
                    Inventory.branch_id == order.branch_id,
                    Inventory.variant_id == item.variant_id
                ).first()
                if inv:
                    inv.stock_actual += item.quantity
                    db.add(InventoryLedger(
                        branch_id=order.branch_id,
                        variant_id=item.variant_id,
                        quantity=item.quantity,
                        movement_type="LIBERACION_TIMEOUT",
                        unit_cost=float(inv.avg_cost or 0),
                        reference_id=f"TIMEOUT-{order.id}",
                    ))
            # [CU18 - Flujo Alterno A - Paso 4] / [DSC018 - Flujo Alterno A - Paso 4] +3. notificar_alerta_cancelacion_timeout_push()
            notificar(
                db, order.user_id,
                "Sesion de pago expirada (5 min)",
                "Tu sesion de pago de 5 minutos expiro. No se realizo ningun cargo y las prendas reservadas han sido liberadas.",
                TIPO_PEDIDO, order.id, "ORDER"
            )
            db.commit()
            return {
                "order_id": order.id,
                "status": order.status,
                "expired": True,
                "message": "La sesion de pago expiro. El stock ha sido liberado y la orden cancelada sin cargo."
            }
        else:
            remaining_seconds = max(0, int((expires_at - now).total_seconds()))
            return {
                "order_id": order.id,
                "status": order.status,
                "expired": False,
                "remaining_seconds": remaining_seconds,
                "message": f"Sesion de pago activa. Tiempo restante: {remaining_seconds} segundos."
            }

    return {
        "order_id": order.id,
        "status": order.status,
        "expired": False,
        "message": f"La orden ya se encuentra en estado {order.status}."
    }


# [CU18 - Flujo Alterno B - Paso 1] (IU) Encargado de sucursal ejecuta revisión de pedidos tras 48h
# [CU18 - Flujo Alterno B - Paso 2] / [DSC018 - Flujo Alterno B - Paso 2] +1. expire_uncollected_pickup(order_id)
@router.post("/orders/{order_id}/expire-uncollected-pickup")
def expire_uncollected_pickup(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(manager_check),
):
    """
    [CU18 - Flujo Alterno B: Expiración de Custodia por Retiro en Sucursal (48 Horas)]
    
    Diagrama de Secuencia y Análisis BCE:
      - Boundary: IU_AdminVentas / Terminal de Encargado de Sucursal
      - Control: CTR_Ventas (POST /api/v1/sales/orders/{order_id}/expire-uncollected-pickup)
      - Entity: CE_Orden (Transición a estado 'RETIRO_EXPIRADO')
      - Entity: CE_Inventario (Reingreso de prendas desde el depósito de retiro a perchas/exhibición)
      - Entity: CE_InventoryLedger (Movimiento 'REINGRESO_EXPIRACION_RETIRO' en Kardex valorado)
      - Entity: CE_NotaDeCredito (Emisión automática de CE_NotaDeCredito por el 100% del valor pagado)
      - Entity: CE_NotificacionPush (Notificación al cliente con código de Nota de Crédito asignado)
      
    Regla de Negocio:
      Si han transcurrido más de 48 horas desde la compra sin que el cliente retire su pedido:
      1. Se desmarca la prenda de reserva y retorna físicamente a exhibición en tienda.
      2. No se realiza reembolso en efectivo ni reversión bancaria (no devolución en dinero).
      3. Se emite automáticamente una Nota de Crédito (CE_NotaDeCredito) vinculada a la cuenta
         del cliente, válida para cualquier compra futura en cualquier sucursal.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    if order.delivery_type != "RETIRO_TIENDA":
        raise HTTPException(status_code=400, detail="Esta orden no corresponde a retiro en sucursal.")

    now = datetime.now(timezone.utc)
    order_time = order.created_at
    if order_time.tzinfo is None:
        order_time = order_time.replace(tzinfo=timezone.utc)

    deadline = order.pickup_deadline or (order_time + timedelta(hours=48))
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if now < deadline:
        hours_left = round((deadline - now).total_seconds() / 3600, 1)
        raise HTTPException(
            status_code=400,
            detail=f"El plazo de custodia aun no ha vencido. Restan {hours_left} horas para el retiro."
        )

    # [CU18 - Flujo Alterno B - Paso 3] / [DSC018 - Flujo Alterno B - Paso 3] +2. retornar_prendas_a_exhibicion_en_kardex()
    order.status = "RETIRO_EXPIRADO"
    for item in order.items:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == order.branch_id,
            Inventory.variant_id == item.variant_id
        ).first()
        if inv:
            inv.stock_actual += item.quantity
            db.add(InventoryLedger(
                branch_id=order.branch_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                movement_type="REINGRESO_EXPIRACION_RETIRO",
                unit_cost=float(inv.avg_cost or 0),
                reference_id=f"EXP-RET-{order.id}",
            ))

    # [CU18 - Flujo Alterno B - Paso 4] / [DSC018 - Flujo Alterno B - Paso 4] +3. emitir_nota_de_credito_cliente(amount=order.total_amount)
    nc_code = f"NC-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    credit_note = CreditNote(
        credit_note_code=nc_code,
        user_id=order.user_id,
        order_id=order.id,
        amount=float(order.total_amount),
        status="VIGENTE",
        reason="Expiracion de custodia de 48 horas en sucursal",
    )
    db.add(credit_note)
    notificar(
        db, order.user_id,
        "Plazo de retiro vencido (48h) - Nota de Credito emitida",
        f"Tu pedido {_numero_orden(order)} supero el plazo de 48h en sucursal. Se reingreso a stock y se genero la Nota de Credito {nc_code} por Bs. {order.total_amount:.2f}.",
        TIPO_PEDIDO, order.id, "ORDER"
    )
    db.commit()
    db.refresh(credit_note)
    return {
        "order_id": order.id,
        "status": order.status,
        "credit_note_code": credit_note.credit_note_code,
        "amount": float(credit_note.amount),
        "message": f"Prendas devueltas a stock y Nota de Credito {nc_code} generada exitosamente."
    }


# [CU22 - Paso 8] (IU) El cliente abre su perfil para consultar notas de crédito disponibles
# [CU22 - Paso 8.1] / [DSC022 - Paso 8.1] +1. get_my_credit_notes()
@router.get("/credit-notes/my-credit-notes", response_model=List[CreditNoteResponse])
def get_my_credit_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [CU22 / CU18] CE_NotaDeCredito: Consulta de Notas de Crédito del cliente.
    Lista saldos a favor disponibles emitidos por cambio por modelo de menor valor o
    por vencimiento del plazo de custodia de 48 horas en retiro en tienda.
    """
    notes = db.query(CreditNote).filter(
        CreditNote.user_id == current_user.id
    ).order_by(CreditNote.created_at.desc()).all()
    return notes
