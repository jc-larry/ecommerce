"""Controlador API REST del paquete Inteligente y Analítica.
Casos de Uso:
- [CU32] Vestidor virtual con Realidad Aumentada (RA) y recomendador biométrico de tallas.
- [CU33] Chatbot asistente inteligente y estilista de moda con recomendaciones cruzadas.
- [CU34] Búsqueda inteligente por voz con procesamiento de lenguaje natural (NLP).
- [CU35] Reportes gerenciales (Kardex físico-valorado, top vendidos, exportación CSV/Voz).
- [CU39] Dashboard global analítico con gráficos interactivos y KPIs en tiempo real.
"""
import io
import csv
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import (
    Product, ProductVariant, Category, Size, Color, ProductImage
)
from app.packages.paquete_envios_y_logistica.models import Shipment
from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger
from app.packages.paquete_inteligente_y_analitica.models import (
    ChatbotConversation, VirtualTryonCapture, VirtualTryonSession, VirtualTryonItem
)
from app.packages.paquete_inteligente_y_analitica.vton_service import VirtualTryonAIService
from app.packages.paquete_inteligente_y_analitica.garment_rig import build_rig as build_garment_rig
from app.packages.paquete_inteligente_y_analitica.schemas import (
    VirtualTryonRequest,
    VirtualTryonResponse,
    TryonSessionCreate,
    TryonSessionResponse,
    TryonItemCreate,
    TryonItemResponse,
    VTONGenerateRequest,
    VTONGenerateResponse,
    TryonCaptureCreate,
    TryonCaptureResponse,
    RemoveBackgroundRequest,
    RemoveBackgroundResponse,
    ChatbotMessageRequest,
    ChatbotMessageResponse,
    VoiceSearchNLPRequest,
    VoiceSearchNLPResponse,
    ManagerReportTopSellingItem,
    ManagerReportKardexItem,
    AnalyticsDashboardResponse,
    ProductSalesTrendResponse,
    SalesTimelinePoint,
    VariantSalesStock,
    BranchStockItem,
)
from app.packages.paquete_reservas_y_citas.models import Reservation
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_seguridad_usuarios.routers import get_current_user
from app.packages.paquete_ventas_y_pagos.models import Order, OrderItem

router = APIRouter(prefix="/api/v1/analytics", tags=["Inteligente y Analítica (IA / RA / BI)"])


# ===================================================================
# CU32: VESTIDOR VIRTUAL (RA / IA - IDM-VTON / FASHN.AI)
# ===================================================================


@router.post("/tryon/remove-background", response_model=RemoveBackgroundResponse)
def remove_background(
    data: RemoveBackgroundRequest,
):
    """[CU32] Segmenta la figura humana y reemplaza el fondo por blanco puro (#FFFFFF).
    # [CU32 - Paso 2] / [DSC032 - Paso 2] +remove_background(image_base64)
    # [CU32 - Paso 3] / [DSC032 - Paso 3] +segment_human_silhouette_rembg()

    Utiliza la red neuronal rembg (u2net/isnet) para detección precisa del contorno
    corporal. Funciona con cualquier fondo arbitrario (alfombra roja, habitación, etc.).
    """
    import time
    start_time = time.time()
    analysis = VirtualTryonAIService.analyze_person(data.image_base64)
    elapsed = round(time.time() - start_time, 2)
    return RemoveBackgroundResponse(
        processed_image_url=analysis["processed_image_url"],
        processing_time_sec=elapsed,
        model_used=f"rembg ({analysis['mask_source']})",
        mask_confidence=analysis["mask_confidence"],
        mask_reliable=analysis["mask_reliable"],
        mask_source=analysis["mask_source"],
        mask_bbox=analysis["mask_bbox"],
        pose_confidence=analysis["pose_confidence"],
        pose_valid=analysis["pose_valid"],
        pose_source=analysis["pose_source"],
        pose_landmarks=analysis["pose_landmarks"],
    )


