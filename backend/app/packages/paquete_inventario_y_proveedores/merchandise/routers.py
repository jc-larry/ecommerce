import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from app.db.session import get_db

from app.packages.paquete_inventario_y_proveedores.merchandise.models import (
    PurchaseOrder, PurchaseDetail, Inventory, InventoryLedger,
    StockTransfer, StockTransferDetail,
)
from app.packages.paquete_inventario_y_proveedores.merchandise.schemas import (
    PurchaseOrderCreate, PurchaseOrderResponse,
    InventoryResponse, InventoryLedgerResponse,
    InventoryValuationResponse, InventoryValuationItem,
    InventoryAdjustmentCreate, InventoryAdjustmentResponse,
    StockTransferCreate, StockTransferResponse, StockTransferDetailResponse,
    StockTransferStatusUpdate, StockThresholdUpdate, StockAlertItem,
)
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import Product, ProductVariant, Color, Size
from app.packages.paquete_inventario_y_proveedores.suppliers.models import Supplier
# Importar control de roles, usuario y logueo de auditoría del paquete de Seguridad
from app.packages.paquete_seguridad_usuarios import (
    User, RoleChecker, log_event, get_current_user, get_branch_scope, BranchScope,
    get_supplier_scope,
)

router = APIRouter(prefix="/api/v1/merchandise", tags=["merchandise"])

# Tanto SUPERADMIN como ENCARGADO pueden registrar compras e ingresos de stock (CU10, central)
staff_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO"])
# Módulos operativos de sucursal (inventario, alertas, ajustes, transferencias): también CAJERO
branch_staff_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO", "CAJERO"])
# Historial de compras: personal de tienda (scoped por sucursal) o el proveedor dueño (scoped a sí mismo)
purchase_history_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO", "CAJERO", "PROVEEDOR"])

REASON_LABELS = {
    "MERMA": "Merma general",
    "MERMA_DEFECTO_FABRICA": "Tara / Defecto textil de fábrica",
    "MERMA_DANIO_TIENDA": "Daño en tienda o probador",
    "MERMA_OBSOLESCENCIA": "Obsolescencia / Liquidación textil",
    "DANO": "Prenda dañada / manchada",
    "PERDIDA": "Pérdida / Extravío",
    "FALTANTE_INVENTARIO": "Faltante en conteo físico",
    "CONTEO": "Ajuste por conteo físico",
    "SOBRANTE_INVENTARIO": "Sobrante en conteo físico (Excedente)",
}

