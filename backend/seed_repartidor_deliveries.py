from app.db.session import SessionLocal
from app.packages.paquete_ventas_y_pagos.models import Order, OrderItem, Payment
from app.packages.paquete_catalogo_y_tiendas.models import ProductVariant
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_envios_y_logistica.models import Shipment, ShipmentTrackingEvent, DeliveryZone
from app.packages.paquete_envios_y_logistica.delivery_persons.models import DeliveryPerson
from datetime import datetime, date

db = SessionLocal()

# 1. Obtener datos base
user = db.query(User).filter(User.email == "repartidor.moto@fashionstore.com").first()
client_user = db.query(User).filter(User.email != "repartidor.moto@fashionstore.com").first()
dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == user.id).first()
branch = db.query(Branch).first()
variant = db.query(ProductVariant).first()
zone = db.query(DeliveryZone).first()

print(f"Repartidor: {user.first_name} {user.last_name} (ID DP: {dp.id if dp else 'None'})")
print(f"Sucursal origen: {branch.name if branch else 'None'}")

# Crear Pedido 1: Asignado directamente al Repartidor (Estado: ASSIGNED)
order1 = Order(
    user_id=client_user.id if client_user else user.id,
    branch_id=branch.id if branch else 1,
    channel="ONLINE",
    status="PAGADO",
    subtotal=320.0,
    discount_amount=0.0,
    total_amount=320.0,
)
db.add(order1)
db.flush()

if variant:
    db.add(OrderItem(order_id=order1.id, variant_id=variant.id, quantity=1, unit_price=320.0))

db.add(Payment(order_id=order1.id, amount=320.0, payment_type="PAYPAL", status="COMPLETED", gateway_reference="PAYPAL:CAP-7711AA01"))

shipment1 = Shipment(
    tracking_number="TRK-7711AA01",
    order_id=order1.id,
    zone_id=zone.id if zone else None,
    delivery_person_id=dp.id,
    claimed_at=datetime.now(),
    delivery_date=date.today(),
    delivery_time="14:00 - 18:00",
    carrier_name=f"{user.first_name} {user.last_name}",
    carrier_phone=dp.phone,
    delivery_address="Condominio Sevilla Los Jardines, Casa #14, Zona Norte, Santa Cruz",
    recipient_name="Marilyn Esther Condori",
    recipient_phone="77012345",
    shipping_cost=15.0,
    status="ASSIGNED",
    notes="Llamar al llegar a la portería. Pago completado por PayPal.",
)
db.add(shipment1)
db.flush()

db.add(ShipmentTrackingEvent(
    shipment_id=shipment1.id,
    status="ASSIGNED",
    location=f"Sucursal {branch.name if branch else 'Central'}",
    description=f"El repartidor {user.first_name} {user.last_name} ({dp.vehicle_type}) aceptó el pedido y se dirige a la sucursal para retiro.",
))

# Crear Pedido 2: En tránsito con el repartidor (Estado: IN_TRANSIT)
order2 = Order(
    user_id=client_user.id if client_user else user.id,
    branch_id=branch.id if branch else 1,
    channel="ONLINE",
    status="PAGADO",
    subtotal=180.0,
    discount_amount=0.0,
    total_amount=180.0,
)
db.add(order2)
db.flush()

if variant:
    db.add(OrderItem(order_id=order2.id, variant_id=variant.id, quantity=1, unit_price=180.0))

db.add(Payment(order_id=order2.id, amount=180.0, payment_type="PAYPAL", status="COMPLETED", gateway_reference="PAYPAL:CAP-8822BB02"))

shipment2 = Shipment(
    tracking_number="TRK-8822BB02",
    order_id=order2.id,
    zone_id=zone.id if zone else None,
    delivery_person_id=dp.id,
    claimed_at=datetime.now(),
    dispatched_at=datetime.now(),
    delivery_date=date.today(),
    delivery_time="Inmediato",
    carrier_name=f"{user.first_name} {user.last_name}",
    carrier_phone=dp.phone,
    delivery_address="Av. Banzer Km 8 1/2, Condominio El Bosque, Manzana 3, Lote 12",
    recipient_name="Carlos Morales",
    recipient_phone="78543210",
    shipping_cost=20.0,
    status="IN_TRANSIT",
    notes="Entregar en recepción o llamar al celular. Cliente esperando.",
)
db.add(shipment2)
db.flush()

db.add(ShipmentTrackingEvent(
    shipment_id=shipment2.id,
    status="PICKED_UP",
    location=f"Sucursal {branch.name if branch else 'Central'}",
    description=f"Paquete retirado por {user.first_name} {user.last_name}.",
))
db.add(ShipmentTrackingEvent(
    shipment_id=shipment2.id,
    status="IN_TRANSIT",
    location="En ruta urbana",
    description="Repartidor en motocicleta en camino al domicilio del cliente.",
))

# Crear Pedido 3: Disponible en la Bolsa de Pedidos para ser tomado (Estado: PENDING_DISPATCH)
order3 = Order(
    user_id=client_user.id if client_user else user.id,
    branch_id=branch.id if branch else 1,
    channel="ONLINE",
    status="PAGADO",
    subtotal=450.0,
    discount_amount=0.0,
    total_amount=450.0,
)
db.add(order3)
db.flush()

if variant:
    db.add(OrderItem(order_id=order3.id, variant_id=variant.id, quantity=2, unit_price=225.0))

db.add(Payment(order_id=order3.id, amount=450.0, payment_type="PAYPAL", status="COMPLETED", gateway_reference="PAYPAL:CAP-9933CC03"))

shipment3 = Shipment(
    tracking_number="TRK-9933CC03",
    order_id=order3.id,
    zone_id=zone.id if zone else None,
    delivery_person_id=None,
    delivery_date=date.today(),
    delivery_time="Hoy por la tarde",
    carrier_name="Por Asignar (Moto Express)",
    carrier_phone="77012345",
    delivery_address="Av. San Martín y Calle 4 Oeste, Edificio Alianza, Piso 4, Dpto 402",
    recipient_name="Alejandra Vaca",
    recipient_phone="69087654",
    shipping_cost=15.0,
    status="PENDING_DISPATCH",
    notes="Prendas empacadas en bolsa ecológica de regalo. Listo para recoger.",
)
db.add(shipment3)
db.flush()

db.add(ShipmentTrackingEvent(
    shipment_id=shipment3.id,
    status="PENDING_DISPATCH",
    location="Almacén Central",
    description="Pedido empaquetado y listo para ser tomado por el repartidor.",
))

db.commit()
print("¡3 Envíos generados exitosamente!")
print(f"1. Asignado a Jorge: {shipment1.tracking_number} (ASSIGNED)")
print(f"2. En tránsito con Jorge: {shipment2.tracking_number} (IN_TRANSIT)")
print(f"3. En bolsa disponible: {shipment3.tracking_number} (PENDING_DISPATCH)")
