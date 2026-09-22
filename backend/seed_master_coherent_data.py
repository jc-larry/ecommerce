"""
Script Maestro de Datos Coherentes y Trazabilidad Comercial para FashionStore.
- 2 Sucursales exclusivas en Santa Cruz (Equipetrol y Ventura Mall).
- Ventas ricas distribuidas por canal (ONLINE y POS) y sucursales.
- Prendas más vendidas por temporada (Vestidos de noche, vestidos florales, blusas bordadas, jeans wide-leg, enterizos palazzo, chaquetas de cuero, etc.).
- Medios de pago variados (PayPal, Tarjeta, QR, Efectivo).
- Arqueos y turnos de caja (CashShift) con balance cerrado y turno abierto actual.
- Facturas legales con NIT y Notas de entrega (IVA 13%).
- Trazabilidad en Libro Mayor (InventoryLedger - Kardex).
- Reservas en probador físico (Reservations).
- Despachos y trazabilidad de repartidor (Shipments).
- Transferencias de stock inter-sucursal (StockTransfer).
"""

from datetime import datetime, timedelta, date
import random
from decimal import Decimal

from sqlalchemy import text
from app.db.session import SessionLocal
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import Product, ProductVariant, Category
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_ventas_y_pagos.models import (
    Order, OrderItem, Payment, EfectivoPayment, TarjetaPayment, QRPayment, PayPalPayment,
    Invoice, CashShift
)
from app.packages.paquete_inventario_y_proveedores.merchandise.models import (
    Inventory, InventoryLedger, StockTransfer, StockTransferDetail
)
from app.packages.paquete_reservas_y_citas.models import Reservation, ReservationItem
from app.packages.paquete_envios_y_logistica.models import (
    Shipment, ShipmentTrackingEvent, DeliveryZone
)
from app.packages.paquete_envios_y_logistica.delivery_persons.models import DeliveryPerson