# [DSC010 - Mensaje 1] Encargado -> IU_Ingreso: 1: registrarLoteIngreso(proveedor_id, sucursal_id, nro_factura, items)
# [DSC010 - Mensaje 2] IU_Ingreso -> CTR_Compras: 2: POST /api/v1/merchandise/intake (PurchaseOrderCreate)
@router.post("/intake", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def register_merchandise_intake(
    intake_data: PurchaseOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check)
):
    """[CU10] Registra compras a proveedores con cálculo de Costo Promedio Ponderado (CPP) y prorrateo de flete."""
    # [DSC010 - Mensaje 3] CTR_Compras -> CE_Proveedor: 3: find_by_id(proveedor_id)
    supplier = db.query(Supplier).filter(Supplier.id == intake_data.supplier_id).first()
    # [DSC010 - Mensaje 4] CE_Proveedor -->> CTR_Compras: 4: Supplier(id=12, razon_social="Textiles Andinos S.A.")
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
        
    branch = db.query(Branch).filter(Branch.id == intake_data.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    if not intake_data.details:
        raise HTTPException(status_code=400, detail="El ingreso debe contener al menos un producto.")

    # [DSC010 - Mensaje 5] CTR_Compras -> CTR_Compras: 5: prorratearCostoLanded(shipping_cost, raw_subtotal)
    shipping = float(intake_data.shipping_cost or 0.0)
    raw_subtotal = sum(item.quantity * item.unit_cost for item in intake_data.details)
    freight_factor = (shipping / raw_subtotal) if (shipping > 0 and raw_subtotal > 0) else 0.0

    # [DSC010 - Mensaje 6] CTR_Compras -> CE_Compra: 6: create_purchase_order(proveedor_id, sucursal_id, status='COMPLETADO', nro_factura, total)
    purchase = PurchaseOrder(
        supplier_id=intake_data.supplier_id,
        branch_id=intake_data.branch_id,
        status="COMPLETADO",
        invoice_number=intake_data.invoice_number,
        shipping_cost=shipping,
        notes=intake_data.notes,
        total_amount=round(raw_subtotal + shipping, 2),
    )
    db.add(purchase)
    db.flush()
    # [DSC010 - Mensaje 7] CE_Compra -->> CTR_Compras: 7: compra PurchaseOrder(id=140)

    total_value = 0.0

    # Loop de procesamiento: Se itera cada variante ingresada en el lote
    for item in intake_data.details:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variante de producto con ID {item.variant_id} no encontrada.")

        # Costo unitario landed (compra + flete prorrateado)
        landed_unit_cost = round(item.unit_cost * (1.0 + freight_factor), 2)
        total_value += (item.quantity * landed_unit_cost)

        # [DSC010 - Mensaje 10] CTR_Compras -> CE_Inventario: 10: get_stock_and_cpp(sucursal_id, variante_id)
        stock_record = db.query(Inventory).filter(
            Inventory.branch_id == purchase.branch_id,
            Inventory.variant_id == item.variant_id
        ).first()

        # [DSC010 - Mensaje 11] CE_Inventario -->> CTR_Compras: 11: StockActual(stock_previo=20, cpp_previo=100.00)
        previous_avg = float(stock_record.avg_cost or 0.0) if stock_record else 0.0
        stock_previo = stock_record.stock_actual if stock_record else 0
        nuevo_stock = stock_previo + item.quantity

        # [DSC010 - Mensaje 12] CTR_Compras -> CTR_Compras: 12: calcularNuevoCPP(stock_prev, cpp_prev, cant_nueva, costo_landed) -> nuevo_cpp
        if not stock_record:
            # Primer ingreso de esta variante
            new_avg = landed_unit_cost
            stock_record = Inventory(
                branch_id=purchase.branch_id,
                variant_id=item.variant_id,
                stock_actual=nuevo_stock,
                avg_cost=new_avg,
                stock_minimo=5,
                stock_maximo=100
            )
            db.add(stock_record)
        else:
            # Fórmula oficial CPP: (stock_ant * cpp_ant + cant_nueva * costo_landed) / stock_total
            if nuevo_stock > 0:
                new_avg = round(
                    (stock_previo * previous_avg + item.quantity * landed_unit_cost) / nuevo_stock, 2
                )
            else:
                new_avg = landed_unit_cost
            # [DSC010 - Mensaje 13] CTR_Compras -> CE_Inventario: 13: update_inventory(sucursal_id, variante_id, stock_adicional, nuevo_cpp)
            stock_record.avg_cost = new_avg
            stock_record.stock_actual = nuevo_stock
            # [DSC010 - Mensaje 14] CE_Inventario -->> CTR_Compras: 14: Inventory(stock_total=30, cpp=110.00)

        # [DSC010 - Mensaje 8] CTR_Compras -> CE_Compra: 8: add_item(compra_id=140, variante_id, cantidad, costo_unitario)
        detail = PurchaseDetail(
            purchase_order_id=purchase.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_cost=landed_unit_cost,
            previous_avg_cost=previous_avg,
            new_avg_cost=new_avg,
        )
        db.add(detail)
        # [DSC010 - Mensaje 9] CE_Compra -->> CTR_Compras: 9: ItemCompra(id=811)

        # [DSC010 - Mensaje 15] CTR_Compras -> CE_Kardex: 15: registrarMovimiento(tipo='INGRESO', ref="FACT-{nro_factura}", cantidad=+qty, costo_unit)
        ref_doc = f"FACT-{purchase.invoice_number}" if purchase.invoice_number else f"OC-{purchase.id}"
        ledger = InventoryLedger(
            branch_id=purchase.branch_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            movement_type="INGRESO",
            unit_cost=landed_unit_cost,
            reference_id=ref_doc
        )
        db.add(ledger)
        # [DSC010 - Mensaje 16] CE_Kardex -->> CTR_Compras: 16: AsientoKardex(id=9452)

    db.commit()
    db.refresh(purchase)

    log_event(
        db, current_user.id, "INSERT", "purchase_orders", purchase.id, 
        {"supplier_id": purchase.supplier_id, "branch_id": purchase.branch_id, 
         "invoice_number": purchase.invoice_number, "total_value": total_value}, 
        request.client.host
    )
    # [DSC010 - Mensaje 17] CTR_Compras -->> IU_Ingreso: 17: HTTP 201 Created PurchaseOrderResponse(compra_id=140, status='COMPLETADO')
    # [DSC010 - Mensaje 18] IU_Ingreso -->> Encargado: 18: renderizarComprobanteIngresoConKardexActualizado()
    return purchase


@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    branch_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(purchase_history_check),
):
    """Historial de órdenes de compra: el personal de tienda lo ve por sucursal (con el
    mismo alcance ya aplicado en el resto del módulo), y un usuario PROVEEDOR solo ve las
    órdenes de su propio proveedor, ignorando cualquier branch_id/supplier_id que envíe."""
    user_roles = [r.name for r in current_user.roles]
    query = db.query(PurchaseOrder).options(selectinload(PurchaseOrder.details))

    if "PROVEEDOR" in user_roles and not any(r in user_roles for r in ("SUPERADMIN", "ENCARGADO", "CAJERO")):
        scope = get_supplier_scope(current_user, db)
        query = query.filter(PurchaseOrder.supplier_id == scope.supplier_id)
    else:
        branch_scope = get_branch_scope(current_user, db)
        effective_branch_id = branch_id if branch_scope.is_central else branch_scope.branch_id
        if effective_branch_id:
            query = query.filter(PurchaseOrder.branch_id == effective_branch_id)
        if supplier_id:
            query = query.filter(PurchaseOrder.supplier_id == supplier_id)

    return query.order_by(PurchaseOrder.created_at.desc()).limit(limit).all()


