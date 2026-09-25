"""Modelos base del paquete Ventas y Pagos.

En el **Ciclo 1** solo se crean las tablas (respaldo del diagrama de clases del análisis:
jerarquías `MedioDePago` y `Comprobante`). Los routers / la lógica transaccional (carrito,
checkout, POS, facturación) llegan en el **Ciclo 2** (CU17–CU24).

Herencia modelada:
* `Payment` ⭅ `EfectivoPayment` / `TarjetaPayment` / `QRPayment` / `CreditoPayment`
  (herencia de tabla única — Single Table Inheritance — discriminador `payment_type`).
* `Invoice` con `doc_type` (`FACTURA` / `NOTA_ENTREGA`) e IVA 13 %.
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import ProductVariant
from app.packages.paquete_seguridad_usuarios.models import User


class Order(Base):
    """
    [CU17 / CU18 / CU19] CE_Orden: Entidad cabecera de pedido / venta omnicanal (ONLINE y POS).
    
    Atributos destacados de Casos de Uso:
      - CU18: Venta Omnicanal con modalidades de entrega:
        * delivery_type: 'ENVIO_DOMICILIO' (con guía CU29) vs. 'RETIRO_TIENDA' (custodia en sucursal).
        * pickup_deadline: Plazo estricto de 48 horas para recojo en tienda física antes de que retorne a exhibición.
        * payment_session_expires_at: Temporizador de 5 minutos (300 segundos) para confirmación en pasarela.
      - CU19: Venta Presencial POS vinculada a turno de caja (cash_shift_id).
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), default="ONLINE", nullable=False)  # 'ONLINE' | 'POS'
    status: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    coupon_code: Mapped[Optional[str]] = mapped_column(String(30))
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    cash_shift_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cash_shifts.id", ondelete="SET NULL"), nullable=True)
    delivery_type: Mapped[str] = mapped_column(String(20), default='ENVIO_DOMICILIO', nullable=False)
    pickup_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_session_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship()
    branch: Mapped[Branch] = relationship()
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="order", uselist=False
    )
    cash_shift: Mapped[Optional["CashShift"]] = relationship("CashShift", back_populates="orders")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    variant: Mapped[ProductVariant] = relationship()


