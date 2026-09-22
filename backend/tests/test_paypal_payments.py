"""Pruebas unitarias para la Pasarela de Pago PayPal (CU18, CU19, CU26)."""
import pytest
from datetime import date, timedelta, datetime, timezone
from fastapi.testclient import TestClient

from app.config import settings
from app.packages.paquete_ventas_y_pagos.paypal_service import paypal_service
from app.main import app
from app.db.session import SessionLocal
from app.packages.paquete_seguridad_usuarios.models import User, SessionToken
from app.packages.paquete_seguridad_usuarios.services import create_access_token
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import ProductVariant, Product
from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory

client = TestClient(app)


def _approve_sim(paypal_order_id, headers):
    """Inicia sesión en el simulador de PayPal y aprueba la orden (como el comprador)."""
    res = client.post(
        "/api/v1/payments/paypal/simulator/approve",
        json={
            "paypal_order_id": paypal_order_id,
            "email": settings.PAYPAL_SIM_EMAIL,
            "password": settings.PAYPAL_SIM_PASSWORD,
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def auth_headers():
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@fashionstore.com", "password": "Password123!"},
    )
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@fashionstore.com").first()
    if not admin:
        admin = db.query(User).filter(User.is_active == True).first()
    token = create_access_token(admin.id)
    session_rec = SessionToken(
        user_id=admin.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        is_revoked=False,
    )
    db.add(session_rec)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_paypal_config():
    """Verifica que el endpoint de configuración pública de PayPal responda correctamente."""
    res = client.get("/api/v1/payments/paypal/config")
    assert res.status_code == 200
    data = res.json()
    assert "client_id" in data
    assert data["currency"] == "USD"
    assert data["exchange_rate_bob_usd"] > 0
    assert "simulated" in data
    if data["simulated"]:
        # Sin credenciales no se expone ningún Client ID ficticio.
        assert data["client_id"] is None


def test_paypal_status():
    """El diagnóstico informa si hay conexión OAuth real con PayPal o modo simulación."""
    res = client.get("/api/v1/payments/paypal/status")
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] in ("sandbox", "live")
    assert isinstance(data["connected"], bool)
    if data["simulated"]:
        assert data["connected"] is False


def test_paypal_create_and_capture_order(auth_headers):
    """Verifica la creación de orden y captura de pago en PayPal."""
    # 1. Crear Orden en PayPal (usando simulación para ejecución sin interacción manual de navegador)
    create_res = client.post(
        "/api/v1/payments/paypal/create-order",
        json={"amount_bob": 348.0, "description": "Compra de Vestido y Blusa", "force_simulation": True},
        headers=auth_headers,
    )
    assert create_res.status_code == 200
    order_data = create_res.json()
    assert "id" in order_data
    assert order_data["amount_bob"] == 348.0
    assert order_data["amount_usd"] == 50.0  # 348 / 6.96 = 50.0
    assert "approve_url" in order_data

    paypal_order_id = order_data["id"]

    # 2. Sin aprobación del comprador no se captura nada.
    early = client.post(
        "/api/v1/payments/paypal/capture-order",
        json={"paypal_order_id": paypal_order_id},
        headers=auth_headers,
    )
    assert early.status_code == 402

    # 3. El comprador inicia sesión en el simulador y aprueba.
    approval = _approve_sim(paypal_order_id, auth_headers)

    # 4. Capturar Pago en PayPal. El simulador no guarda estado en memoria: la aprobación
    #    sigue valiendo aunque el servidor se haya reiniciado entre ambos pasos.
    paypal_service.__init__()
    capture_res = client.post(
        "/api/v1/payments/paypal/capture-order",
        json={"paypal_order_id": paypal_order_id, "approval_token": approval["approval_token"]},
        headers=auth_headers,
    )
    assert capture_res.status_code == 200
    cap_data = capture_res.json()
    assert cap_data["status"] == "COMPLETED"
    assert "gateway_reference" in cap_data
    assert cap_data["payer"]["email_address"] == settings.PAYPAL_SIM_EMAIL


def test_paypal_simulator_login(auth_headers):
    """El simulador acepta solo la cuenta configurada (correo insensible a mayúsculas)."""
    ok = client.post(
        "/api/v1/payments/paypal/simulator/login",
        json={"email": settings.PAYPAL_SIM_EMAIL.upper(), "password": settings.PAYPAL_SIM_PASSWORD},
        headers=auth_headers,
    )
    assert ok.status_code == 200
    assert ok.json()["payer"]["email_address"] == settings.PAYPAL_SIM_EMAIL
    assert "password" not in ok.text.lower()

    bad = client.post(
        "/api/v1/payments/paypal/simulator/login",
        json={"email": settings.PAYPAL_SIM_EMAIL, "password": "incorrecta"},
        headers=auth_headers,
    )
    assert bad.status_code == 401


def test_cu26_reserva_con_pago_online_paypal(auth_headers):
    """Verifica que una reserva agendada con pago online PayPal guarde la referencia y estado de seña."""
    db = SessionLocal()
    branch = db.query(Branch).filter(Branch.city == "Santa Cruz").first()
    variant = db.query(ProductVariant).first()

    # Asegurar stock
    inv = (
        db.query(Inventory)
        .filter(
            Inventory.branch_id == branch.id,
            Inventory.variant_id == variant.id,
        )
        .first()
    )
    if not inv:
        inv = Inventory(branch_id=branch.id, variant_id=variant.id, stock_actual=10)
        db.add(inv)
    else:
        inv.stock_actual += 5
    db.commit()

    tomorrow = date.today() + timedelta(days=1)
    base_payload = {
        "branch_id": branch.id,
        "appointment_date": tomorrow.isoformat(),
        "appointment_time": "15:00",
        "payment_method": "PAYPAL",
        "items": [{"variant_id": variant.id, "quantity": 1}],
    }

    # Una referencia inventada (orden nunca creada en PayPal) no aparta prendas.
    fake = client.post(
        "/api/v1/reservations",
        json={**base_payload, "payment_reference": "PAYPAL:CAP-88492019482"},
        headers=auth_headers,
    )
    assert fake.status_code == 400

    order = client.post(
        "/api/v1/payments/paypal/create-order",
        json={"amount_bob": 500.0, "description": "Seña reserva", "force_simulation": True},
        headers=auth_headers,
    ).json()
    reference = f"PAYPAL:{order['id']}"
    # Orden creada pero no pagada: tampoco aparta prendas.
    unpaid = client.post("/api/v1/reservations", json={**base_payload, "payment_reference": reference}, headers=auth_headers)
    assert unpaid.status_code == 402
    approval = _approve_sim(order["id"], auth_headers)
    cap = client.post(
        "/api/v1/payments/paypal/capture-order",
        json={"paypal_order_id": order["id"], "approval_token": approval["approval_token"]},
        headers=auth_headers,
    )
    assert cap.status_code == 200
    reference = f"PAYPAL:{cap.json()['id']}"
    # Un comprobante de captura adulterado no aparta prendas.
    forged_ref = reference[:-1] + ("0" if reference[-1] != "0" else "1")
    forged = client.post("/api/v1/reservations", json={**base_payload, "payment_reference": forged_ref}, headers=auth_headers)
    assert forged.status_code == 400
    res = client.post("/api/v1/reservations", json={**base_payload, "payment_reference": reference}, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["payment_method"] == "PAYPAL"
    assert data["payment_reference"] == reference
    assert data["deposit_paid"] is True
    assert data["deposit_amount"] > 0
    assert data["balance_due"] == round(data["total_amount"] - data["deposit_amount"], 2)
    db.close()