@router.get("/inventory", response_model=List[InventoryResponse])
def get_inventory_levels(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(branch_staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU10] Consulta el stock de variantes actual global (central) o de la sucursal del usuario.

    Incluye datos de exhibición (nombre, SKU, color, talla, imagen, precio de venta) para que
    el POS pueda listar productos vendibles sin depender de /valuation (que expone costo/margen
    y por eso está restringido a SUPERADMIN/ENCARGADO)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = (
        db.query(Inventory, ProductVariant, Product, Color, Size)
        .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(Color, Color.id == ProductVariant.color_id)
        .outerjoin(Size, Size.id == ProductVariant.size_id)
    )
    if effective_branch_id:
        query = query.filter(Inventory.branch_id == effective_branch_id)

    results = []
    for inv, variant, prod, color, size in query.all():
        sale_price = float(variant.price_override if variant.price_override is not None else (prod.base_price or 0))
        img_url = None
        if prod.images:
            primary = next((img.image_url for img in prod.images if img.is_primary), None)
            img_url = primary or prod.images[0].image_url
        results.append(InventoryResponse(
            branch_id=inv.branch_id,
            variant_id=inv.variant_id,
            stock_actual=inv.stock_actual,
            avg_cost=float(inv.avg_cost or 0),
            stock_minimo=inv.stock_minimo,
            stock_maximo=inv.stock_maximo,
            sku=variant.sku,
            product_name=prod.name,
            color_name=color.name if color else "Estándar",
            size_name=size.name if size else "Única",
            image_url=img_url,
            sale_price=sale_price,
        ))
    return results

@router.get("/ledger", response_model=List[InventoryLedgerResponse])
def get_inventory_ledger(
    branch_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(branch_staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU10] Consulta el historial del libro diario de movimientos de inventario"""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(InventoryLedger)
    if effective_branch_id:
        query = query.filter(InventoryLedger.branch_id == effective_branch_id)
    if movement_type:
        query = query.filter(InventoryLedger.movement_type == movement_type)
    return query.order_by(InventoryLedger.created_at.desc()).limit(limit).all()


# [CU37 - Paso 1] (IU) Personal administrativo abre el reporte de valoración CPP
@router.get("/valuation", response_model=InventoryValuationResponse)
# [CU37 - Paso 2] / [DSC037 - Paso 2] +1. get_inventory_valuation(branch_id)
def get_inventory_valuation(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU37] Valoración de inventario / capital invertido por COSTO PROMEDIO PONDERADO y márgenes comerciales."""
    branch_id = branch_id if scope.is_central else scope.branch_id
    # [CU37 - Paso 4] / [DSC037 - Paso 4] CTR_Inventory -> CE_Inventario: +2. select_inventory(branch_id)
    query = (
        db.query(Inventory, ProductVariant, Product, Branch, Color, Size)
        .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .join(Branch, Branch.id == Inventory.branch_id)
        .outerjoin(Color, Color.id == ProductVariant.color_id)
        .outerjoin(Size, Size.id == ProductVariant.size_id)
    )
    if branch_id:
        query = query.filter(Inventory.branch_id == branch_id)

    items: List[InventoryValuationItem] = []
    capital = 0.0
    total_venta = 0.0
    total_unidades = 0

    # [CU37 - Paso 6] / [DSC037 - Paso 6] [loop: Para cada fila de inventario] CTR_Inventory -> CE_Variante: +3. calc_capital_and_margins()
    for inv, variant, prod, branch, color, size in query.all():
        avg = float(inv.avg_cost or 0)
        cost_total = round(inv.stock_actual * avg, 2)
        sale_price = float(variant.price_override if variant.price_override is not None else (prod.base_price or 0))
        sale_total = round(inv.stock_actual * sale_price, 2)
        margin_unit = round(sale_price - avg, 2)
        margin_percent = round(((sale_price - avg) / sale_price * 100) if sale_price > 0 else 0.0, 1)

        capital += cost_total
        total_venta += sale_total
        total_unidades += inv.stock_actual

        img_url = None
        if prod.images:
            primary = next((img.image_url for img in prod.images if img.is_primary), None)
            img_url = primary or prod.images[0].image_url

        items.append(InventoryValuationItem(
            branch_id=inv.branch_id,
            branch_name=branch.name,
            variant_id=inv.variant_id,
            sku=variant.sku,
            product_name=prod.name,
            color_name=color.name if color else "Estándar",
            color_hex=color.hex_code if color else "#999999",
            size_name=size.name if size else "Única",
            image_url=img_url,
            stock_actual=inv.stock_actual,
            avg_cost=avg,
            valor=cost_total,
            sale_price=sale_price,
            valor_venta=sale_total,
            margen_bruto_unit=margin_unit,
            margen_bruto_percent=margin_percent,
        ))

    utilidad_proyectada = round(total_venta - capital, 2)
    margen_promedio = round((utilidad_proyectada / total_venta * 100) if total_venta > 0 else 0.0, 1)

    # [CU37 - Paso 7] / [DSC037 - Paso 7] CTR_Inventory -->> IU_Valuation: HTTP 200 OK (capital_invertido, items[])
    return InventoryValuationResponse(
        branch_id=branch_id,
        capital_invertido=round(capital, 2),
        total_valor_venta=round(total_venta, 2),
        utilidad_bruta_proyectada=utilidad_proyectada,
        margen_bruto_promedio_percent=margen_promedio,
        total_unidades=total_unidades,
        items=items,
    )


# [CU38 - Paso 1] (IU) Encargado registra solicitud de ajuste de stock (merma/sobrante) en IU_Adjustments
@router.post("/adjustments", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_201_CREATED)
# [CU38 - Paso 2] / [DSC038 - Paso 2] +1. register_inventory_adjustment(datos)
def register_inventory_adjustment(
    data: InventoryAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU38] Registra mermas, daños, pérdidas textiles o sobrantes de inventario con cálculo financiero en Bs."""
    if not scope.is_central:
        data.branch_id = scope.branch_id
    if data.quantity == 0:
        raise HTTPException(status_code=400, detail="La cantidad del ajuste no puede ser cero.")

    # [CU38 - Paso 3] / [DSC038 - Paso 3] CTR_Inventory -> CE_Inventario: +2. check_inventory_exists(branch_id, variant_id)
    stock_record = db.query(Inventory).filter(
        Inventory.branch_id == data.branch_id,
        Inventory.variant_id == data.variant_id
    ).first()
    if not stock_record:
        raise HTTPException(status_code=404, detail="No existe inventario para esa variante en la sucursal indicada.")

    if data.quantity < 0 and stock_record.stock_actual + data.quantity < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente para dar de baja (actual {stock_record.stock_actual}, ajuste {data.quantity})."
        )

    unit_cost = float(stock_record.avg_cost or 0)
    financial_impact = round(abs(data.quantity) * unit_cost, 2)
    movement_type = "SOBRANTE" if data.quantity > 0 else "MERMA"
    reason_label = REASON_LABELS.get(data.reason, data.reason)

    # [CU38 - Paso 4] / [DSC038 - Paso 4] [alt: Cantidad válida y stock suficiente] CTR_Inventory -> CE_Inventario: +3. update_stock(delta)
    stock_record.stock_actual += data.quantity
    # [CU38 - Paso 5] / [DSC038 - Paso 5] CTR_Inventory -> CE_LibroMayor: +4. insert_entry(type='AJUSTE', qty=delta)
    ledger = InventoryLedger(
        branch_id=data.branch_id,
        variant_id=data.variant_id,
        quantity=data.quantity,
        movement_type=movement_type,
        unit_cost=unit_cost,
    )
    db.add(ledger)
    db.flush()
    ledger.reference_id = f"AJU-{ledger.id}"
    db.commit()
    db.refresh(ledger)

    # [CU38 - Paso 6] / [DSC038 - Paso 6] [opt: CU36] CTR_Inventory -> CE_Bitacora: +5. log_event('INSERT', 'inventory_ledger')
    log_event(
        db, current_user.id, "INSERT", "inventory_ledger", ledger.id,
        {"reason": data.reason, "reason_label": reason_label, "quantity": data.quantity, 
         "financial_impact": financial_impact, "note": data.note,
         "branch_id": data.branch_id, "variant_id": data.variant_id},
        request.client.host
    )
    # [CU38 - Paso 7] / [DSC038 - Paso 7] CTR_Inventory -->> IU_Adjustments: HTTP 201 Created (Ajuste registrado)
    return InventoryAdjustmentResponse(
        ledger_id=ledger.id,
        branch_id=data.branch_id,
        variant_id=data.variant_id,
        quantity=data.quantity,
        reason=data.reason,
        reason_label=reason_label,
        unit_cost=unit_cost,
        financial_impact=financial_impact,
        stock_resultante=stock_record.stock_actual,
        reference_id=ledger.reference_id,
    )


# ===================================================================
# CU15 — Transferencias de Inventario entre Sucursales
# ===================================================================

def _build_transfer_response(db: Session, trf: StockTransfer) -> StockTransferResponse:
    details_resp = []
    for d in trf.details:
        variant = db.query(ProductVariant).filter(ProductVariant.id == d.variant_id).first()
        prod_name = None
        size_name = None
        color_name = None
        sku = None
        if variant:
            sku = variant.sku
            prod = db.query(Product).filter(Product.id == variant.product_id).first()
            prod_name = prod.name if prod else None
            size = db.query(Size).filter(Size.id == variant.size_id).first()
            size_name = size.name if size else None
            color = db.query(Color).filter(Color.id == variant.color_id).first()
            color_name = color.name if color else None

        details_resp.append(
            StockTransferDetailResponse(
                id=d.id,
                variant_id=d.variant_id,
                quantity=d.quantity,
                sku=sku,
                product_name=prod_name,
                size=size_name,
                color=color_name,
            )
        )

    return StockTransferResponse(
        id=trf.id,
        transfer_number=trf.transfer_number,
        origin_branch_id=trf.origin_branch_id,
        origin_branch_name=trf.origin_branch.name if trf.origin_branch else "Origen",
        destination_branch_id=trf.destination_branch_id,
        destination_branch_name=trf.destination_branch.name if trf.destination_branch else "Destino",
        status=trf.status,
        notes=trf.notes,
        created_at=trf.created_at,
        updated_at=trf.updated_at,
        completed_at=trf.completed_at,
        details=details_resp,
    )


# =========================================================================================================
# CU15 / DSC015: GESTIÓN DE INVENTARIO Y TRANSFERENCIAS ENTRE SUCURSALES (UML 2.5)
# Diagrama de Secuencia Canónico: 3 Fases y 28 Mensajes
# Participantes:
#   - Encargado Sucursal Origen / Destino
#   - Interfaz_Gestion_Inventario (IU)
#   - Controlador_Traspasos_Inventario (CTR)
#   - Entidad_Inventario_Sucursal (CE_I)
#   - Entidad_Kardex_Movimientos (CE_K)
#   - Entidad_Traspaso_Mercaderia (CE_T)
# =========================================================================================================

# ---------------------------------------------------------------------------------------------------------
# FASE 1: Solicitud de Traspaso Inter-Sucursal (Mensajes 1 al 8)
# ---------------------------------------------------------------------------------------------------------
# [DSC015 - Mensaje 1] Encargado Sucursal Origen -> Interfaz_Gestion_Inventario: solicitarTraspaso(sucursal_origen, sucursal_destino, lista_prendas, cantidades)
# [DSC015 - Mensaje 2] Interfaz_Gestion_Inventario -> Controlador_Traspasos_Inventario: registrarSolicitudTraspaso(datos_traspaso)
@router.post("/transfers", response_model=StockTransferResponse, status_code=201)
def create_stock_transfer(
    data: StockTransferCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU15 / DSC015 - Fase 1] Crea una solicitud de transferencia de inventario entre sucursales."""
    if not scope.is_central:
        # Un ENCARGADO/CAJERO solo puede originar transferencias desde su propia sucursal;
        # el destino sí puede ser cualquier otra sucursal de la cadena.
        data.origin_branch_id = scope.branch_id
    if data.origin_branch_id == data.destination_branch_id:
        raise HTTPException(status_code=400, detail="La sucursal de origen y destino no pueden ser la misma.")

    origin = db.query(Branch).filter(Branch.id == data.origin_branch_id).first()
    dest = db.query(Branch).filter(Branch.id == data.destination_branch_id).first()
    if not origin or not dest:
        raise HTTPException(status_code=404, detail="Sucursal de origen o destino no encontrada.")

    if not data.details:
        raise HTTPException(status_code=400, detail="La transferencia debe contener al menos un producto.")

    # [DSC015 - Mensaje 3] Controlador_Traspasos_Inventario -> Entidad_Inventario_Sucursal: verificarStockDisponible(sucursal_origen, prendas)
    for item in data.details:
        if not db.query(ProductVariant.id).filter(ProductVariant.id == item.variant_id).first():
            raise HTTPException(status_code=404, detail=f"Variante {item.variant_id} no encontrada.")
        inv_check = db.query(Inventory).filter(
            Inventory.branch_id == data.origin_branch_id,
            Inventory.variant_id == item.variant_id
        ).first()
        if not inv_check or inv_check.stock_actual < item.quantity:
            current_stk = inv_check.stock_actual if inv_check else 0
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente en origen para variante {item.variant_id} (Disponible: {current_stk}, Requerido: {item.quantity})."
            )

    # [DSC015 - Mensaje 4] Entidad_Inventario_Sucursal --> Controlador_Traspasos_Inventario: stock_suficiente_confirmado

    # [DSC015 - Mensaje 5] Controlador_Traspasos_Inventario -> Entidad_Traspaso_Mercaderia: crearRegistroTraspaso(estado="SOLICITADA", codigo="TRF-2026-001")
    transfer_num = f"TRF-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    trf = StockTransfer(
        transfer_number=transfer_num,
        origin_branch_id=data.origin_branch_id,
        destination_branch_id=data.destination_branch_id,
        requested_by_id=current_user.id,
        status="SOLICITADA",
        notes=data.notes,
    )
    db.add(trf)
    db.flush()

    for item in data.details:
        detail = StockTransferDetail(
            transfer_id=trf.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
        )
        db.add(detail)

    db.commit()
    db.refresh(trf)

    # [DSC015 - Mensaje 6] Entidad_Traspaso_Mercaderia --> Controlador_Traspasos_Inventario: traspaso_id = 101
    log_event(db, current_user.id, "INSERT", "stock_transfers", trf.id,
              {"transfer_number": trf.transfer_number, "origin_id": origin.id, "dest_id": dest.id},
              request.client.host)

    # [DSC015 - Mensaje 7] Controlador_Traspasos_Inventario --> Interfaz_Gestion_Inventario: confirmacionRegistro(traspaso_id=101)
    # [DSC015 - Mensaje 8] Interfaz_Gestion_Inventario --> Encargado Sucursal Origen: notificar("Solicitud de traspaso registrada exitosamente")
    return _build_transfer_response(db, trf)


