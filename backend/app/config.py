import os
from dotenv import load_dotenv

load_dotenv(override=True)


def _csv(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


class Settings:
    """Configuración central de la plataforma FashionStore (leída desde variables de entorno)."""

    PROJECT_NAME: str = "FashionStore"

    # --- Base de datos (PostgreSQL) ---
    # Formato esperado: postgresql+psycopg2://usuario:contrasena@host:puerto/basededatos
    # Normaliza automáticamente URLs de Render o proveedores cloud (postgres:// -> postgresql+psycopg2://)
    _raw_db: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fashionstore",
    )
    if _raw_db.startswith("postgres://"):
        _raw_db = _raw_db.replace("postgres://", "postgresql+psycopg2://", 1)
    elif _raw_db.startswith("postgresql://") and not _raw_db.startswith("postgresql+psycopg2://"):
        _raw_db = _raw_db.replace("postgresql://", "postgresql+psycopg2://", 1)

    DATABASE_URL: str = _raw_db

    # --- Seguridad / JWT ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clave_secreta_super_segura_para_el_primer_parcial")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # --- CORS ---
    BACKEND_CORS_ORIGINS: list[str] = _csv(
        "BACKEND_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
    )

    # --- Frontend (para armar enlaces en los correos) ---
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:4200")

    # --- Correo saliente (SMTP) para el enlace de recuperación (CU03) ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "marilynesthercondori@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "efnoskvuyotrwtuh")
    SMTP_FROM: str = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "marilynesthercondori@gmail.com"))
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "FashionStore")

    # --- Pasarela de Pago PayPal (Sandbox / Producción) ---
    # Credenciales de la app REST creada en https://developer.paypal.com (Apps & Credentials).
    # Vacías => modo simulación (sin cobro). Con credenciales sandbox => conexión real con PayPal.
    @property
    def PAYPAL_CLIENT_ID(self) -> str:
        return os.getenv("PAYPAL_CLIENT_ID", "")

    @property
    def PAYPAL_CLIENT_SECRET(self) -> str:
        return os.getenv("PAYPAL_CLIENT_SECRET", "")

    @property
    def PAYPAL_MODE(self) -> str:
        return os.getenv("PAYPAL_MODE", "sandbox")

    @property
    def PAYPAL_EXCHANGE_RATE_BOB_USD(self) -> float:
        return float(os.getenv("PAYPAL_EXCHANGE_RATE_BOB_USD", "6.96"))

    # --- Simulador de PayPal ---
    # La cuenta PayPal del comercio está registrada en Bolivia (BOB) y no puede recibir cobros,
    # así que por defecto se usa el simulador: misma experiencia de PayPal (login + revisión)
    # sin contactar a PayPal. PAYPAL_SIMULATION=false vuelve a la conexión real sandbox/live.
    @property
    def PAYPAL_SIMULATION(self) -> bool:
        return os.getenv("PAYPAL_SIMULATION", "true").lower() in ("true", "1", "yes")

    @property
    def PAYPAL_SIM_EMAIL(self) -> str:
        return os.getenv("PAYPAL_SIM_EMAIL", "condoridiaz2005@gmail.com").strip().lower()

    @property
    def PAYPAL_SIM_PASSWORD(self) -> str:
        return os.getenv("PAYPAL_SIM_PASSWORD", "Mari123!")

    @property
    def PAYPAL_SIM_NAME(self) -> str:
        return os.getenv("PAYPAL_SIM_NAME", "Marilyn Esther")

    @property
    def paypal_api_base(self) -> str:
        if self.PAYPAL_MODE.lower() == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)


settings = Settings()