class Payment(Base):
    """[CU18, CU19] CE_MedioDePago: Entidad de pago — clase base de la jerarquía (Single Table Inheritance).

    `MedioDePago` ⭅ Efectivo / Tarjeta / QR / Crédito. El discriminador es `payment_type`.
    En CU19 [Paso 1.5] insert_payment(order_id, type='EFECTIVO', amount, cash_received, cash_change) registra el pago en efectivo y cambio.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # EFECTIVO, TARJETA, QR, PAYPAL, CREDITO
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMADO", nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Atributos específicos según subclase (STI)
    cash_received: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))  # Efectivo
    cash_change: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))    # Efectivo
    card_brand: Mapped[Optional[str]] = mapped_column(String(20))          # Tarjeta
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))           # Tarjeta
    gateway_reference: Mapped[Optional[str]] = mapped_column(String(100))  # Tarjeta / Pasarela
    qr_reference: Mapped[Optional[str]] = mapped_column(String(100))       # QR
    paypal_payer_id: Mapped[Optional[str]] = mapped_column(String(50))     # PayPal
    paypal_payer_email: Mapped[Optional[str]] = mapped_column(String(100)) # PayPal
    credit_due_date: Mapped[Optional[date]] = mapped_column(Date)          # Crédito

    order: Mapped[Order] = relationship("Order", back_populates="payments")

    __mapper_args__ = {
        "polymorphic_on": payment_type,
        "polymorphic_identity": "PAGO",
    }


class EfectivoPayment(Payment):
    """[CU19] CE_MedioDePago (Efectivo): Registra monto pagado, efectivo recibido y cambio entregado (Paso 1.5)."""
    __mapper_args__ = {"polymorphic_identity": "EFECTIVO"}


class TarjetaPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "TARJETA"}


class QRPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "QR"}


class PayPalPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "PAYPAL"}


class CreditoPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "CREDITO"}


class Invoice(Base):
    """[CU19, CU20] CE_Factura: Comprobante fiscal computarizado con desglose del 13% IVA y código de control.
    En CU19 [Paso 1.6.1] CTR_Facturacion -> CE_Factura: insert(order_id, doc_type='FACTURA', subtotal, tax_amount).
    """
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), unique=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(15), nullable=False)  # 'FACTURA' | 'NOTA_ENTREGA'
    tax_rate: Mapped[float] = mapped_column(Numeric(4, 3), default=0.130, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    control_code: Mapped[Optional[str]] = mapped_column(String(40))  # solo FACTURA
    customer_nit: Mapped[Optional[str]] = mapped_column(String(20))
    customer_name: Mapped[Optional[str]] = mapped_column(String(150))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="invoice")


class CashShift(Base):
    """[CU19, CU23] CE_SesionCaja: Entidad de Turno y Sesión de Caja registradora (apertura, operaciones y arqueo).
    En CU19 [Paso 1.2] CTR_POS -> CE_SesionCaja: get_session(session_id) verifica session_status == 'ABIERTA'.
    """
    __tablename__ = "cash_shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    cashier_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    opening_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    closing_amount_declared: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    closing_amount_system: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    difference: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="ABIERTO", nullable=False)  # 'ABIERTO', 'CERRADO'
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255))

    cashier: Mapped[User] = relationship("User")
    branch: Mapped[Branch] = relationship("Branch")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="cash_shift")


class Cart(Base):
    """[CU17] Carrito de compras digital."""
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[Optional[User]] = relationship("User")
    items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    """[CU17] Ítem del carrito de compras digital."""
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cart: Mapped[Cart] = relationship("Cart", back_populates="items")
    variant: Mapped[ProductVariant] = relationship("ProductVariant")


class Quotation(Base):
    """[CU21] Cotización comercial para clientes."""
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(100))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(30))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    # [Separación por sucursal] Nullable por compatibilidad con cotizaciones antiguas sin este dato.
    branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="VIGENTE", nullable=False)  # 'VIGENTE', 'CONVERTIDA', 'VENCIDA'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_by: Mapped[User] = relationship("User")
    items: Mapped[List["QuotationItem"]] = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")


class QuotationItem(Base):
    """[CU21] Ítem de la cotización comercial."""
    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    quotation: Mapped[Quotation] = relationship("Quotation", back_populates="items")
    variant: Mapped[ProductVariant] = relationship("ProductVariant")


class CreditNote(Base):
    """
    [CU22 / CU18] CE_NotaDeCredito: Saldo a favor del cliente para compras posteriores.
    
    Casos de Uso de Aplicación:
      - [CU22 - Paso 4]: Cambio por modelo donde la prenda elegida tiene menor precio que la original.
        Por política comercial no se reembolsa efectivo; se emite una Nota de Crédito reutilizable.
      - [CU18 - Flujo Alterno B]: Expiración de custodia por retiro en sucursal (48 horas vencidas).
        La prenda retorna al inventario general y se protege el dinero del cliente con una Nota de Crédito.
    """
    __tablename__ = "credit_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    credit_note_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    return_id: Mapped[Optional[int]] = mapped_column(ForeignKey("order_returns.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="VIGENTE", nullable=False)  # 'VIGENTE' | 'APLICADA' | 'ANULADA'
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User")
    order: Mapped[Optional[Order]] = relationship("Order")


class OrderReturn(Base):
    """
    [CU22] CE_Devolucion: Registro formal de cambio o devolución de prendas.
    
    Subflujos Soportados:
      - 'CAMBIO_TALLA': Mismo producto en diferente talla (Diferencia: Bs. 0.00).
      - 'CAMBIO_MODELO': Prenda de modelo diferente.
        * Si el precio es mayor: difference_amount > 0 (cobro de saldo en caja/pasarela).
        * Si el precio es menor: difference_amount < 0 (emite CE_NotaDeCredito, cero efectivo).
      - 'DEVOLUCION_DINERO': Reembolso formal previo control de calidad y límite de 14 días.
    """
    __tablename__ = "order_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    return_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    processed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    return_type: Mapped[str] = mapped_column(String(25), nullable=False)  # 'DEVOLUCION_DINERO' | 'CAMBIO_PRENDA' | 'CAMBIO_TALLA' | 'CAMBIO_MODELO'
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    refund_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    difference_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    credit_note_id: Mapped[Optional[int]] = mapped_column(ForeignKey("credit_notes.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="APROBADA", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped[Order] = relationship("Order")
    processed_by: Mapped[User] = relationship("User")
    credit_note: Mapped[Optional[CreditNote]] = relationship("CreditNote", foreign_keys=[credit_note_id])
    items: Mapped[List["OrderReturnItem"]] = relationship("OrderReturnItem", back_populates="order_return", cascade="all, delete-orphan")


class OrderReturnItem(Base):
    """[CU22] Prenda devuelta o cambiada."""
    __tablename__ = "order_return_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("order_returns.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    replacement_variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=True)

    order_return: Mapped[OrderReturn] = relationship("OrderReturn", back_populates="items")
    variant: Mapped[ProductVariant] = relationship("ProductVariant", foreign_keys=[variant_id])
    replacement_variant: Mapped[Optional[ProductVariant]] = relationship("ProductVariant", foreign_keys=[replacement_variant_id])