def _assert_transfer_in_scope(trf: StockTransfer, scope: BranchScope) -> None:
    """Un ENCARGADO/CAJERO solo puede ver/operar transferencias que involucren su sucursal."""
    if scope.is_central:
        return
    if scope.branch_id not in (trf.origin_branch_id, trf.destination_branch_id):
        raise HTTPException(status_code=404, detail="Transferencia no encontrada.")


@router.get("/transfers", response_model=List[StockTransferResponse])
def list_stock_transfers(
    branch_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(branch_staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU15] Lista las transferencias de inventario registradas."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(StockTransfer)
    if effective_branch_id:
        query = query.filter((StockTransfer.origin_branch_id == effective_branch_id) | (StockTransfer.destination_branch_id == effective_branch_id))
    if status_filter:
        query = query.filter(StockTransfer.status == status_filter.upper())

    return [_build_transfer_response(db, t) for t in query.order_by(StockTransfer.created_at.desc()).all()]


@router.get("/transfers/{transfer_id}", response_model=StockTransferResponse)
def get_stock_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(branch_staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU15] Obtiene el detalle de una transferencia específica."""
    trf = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
    if not trf:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada.")
    _assert_transfer_in_scope(trf, scope)
    return _build_transfer_response(db, trf)


# ---------------------------------------------------------------------------------------------------------
# FASES 2 Y 3: Despacho en Origen y Recepción en Destino (Mensajes 9 al 28)
# ---------------------------------------------------------------------------------------------------------
@router.put("/transfers/{transfer_id}/status", response_model=StockTransferResponse)
def update_transfer_status(
    transfer_id: int,
    data: StockTransferStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU15 / DSC015 - Fases 2 y 3] Actualiza el estado de la transferencia afectando existencias y el libro mayor (ACID)."""
    trf = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
    if not trf:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada.")
    _assert_transfer_in_scope(trf, scope)

    new_status = data.status
    current_status = trf.status

    if current_status == new_status:
        return _build_transfer_response(db, trf)

    if current_status in ["COMPLETADA", "CANCELADA"]:
        raise HTTPException(status_code=400, detail=f"No se puede cambiar el estado de una transferencia ya {current_status}.")

    # =====================================================================================================
    # FASE 2: Despacho Físico y Salida de Almacén Origen (Transacción en Origen) [Mensajes 9 al 18]
    # =====================================================================================================
    # [DSC015 - Mensaje 9] Encargado Sucursal Origen -> Interfaz_Gestion_Inventario: despacharPrendasFisicas(traspaso_id=101)
    # [DSC015 - Mensaje 10] Interfaz_Gestion_Inventario -> Controlador_Traspasos_Inventario: procesarSalidaMercaderia(traspaso_id=101)
    if new_status == "EN_TRANSITO":
        if current_status != "SOLICITADA":
            raise HTTPException(status_code=400, detail="Solo se puede pasar a EN_TRANSITO desde SOLICITADA.")

        # Verificar stock suficiente en origen para todos los items
        for d in trf.details:
            inv = db.query(Inventory).filter(
                Inventory.branch_id == trf.origin_branch_id,
                Inventory.variant_id == d.variant_id
            ).first()
            if not inv or inv.stock_actual < d.quantity:
                current_stk = inv.stock_actual if inv else 0
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente en origen para variante {d.variant_id} (Disponible: {current_stk}, Requerido: {d.quantity})."
                )

        # [DSC015 - Mensaje 11] Controlador_Traspasos_Inventario -> Entidad_Inventario_Sucursal: restarStockOrigen(sucursal_origen, prendas, cantidades)
        for d in trf.details:
            inv = db.query(Inventory).filter(
                Inventory.branch_id == trf.origin_branch_id,
                Inventory.variant_id == d.variant_id
            ).first()
            inv.stock_actual -= d.quantity

            # [DSC015 - Mensaje 13] Controlador_Traspasos_Inventario -> Entidad_Kardex_Movimientos: asentarMovimientoSalidaKardex(sucursal_origen, tipo="TRASPASO_SALIDA", ref="TRF-101")
            ledger = InventoryLedger(
                branch_id=trf.origin_branch_id,
                variant_id=d.variant_id,
                quantity=-d.quantity,
                movement_type="TRANSFERENCIA_SALIDA",
                unit_cost=float(inv.avg_cost or 0),
                reference_id=trf.transfer_number,
            )
            db.add(ledger)

        # [DSC015 - Mensaje 12] Entidad_Inventario_Sucursal --> Controlador_Traspasos_Inventario: stock_origen_descontado
        # [DSC015 - Mensaje 14] Entidad_Kardex_Movimientos --> Controlador_Traspasos_Inventario: asiento_salida_registrado

        # [DSC015 - Mensaje 15] Controlador_Traspasos_Inventario -> Entidad_Traspaso_Mercaderia: actualizarEstadoTraspaso(traspaso_id=101, nuevo_estado="EN_TRANSITO")
        trf.status = "EN_TRANSITO"
        # [DSC015 - Mensaje 16] Entidad_Traspaso_Mercaderia --> Controlador_Traspasos_Inventario: estado_actualizado
        # [DSC015 - Mensaje 17] Controlador_Traspasos_Inventario --> Interfaz_Gestion_Inventario: confirmacionDespacho()
        # [DSC015 - Mensaje 18] Interfaz_Gestion_Inventario --> Encargado Sucursal Origen: notificar("Mercadería en camino a sucursal destino")

    # =====================================================================================================
    # FASE 3: Recepción Física e Ingreso en Almacén Destino (Transacción en Destino) [Mensajes 19 al 28]
    # =====================================================================================================
    # [DSC015 - Mensaje 19] Encargado Sucursal Destino -> Interfaz_Gestion_Inventario: confirmarRecepcionFisica(traspaso_id=101)
    # [DSC015 - Mensaje 20] Interfaz_Gestion_Inventario -> Controlador_Traspasos_Inventario: procesarIngresoMercaderia(traspaso_id=101)
    elif new_status == "COMPLETADA":
        # Salto directo: Si venía de SOLICITADA directo a COMPLETADA, descontar primero de origen
        if current_status == "SOLICITADA":
            for d in trf.details:
                inv = db.query(Inventory).filter(
                    Inventory.branch_id == trf.origin_branch_id,
                    Inventory.variant_id == d.variant_id
                ).first()
                if not inv or inv.stock_actual < d.quantity:
                    current_stk = inv.stock_actual if inv else 0
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente en origen para variante {d.variant_id} (Disponible: {current_stk}, Requerido: {d.quantity})."
                    )
                inv.stock_actual -= d.quantity
                db.add(InventoryLedger(
                    branch_id=trf.origin_branch_id,
                    variant_id=d.variant_id,
                    quantity=-d.quantity,
                    movement_type="TRANSFERENCIA_SALIDA",
                    unit_cost=float(inv.avg_cost or 0),
                    reference_id=trf.transfer_number,
                ))

        # [DSC015 - Mensaje 21] Controlador_Traspasos_Inventario -> Entidad_Inventario_Sucursal: sumarStockDestino(sucursal_destino, prendas, cantidades)
        for d in trf.details:
            dest_inv = db.query(Inventory).filter(
                Inventory.branch_id == trf.destination_branch_id,
                Inventory.variant_id == d.variant_id
            ).first()
            # Tomar el costo promedio del origen para mantener valoración consistente
            origin_inv = db.query(Inventory).filter(
                Inventory.branch_id == trf.origin_branch_id,
                Inventory.variant_id == d.variant_id
            ).first()
            unit_cost = float(origin_inv.avg_cost if origin_inv else 0)

            if not dest_inv:
                dest_inv = Inventory(
                    branch_id=trf.destination_branch_id,
                    variant_id=d.variant_id,
                    stock_actual=d.quantity,
                    avg_cost=unit_cost,
                )
                db.add(dest_inv)
            else:
                prev_stock = dest_inv.stock_actual
                prev_cost = float(dest_inv.avg_cost or 0.0)
                new_stock = prev_stock + d.quantity
                if new_stock > 0:
                    dest_inv.avg_cost = round(((prev_stock * prev_cost) + (d.quantity * unit_cost)) / new_stock, 2)
                dest_inv.stock_actual = new_stock

            # [DSC015 - Mensaje 23] Controlador_Traspasos_Inventario -> Entidad_Kardex_Movimientos: asentarMovimientoIngresoKardex(sucursal_destino, tipo="TRASPASO_INGRESO", ref="TRF-101")
            db.add(InventoryLedger(
                branch_id=trf.destination_branch_id,
                variant_id=d.variant_id,
                quantity=d.quantity,
                movement_type="TRANSFERENCIA_ENTRADA",
                unit_cost=unit_cost,
                reference_id=trf.transfer_number,
            ))

        # [DSC015 - Mensaje 22] Entidad_Inventario_Sucursal --> Controlador_Traspasos_Inventario: stock_destino_incrementado
        # [DSC015 - Mensaje 24] Entidad_Kardex_Movimientos --> Controlador_Traspasos_Inventario: asiento_ingreso_registrado

        # [DSC015 - Mensaje 25] Controlador_Traspasos_Inventario -> Entidad_Traspaso_Mercaderia: actualizarEstadoTraspaso(traspaso_id=101, nuevo_estado="COMPLETADA")
        trf.status = "COMPLETADA"
        trf.completed_at = func.now()
        trf.received_by_id = current_user.id
        # [DSC015 - Mensaje 26] Entidad_Traspaso_Mercaderia --> Controlador_Traspasos_Inventario: traspaso_finalizado
        # [DSC015 - Mensaje 27] Controlador_Traspasos_Inventario --> Interfaz_Gestion_Inventario: confirmacionRecepcion()
        # [DSC015 - Mensaje 28] Interfaz_Gestion_Inventario --> Encargado Sucursal Destino: notificar("Prendas incorporadas al inventario de la sucursal")

    # -----------------------------------------------------------------------------------------------------
    # Transición alternativa: CANCELADA (Reversión si estaba en tránsito)
    # -----------------------------------------------------------------------------------------------------
    elif new_status == "CANCELADA":
        # Si ya estaba en tránsito, revertir el descuento en origen
        if current_status == "EN_TRANSITO":
            for d in trf.details:
                inv = db.query(Inventory).filter(
                    Inventory.branch_id == trf.origin_branch_id,
                    Inventory.variant_id == d.variant_id
                ).first()
                if inv:
                    inv.stock_actual += d.quantity
                    db.add(InventoryLedger(
                        branch_id=trf.origin_branch_id,
                        variant_id=d.variant_id,
                        quantity=d.quantity,
                        movement_type="TRANSFERENCIA_REVERSION",
                        unit_cost=float(inv.avg_cost or 0),
                        reference_id=trf.transfer_number,
                    ))
        trf.status = "CANCELADA"

    if data.notes:
        trf.notes = f"{trf.notes or ''} | {data.notes}".strip(" |")

    db.commit()
    db.refresh(trf)

    log_event(db, current_user.id, "UPDATE", "stock_transfers", trf.id,
              {"transfer_number": trf.transfer_number, "new_status": trf.status},
              request.client.host)

    return _build_transfer_response(db, trf)


