"""Servicio de integración con la Pasarela de Pagos PayPal (REST API v2).

Crea y captura órdenes en PayPal (sandbox o live) con conversión BOB -> USD.

Modo simulación (por defecto, PAYPAL_SIMULATION=true, o sin credenciales reales): el
comprador inicia sesión en una ventana tipo PayPal con la cuenta del simulador
(PAYPAL_SIM_EMAIL / PAYPAL_SIM_PASSWORD), aprueba, y recién entonces la orden se captura.
El simulador no guarda estado: el ID de la orden (con su monto), la aprobación y la captura
van firmados con HMAC(SECRET_KEY), así que funcionan aunque el servidor se reinicie entre
un paso y otro (uvicorn --reload, Render dormido) o haya varios procesos.
Con PAYPAL_SIMULATION=false y credenciales reales, cualquier fallo de PayPal se reporta
como error: nunca se fabrica un pago aprobado.
"""
import uuid
import base64
import hmac
import logging
import json
import re
from typing import Dict, Any, Optional

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger("paypal_service")
logger.setLevel(logging.DEBUG)

SIMULATED_ORDER_PREFIX = "PAYPAL-SIM-"
PAYPAL_UNAVAILABLE = "No se pudo procesar el pago con PayPal. Intenta nuevamente en unos minutos."
SIM_LOGIN_FAILED = "Parece que el correo electrónico o la contraseña son incorrectos. Inténtalo de nuevo."
SIM_NOT_APPROVED = "El comprador no aprobó el pago en PayPal. Inicia sesión y confirma el pago."
SIM_BAD_ORDER = "La orden de PayPal no existe."
# PAYPAL-SIM-<10 hex>-<centavos USD>-<firma 16>  y, ya cobrada:  <orden>-C<firma 12>
_SIM_ORDER_RE = re.compile(r"(PAYPAL-SIM-[0-9A-F]{10}-(\d{1,9}))-([0-9A-F]{16})")
_SIM_CAPTURED_RE = re.compile(r"(PAYPAL-SIM-[0-9A-F]{10}-\d{1,9}-[0-9A-F]{16})-C([0-9A-F]{12})")