@router.post("/tryon/sessions", response_model=TryonSessionResponse)
def create_tryon_session(
    data: TryonSessionCreate,
    db: Session = Depends(get_db),
):
    """[CU32] Inicia una sesión formal de vestidor virtual (Web o Móvil)."""
    token = uuid.uuid4().hex
    session = VirtualTryonSession(
        session_token=token,
        channel=data.channel,
        status="ACTIVE",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return TryonSessionResponse(
        id=session.id,
        session_token=session.session_token,
        channel=session.channel,
        status=session.status,
        started_at=session.started_at,
        items_count=0,
    )


@router.post("/tryon/items", response_model=TryonItemResponse)
def log_tested_item(
    data: TryonItemCreate,
    db: Session = Depends(get_db),
):
    """[CU32] Registra una prenda y variante probada en la sesión activa del vestidor."""
    session = db.query(VirtualTryonSession).filter(VirtualTryonSession.session_token == data.session_token).first()
    if not session:
        # Crea la sesión si no existía previamente
        session = VirtualTryonSession(session_token=data.session_token, channel="WEB", status="ACTIVE")
        db.add(session)
        db.commit()
        db.refresh(session)

    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    variant = None
    color_name = None
    color_hex = None
    if data.variant_id:
        variant = db.query(ProductVariant).filter(ProductVariant.id == data.variant_id).first()
        if variant and variant.color:
            color_name = variant.color.name
            color_hex = variant.color.hex_code

    item = VirtualTryonItem(
        session_id=session.id,
        product_id=product.id,
        variant_id=data.variant_id,
        tested_size=data.tested_size,
        fit_feedback=data.fit_feedback,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    prod_img = product.images[0].image_url if product.images else "/assets/images/placeholder.png"

    return TryonItemResponse(
        id=item.id,
        session_id=session.id,
        product_id=product.id,
        product_name=product.name,
        variant_id=data.variant_id,
        color_name=color_name,
        color_hex=color_hex,
        image_url=prod_img,
        tested_size=item.tested_size,
        fit_feedback=item.fit_feedback,
        tested_at=item.tested_at,
    )


@router.get("/tryon/sessions/{token}/items", response_model=List[TryonItemResponse])
def get_session_tested_items(
    token: str,
    db: Session = Depends(get_db),
):
    """[CU32] Obtiene el historial de todas las prendas probadas en la sesión de vestidor."""
    session = db.query(VirtualTryonSession).filter(VirtualTryonSession.session_token == token).first()
    if not session:
        return []

    items = db.query(VirtualTryonItem).filter(VirtualTryonItem.session_id == session.id).order_by(desc(VirtualTryonItem.tested_at)).all()
    results = []
    for it in items:
        p = it.product
        v = it.variant
        c_name = v.color.name if (v and v.color) else None
        c_hex = v.color.hex_code if (v and v.color) else None
        img = p.images[0].image_url if (p and p.images) else "/assets/images/placeholder.png"
        results.append(TryonItemResponse(
            id=it.id,
            session_id=session.id,
            product_id=it.product_id,
            product_name=p.name if p else "Prenda",
            variant_id=it.variant_id,
            color_name=c_name,
            color_hex=c_hex,
            image_url=img,
            tested_size=it.tested_size,
            fit_feedback=it.fit_feedback,
            tested_at=it.tested_at,
        ))
    return results


@router.get("/tryon/garment-rig/{product_id}")
def get_garment_rig(
    product_id: int,
    image_url: Optional[str] = Query(
        None,
        description="Foto concreta a medir (variante de color). Si se omite, la principal.",
    ),
    force: bool = Query(False, description="Ignora la caché y vuelve a medir la prenda."),
    db: Session = Depends(get_db),
):
    """[CU32] Rig de la prenda para el probador en vivo (cámara encendida).

    El probador en vivo deforma la prenda sobre el cuerpo en cada fotograma, así que no
    puede llamar al servidor por frame. Este endpoint hace, una sola vez y con caché en
    disco, la parte cara: recorta la prenda del fondo con rembg y **mide** dónde están su
    hombro, su cintura, su bajo y sus mangas. El cliente descarga el PNG recortado y las
    medidas, y a partir de ahí trabaja solo y sin red.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    source = image_url
    if not source:
        images = list(product.images or [])
        primary = next((i for i in images if i.is_primary), images[0] if images else None)
        source = primary.image_url if primary else None
    if not source:
        raise HTTPException(status_code=404, detail="La prenda no tiene fotografía que medir.")

    rig = build_garment_rig(
        product_id=product.id,
        image_source=source,
        category_name=product.category.name if product.category else "",
        product_name=product.name or "",
        sleeve_length=product.sleeve_length or "",
        force=force,
    )
    if rig is None:
        raise HTTPException(
            status_code=422,
            detail="No se pudo medir la prenda a partir de su fotografía.",
        )
    return rig


@router.post("/tryon/generate-vton", response_model=VTONGenerateResponse)
def generate_vton_with_ai(
    data: VTONGenerateRequest,
    db: Session = Depends(get_db),
):
    """[CU32] Genera la prueba fotorrealista textil utilizando modelos generativos (IDM-VTON / Fashn.ai)."""
    # [CU32 - Paso 4] / [DSC032 - Paso 4] +generate_vton(person_image, garment_image, model_choice)
    # [CU32 - Paso 5] / [DSC032 - Paso 5] +cascade_vton_inference(FASHN -> IDM_VTON -> local_anatomico)
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    garment_img = data.garment_image
    if not garment_img:
        garment_img = product.images[0].image_url if product.images else "/assets/images/placeholder.png"

    category_source = data.category
    if product.category and product.category.name:
        category_source = product.category.name
    category = VirtualTryonAIService.normalize_category(category_source)

    rec_size = data.recommended_size or "M"
    garment_landmarks = VirtualTryonAIService.get_garment_landmarks(
        product_tags=product.tags or "",
        category_name=product.category.name if product.category else category,
    )

    # Invocar al servicio de inferencia VTON
    ai_result = VirtualTryonAIService.generate_vton_look(
        person_image_data=data.person_image,
        garment_image_url=garment_img,
        product_name=product.name,
        category=category,
        model_choice=data.model_choice,
        recommended_size=rec_size,
        garment_landmarks=garment_landmarks,
    )

    session = None
    if data.session_token:
        session = db.query(VirtualTryonSession).filter(VirtualTryonSession.session_token == data.session_token).first()

    # Guardar la captura generada en la base de datos
    vton_confidence = ai_result.get("mask_confidence")
    if vton_confidence is None:
        # Los motores VTON remotos devuelven su propia evaluación; la máscara
        # local solo se persiste cuando fue calculada en este backend.
        vton_confidence = 0.95
    capture = VirtualTryonCapture(
        session_id=session.id if session else None,
        product_id=product.id,
        variant_id=data.variant_id,
        photo_url=ai_result["result_image_url"],
        original_photo_url=data.person_image[:500] if data.person_image else None,
        generation_model=ai_result["model_used"],
        confidence_score=vton_confidence,
        recommended_size=rec_size,
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    return VTONGenerateResponse(
        capture_id=capture.id,
        product_id=product.id,
        product_name=product.name,
        result_image_url=ai_result["result_image_url"],
        original_photo_url=data.person_image if len(data.person_image) < 1000 else None,
        generation_model=ai_result["model_used"],
        processing_time_sec=ai_result["processing_time_sec"],
        status="COMPLETED",
        style_advice=ai_result["style_advice"],
        mask_confidence=ai_result.get("mask_confidence"),
        mask_reliable=ai_result.get("mask_reliable"),
        mask_source=ai_result.get("mask_source"),
        pose_confidence=ai_result.get("pose_confidence"),
        pose_valid=ai_result.get("pose_valid"),
        pose_source=ai_result.get("pose_source"),
        pose_landmarks=ai_result.get("pose_landmarks"),
        fit_mode=ai_result.get("fit_mode"),
    )


@router.post("/tryon/simulate", response_model=VirtualTryonResponse)
def simulate_virtual_tryon(
    data: VirtualTryonRequest,
    db: Session = Depends(get_db),
):
    """[CU32] Simula la prueba de prenda en el vestidor virtual y recomienda talla según biometría."""
    # [CU32 - Paso 3] / [DSC032 - Paso 3] +simulate_measurements(chest, waist, hips, height, weight)
    # [CU32 - Paso 4] / [DSC032 - Paso 4] +calculate_recommended_size_and_fit_feedback()
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    # 1. Algoritmo biométrico de cálculo de talla
    rec_size = "M"
    fit_assessment = "Corte regular estándar"
    confidence = 0.92

    if data.chest_cm:
        if data.chest_cm < 88:
            rec_size = "XS"
            fit_assessment = "Ajuste ceñido ideal para silueta delgada."
        elif data.chest_cm <= 94:
            rec_size = "S"
            fit_assessment = "Ajuste slim fit elegante y cómodo."
        elif data.chest_cm <= 102:
            rec_size = "M"
            fit_assessment = "Ajuste estándar equilibrado."
        elif data.chest_cm <= 110:
            rec_size = "L"
            fit_assessment = "Ajuste amplio con caída holgada."
        else:
            rec_size = "XL"
            fit_assessment = "Talla confort para mayor libertad de movimiento."
    elif data.user_height_cm and data.user_weight_kg:
        h_m = data.user_height_cm / 100.0
        bmi = data.user_weight_kg / (h_m * h_m)
        if bmi < 19.5:
            rec_size = "S"
            fit_assessment = "Silueta estilizada con ajuste definido."
        elif bmi <= 24.5:
            rec_size = "M"
            fit_assessment = "Medida regular óptima para tus proporciones."
        elif bmi <= 28.5:
            rec_size = "L"
            fit_assessment = "Talla espaciosa recomendada para caída natural."
        else:
            rec_size = "XL"
            fit_assessment = "Corte holgado de máxima comodidad."

    # 2. Silueta morfológica y puntos de tensión
    body_shape = "Silueta Estándar"
    chest_fit = "Ajuste Óptimo"
    waist_fit = "Ajuste Cómodo"
    hip_fit = "Caída Natural"

    chest = data.chest_cm or 92.0
    waist = data.waist_cm or 74.0
    hip = data.hip_cm or 96.0

    if data.chest_cm and data.waist_cm and data.hip_cm:
        if chest > waist + 15 and hip > waist + 15 and abs(chest - hip) <= 6:
            body_shape = "Reloj de Arena"
        elif chest > hip + 7:
            body_shape = "Triángulo Invertido (Atlético)"
        elif hip > chest + 7:
            body_shape = "Pera / Triangular"
        elif abs(chest - waist) <= 12 and abs(waist - hip) <= 12:
            body_shape = "Rectangular"
        elif waist >= chest:
            body_shape = "Ovalada / Manzana"

    if rec_size in ["XS", "S"]:
        chest_fit = "Ceñido estructurado sin tirantez"
        waist_fit = "Contorno definido y entallado"
        hip_fit = "Caída recta estilizada"
    elif rec_size == "M":
        chest_fit = "Ajuste equilibrado y anatómicamente confortable"
        waist_fit = "Ajuste fluido con libertad respiratoria"
        hip_fit = "Caída natural y anatómica"
    else:
        chest_fit = "Corte relajado de máxima holgura"
        waist_fit = "Libertad total de movimiento en cintura"
        hip_fit = "Caída amplia y sin fricción"

    # Imagen del producto dinámica
    prod_image = product.images[0].image_url if product.images else "/assets/images/placeholder.png"
    sim_image = data.photo_url or prod_image
    user_photo_processed = bool(data.photo_url or data.photo_base64)

    advice = (
        f"La prenda '{product.name}' en talla {rec_size} armoniza con tu silueta {body_shape}. "
        f"Confeccionada con caída suave para eventos casuales y de temporada."
    )

    measurements_dict = {
        "height": data.user_height_cm,
        "weight": data.user_weight_kg,
        "chest": data.chest_cm,
        "waist": data.waist_cm,
        "hip": data.hip_cm,
    }

    session = None
    if data.session_token:
        session = db.query(VirtualTryonSession).filter(VirtualTryonSession.session_token == data.session_token).first()

    capture = VirtualTryonCapture(
        session_id=session.id if session else None,
        product_id=product.id,
        variant_id=data.variant_id,
        photo_url=sim_image,
        recommended_size=rec_size,
        measurements_json=json.dumps(measurements_dict),
        generation_model="AR_HYBRID",
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    size_scales = {"XS": 0.94, "S": 0.98, "M": 1.04, "L": 1.12, "XL": 1.20, "XXL": 1.28}
    fit_scale = size_scales.get(rec_size, 1.0)

    # Calcular landmarks anatómicos para posicionamiento preciso en el frontend
    garment_lm = VirtualTryonAIService.get_garment_landmarks(
        product_tags=product.tags or "",
        category_name=product.category.name if product.category else "",
    )
    body_lm = VirtualTryonAIService.compute_body_landmarks(
        height_cm=data.user_height_cm or 168,
        chest_cm=data.chest_cm or 90,
        waist_cm=data.waist_cm or 70,
        hip_cm=data.hip_cm or 94,
    )

    return VirtualTryonResponse(
        id=capture.id,
        product_id=product.id,
        product_name=product.name,
        recommended_size=rec_size,
        fit_scale_factor=fit_scale,
        confidence_score=confidence,
        simulation_image_url=sim_image,
        fit_assessment=fit_assessment,
        style_advice=advice,
        body_shape=body_shape,
        chest_fit=chest_fit,
        waist_fit=waist_fit,
        hip_fit=hip_fit,
        user_photo_processed=user_photo_processed,
        garment_landmarks=garment_lm,
        body_landmarks=body_lm,
        created_at=capture.created_at,
    )


@router.post("/tryon/captures", response_model=TryonCaptureResponse)
def save_tryon_capture(
    data: TryonCaptureCreate,
    db: Session = Depends(get_db),
):
    """[CU32] Guarda una captura del look probado en el vestidor virtual."""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    session = None
    if data.session_token:
        session = db.query(VirtualTryonSession).filter(VirtualTryonSession.session_token == data.session_token).first()

    capture = VirtualTryonCapture(
        session_id=session.id if session else None,
        product_id=product.id,
        variant_id=data.variant_id,
        photo_url=data.photo_url,
        original_photo_url=data.original_photo_url,
        generation_model=data.generation_model or "IDM-VTON",
        recommended_size=data.recommended_size,
        measurements_json=data.measurements_json,
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)

    return TryonCaptureResponse(
        id=capture.id,
        product_id=product.id,
        product_name=product.name,
        variant_id=capture.variant_id,
        photo_url=capture.photo_url,
        original_photo_url=capture.original_photo_url,
        generation_model=capture.generation_model,
        recommended_size=capture.recommended_size,
        confidence_score=capture.confidence_score,
        created_at=capture.created_at,
    )


# ===================================================================
# CU33: CHATBOT ASISTENTE & ESTILISTA IA
# ===================================================================

# ===================================================================
# CU33: CHATBOT ASISTENTE & ESTILISTA IA
# ===================================================================

_GARMENT_STEMS = {
    "blusa": ["blusa", "blusas", "peplum", "camisola"],
    "vestido": ["vestido", "vestidos", "maxi", "midi"],
    "pantalon": ["pantalon", "pantalones", "pantalón", "jean", "jeans", "denim"],
    "falda": ["falda", "faldas"],
    "short": ["short", "shorts", "bermuda", "bermudas"],
    "top": ["top", "tops", "crop", "bustier", "corset"],
    "camisa": ["camisa", "camisas", "camiseta", "camisetas", "remera", "remeras", "polera", "poleras"],
    "chaqueta": ["chaqueta", "chaquetas", "blazer", "blazers", "abrigo", "abrigos", "bomber", "cardigan", "saco"],
    "lenceria": ["lenceria", "lencería", "pijama", "pijamas", "saten", "satén", "dormir", "íntima", "intima"],
    "deportiva": ["deportiva", "deportivo", "legging", "leggings", "activewear", "gym", "fitness"],
    "bano": ["bikini", "bikinis", "playa", "baño", "bano", "traje de baño"],
}

_COLOR_STEMS = {
    "blanco": ["blanco", "blanca", "blancos", "blancas"],
    "negro": ["negro", "negra", "negros", "negras"],
    "rojo": ["rojo", "roja", "rojos", "rojas"],
    "azul": ["azul", "azules", "celeste", "celestes"],
    "verde": ["verde", "verdes"],
    "amarillo": ["amarillo", "amarilla", "amarillos", "amarillas"],
    "rosa": ["rosa", "rosado", "rosada", "rosados", "rosadas"],
    "beige": ["beige", "camel", "arena"],
    "marron": ["marron", "marrón", "marrones", "cafe", "café", "chocolate"],
    "gris": ["gris", "grises"],
    "dorado": ["dorado", "dorada", "dorados", "doradas"],
}

_STOP_WORDS = {
    "hola", "buen", "dia", "dias", "buenas", "tardes", "noches", "por", "favor",
    "tienen", "tiene", "quiero", "quisiera", "busco", "buscar", "mostrar", "muestrame",
    "muéstrame", "ensename", "enséñame", "que", "qué", "para", "como", "cómo", "esta",
    "estan", "están", "unos", "unas", "sobre", "algun", "alguna", "algunas", "algunos",
    "algo", "tienda", "catalogo", "catálogo", "prenda", "prendas", "ropa"
}

def _resolve_primary_product_image(p: Product) -> str:
    if p.images:
        for img in p.images:
            if getattr(img, "is_primary", False) and img.image_url:
                return img.image_url
        if p.images[0].image_url:
            return p.images[0].image_url
    return "/uploads/products/blusa_peplum_blanca.png"


@router.post("/chatbot/message", response_model=ChatbotMessageResponse)
def handle_chatbot_message(
    data: ChatbotMessageRequest,
    db: Session = Depends(get_db),
):
    """[CU33] Motor conversacional del Asistente Virtual / Estilista IA con recomendaciones dinámicas."""
    # [CU33 - Paso 2] / [DSC033 - Paso 2] +handle_chatbot_message(message, session_token)
    # [CU33 - Paso 3] / [DSC033 - Paso 3] +classify_intent_and_extract_entities()
    msg = data.message.lower().strip()
    session_tok = data.session_token or uuid.uuid4().hex

    reply = ""
    intent = "GENERAL"
    suggested_products = []
    actions = []

    # 1. Detección de intenciones conversacionales y de atención al cliente
    if any(k in msg for k in ["hola", "buen dia", "buenas", "que tal", "inicio", "saludos"]):
        intent = "GREETING"
        reply = (
            "¡Hola! 👋 Soy tu Asistente Virtual y Estilista de FashionStore 👗✨. "
            "Puedo ayudarte a encontrar prendas perfectas, recomendarte combinaciones, verificar disponibilidad, "
            "consultar sucursales o rastrear tu pedido. ¿Qué prenda o estilo buscas hoy?"
        )
        actions = ["Ver blusas", "Ver vestidos de fiesta", "Rastrear mi pedido", "Horarios de sucursales"]

    elif any(k in msg for k in ["sucursal", "horario", "ubicacion", "ubicación", "donde estan", "dónde están", "direccion", "dirección"]):
        intent = "STORE_INFO"
        branches = db.query(Branch).filter(Branch.is_active == True).limit(4).all()
        branch_lines = [f"• {b.name}: {b.address} ({b.city})" for b in branches]
        reply = (
            f"Contamos con sucursales activas preparadas para atenderte:\n" +
            "\n".join(branch_lines) +
            "\n\n¡Puedes agendar una reserva de probador desde la app para tener tus prendas listas al llegar!"
        )
        actions = ["Reservar probador", "Ver catálogo", "Hablar con asesor"]

    elif any(k in msg for k in ["rastrear", "tracking", "donde esta mi", "dónde está mi", "mi paquete", "despacho", "estado de mi pedido"]):
        intent = "ORDER_TRACKING"
        trk_match = re.search(r"TRK-[A-Z0-9]{6,8}", data.message.upper())
        if trk_match:
            code = trk_match.group(0)
            shipment = db.query(Shipment).filter(Shipment.tracking_number == code).first()
            if shipment:
                reply = (
                    f"📦 Estado del paquete {code}: **{shipment.status}**.\n"
                    f"Destino: {shipment.delivery_address}. Transportista: {shipment.carrier_name}."
                )
            else:
                reply = f"No encontré despachos con el código {code}. Por favor verifica el número de guía."
        else:
            reply = (
                "Para rastrear tu pedido en tiempo real, indícame tu código de seguimiento (ejemplo: TRK-A1B2C3D4) "
                "o consúltalo en el menú de Envíos de la tienda."
            )
            actions = ["Consultar Envíos", "Hablar con un asesor"]

    elif any(k in msg for k in ["reserva", "probador", "cita", "apartar", "separar prenda"]):
        intent = "RESERVATION"
        reply = (
            "¡Puedes reservar hasta 5 prendas para probártelas en cualquiera de nuestras sucursales! "
            "El stock queda apartado exclusivamente para ti durante 48 horas sin costo adicional."
        )
        actions = ["Ir a Reservas", "Explorar catálogo"]

    elif any(k in msg for k in ["talla", "tallas", "medida", "medidas", "que talla", "qué talla"]):
        intent = "SIZE_ADVICE"
        reply = (
            "En FashionStore manejamos tallas desde XS hasta XL (y numéricas de 36 a 44). "
            "En la ficha de cada prenda encontrarás la guía de medidas detallada, y puedes usar nuestro "
            "Vestidor Virtual con Inteligencia Artificial para obtener una recomendación biométrica personalizada."
        )
        actions = ["Probar en Vestidor Virtual", "Ver catálogo"]

    elif any(k in msg for k in ["delivery", "envio", "envío", "costo de envio", "costo de envío", "cuanto tarda", "cuánto tarda"]):
        intent = "SHIPPING_INFO"
        reply = (
            "Contamos con nuestras 2 exclusivas sucursales en Santa Cruz (Equipetrol y Ventura Mall) y realizamos envíos a domicilio en toda la ciudad y el país. "
            "El plazo de entrega en zona urbana es de 24 a 48 horas con número de seguimiento en vivo."
        )
        actions = ["Ver tarifas de envío", "Ver catálogo"]

    elif any(k in msg for k in ["pago", "pagos", "metodo de pago", "método de pago", "tarjeta", "qr", "paypal", "efectivo"]):
        intent = "PAYMENT_INFO"
        reply = (
            "Aceptamos pagos 100% seguros mediante:\n"
            "• Código QR Simple (Transferencia bancaria instantánea)\n"
            "• Tarjetas de Débito y Crédito (Visa / Mastercard)\n"
            "• PayPal en moneda internacional\n"
            "• Efectivo en caja si retiras en sucursal."
        )
        actions = ["Ver catálogo", "Consultar promociones"]

    elif any(k in msg for k in ["cambio", "cambios", "devolucion", "devolución", "garantia", "garantía"]):
        intent = "RETURNS_INFO"
        reply = (
            "Cuentas con hasta 30 días calendario para solicitar cambio o devolución en cualquiera de nuestras sucursales "
            "o mediante retiro a domicilio, presentando tu comprobante y la prenda con sus etiquetas originales."
        )
        actions = ["Ver sucursales", "Contactar soporte"]

    elif any(k in msg for k in ["cupon", "cupón", "descuento", "descuentos", "promocion", "promoción", "rebaja", "oferta"]):
        intent = "PROMOTIONS_INFO"
        reply = (
            "¡Aprovecha nuestras promociones vigentes! 🎉\n"
            "Usa el cupón **BIENVENIDA10** al pagar para obtener un 10% de descuento en tu compra, "
            "o explora nuestras prendas con precios especiales de temporada."
        )
        prods = db.query(Product).filter(Product.is_active == True).order_by(Product.discount_percent.desc(), Product.id.asc()).limit(3).all()
        for p in prods:
            suggested_products.append({
                "id": p.id,
                "name": p.name,
                "price": float(p.base_price),
                "image_url": _resolve_primary_product_image(p),
            })
        actions = ["Ver ofertas del catálogo", "Vestidor Virtual"]

    elif any(k in msg for k in ["elegante", "boda", "fiesta", "gala", "graduacion", "graduación", "noche"]):
        intent = "STYLE_RECOMMENDATION"
        reply = (
            "Para ocasiones de gala y eventos especiales, te sugiero prendas elegantes de corte formal y telas sofisticadas. "
            "Aquí tienes algunas de nuestras piezas destacadas para deslumbrar:"
        )
        prods = (
            db.query(Product)
            .filter(
                Product.is_active == True,
                or_(
                    Product.tags.ilike("%elegante%"),
                    Product.tags.ilike("%fiesta%"),
                    Product.description.ilike("%elegante%"),
                    Product.name.ilike("%blazer%"),
                    Product.name.ilike("%vestido%"),
                )
            )
            .order_by(Product.base_price.desc())
            .limit(3)
            .all()
        )
        if not prods:
            prods = db.query(Product).filter(Product.is_active == True).order_by(Product.base_price.desc()).limit(3).all()
        for p in prods:
            suggested_products.append({
                "id": p.id,
                "name": p.name,
                "price": float(p.base_price),
                "image_url": _resolve_primary_product_image(p),
            })
        actions = ["Probar en Vestidor Virtual", "Ver vestidos de fiesta"]

    else:
        # Búsqueda semántica inteligente en el catálogo con normalización de plurales y raíces
        intent = "CATALOG_SEARCH"
        detected_garment = None
        for canonical, variants in _GARMENT_STEMS.items():
            if any(v in msg for v in variants):
                detected_garment = canonical
                break

        detected_color = None
        for canonical, variants in _COLOR_STEMS.items():
            if any(v in msg for v in variants):
                detected_color = canonical
                break

        detected_material = None
        for mat in ["lino", "seda", "algodon", "algodón", "cuero", "encaje", "saten", "satén", "denim"]:
            if mat in msg:
                detected_material = mat
                break

        q = db.query(Product).filter(Product.is_active == True)

        filter_clauses = []
        if detected_garment:
            variants = _GARMENT_STEMS[detected_garment]
            clause = or_(*(
                [Product.name.ilike(f"%{v}%") for v in variants] +
                [Product.description.ilike(f"%{v}%") for v in variants] +
                [Product.tags.ilike(f"%{v}%") for v in variants]
            ))
            filter_clauses.append(clause)

        if detected_color:
            color_variants = _COLOR_STEMS[detected_color]
            color_clause = or_(*(
                [Product.name.ilike(f"%{c}%") for c in color_variants] +
                [Product.description.ilike(f"%{c}%") for c in color_variants] +
                [Product.tags.ilike(f"%{c}%") for c in color_variants] +
                [Product.variants.any(ProductVariant.color.has(Color.name.ilike(f"%{detected_color}%")))]
            ))
            filter_clauses.append(color_clause)

        if detected_material:
            mat_clean = detected_material.replace("ó", "o")
            filter_clauses.append(or_(
                Product.material.ilike(f"%{mat_clean}%"),
                Product.description.ilike(f"%{mat_clean}%"),
                Product.tags.ilike(f"%{mat_clean}%"),
            ))

        # Si no hubo coincidencia de stem, filtrar palabras significativas
        if not filter_clauses:
            tokens = [w for w in re.findall(r"\w+", msg) if len(w) > 2 and w not in _STOP_WORDS]
            if tokens:
                for token in tokens:
                    stem = token[:-1] if (token.endswith("s") or token.endswith("es")) and len(token) > 4 else token
                    filter_clauses.append(or_(
                        Product.name.ilike(f"%{stem}%"),
                        Product.description.ilike(f"%{stem}%"),
                        Product.tags.ilike(f"%{stem}%"),
                    ))

        matched = []
        if filter_clauses:
            matched = q.filter(*filter_clauses).limit(4).all()

        if not matched and detected_garment:
            # Reintentar solo por prenda
            matched = db.query(Product).filter(
                Product.is_active == True,
                or_(*[Product.name.ilike(f"%{v}%") for v in _GARMENT_STEMS[detected_garment]])
            ).limit(4).all()

        if not matched:
            # Fallback elegante a novedades activas para no dejar al cliente con pantalla vacía
            matched = db.query(Product).filter(Product.is_active == True).order_by(Product.id.asc()).limit(3).all()
            reply = (
                "Aquí tienes algunas de nuestras prendas destacadas de la temporada. "
                "Puedes seleccionar cualquiera para ver fotos, tallas disponibles o probártela en el vestidor virtual:"
            )
        else:
            term_desc = f"{detected_garment or 'prendas'}"
            if detected_color:
                term_desc += f" en tono {detected_color}"
            if detected_material:
                term_desc += f" de {detected_material}"
            reply = f"Encontré estas hermosas opciones de {term_desc} en nuestra colección:"

        for p in matched:
            suggested_products.append({
                "id": p.id,
                "name": p.name,
                "price": float(p.base_price),
                "image_url": _resolve_primary_product_image(p),
            })
        actions = ["Ver detalles", "Vestidor Virtual", "Ver vestidos", "Ver blusas"]

    # Guardar en base de datos
    db.add(ChatbotConversation(
        session_token=session_tok,
        sender="USER",
        message=data.message,
        intent=intent,
    ))
    db.add(ChatbotConversation(
        session_token=session_tok,
        sender="BOT",
        message=reply,
        intent=intent,
        metadata_json=json.dumps({"suggested_count": len(suggested_products)}),
    ))
    db.commit()

    return ChatbotMessageResponse(
        reply=reply,
        session_token=session_tok,
        detected_intent=intent,
        suggested_products=suggested_products,
        suggested_actions=actions,
    )


# ===================================================================
# CU34: BÚSQUEDA POR VOZ CON NLP
# ===================================================================

@router.post("/search/voice-nlp", response_model=VoiceSearchNLPResponse)
def search_catalog_voice_nlp(
    data: VoiceSearchNLPRequest,
    db: Session = Depends(get_db),
):
    """[CU34] Extrae entidades semánticas (prenda, color, precio, género) del texto transcrito por voz."""
    # [CU34 - Paso 2] / [DSC034 - Paso 2] +search_catalog_voice_nlp(transcription)
    # [CU34 - Paso 3] / [DSC034 - Paso 3] +extract_voice_facets(garment, color, gender, max_price)
    query = data.query_text.lower().strip()

    extracted = {
        "color": None,
        "garment": None,
        "gender": None,
        "max_price": None,
    }

    # 1. Extracción de color con soporte de variaciones de género y plurales
    for canonical, variants in _COLOR_STEMS.items():
        if any(v in query for v in variants):
            extracted["color"] = canonical
            break

    # 2. Extracción de tipo de prenda con soporte de singular y plural
    for canonical, variants in _GARMENT_STEMS.items():
        if any(v in query for v in variants):
            extracted["garment"] = canonical
            break

    # 3. Extracción de género
    genders_known = {
        "mujer": "Damas", "damas": "Damas", "femenina": "Damas", "dama": "Damas", "chica": "Damas",
        "hombre": "Caballeros", "caballero": "Caballeros", "varon": "Caballeros", "masculino": "Caballeros",
        "niño": "Niños", "niña": "Niños", "infantil": "Niños"
    }
    for gen_k, gen_v in genders_known.items():
        if gen_k in query:
            extracted["gender"] = gen_v
            break

    # 4. Extracción de precio flexible ("menos de 200", "hasta 150", "de 180", "menor a 250", "maximo 300")
    price_match = re.search(r"(?:menos de|hasta|maximo|máximo|menor a|menor de|debajo de|de|por)\s*(\d+)", query)
    if price_match:
        extracted["max_price"] = float(price_match.group(1))

    # 5. Consulta dinámica en base de datos
    q = db.query(Product).filter(Product.is_active == True)

    if extracted["garment"]:
        variants = _GARMENT_STEMS[extracted["garment"]]
        q = q.filter(or_(*(
            [Product.name.ilike(f"%{v}%") for v in variants] +
            [Product.description.ilike(f"%{v}%") for v in variants] +
            [Product.tags.ilike(f"%{v}%") for v in variants]
        )))

    if extracted["color"]:
        color_variants = _COLOR_STEMS[extracted["color"]]
        q = q.filter(or_(*(
            [Product.name.ilike(f"%{c}%") for c in color_variants] +
            [Product.description.ilike(f"%{c}%") for c in color_variants] +
            [Product.tags.ilike(f"%{c}%") for c in color_variants] +
            [Product.variants.any(ProductVariant.color.has(Color.name.ilike(f"%{extracted['color']}%")))]
        )))

    if extracted["max_price"]:
        q = q.filter(Product.base_price <= extracted["max_price"])

    # Si se dijo "barato" o "económico", ordenar por precio ascendente
    if any(b in query for b in ["barato", "barata", "baratos", "baratas", "economico", "económico"]):
        q = q.order_by(Product.base_price.asc())

    products_matched = q.limit(10).all()

    # Si no hubo coincidencia estricta de entidades, búsqueda de texto general con las palabras dichas
    if not products_matched:
        tokens = [w for w in re.findall(r"\w+", query) if len(w) > 2 and w not in _STOP_WORDS]
        if tokens:
            general_filters = []
            for t in tokens:
                general_filters.append(or_(
                    Product.name.ilike(f"%{t}%"),
                    Product.description.ilike(f"%{t}%"),
                    Product.tags.ilike(f"%{t}%"),
                ))
            products_matched = db.query(Product).filter(Product.is_active == True, or_(*general_filters)).limit(8).all()

    results = []
    for p in products_matched:
        results.append({
            "id": p.id,
            "name": p.name,
            "base_price": float(p.base_price),
            "image_url": _resolve_primary_product_image(p),
            "category_name": p.category.name if p.category else "General",
        })

    return VoiceSearchNLPResponse(
        original_query=data.query_text,
        extracted_entities=extracted,
        matched_products_count=len(results),
        products=results,
    )


# ===================================================================
# CU35: REPORTES GERENCIALES (KARDEX, TOP VENDIDOS, EXPORTACIÓN CSV/VOZ)
# ===================================================================

@router.get("/reports/kardex", response_model=List[ManagerReportKardexItem])
def get_kardex_report(
    branch_id: Optional[int] = Query(None, description="Filtrar por sucursal"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU35] Consulta el Kardex Físico-Valorado de inventario con movimientos cronológicos."""
    query = db.query(InventoryLedger)
    if branch_id:
        query = query.filter(InventoryLedger.branch_id == branch_id)

    ledger_records = query.order_by(InventoryLedger.created_at.desc()).limit(200).all()

    report = []
    for r in ledger_records:
        branch = db.query(Branch).filter(Branch.id == r.branch_id).first()
        variant = db.query(ProductVariant).filter(ProductVariant.id == r.variant_id).first()
        prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None

        unit_c = float(r.unit_cost)
        total_c = round(abs(r.quantity) * unit_c, 2)

        report.append(
            ManagerReportKardexItem(
                id=r.id,
                date=r.created_at,
                branch_name=branch.name if branch else "Sucursal",
                product_name=prod.name if prod else "Prenda",
                sku=variant.sku if variant else "-",
                movement_type=r.movement_type,
                quantity=r.quantity,
                unit_cost=unit_c,
                total_cost=total_c,
                reference_id=r.reference_id,
            )
        )
    return report


@router.get("/reports/kardex/export-csv")
def export_kardex_csv(
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU35] Exporta el Kardex en formato tabular CSV compatible con Microsoft Excel."""
    records = get_kardex_report(branch_id=branch_id, db=db, current_user=current_user)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Fecha", "Sucursal", "Producto", "SKU", "Tipo Movimiento", "Cantidad", "Costo Unit (Bs.)", "Costo Total (Bs.)", "Referencia"])

    for r in records:
        writer.writerow([
            r.id,
            r.date.strftime("%Y-%m-%d %H:%M:%S"),
            r.branch_name,
            r.product_name,
            r.sku,
            r.movement_type,
            r.quantity,
            f"{r.unit_cost:.2f}",
            f"{r.total_cost:.2f}",
            r.reference_id or "-",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kardex_inventario.csv"}
    )


@router.get("/reports/top-selling", response_model=List[ManagerReportTopSellingItem])
def get_top_selling_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU35] Reporte de prendas más vendidas por volumen de unidades y facturación total."""
    # [CU35 - Paso 2] / [DSC035 - Paso 2] +get_top_selling_products(limit)
    # [CU35 - Paso 3] / [DSC035 - Paso 3] +aggregate_sales_by_product_volume_and_revenue()
    results = (
        db.query(
            ProductVariant.product_id,
            func.sum(OrderItem.quantity).label("total_units"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue")
        )
        .join(OrderItem, OrderItem.variant_id == ProductVariant.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status == "PAGADA")
        .group_by(ProductVariant.product_id)
        .order_by(desc("total_units"))
        .limit(limit)
        .all()
    )

    items = []
    for pid, units, revenue in results:
        prod = db.query(Product).filter(Product.id == pid).first()
        if not prod:
            continue
        img = prod.images[0].image_url if prod.images else None
        cat_name = prod.category.name if prod.category else "Sin categoría"
        items.append(
            ManagerReportTopSellingItem(
                product_id=prod.id,
                product_name=prod.name,
                category_name=cat_name,
                total_units_sold=int(units or 0),
                total_revenue=round(float(revenue or 0.0), 2),
                image_url=img,
            )
        )
    return items


@router.get("/reports/executive-summary")
def get_executive_summary_voice(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU35] Genera un resumen ejecutivo de ventas y operaciones optimizado para síntesis de voz (TTS)."""
    # [CU35 - Paso 2] / [DSC035 - Paso 2] +get_executive_summary_voice()
    # [CU35 - Paso 3] / [DSC035 - Paso 3] +consolidate_sales_kpis_and_inventory()
    total_revenue = db.query(func.sum(Order.total_amount)).filter(Order.status == "PAGADA").scalar() or 0.0
    total_orders = db.query(func.count(Order.id)).filter(Order.status == "PAGADA").scalar() or 0
    active_reservations = db.query(func.count(Reservation.id)).filter(Reservation.status.in_(["PENDING", "PREPARING", "READY"])).scalar() or 0
    pending_shipments = db.query(func.count(Shipment.id)).filter(Shipment.status.in_(["PENDING_DISPATCH", "DISPATCHED", "IN_TRANSIT"])).scalar() or 0

    voice_script = (
        f"Informe ejecutivo de FashionStore. Hasta la fecha se han concretado {total_orders} pedidos pagados, "
        f"alcanzando una recaudación de {round(float(total_revenue), 2)} bolivianos. "
        f"En operaciones, contamos con {active_reservations} reservas activas en probadores "
        f"y {pending_shipments} envíos en proceso de despacho y logística."
    )

    return {
        "summary_text": voice_script,
        "total_revenue": round(float(total_revenue), 2),
        "total_orders": total_orders,
        "active_reservations": active_reservations,
        "pending_shipments": pending_shipments,
    }


@router.get("/reports/product-sales-trend", response_model=ProductSalesTrendResponse)
def get_product_sales_trend(
    product_id: int = Query(..., description="ID de la prenda o producto"),
    months: int = Query(6, ge=1, le=24, description="Meses hacia atrás para analizar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU35] Análisis histórico de demanda y ventas por prenda para decidir pedidos y reposición de stock."""
    # [CU35 - Paso 2] / [DSC035 - Paso 2] +get_product_sales_trend(product_id, months)
    # [CU35 - Paso 3] / [DSC035 - Paso 3] +compute_sales_velocity_and_stock_coverage()
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    img = prod.images[0].image_url if prod.images else None
    cat_name = prod.category.name if prod.category else "Sin categoría"
    base_price = float(prod.base_price or 0.0)

    variant_ids = [v.id for v in prod.variants]
    if not variant_ids:
        return ProductSalesTrendResponse(
            product_id=prod.id,
            product_name=prod.name,
            category_name=cat_name,
            base_price=base_price,
            image_url=img,
            total_units_sold=0,
            total_revenue=0.0,
            current_total_stock=0,
            weekly_velocity=0.0,
            days_of_stock_left=0.0,
            reorder_decision="BAJA_ROTACION",
            reorder_label="Sin Variantes / Sin Stock",
            reorder_badge_class="secondary",
            reorder_recommendation="Esta prenda no cuenta con variantes activas. Registre variantes antes de solicitar pedidos.",
            suggested_reorder_units=0,
            timeline=[],
            variants_breakdown=[],
            branches_stock=[],
        )

    # 1. Existencias actuales totales y por sucursal
    branches_stock_map: Dict[int, Dict[str, Any]] = {}
    inventories = db.query(Inventory).filter(Inventory.variant_id.in_(variant_ids)).all()
    total_stock = 0
    variant_stock_map: Dict[int, int] = {vid: 0 for vid in variant_ids}

    for inv in inventories:
        total_stock += inv.stock_actual
        variant_stock_map[inv.variant_id] = variant_stock_map.get(inv.variant_id, 0) + inv.stock_actual
        if inv.branch_id not in branches_stock_map:
            branch = db.query(Branch).filter(Branch.id == inv.branch_id).first()
            b_name = branch.name if branch else f"Sucursal #{inv.branch_id}"
            branches_stock_map[inv.branch_id] = {"branch_id": inv.branch_id, "branch_name": b_name, "stock": 0}
        branches_stock_map[inv.branch_id]["stock"] += inv.stock_actual

    branches_stock = [BranchStockItem(**v) for v in branches_stock_map.values()]

    # 2. Consultar ventas históricas en el rango de meses
    since_date = datetime.now() - timedelta(days=months * 30)
    order_items = (
        db.query(OrderItem, Order.created_at)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.status == "PAGADA",
            OrderItem.variant_id.in_(variant_ids),
            Order.created_at >= since_date,
        )
        .order_by(Order.created_at.asc())
        .all()
    )

    total_units_sold = 0
    total_revenue = 0.0
    variant_sold_map: Dict[int, int] = {vid: 0 for vid in variant_ids}

    timeline_dict: Dict[str, Dict[str, Any]] = {}

    for item, order_date in order_items:
        qty = item.quantity
        rev = float(item.unit_price * qty)
        total_units_sold += qty
        total_revenue += rev
        variant_sold_map[item.variant_id] = variant_sold_map.get(item.variant_id, 0) + qty

        if months <= 3:
            period_key = order_date.strftime("%Y-W%W")
            date_label = f"Semana {order_date.strftime('%W (%b)')}"
        else:
            period_key = order_date.strftime("%Y-%m")
            date_label = order_date.strftime("%b %Y")

        if period_key not in timeline_dict:
            timeline_dict[period_key] = {
                "period": period_key,
                "date_label": date_label,
                "units_sold": 0,
                "revenue": 0.0,
            }
        timeline_dict[period_key]["units_sold"] += qty
        timeline_dict[period_key]["revenue"] = round(timeline_dict[period_key]["revenue"] + rev, 2)

    timeline = [
        SalesTimelinePoint(
            period=k,
            date_label=v["date_label"],
            units_sold=v["units_sold"],
            revenue=round(v["revenue"], 2),
        )
        for k, v in sorted(timeline_dict.items(), key=lambda x: x[0])
    ]

    # 3. Desglose de variantes (Talla / Color)
    variants_breakdown = []
    for var in prod.variants:
        size_name = var.size.name if var.size else "-"
        color_name = var.color.name if var.color else "-"
        color_hex = var.color.hex_code if var.color else "#CCCCCC"
        variants_breakdown.append(
            VariantSalesStock(
                variant_id=var.id,
                sku=var.sku,
                size=size_name,
                color=color_name,
                color_hex=color_hex,
                current_stock=variant_stock_map.get(var.id, 0),
                units_sold=variant_sold_map.get(var.id, 0),
            )
        )

    # 4. Cálculo de Velocidad y Decisión de Reabastecimiento
    weeks_in_range = max(1.0, (months * 4.33))
    weekly_velocity = round(total_units_sold / weeks_in_range, 2)
    daily_velocity = weekly_velocity / 7.0 if weekly_velocity > 0 else 0.0

    if daily_velocity > 0:
        days_of_stock_left = round(total_stock / daily_velocity, 1)
    else:
        days_of_stock_left = 999.0 if total_stock > 0 else 0.0

    if total_units_sold > 0 and days_of_stock_left <= 10:
        decision = "URGENTE_REORDENAR"
        label = "¡URGENTE! Agotamiento Inminente"
        badge_class = "danger"
        recom = f"Conviene realizar pedido urgente al proveedor. El stock actual ({total_stock} uds) solo cubre aprox. {int(days_of_stock_left)} días de ventas."
        suggested_reorder = max(10, int(round((weekly_velocity * 4.33) - total_stock)))
    elif total_units_sold > 0 and days_of_stock_left <= 25:
        decision = "CONVIENE_PEDIR"
        label = "Conviene Hacer Pedido"
        badge_class = "warning"
        recom = f"Se recomienda programar orden de compra. El stock actual cubre {int(days_of_stock_left)} días al ritmo de {weekly_velocity} uds/semana."
        suggested_reorder = max(10, int(round((weekly_velocity * 4.33) - total_stock)))
    elif total_units_sold > 0 and days_of_stock_left <= 60:
        decision = "STOCK_ADECUADO"
        label = "Stock Adecuado"
        badge_class = "success"
        recom = f"Existencias saludables. El inventario actual ({total_stock} uds) cubre aproximadamente {int(days_of_stock_left / 7)} semanas de demanda estimada."
        suggested_reorder = 0
    else:
        decision = "BAJA_ROTACION"
        label = "Baja Rotación / Stock Abundante"
        badge_class = "info"
        recom = f"Demanda baja o stock muy holgado ({total_stock} uds para más de 60 días). No se aconseja realizar nuevos pedidos en este momento."
        suggested_reorder = 0

    return ProductSalesTrendResponse(
        product_id=prod.id,
        product_name=prod.name,
        category_name=cat_name,
        base_price=base_price,
        image_url=img,
        total_units_sold=total_units_sold,
        total_revenue=round(total_revenue, 2),
        current_total_stock=total_stock,
        weekly_velocity=weekly_velocity,
        days_of_stock_left=days_of_stock_left,
        reorder_decision=decision,
        reorder_label=label,
        reorder_badge_class=badge_class,
        reorder_recommendation=recom,
        suggested_reorder_units=suggested_reorder,
        timeline=timeline,
        variants_breakdown=variants_breakdown,
        branches_stock=branches_stock,
    )


# ===================================================================
# CU39: DASHBOARD GLOBAL ANALÍTICO
# ===================================================================

@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def get_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU39] Métricas globales en tiempo real y KPIs para el panel de control directivo."""
    # [CU39 - Paso 2] / [DSC039 - Paso 2] +get_analytics_dashboard()
    # [CU39 - Paso 3] / [DSC039 - Paso 3] +compute_multichannel_sales_and_inventory_kpis()
    # 1. Total ventas
    revenue_sum = db.query(func.sum(Order.total_amount)).filter(Order.status == "PAGADA").scalar() or 0.0
    orders_cnt = db.query(func.count(Order.id)).filter(Order.status == "PAGADA").scalar() or 0
    avg_ticket = round(float(revenue_sum) / max(orders_cnt, 1), 2)

    # 2. Alertas de inventario bajo
    low_stock = (
        db.query(func.count(Inventory.variant_id))
        .filter(Inventory.stock_actual <= Inventory.stock_minimo)
        .scalar() or 0
    )

    # 3. Ventas por canal (ONLINE vs POS)
    pos_revenue = (
        db.query(func.sum(Order.total_amount))
        .filter(Order.status == "PAGADA", Order.channel == "POS")
        .scalar() or 0.0
    )
    online_revenue = (
        db.query(func.sum(Order.total_amount))
        .filter(Order.status == "PAGADA", Order.channel == "ONLINE")
        .scalar() or 0.0
    )

    # 4. Ventas por categoría
    cat_sales = (
        db.query(
            Category.name,
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("sales")
        )
        .select_from(Category)
        .join(Product, Product.category_id == Category.id)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(OrderItem, OrderItem.variant_id == ProductVariant.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status == "PAGADA")
        .group_by(Category.name)
        .all()
    )
    category_list = [{"name": c[0], "value": round(float(c[1] or 0), 2)} for c in cat_sales]

    # 5. Ventas por sucursal
    branch_sales = (
        db.query(
            Branch.name,
            func.sum(Order.total_amount).label("sales")
        )
        .join(Order, Order.branch_id == Branch.id)
        .filter(Order.status == "PAGADA")
        .group_by(Branch.name)
        .all()
    )
    branch_list = [{"name": b[0], "value": round(float(b[1] or 0), 2)} for b in branch_sales]

    # 6. Ventas últimos 7 días
    daily_sales = []
    today = datetime.now().date()
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        day_rev = (
            db.query(func.sum(Order.total_amount))
            .filter(
                Order.status == "PAGADA",
                Order.created_at >= day_start,
                Order.created_at <= day_end,
            )
            .scalar() or 0.0
        )
        daily_sales.append({
            "date": day_date.strftime("%d/%m"),
            "revenue": round(float(day_rev), 2)
        })

    return AnalyticsDashboardResponse(
        total_sales_revenue=round(float(revenue_sum), 2),
        total_orders_count=orders_cnt,
        average_ticket=avg_ticket,
        low_stock_items_count=low_stock,
        sales_by_channel={"ONLINE": round(float(online_revenue), 2), "POS": round(float(pos_revenue), 2)},
        sales_by_category=category_list,
        sales_by_branch=branch_list,
        daily_sales_last_7_days=daily_sales,
    )