# ===================================================================
# CU16 — Configuración y Alertas de Stock (Mínimo / Máximo)
# ===================================================================

# [CU16 - Paso 1] / [DSC016 - Paso 1] +1. verify_inventory_thresholds(branch_id, variant_id)
def verify_inventory_thresholds(db: Session, branch_id: int, variant_id: int):
    """
    [CU16] Fase 1: Detección Automática de Quiebre de Stock tras Venta o Transferencia.
    Verifica si el stock de una variante en una sucursal cayó por debajo del umbral mínimo.
    """
    # [CU16 - Paso 2] / [DSC016 - Paso 2] +2. select(branch_id, variant_id)
    inv = db.query(Inventory).filter(
        Inventory.branch_id == branch_id,
        Inventory.variant_id == variant_id
    ).first()
    # [CU16 - Paso 3] / [DSC016 - Paso 3] +3. stock_actual_vs_thresholds
    if not inv:
        return None

    # [CU16 - Paso 4] / [DSC016 - Paso 4] +4. insert_alert(type="STOCK_MINIMO", severity="CRITICA") / notificacion emitida
    if inv.stock_actual <= inv.stock_minimo:
        # Notificación emitida automáticamente por el sistema
        return {
            "alert": "STOCK_MINIMO",
            "severity": "CRITICA",
            "branch_id": branch_id,
            "variant_id": variant_id,
            "stock_actual": inv.stock_actual,
            "stock_minimo": inv.stock_minimo
        }
    return None