class PayPalService:

    @property
    def client_id(self) -> str:
        return settings.PAYPAL_CLIENT_ID

    @property
    def client_secret(self) -> str:
        return settings.PAYPAL_CLIENT_SECRET

    @property
    def base_url(self) -> str:
        return settings.paypal_api_base

    @property
    def exchange_rate(self) -> float:
        return settings.PAYPAL_EXCHANGE_RATE_BOB_USD

    def bob_to_usd(self, amount_bob: float) -> float:
        """Convierte monto en Bolivianos a Dólares Estadounidenses con 2 decimales."""
        if not self.exchange_rate or self.exchange_rate <= 0:
            return round(amount_bob / 6.96, 2)
        return round(float(amount_bob) / self.exchange_rate, 2)

    def is_simulation(self) -> bool:
        """True si no hay credenciales reales de PayPal, si el modo es simulación o flag activa."""
        if str(settings.PAYPAL_MODE).lower() in ("simulation", "simulator", "simulado"):
            return True
        if settings.PAYPAL_SIMULATION:
            return True
        cid = (self.client_id or "").lower()
        secret = (self.client_secret or "").lower()
        return not cid or not secret or "demo" in cid or "test" in cid or "demo" in secret

    # ------------------------------------------------------------------
    # Simulador: inicio de sesión del comprador y aprobación de la orden
    # ------------------------------------------------------------------
    def simulator_account(self) -> Dict[str, Any]:
        """Perfil público de la cuenta compradora del simulador (sin contraseña)."""
        given, _, surname = settings.PAYPAL_SIM_NAME.partition(" ")
        return {
            "payer_id": "SIM" + hmac.new(
                settings.SECRET_KEY.encode(), settings.PAYPAL_SIM_EMAIL.encode(), "sha256"
            ).hexdigest()[:10].upper(),
            "email_address": settings.PAYPAL_SIM_EMAIL,
            "name": {"given_name": given, "surname": surname},
        }

    def simulator_login(self, email: str, password: str) -> Dict[str, Any]:
        """Valida las credenciales de la cuenta del simulador. Lanza 401 si no coinciden.

        La contraseña solo se compara (en tiempo constante); nunca se registra ni se guarda.
        """
        email_ok = hmac.compare_digest((email or "").strip().lower().encode(), settings.PAYPAL_SIM_EMAIL.encode())
        pass_ok = hmac.compare_digest((password or "").encode(), settings.PAYPAL_SIM_PASSWORD.encode())
        if not (email_ok and pass_ok):
            raise HTTPException(status_code=401, detail=SIM_LOGIN_FAILED)
        return self.simulator_account()

    # --- Firmas del simulador (sin estado en memoria) ---
    @staticmethod
    def _sign(*parts: str, length: int = 16) -> str:
        msg = "|".join(parts).encode()
        return hmac.new(settings.SECRET_KEY.encode(), msg, "sha256").hexdigest()[:length].upper()

    def _new_sim_order_id(self, amount_usd: float) -> str:
        base = f"{SIMULATED_ORDER_PREFIX}{uuid.uuid4().hex[:10].upper()}-{int(round(amount_usd * 100))}"
        return f"{base}-{self._sign('order', base)}"

    def _sim_order_amount(self, paypal_order_id: str) -> Optional[float]:
        """Monto USD de una orden simulada auténtica (firma válida); None si es falsa."""
        m = _SIM_ORDER_RE.fullmatch(paypal_order_id or "")
        if not m or not hmac.compare_digest(m.group(3), self._sign("order", m.group(1))):
            return None
        return int(m.group(2)) / 100

    def _approval_token(self, paypal_order_id: str) -> str:
        return self._sign("approved", paypal_order_id, settings.PAYPAL_SIM_EMAIL, length=32)

    def _captured_id(self, paypal_order_id: str) -> str:
        return f"{paypal_order_id}-C{self._sign('captured', paypal_order_id, length=12)}"

    def simulator_approve(self, paypal_order_id: str, email: str, password: str) -> Dict[str, Any]:
        """El comprador inicia sesión y aprueba una orden simulada (equivale a 'Pagar' en PayPal).

        Devuelve un `approval_token` firmado que `/capture-order` exige para cobrar la orden.
        """
        if self._sim_order_amount(paypal_order_id) is None:
            raise HTTPException(status_code=400, detail=SIM_BAD_ORDER)
        payer = self.simulator_login(email, password)
        logger.info("Orden simulada aprobada por el comprador: %s", paypal_order_id)
        return {
            "id": paypal_order_id,
            "status": "APPROVED",
            "payer": payer,
            "approval_token": self._approval_token(paypal_order_id),
        }

    def _basic_auth_header(self) -> Dict[str, str]:
        encoded = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {encoded}", "Content-Type": "application/x-www-form-urlencoded"}

    async def get_access_token(self) -> str:
        """Obtiene token OAuth 2.0 de PayPal. Lanza 502 si PayPal no responde correctamente."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                logger.debug(f"🔐 Solicitando token OAuth a: {self.base_url}/v1/oauth2/token")
                resp = await client.post(
                    f"{self.base_url}/v1/oauth2/token",
                    headers=self._basic_auth_header(),
                    data={"grant_type": "client_credentials"},
                )
        except httpx.HTTPError as exc:
            logger.error("❌ Error conectando con PayPal OAuth: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        if resp.status_code != 200:
            logger.error("❌ PayPal OAuth rechazó (%s): %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail=f"PayPal OAuth error {resp.status_code}")

        logger.debug("✅ Token OAuth obtenido exitosamente")
        return resp.json()["access_token"]

    async def check_connection(self) -> Dict[str, Any]:
        """Comprueba la conexión real con PayPal pidiendo un token OAuth.

        Sirve para demostrar (y diagnosticar) que las credenciales sandbox son válidas
        sin crear ninguna orden. Nunca expone el token ni el secret.
        """
        status = {"mode": settings.PAYPAL_MODE, "api_base": self.base_url, "simulated": self.is_simulation()}
        if self.is_simulation():
            return {**status, "connected": False, "detail": "Simulador de PayPal activo (no se contacta a PayPal)."}
        try:
            await self.get_access_token()
        except HTTPException:
            return {**status, "connected": False, "detail": "PayPal rechazó las credenciales o no respondió."}
        return {**status, "connected": True, "detail": "Conexión OAuth con PayPal establecida."}

    async def create_order(
        self,
        amount_bob: float,
        reference_id: str,
        description: str = "Pago en FashionStore",
        customer_email: Optional[str] = None,
        force_simulation: bool = False,
    ) -> Dict[str, Any]:
        """Crea una orden en PayPal (intent: CAPTURE). Retorna el order_id y approve_url.

        En modo simulación o si force_simulation=True: genera orden simulada inmediatamente.
        """
        amount_usd = self.bob_to_usd(amount_bob)
        is_sim = self.is_simulation() or force_simulation
        base = {
            "amount_bob": amount_bob,
            "amount_usd": amount_usd,
            "currency": "USD",
            "exchange_rate": self.exchange_rate,
            "simulated": is_sim,
        }

        if is_sim:
            sim_id = self._new_sim_order_id(amount_usd)
            logger.info(f"Orden simulada creada: {sim_id} (Bs. {amount_bob:.2f} = USD {amount_usd:.2f})")
            return {**base, "id": sim_id, "status": "CREATED", "approve_url": sim_id}

        token = await self.get_access_token()

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "description": description[:120],
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{amount_usd:.2f}",
                    },
                }
            ],
            "application_context": {
                "brand_name": "FashionStore",
                "user_action": "PAY_NOW",
                "shipping_preference": "NO_SHIPPING",
                "return_url": f"{settings.FRONTEND_URL}/store/checkout/success",
                "cancel_url": f"{settings.FRONTEND_URL}/store/checkout/cancel",
            },
        }

        logger.debug(f"📤 Creando orden en PayPal:")
        logger.debug(f"   - URL: {self.base_url}/v2/checkout/orders")
        logger.debug(f"   - Monto: {amount_bob} BOB = {amount_usd} USD")
        logger.debug(f"   - Reference: {reference_id}")
        logger.debug(f"   - Return URL: {settings.FRONTEND_URL}/store/checkout/success")
        logger.debug(f"   - Cancel URL: {settings.FRONTEND_URL}/store/checkout/cancel")
        logger.debug(f"   - Payload completo: {json.dumps(payload, indent=2)}")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v2/checkout/orders",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.error(f"❌ Excepción en create_order de PayPal: {exc}")
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        data = resp.json()
        logger.debug(f"📥 Respuesta PayPal ({resp.status_code}): {json.dumps(data, indent=2)}")

        if resp.status_code not in (200, 201):
            error_msg = data.get("message", "Error desconocido")
            error_details = data.get("details", [])
            error_name = data.get("name", "UNKNOWN_ERROR")

            logger.error(f"❌ PayPal rechazó la orden:")
            logger.error(f"   - Status: {resp.status_code}")
            logger.error(f"   - Error Name: {error_name}")
            logger.error(f"   - Mensaje: {error_msg}")
            logger.error(f"   - Detalles: {json.dumps(error_details, indent=2)}")

            raise HTTPException(status_code=502, detail=f"PayPal {error_name}: {error_msg}")

        approve_url = next((l.get("href") for l in data.get("links", []) if l.get("rel") in ("approve", "payer-action")), None)
        logger.info(f"✅ Orden PayPal creada: {data.get('id')} | Approve URL: {approve_url}")
        return {**base, "id": data.get("id"), "status": data.get("status"), "approve_url": approve_url}

    async def capture_order(self, paypal_order_id: str, approval_token: Optional[str] = None) -> Dict[str, Any]:
        """Captura los fondos de una orden aprobada por el comprador.

        Orden simulada: solo se captura con el `approval_token` que devolvió
        `simulator_approve`; no se contacta a PayPal. El `id` devuelto (orden + firma de
        captura) es el comprobante que el checkout y las reservas verifican.
        """
        if self.is_simulation() or (paypal_order_id and paypal_order_id.startswith(SIMULATED_ORDER_PREFIX)):
            if self._sim_order_amount(paypal_order_id) is None:
                raise HTTPException(status_code=400, detail=SIM_BAD_ORDER)
            if not approval_token or not hmac.compare_digest(
                approval_token.upper(), self._approval_token(paypal_order_id)
            ):
                raise HTTPException(status_code=402, detail=SIM_NOT_APPROVED)
            payer = self.simulator_account()
            captured_id = self._captured_id(paypal_order_id)
            capture_id = f"CAP-SIM-{captured_id[-12:]}"
            logger.info(f"Captura simulada: {paypal_order_id} → {capture_id}")
            return {
                "id": captured_id,
                "status": "COMPLETED",
                "capture_id": capture_id,
                "payer": payer,
                "gateway_reference": f"PAYPAL:{capture_id}",
                "simulated": True,
            }

        token = await self.get_access_token()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v2/checkout/orders/{paypal_order_id}/capture",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={},
                )
        except httpx.HTTPError as exc:
            logger.error("Excepción en capture_order de PayPal: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        data = resp.json()
        if resp.status_code not in (200, 201) or data.get("status") != "COMPLETED":
            logger.warning("Captura PayPal rechazada (%s): %s", resp.status_code, data)
            raise HTTPException(status_code=402, detail="PayPal no aprobó el pago. Verifica tu cuenta o intenta otro medio.")

        purchase_units = data.get("purchase_units", [])
        captures = purchase_units[0].get("payments", {}).get("captures", []) if purchase_units else []
        capture_id = captures[0].get("id") if captures else paypal_order_id
        return {
            "id": data.get("id"),
            "status": "COMPLETED",
            "capture_id": capture_id,
            "payer": data.get("payer", {}),
            "gateway_reference": f"PAYPAL:{capture_id}",
            "simulated": False,
        }

    def verify_completed_order(self, paypal_order_id: str, expected_amount_bob: float) -> None:
        """Comprueba en PayPal (lado servidor) que la orden esté cobrada por el monto esperado.

        Se usa en el checkout para no registrar como pagado un pedido solo porque el cliente
        envió un ID de orden. Lanza HTTPException si el pago no es válido.
        """
        if self.is_simulation() or (paypal_order_id and paypal_order_id.startswith(SIMULATED_ORDER_PREFIX)):
            # Mismas reglas que con PayPal real: la orden debe existir, estar cobrada y cubrir el monto.
            m = _SIM_CAPTURED_RE.fullmatch(paypal_order_id or "")
            if not m:
                if self._sim_order_amount(paypal_order_id) is not None:
                    raise HTTPException(status_code=402, detail="El pago de PayPal no está completado.")
                raise HTTPException(status_code=400, detail=SIM_BAD_ORDER)
            paid_usd = self._sim_order_amount(m.group(1))
            if paid_usd is None or not hmac.compare_digest(paypal_order_id, self._captured_id(m.group(1))):
                raise HTTPException(status_code=400, detail=SIM_BAD_ORDER)
            if paid_usd + 0.01 < self.bob_to_usd(expected_amount_bob):
                raise HTTPException(status_code=402, detail="El monto pagado en PayPal no cubre el total del pedido.")
            return

        try:
            with httpx.Client(timeout=15.0) as client:
                token_resp = client.post(
                    f"{self.base_url}/v1/oauth2/token",
                    headers=self._basic_auth_header(),
                    data={"grant_type": "client_credentials"},
                )
                if token_resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)
                resp = client.get(
                    f"{self.base_url}/v2/checkout/orders/{paypal_order_id}",
                    headers={"Authorization": f"Bearer {token_resp.json()['access_token']}"},
                )
        except httpx.HTTPError as exc:
            logger.error("Error verificando orden PayPal: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="La orden de PayPal no existe.")
        data = resp.json()
        if data.get("status") != "COMPLETED":
            raise HTTPException(status_code=402, detail="El pago de PayPal no está completado.")
        units = data.get("purchase_units") or [{}]
        paid_usd = float(units[0].get("amount", {}).get("value", 0))
        if paid_usd + 0.01 < self.bob_to_usd(expected_amount_bob):
            raise HTTPException(status_code=402, detail="El monto pagado en PayPal no cubre el total del pedido.")


paypal_service = PayPalService()