def run_master_seed():
    db = SessionLocal()
    try:
        print("=== 1. Normalización de pedidos existentes ===")
        # Asegurar que los pedidos 'PAGADO' pasen a 'PAGADA' para compatibilidad con Analytics
        cnt_fixed = db.execute(text("UPDATE orders SET status = 'PAGADA' WHERE status = 'PAGADO'")).rowcount
        print(f"Pedidos corregidos a status 'PAGADA': {cnt_fixed}")

        # Distribuir algunos pedidos antiguos a Branch 2 si todos estaban en 1
        orders_br1 = db.query(Order).filter(Order.branch_id == 1).order_by(Order.id).all()
        if len(orders_br1) > 40:
            for idx, ord_item in enumerate(orders_br1):
                if idx % 3 == 0:
                    ord_item.branch_id = 2
            db.commit()
            print("Balanceados pedidos históricos entre Sucursal 1 y 2.")

        # Obtener sucursales
        branch1 = db.query(Branch).filter(Branch.id == 1).first() # Equipetrol
        branch2 = db.query(Branch).filter(Branch.id == 2).first() # Ventura Mall
        print(f"Sucursal 1: {branch1.name} (ID: {branch1.id})")
        print(f"Sucursal 2: {branch2.name} (ID: {branch2.id})")

        # Obtener usuarios clave
        cajero1 = db.query(User).filter(User.email == "cajero.equipetrol@fashionstore.com").first() or db.query(User).filter(User.id == 20).first()
        cajero2 = db.query(User).filter(User.email == "cajera.ventura@fashionstore.com").first() or db.query(User).filter(User.id == 22).first()
        admin_user = db.query(User).filter(User.email == "admin@fashionstore.com").first()
        repartidor_user = db.query(User).filter(User.email == "repartidor.moto@fashionstore.com").first()
        dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == repartidor_user.id).first() if repartidor_user else None
        
        # Clientes
        clients = db.query(User).filter(User.email.in_([
            "cliente@fashionstore.com",
            "marilynesthercondori@gmail.com",
            "ana.perez@example.com",
            "sofia.lopez@example.com",
            "condoriesther888@gmail.com"
        ])).all()
        if not clients:
            clients = db.query(User).filter(User.id != 1).limit(5).all()

        today = datetime.now().date()
        now = datetime.now()

        # === 2. Turnos de Caja (CashShift) para ambas sucursales ===
        print("=== 2. Generando Turnos y Arqueos de Caja (CashShift) ===")
        shifts_to_link = []
        
        # Generar turnos para los últimos 7 días
        for day_offset in range(6, -1, -1):
            shift_date = today - timedelta(days=day_offset)
            is_today = (day_offset == 0)

            # Turno Sucursal Equipetrol
            shift1 = CashShift(
                cashier_id=cajero1.id if cajero1 else 1,
                branch_id=1,
                opening_amount=500.0,
                status="ABIERTO" if is_today else "CERRADO",
                opened_at=datetime.combine(shift_date, datetime.min.time()) + timedelta(hours=9),
                closed_at=None if is_today else (datetime.combine(shift_date, datetime.min.time()) + timedelta(hours=21)),
                notes="Turno continuo Equipetrol" + (" (En curso)" if is_today else " (Cierre conforme)")
            )
            db.add(shift1)
            db.flush()
            shifts_to_link.append((shift1, shift_date, 1))

            # Turno Sucursal Ventura Mall
            shift2 = CashShift(
                cashier_id=cajero2.id if cajero2 else 1,
                branch_id=2,
                opening_amount=500.0,
                status="ABIERTO" if is_today else "CERRADO",
                opened_at=datetime.combine(shift_date, datetime.min.time()) + timedelta(hours=10),
                closed_at=None if is_today else (datetime.combine(shift_date, datetime.min.time()) + timedelta(hours=22)),
                notes="Turno Mall Ventura" + (" (En curso)" if is_today else " (Arqueo verificado)")
            )
            db.add(shift2)
            db.flush()
            shifts_to_link.append((shift2, shift_date, 2))

        # === 3. Selección de Prendas Top por Categoría y Temporada ===
        print("=== 3. Identificando Prendas Emblemáticas para Ventas ===")
        
        # Buscar productos relevantes
        top_prods_data = [
            # (Categoría, ID deseado o nombre aproximado, unidades venta deseadas, popularidad)
            ("Vestidos", [60, 65, 11, 42, 10, 59, 32, 64]),
            ("Blusas", [8, 1, 24]),
            ("Jeans / Mezclilla", [13, 69, 56, 71]),
            ("Pantalones", [34, 45, 70]),
            ("Chaquetas / Chamarras", [20, 21]),
            ("Enterizos / Monos", [9, 49, 47, 72]),
            ("Tops / Crop Tops", [12, 14, 23, 31]),
            ("Suéteres y Tejidos", [17, 18, 16]),
            ("Ropa de dormir / Pijamas", [52, 57, 58])
        ]

        products_catalog = {}
        for cat_name, prod_ids in top_prods_data:
            prods = db.query(Product).filter(Product.id.in_(prod_ids)).all()
            if not prods:
                prods = db.query(Product).join(Category).filter(Category.name.ilike(f"%{cat_name[:4]}%")).limit(4).all()
            products_catalog[cat_name] = prods

        print(f"Categorías preparadas: {list(products_catalog.keys())}")

        # Clientes recurrentes con NITs para Facturación
        customer_profiles = [
            {"name": "Marilyn Esther Condori", "nit": "6849201019", "email": "condoriesther888@gmail.com"},
            {"name": "Valeria Antelo Justiniano", "nit": "4920194012", "email": "valeria.antelo@gmail.com"},
            {"name": "Camila Suárez Ribera", "nit": "5839201017", "email": "camila.suarez@hotmail.com"},
            {"name": "Luciana Banzer Paz", "nit": "7849201015", "email": "luciana.banzer@gmail.com"},
            {"name": "Andrea Roca Aguilera", "nit": "3920194011", "email": "andrea.roca@yahoo.com"},
            {"name": "Natalia Vaca Diez", "nit": "8392019013", "email": "natalia.vaca@gmail.com"},
            {"name": "Mariana Justiniano Pinto", "nit": "9201948016", "email": "mariana.j@gmail.com"},
            {"name": "Sofía Mercado Saucedo", "nit": "4820193018", "email": "sofia.mercado@gmail.com"}
        ]

        print("=== 4. Creando Transacciones y Ventas Realistas ===")
        new_orders_count = 0
        total_seeded_revenue = Decimal(0.0)

        # Repartir ventas a lo largo de los últimos 14 días con énfasis en los últimos 7 días y HOY
        for day_offset in range(13, -1, -1):
            order_date = today - timedelta(days=day_offset)
            # Más ventas en fin de semana y hoy
            is_weekend = order_date.weekday() in (4, 5, 6) # Viernes, Sábado, Domingo
            daily_orders_qty = random.randint(5, 9) if is_weekend else random.randint(3, 6)
            if day_offset == 0:
                daily_orders_qty = 6 # Ventas para hoy día

            for _ in range(daily_orders_qty):
                # Elegir sucursal de manera equitativa
                target_branch_id = 1 if random.random() < 0.52 else 2
                
                # Elegir canal: 55% POS presencial en Santa Cruz, 45% ONLINE
                channel = "POS" if random.random() < 0.55 else "ONLINE"
                
                # Encontrar turno de caja correspondiente si es POS
                assigned_shift = None
                if channel == "POS":
                    for s, s_date, s_br in shifts_to_link:
                        if s_date == order_date and s_br == target_branch_id:
                            assigned_shift = s
                            break

                # Horario de la venta
                hour = random.randint(10, 20)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                created_dt = datetime.combine(order_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute, seconds=second)

                cust_prof = random.choice(customer_profiles)
                chosen_user = random.choice(clients) if clients else admin_user

                # Crear cabecera de orden
                order = Order(
                    user_id=chosen_user.id,
                    branch_id=target_branch_id,
                    channel=channel,
                    status="PAGADA",
                    subtotal=Decimal(0.0),
                    discount_amount=Decimal(0.0),
                    coupon_code="FASHION10" if random.random() < 0.15 else None,
                    total_amount=Decimal(0.0),
                    cash_shift_id=assigned_shift.id if assigned_shift else None,
                    created_at=created_dt
                )
                db.add(order)
                db.flush()

                # Seleccionar de 1 a 3 prendas para esta venta
                num_items = random.choices([1, 2, 3], weights=[0.60, 0.30, 0.10])[0]
                order_subtotal = Decimal(0.0)

                # Priorizar vestidos y categorías clave
                available_cats = list(products_catalog.keys())
                for _ in range(num_items):
                    chosen_cat = random.choices(
                        available_cats,
                        weights=[0.30, 0.15, 0.12, 0.10, 0.08, 0.10, 0.05, 0.05, 0.05]
                    )[0]
                    prods_in_cat = products_catalog.get(chosen_cat, [])
                    if not prods_in_cat:
                        continue
                    prod = random.choice(prods_in_cat)
                    if not prod.variants:
                        continue
                    variant = random.choice(prod.variants)
                    item_qty = random.choices([1, 2], weights=[0.85, 0.15])[0]
                    price = Decimal(str(prod.base_price or 180.0))

                    order_item = OrderItem(
                        order_id=order.id,
                        variant_id=variant.id,
                        quantity=item_qty,
                        unit_price=price
                    )
                    db.add(order_item)
                    order_subtotal += (price * item_qty)

                    # Registrar movimiento en Kardex / InventoryLedger
                    ledger = InventoryLedger(
                        branch_id=target_branch_id,
                        variant_id=variant.id,
                        quantity=-item_qty,
                        movement_type="VENTA",
                        unit_cost=Decimal(str(round(float(price) * 0.55, 2))),
                        reference_id=f"ORD-{order.id}",
                        created_at=created_dt
                    )
                    db.add(ledger)

                    # Actualizar stock en inventory
                    inv_row = db.query(Inventory).filter(
                        Inventory.branch_id == target_branch_id,
                        Inventory.variant_id == variant.id
                    ).first()
                    if inv_row:
                        inv_row.stock_actual = max(3, inv_row.stock_actual - item_qty)

                discount = Decimal(str(round(float(order_subtotal) * 0.10, 2))) if order.coupon_code else Decimal(0.0)
                order_total = order_subtotal - discount
                order.subtotal = order_subtotal
                order.discount_amount = discount
                order.total_amount = order_total
                total_seeded_revenue += order_total

                # Crear Pago (Payment)
                if channel == "POS":
                    ptype = random.choices(["EFECTIVO", "TARJETA", "QR"], weights=[0.45, 0.40, 0.15])[0]
                else:
                    ptype = random.choices(["PAYPAL", "TARJETA", "QR"], weights=[0.40, 0.40, 0.20])[0]

                if ptype == "EFECTIVO":
                    rec = Decimal(str(int(order_total // 10 * 10 + 20)))
                    payment = EfectivoPayment(
                        order_id=order.id,
                        amount=order_total,
                        status="CONFIRMADO",
                        paid_at=created_dt,
                        cash_received=rec,
                        cash_change=rec - order_total
                    )
                elif ptype == "TARJETA":
                    payment = TarjetaPayment(
                        order_id=order.id,
                        amount=order_total,
                        status="CONFIRMADO",
                        paid_at=created_dt,
                        card_brand=random.choice(["VISA", "MASTERCARD"]),
                        card_last4=f"{random.randint(1000, 9999)}",
                        gateway_reference=f"AUTH-{random.randint(100000, 999999)}"
                    )
                elif ptype == "PAYPAL":
                    payment = PayPalPayment(
                        order_id=order.id,
                        amount=order_total,
                        status="CONFIRMADO",
                        paid_at=created_dt,
                        paypal_payer_id=f"PAYER-{random.randint(10000, 99999)}",
                        paypal_payer_email=cust_prof["email"],
                        gateway_reference=f"PAYPAL:CAP-{random.randint(10000000, 99999999)}"
                    )
                else: # QR
                    payment = QRPayment(
                        order_id=order.id,
                        amount=order_total,
                        status="CONFIRMADO",
                        paid_at=created_dt,
                        qr_reference=f"BCP-QR-{random.randint(1000000, 9999999)}"
                    )
                db.add(payment)

                # Generar Factura (CU20) con IVA 13%
                sub = order_total
                tax = Decimal(str(round(float(sub) * 0.13, 2)))
                invoice = Invoice(
                    order_id=order.id,
                    doc_type="FACTURA" if random.random() < 0.75 else "NOTA_ENTREGA",
                    tax_rate=Decimal("0.130"),
                    subtotal=sub - tax,
                    tax_amount=tax,
                    total=sub,
                    control_code=f"E4-9F-{random.randint(10, 99)}-BA-{random.randint(10, 99)}" if random.random() < 0.75 else None,
                    customer_nit=cust_prof["nit"],
                    customer_name=cust_prof["name"],
                    issued_at=created_dt
                )
                db.add(invoice)

                new_orders_count += 1

        print(f"Total nuevas órdenes generadas: {new_orders_count}")
        print(f"Monto total nuevo facturado: Bs. {total_seeded_revenue}")

        # === 5. Actualizar Totales del Arqueo en CashShifts cerrados ===
        for shift, s_date, s_br in shifts_to_link:
            if shift.status == "CERRADO":
                # Calcular ventas en efectivo asociadas
                cash_sales = db.query(Payment).join(Order).filter(
                    Order.cash_shift_id == shift.id,
                    Payment.payment_type == "EFECTIVO"
                ).all()
                cash_sum = sum([Decimal(str(p.amount)) for p in cash_sales])
                system_total = Decimal("500.00") + cash_sum
                # Simular pequeña diferencia de arqueo (entre -5 y +5 Bs o exacto)
                diff = Decimal(random.choice([0.0, 0.0, 0.0, -2.0, 5.0, -1.50]))
                shift.closing_amount_system = system_total
                shift.closing_amount_declared = system_total + diff
                shift.difference = diff

        # === 6. Generar Reservas Físicas en Probador (Reservations) ===
        print("=== 5. Generando Reservas en Probadores (CU26-CU28) ===")
        # Limpiar reservas antiguas huérfanas si hubieran
        res_prods = db.query(Product).filter(Product.id.in_([60, 65, 11, 42, 20, 9])).all()
        
        sample_reservations = [
            ("RES-SCZ-101", 1, "READY", today, "15:00", "Probador VIP 1 - Cliente notificó que llega en 10 min."),
            ("RES-SCZ-102", 1, "PREPARING", today, "17:30", "Seleccionar perchas y planchar vestido de noche."),
            ("RES-SCZ-103", 2, "READY", today, "16:00", "Ventura Mall - Probador 2 listo para prueba."),
            ("RES-SCZ-104", 2, "PENDING", today + timedelta(days=1), "11:00", "Cita programada online para mañana."),
            ("RES-SCZ-105", 1, "PENDING", today + timedelta(days=1), "16:00", "Prueba de conjunto sastre y blusa."),
            ("RES-SCZ-106", 2, "COMPLETED", today - timedelta(days=1), "18:00", "Prueba realizada con éxito - Cliente compró ambas prendas."),
            ("RES-SCZ-107", 1, "COMPLETED", today - timedelta(days=2), "14:30", "Prueba realizada y convertida a POS.")
        ]

        for code, br_id, st, app_date, app_time, note in sample_reservations:
            existing = db.query(Reservation).filter(Reservation.reservation_code == code).first()
            if existing:
                continue
            client_u = random.choice(clients) if clients else admin_user
            res_obj = Reservation(
                reservation_code=code,
                customer_id=client_u.id,
                branch_id=br_id,
                status=st,
                appointment_date=app_date,
                appointment_time=app_time,
                reschedule_count=0,
                grace_period_notified=False,
                reserved_at=datetime.combine(app_date, datetime.min.time()) + timedelta(hours=9),
                expires_at=datetime.combine(app_date, datetime.min.time()) + timedelta(hours=21),
                notes=note,
                total_amount=Decimal("450.00"),
                deposit_amount=Decimal("50.00"),
                payment_method="TARJETA" if br_id == 1 else "PAYPAL",
                payment_reference=f"DEP-{random.randint(10000, 99999)}",
                deposit_paid=True
            )
            db.add(res_obj)
            db.flush()

            # Agregar ítems a la reserva
            if res_prods:
                p1 = res_prods[br_id % len(res_prods)]
                if p1.variants:
                    db.add(ReservationItem(reservation_id=res_obj.id, variant_id=p1.variants[0].id, quantity=1))

        # === 7. Generar Transferencias de Stock Inter-Sucursal (CU15) ===
        print("=== 6. Generando Transferencias de Stock entre Sucursales ===")
        # Transferencia 1: Equipetrol -> Ventura Mall (COMPLETADA)
        tr1 = db.query(StockTransfer).filter(StockTransfer.transfer_number == "TRF-SCZ-2026-01").first()
        if not tr1:
            tr1 = StockTransfer(
                transfer_number="TRF-SCZ-2026-01",
                origin_branch_id=1,
                destination_branch_id=2,
                requested_by_id=cajero2.id if cajero2 else 1,
                received_by_id=cajero2.id if cajero2 else 1,
                status="COMPLETADA",
                notes="Reabastecimiento de vestidos y enterizos para fin de semana en Ventura Mall.",
                created_at=datetime.now() - timedelta(days=2),
                completed_at=datetime.now() - timedelta(days=1, hours=4)
            )
            db.add(tr1)
            db.flush()
            if res_prods and res_prods[0].variants:
                db.add(StockTransferDetail(transfer_id=tr1.id, variant_id=res_prods[0].variants[0].id, quantity=10))

        # Transferencia 2: Ventura Mall -> Equipetrol (EN_TRANSITO)
        tr2 = db.query(StockTransfer).filter(StockTransfer.transfer_number == "TRF-SCZ-2026-02").first()
        if not tr2:
            tr2 = StockTransfer(
                transfer_number="TRF-SCZ-2026-02",
                origin_branch_id=2,
                destination_branch_id=1,
                requested_by_id=cajero1.id if cajero1 else 1,
                status="EN_TRANSITO",
                notes="Traspaso urgente de jeans y blusas bordadas solicitado por Equipetrol.",
                created_at=datetime.now() - timedelta(hours=3)
            )
            db.add(tr2)
            db.flush()
            if len(res_prods) > 1 and res_prods[1].variants:
                db.add(StockTransferDetail(transfer_id=tr2.id, variant_id=res_prods[1].variants[0].id, quantity=8))

        # === 8. Despachos y Entregas de Repartidor (CU29-CU30) ===
        print("=== 7. Verificando Despachos y Logística de Repartidor ===")
        # Asegurar envíos activos asignados al repartidor Jorge Torrez
        if dp and repartidor_user:
            # Envíos completados para historial
            past_order = db.query(Order).filter(Order.channel == "ONLINE", Order.status == "PAGADA").first()
            if past_order:
                shp_done = db.query(Shipment).filter(Shipment.tracking_number == "TRK-HIST-001").first()
                if not shp_done:
                    shp_done = Shipment(
                        tracking_number="TRK-HIST-001",
                        order_id=past_order.id,
                        zone_id=2,
                        delivery_person_id=dp.id,
                        claimed_at=datetime.now() - timedelta(days=1, hours=5),
                        delivery_date=today - timedelta(days=1),
                        delivery_time="15:30",
                        carrier_name="Jorge Torrez (Moto Express)",
                        carrier_phone=dp.phone,
                        delivery_address="Barrio Sirari, Calle Los Claveles #210, Santa Cruz",
                        recipient_name="Camila Suárez",
                        recipient_phone="77312984",
                        shipping_cost=18.0,
                        status="DELIVERED",
                        dispatched_at=datetime.now() - timedelta(days=1, hours=4),
                        delivered_at=datetime.now() - timedelta(days=1, hours=3),
                        notes="Entregado en puerta en mano propia.",
                        received_by_name="Camila Suárez"
                    )
                    db.add(shp_done)

        db.commit()
        print("=== ¡MASTER SEED EJECUTADO EXITOSAMENTE! ===")

    except Exception as e:
        db.rollback()
        print(f"ERROR DURANTE SEED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_master_seed()