# [CU16 - Paso 7] (IU) Encargado abre el panel de alertas de inventario
@router.get("/inventory/alerts", response_model=List[StockAlertItem])
# [CU16 - Paso 8] / [DSC016 - Paso 8] +1. get_stock_alerts(branch_id)
def get_stock_alerts(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(branch_staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU16] Fase 2: Gestión y Visualización de Alertas por el Encargado de Tienda."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = (
        db.query(Inventory, Branch.name.label("branch_name"), ProductVariant, Product.name.label("product_name"), Size.name.label("size_name"), Color.name.label("color_name"))
        .join(Branch, Branch.id == Inventory.branch_id)
        .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(Size, Size.id == ProductVariant.size_id)
        .outerjoin(Color, Color.id == ProductVariant.color_id)
        .filter(
            (Inventory.stock_actual <= Inventory.stock_minimo) |
            (Inventory.stock_actual >= Inventory.stock_maximo)
        )
    )
    if effective_branch_id:
        query = query.filter(Inventory.branch_id == effective_branch_id)

    # [CU16 - Paso 9] / [DSC016 - Paso 9] +2. select_unresolved(branch_id)
    rows = query.order_by(Inventory.stock_actual.asc()).all()

    alerts = []
    for inv, b_name, var, p_name, s_name, c_name in rows:
        alert_type = "QUIEBRE_STOCK" if inv.stock_actual <= inv.stock_minimo else "SOBRESTOCK"
        alerts.append(
            StockAlertItem(
                branch_id=inv.branch_id,
                branch_name=b_name,
                variant_id=inv.variant_id,
                product_name=p_name,
                sku=var.sku,
                size=s_name or "Única",
                color=c_name or "Estándar",
                stock_actual=inv.stock_actual,
                stock_minimo=inv.stock_minimo,
                stock_maximo=inv.stock_maximo,
                alert_type=alert_type,
            )
        )
    # [CU16 - Paso 11] / [DSC016 - Paso 11] +3. HTTP 200 OK (alertas_con_variantes[]) / renderizarAlertas
    return alerts


@router.put("/inventory/thresholds/{branch_id}/{variant_id}")
def update_stock_thresholds(
    branch_id: int,
    variant_id: int,
    data: StockThresholdUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """Configura umbrales operativos de stock mínimo y máximo para una sucursal y variante."""
    if not scope.is_central and branch_id != scope.branch_id:
        raise HTTPException(status_code=404, detail="Registro de inventario no encontrado.")
    inv = db.query(Inventory).filter(
        Inventory.branch_id == branch_id,
        Inventory.variant_id == variant_id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Registro de inventario no encontrado.")

    if data.stock_minimo >= data.stock_maximo:
        raise HTTPException(status_code=400, detail="El stock mínimo debe ser menor al stock máximo.")

    inv.stock_minimo = data.stock_minimo
    inv.stock_maximo = data.stock_maximo
    db.commit()

    log_event(db, current_user.id, "UPDATE", "inventory", variant_id,
              {"branch_id": branch_id, "stock_minimo": data.stock_minimo, "stock_maximo": data.stock_maximo},
              request.client.host)

    return {"message": "Umbrales actualizados.", "stock_minimo": inv.stock_minimo, "stock_maximo": inv.stock_maximo}

