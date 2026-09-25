# -*- coding: utf-8 -*-
"""
Motor de Renderizado Automatizado de Diagramas de Arquitectura UML 2.5+
FashionStore - Sistemas de Información II (UAGRM)

Genera imágenes PNG en ultra alta resolución (200 DPI) para:
- 4.2. Implementación de la Arquitectura del Sistema (Sistema Principal)
- 4.3. Implementación de la Arquitectura del Subsistema (Subsistemas 1 al 8)

Corrige:
1. Estereotipos erróneos (<<Entity>> en vistas -> <<View>>)
2. Estereotipos de software/librerías (<<Device>> en ReportLab/ARCore -> <<Library>> / <<External Service>>)
3. Conflicto de numeración entre Paquete 5 (Reservas) y Paquete 6 (Envíos)
4. Encabezados y títulos oficiales
5. Mapeo simétrico 1 a 1 con backend FastAPI, frontend Angular y PostgreSQL.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc, Circle

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "diagramas_arquitectura_paquetes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Paleta corporativa
COLOR_BORDER = "#991b1b"        # Borde rojo oscuro/borgoña
COLOR_BG_TOP = (254/255, 242/255, 242/255) # #fef2f2
COLOR_BG_BOT = (248/255, 113/255, 113/255) # #f87171
COLOR_TEXT_STEREO = "#374151"   # Gris carbón para estereotipos
COLOR_TEXT_NAME = "#0f172a"     # Casi negro para legibilidad
COLOR_LINE = "#374151"          # Líneas de conexión

def draw_header(ax, main_title, subtitle=""):
    """Dibuja el encabezado oficial del capítulo de arquitectura."""
    ax.text(0.6, ax.get_ylim()[1] - 0.45, main_title, fontsize=12.5, fontweight="bold",
            fontfamily="sans-serif", color="#000000", ha="left", va="center")
    if subtitle:
        ax.text(0.6, ax.get_ylim()[1] - 0.95, subtitle, fontsize=11.5, fontweight="bold",
                fontfamily="sans-serif", color="#000000", ha="left", va="center")

def draw_component_icon(ax, x_right, y_top, size=0.24):
    """Pictograma UML 2.5 de Componente en la esquina superior derecha."""
    w = size
    h = size * 1.25
    x = x_right - w - 0.08
    y = y_top - h - 0.08
    
    rect = patches.Rectangle((x, y), w, h, facecolor="#ffffff", edgecolor=COLOR_BORDER, lw=0.8, zorder=6)
    ax.add_patch(rect)
    
    tab_w = w * 0.45
    tab_h = h * 0.22
    t1_y = y + h * 0.58
    t2_y = y + h * 0.18
    
    r1 = patches.Rectangle((x - tab_w * 0.5, t1_y), tab_w, tab_h, facecolor="#ffffff", edgecolor=COLOR_BORDER, lw=0.7, zorder=7)
    r2 = patches.Rectangle((x - tab_w * 0.5, t2_y), tab_w, tab_h, facecolor="#ffffff", edgecolor=COLOR_BORDER, lw=0.7, zorder=7)
    ax.add_patch(r1)
    ax.add_patch(r2)

def draw_component(ax, x, y, width, height, stereotype, name, font_scale=1.0):
    """Dibuja una caja de componente UML con degradado vertical coral y textos limpios."""
    left = x - width / 2
    right = x + width / 2
    bot = y - height / 2
    top = y + height / 2
    
    # Degradado
    cmap_data = np.zeros((128, 1, 3))
    for i in range(128):
        t = i / 127.0
        cmap_data[i, 0] = [
            COLOR_BG_TOP[0]*(1-t) + COLOR_BG_BOT[0]*t,
            COLOR_BG_TOP[1]*(1-t) + COLOR_BG_BOT[1]*t,
            COLOR_BG_TOP[2]*(1-t) + COLOR_BG_BOT[2]*t
        ]
    ax.imshow(cmap_data, extent=[left, right, bot, top], origin="upper", aspect="auto", zorder=3)
    
    # Borde exterior
    border = patches.Rectangle((left, bot), width, height, facecolor="none", edgecolor=COLOR_BORDER, lw=1.1, zorder=4)
    ax.add_patch(border)
    
    # Ícono
    draw_component_icon(ax, right, top, size=min(0.22, height*0.3))
    
    # Estereotipo
    ax.text(x, y + height*0.14, f"«{stereotype}»", ha="center", va="center",
            fontsize=6.8*font_scale, fontfamily="sans-serif", color=COLOR_TEXT_STEREO, zorder=5)
    
    # Nombre
    display_name = name
    if len(name) > 20 and "\n" not in name:
        parts = name.split("_")
        if len(parts) > 1:
            mid = len(parts) // 2
            display_name = "_".join(parts[:mid]) + "_\n" + "_".join(parts[mid:])
    ax.text(x, y - height*0.18, display_name, ha="center", va="center",
            fontsize=7.8*font_scale, fontfamily="sans-serif", fontweight="bold", color=COLOR_TEXT_NAME, zorder=5)
    
    return {"left": left, "right": right, "top": top, "bottom": bot, "center_x": x, "center_y": y}

def draw_ball_socket(ax, b_view, b_ctrl, ball_r=0.08, socket_r=0.14):
    """Conector Ball-and-Socket: Socket en vista, Ball en controlador."""
    x1, y1 = b_view["center_x"], b_view["bottom"]
    x2, y2 = b_ctrl["center_x"], b_ctrl["top"]
    
    mid_y = (y1 + y2) / 2
    mid_x = (x1 + x2) / 2
    
    # Línea vista -> socket
    ax.plot([x1, mid_x], [y1, mid_y + socket_r*0.8], color=COLOR_LINE, lw=1.05, zorder=3)
    # Socket (arco)
    arc = Arc((mid_x, mid_y), socket_r*2, socket_r*2, angle=0, theta1=200, theta2=340,
              color=COLOR_LINE, lw=1.3, zorder=4)
    ax.add_patch(arc)
    # Ball (círculo)
    circ = Circle((mid_x, mid_y), ball_r, facecolor="#ffffff", edgecolor=COLOR_LINE, lw=1.1, zorder=5)
    ax.add_patch(circ)
    # Línea ball -> controlador
    ax.plot([mid_x, x2], [mid_y - ball_r, y2], color=COLOR_LINE, lw=1.05, zorder=3)

def draw_dep(ax, b_from, b_to, rad=0.0):
    """Flecha de dependencia UML discontinua (..>)."""
    x1, y1 = b_from["center_x"], b_from["center_y"]
    x2, y2 = b_to["center_x"], b_to["center_y"]
    
    if y1 > y2 + 0.3:
        p_from = (x1, b_from["bottom"])
        p_to = (x2, b_to["top"])
    elif y1 < y2 - 0.3:
        p_from = (x1, b_from["top"])
        p_to = (x2, b_to["bottom"])
    elif x1 < x2:
        p_from = (b_from["right"], y1)
        p_to = (b_to["left"], y2)
    else:
        p_from = (b_from["left"], y1)
        p_to = (b_to["right"], y2)
        
    conn = f"arc3,rad={rad}" if rad != 0.0 else "arc3"
    ax.annotate("", xy=p_to, xytext=p_from,
                arrowprops=dict(arrowstyle="->", linestyle="--", color=COLOR_LINE, lw=1.0,
                                mutation_scale=10, connectionstyle=conn), zorder=2)

def draw_package(ax, x, y, width, height, title, subtitle="", title_pos="center"):
    """Dibuja una carpeta de paquete con lengüeta superior."""
    left = x - width / 2
    right = x + width / 2
    bot = y - height / 2
    top = y + height / 2
    
    tab_w = min(width * 0.45, 2.5)
    tab_h = 0.28
    
    tab = patches.Rectangle((left, top), tab_w, tab_h, facecolor="#fecaca", edgecolor=COLOR_BORDER, lw=1.0, zorder=2)
    body = patches.Rectangle((left, bot), width, height, facecolor="#fee2e2", edgecolor=COLOR_BORDER, lw=1.1, zorder=2)
    ax.add_patch(tab)
    ax.add_patch(body)
    
    if title_pos == "top":
        ax.text(x, top - 0.35, title, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#991b1b", zorder=5)
    else:
        if subtitle:
            ax.text(x, y + 0.10, title, ha="center", va="center", fontsize=7.2, fontweight="bold", color="#991b1b", zorder=5)
            ax.text(x, y - 0.14, subtitle, ha="center", va="center", fontsize=6.8, color="#1f2937", zorder=5)
        else:
            ax.text(x, y, title, ha="center", va="center", fontsize=7.5, fontweight="bold", color="#991b1b", zorder=5)
        
    return {"left": left, "right": right, "top": top, "bottom": bot, "center_x": x, "center_y": y}

# =============================================================================
# 1. SUBSISTEMA 1: Seguridad_Y_Usuarios
# =============================================================================
def render_subsistema_1():
    fig, ax = plt.subplots(figsize=(15, 8.2), dpi=200)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 1: Seguridad_Y_Usuarios")
    
    # Fila 1: Vistas (Todas <<View>>)
    v_login = draw_component(ax, 2.0, 6.2, 2.1, 1.0, "View", "Login")
    v_reg = draw_component(ax, 4.5, 6.2, 2.1, 1.0, "View", "Register")
    v_rec = draw_component(ax, 7.0, 6.2, 2.1, 1.0, "View", "Recover")
    v_roles = draw_component(ax, 10.0, 6.2, 2.3, 1.0, "View", "UsuariosRoles")
    v_audit = draw_component(ax, 13.0, 6.2, 2.3, 1.0, "View", "AuditLog_View")
    
    # Fila 2: Controladores
    c_auth = draw_component(ax, 4.5, 4.0, 2.4, 1.0, "Controller", "CTR_Auth")
    c_users = draw_component(ax, 10.0, 4.0, 2.4, 1.0, "Controller", "CTR_Users")
    c_audit = draw_component(ax, 13.0, 4.0, 2.4, 1.0, "Controller", "CTR_Auditoria")
    
    # Fila 3: Entidades
    e_user = draw_component(ax, 2.5, 1.5, 2.2, 1.0, "Entity", "Usuario")
    e_rol = draw_component(ax, 5.5, 1.5, 2.2, 1.0, "Entity", "Rol")
    e_token = draw_component(ax, 8.5, 1.5, 2.2, 1.0, "Entity", "SessionToken")
    e_audit = draw_component(ax, 12.0, 1.5, 2.2, 1.0, "Entity", "AuditLog")
    
    # Conexiones Ball & Socket
    draw_ball_socket(ax, v_login, c_auth)
    draw_ball_socket(ax, v_reg, c_auth)
    draw_ball_socket(ax, v_rec, c_auth)
    draw_ball_socket(ax, v_roles, c_users)
    draw_ball_socket(ax, v_audit, c_audit)
    
    # Dependencias Controlador -> Entidades
    draw_dep(ax, c_auth, e_user)
    draw_dep(ax, c_auth, e_rol)
    draw_dep(ax, c_auth, e_token)
    draw_dep(ax, c_auth, e_audit)
    
    draw_dep(ax, c_users, e_user)
    draw_dep(ax, c_users, e_rol)
    draw_dep(ax, c_users, e_audit)
    
    draw_dep(ax, c_audit, e_audit)
    
    out = os.path.join(OUTPUT_DIR, "4_3_1_Subsistema_1_Seguridad_Y_Usuarios.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 2. SUBSISTEMA 2: Catalogo_Y_Tiendas
# =============================================================================
def render_subsistema_2():
    fig, ax = plt.subplots(figsize=(15, 8.2), dpi=200)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 2: Catalogo_Y_Tiendas")
    
    # Fila 1: Vistas (Todas <<View>>)
    v_bra = draw_component(ax, 2.4, 6.2, 2.2, 1.0, "View", "Branches")
    v_emp = draw_component(ax, 5.0, 6.2, 2.2, 1.0, "View", "Employees")
    v_prod = draw_component(ax, 9.0, 6.2, 2.2, 1.0, "View", "Products")
    v_store = draw_component(ax, 12.2, 6.2, 2.2, 1.0, "View", "StoreHome")
    
    # Fila 2: Controladores
    c_bra = draw_component(ax, 3.7, 4.0, 2.6, 1.0, "Controller", "CTR_Branches")
    c_cat = draw_component(ax, 10.6, 4.0, 2.6, 1.0, "Controller", "CTR_Catalogo")
    
    # Fila 3: Entidades
    e_suc = draw_component(ax, 2.5, 1.5, 2.3, 1.0, "Entity", "Sucursal")
    e_pro = draw_component(ax, 5.8, 1.5, 2.3, 1.0, "Entity", "Producto")
    e_var = draw_component(ax, 9.0, 1.5, 2.3, 1.0, "Entity", "Variante")
    e_param = draw_component(ax, 12.5, 1.5, 2.5, 1.0, "Entity", "ParametroCatalogo")
    
    # Ball & Socket
    draw_ball_socket(ax, v_bra, c_bra)
    draw_ball_socket(ax, v_emp, c_bra)
    draw_ball_socket(ax, v_prod, c_cat)
    draw_ball_socket(ax, v_store, c_cat)
    
    # Dependencias
    draw_dep(ax, c_bra, e_suc)
    draw_dep(ax, c_cat, e_pro)
    draw_dep(ax, c_cat, e_var)
    draw_dep(ax, c_cat, e_param)
    
    out = os.path.join(OUTPUT_DIR, "4_3_2_Subsistema_2_Catalogo_Y_Tiendas.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 3. SUBSISTEMA 3: Inventario_Y_Proveedores
# =============================================================================
def render_subsistema_3():
    fig, ax = plt.subplots(figsize=(18, 8.5), dpi=200)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 8.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 3: Inventario_Y_Proveedores")
    
    # Vistas (Fila 1)
    v_trans = draw_component(ax, 1.8, 6.4, 2.3, 0.9, "View", "Transferencias\nInventario", font_scale=0.9)
    v_alert = draw_component(ax, 4.4, 6.4, 2.3, 0.9, "View", "Configuracion\nAlertasStock", font_scale=0.9)
    v_kard = draw_component(ax, 7.0, 6.4, 2.3, 0.9, "View", "MonitorStock\nKardex", font_scale=0.9)
    v_adj = draw_component(ax, 9.6, 6.4, 2.0, 0.9, "View", "Adjustments", font_scale=0.9)
    v_val = draw_component(ax, 11.9, 6.4, 2.0, 0.9, "View", "Valuation", font_scale=0.9)
    v_merc = draw_component(ax, 14.2, 6.4, 2.0, 0.9, "View", "Merchandise", font_scale=0.9)
    v_supp = draw_component(ax, 16.5, 6.4, 2.0, 0.9, "View", "Suppliers", font_scale=0.9)
    
    # Controladores (Fila 2)
    c_trans = draw_component(ax, 1.8, 4.2, 2.2, 0.9, "Controller", "CTR_Transferencias", font_scale=0.85)
    c_alert = draw_component(ax, 4.4, 4.2, 2.2, 0.9, "Controller", "CTR_AlertasStock", font_scale=0.85)
    c_kard = draw_component(ax, 7.0, 4.2, 2.2, 0.9, "Controller", "CTR_KardexLedger", font_scale=0.85)
    c_inv = draw_component(ax, 12.0, 4.2, 2.4, 0.9, "Controller", "CTR_Inventario", font_scale=0.9)
    c_supp = draw_component(ax, 16.5, 4.2, 2.2, 0.9, "Controller", "CTR_Proveedores", font_scale=0.85)
    
    # Entidades (Fila 3)
    e_trans = draw_component(ax, 1.3, 1.5, 2.0, 0.9, "Entity", "CE_Transferencia", font_scale=0.8)
    e_itrans = draw_component(ax, 3.5, 1.5, 2.0, 0.9, "Entity", "CE_ItemTransferencia", font_scale=0.75)
    e_invsuc = draw_component(ax, 5.7, 1.5, 2.1, 0.9, "Entity", "CE_InventarioSucursal", font_scale=0.75)
    e_mayor = draw_component(ax, 8.0, 1.5, 2.1, 0.9, "Entity", "CE_LibroMayor", font_scale=0.8)
    e_alert = draw_component(ax, 10.3, 1.5, 2.0, 0.9, "Entity", "CE_AlertaStock", font_scale=0.8)
    e_inv = draw_component(ax, 12.5, 1.5, 2.0, 0.9, "Entity", "CE_Inventario", font_scale=0.85)
    e_comp = draw_component(ax, 14.7, 1.5, 2.0, 0.9, "Entity", "CE_Compra", font_scale=0.85)
    e_supp = draw_component(ax, 16.8, 1.5, 1.9, 0.9, "Entity", "CE_Proveedor", font_scale=0.85)
    
    # Conexiones
    draw_ball_socket(ax, v_trans, c_trans)
    draw_ball_socket(ax, v_alert, c_alert)
    draw_ball_socket(ax, v_kard, c_kard)
    draw_ball_socket(ax, v_adj, c_inv)
    draw_ball_socket(ax, v_val, c_inv)
    draw_ball_socket(ax, v_merc, c_inv)
    draw_ball_socket(ax, v_supp, c_supp)
    
    draw_dep(ax, c_trans, c_alert)
    draw_dep(ax, c_trans, c_kard, rad=0.2)
    
    draw_dep(ax, c_trans, e_trans)
    draw_dep(ax, c_trans, e_itrans)
    draw_dep(ax, c_trans, e_invsuc)
    draw_dep(ax, c_alert, e_invsuc)
    draw_dep(ax, c_alert, e_alert)
    draw_dep(ax, c_kard, e_invsuc)
    draw_dep(ax, c_kard, e_mayor)
    draw_dep(ax, c_inv, e_alert)
    draw_dep(ax, c_inv, e_inv)
    draw_dep(ax, c_inv, e_comp)
    draw_dep(ax, c_supp, e_supp)
    draw_dep(ax, c_supp, e_comp)
    
    out = os.path.join(OUTPUT_DIR, "4_3_3_Subsistema_3_Inventario_Y_Proveedores.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 4. SUBSISTEMA 4: Ventas_Y_Pagos
# =============================================================================
def render_subsistema_4():
    fig, ax = plt.subplots(figsize=(20.5, 9.2), dpi=200)
    ax.set_xlim(0, 20.5)
    ax.set_ylim(0, 9.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 4: Ventas_Y_Pagos")
    
    # 8 Vistas (Fila 1)
    views = [
        ("CarritoWebMovil", 1.4), ("CheckoutDigital", 3.8), ("PuntoDeVentaPOS", 6.2),
        ("ArqueoCajaPOS", 8.6), ("FacturacionNotas", 11.0), ("CotizacionComercial", 13.4),
        ("DevolucionesCambios", 15.8), ("HistorialCompras", 18.2)
    ]
    b_views = {}
    for name, x in views:
        b_views[name] = draw_component(ax, x, 7.5, 2.1, 0.9, "View", name, font_scale=0.8)
        
    # 8 Controladores (Fila 2)
    ctrls = [
        ("CTR_Carrito", 1.4), ("CTR_Checkout", 3.8), ("CTR_POS", 6.2),
        ("CTR_ArqueoCaja", 8.6), ("CTR_Facturacion", 11.0), ("CTR_Cotizacion", 13.4),
        ("CTR_Devoluciones", 15.8), ("CTR_HistorialCompras", 18.2)
    ]
    b_ctrls = {}
    for name, x in ctrls:
        b_ctrls[name] = draw_component(ax, x, 5.2, 2.1, 0.9, "Controller", name, font_scale=0.8)
        
    # Capa Externa / Dispositivos (Fila 2.5)
    ext_pay = draw_component(ax, 3.8, 3.3, 2.3, 0.9, "External Service", "PasarelaPagos_API", font_scale=0.75)
    dev_pos = draw_component(ax, 6.2, 3.3, 2.3, 0.9, "Device", "ImpresionTermicaPOS", font_scale=0.75)
    ext_sin = draw_component(ax, 11.0, 3.3, 2.3, 0.9, "External System", "SIN_FacturacionVirtual", font_scale=0.75)
    
    # 9 Entidades (Fila 3)
    ents = [
        ("CE_Carrito", 1.3), ("CE_Orden", 3.4), ("CE_ItemOrden", 5.5),
        ("CE_PagoPolimorfico", 7.8), ("CE_Factura", 10.1), ("CE_SesionCaja", 12.3),
        ("CE_MovimientosCaja", 14.5), ("CE_Cotizacion", 16.7), ("CE_Devolucion", 18.9)
    ]
    b_ents = {}
    for name, x in ents:
        b_ents[name] = draw_component(ax, x, 1.2, 1.95, 0.9, "Entity", name, font_scale=0.75)
        
    # Ball & Socket Vistas -> Controladores
    for (v_name, _), (c_name, _) in zip(views, ctrls):
        draw_ball_socket(ax, b_views[v_name], b_ctrls[c_name])
        
    # Colaboraciones entre controladores
    draw_dep(ax, b_ctrls["CTR_Carrito"], b_ctrls["CTR_Checkout"])
    draw_dep(ax, b_ctrls["CTR_POS"], b_ctrls["CTR_ArqueoCaja"])
    draw_dep(ax, b_ctrls["CTR_Checkout"], b_ctrls["CTR_Facturacion"], rad=0.15)
    draw_dep(ax, b_ctrls["CTR_POS"], b_ctrls["CTR_Facturacion"], rad=0.15)
    
    # Controladores a Servicios / Dispositivos
    draw_dep(ax, b_ctrls["CTR_Checkout"], ext_pay)
    draw_dep(ax, b_ctrls["CTR_POS"], dev_pos)
    draw_dep(ax, b_ctrls["CTR_Facturacion"], ext_sin)
    
    # Controladores a Entidades
    draw_dep(ax, b_ctrls["CTR_Carrito"], b_ents["CE_Carrito"])
    draw_dep(ax, b_ctrls["CTR_Checkout"], b_ents["CE_Orden"])
    draw_dep(ax, b_ctrls["CTR_Checkout"], b_ents["CE_PagoPolimorfico"])
    draw_dep(ax, b_ctrls["CTR_POS"], b_ents["CE_Orden"])
    draw_dep(ax, b_ctrls["CTR_POS"], b_ents["CE_ItemOrden"])
    draw_dep(ax, b_ctrls["CTR_POS"], b_ents["CE_PagoPolimorfico"])
    draw_dep(ax, b_ctrls["CTR_ArqueoCaja"], b_ents["CE_SesionCaja"])
    draw_dep(ax, b_ctrls["CTR_ArqueoCaja"], b_ents["CE_MovimientosCaja"])
    draw_dep(ax, b_ctrls["CTR_Facturacion"], b_ents["CE_Factura"])
    draw_dep(ax, b_ctrls["CTR_Cotizacion"], b_ents["CE_Cotizacion"])
    draw_dep(ax, b_ctrls["CTR_Devoluciones"], b_ents["CE_Devolucion"])
    draw_dep(ax, b_ctrls["CTR_HistorialCompras"], b_ents["CE_Orden"])
    
    out = os.path.join(OUTPUT_DIR, "4_3_4_Subsistema_4_Ventas_Y_Pagos.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 5. SUBSISTEMA 5: Reservas_Y_Citas
# =============================================================================
def render_subsistema_5():
    fig, ax = plt.subplots(figsize=(16, 8.2), dpi=200)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 5: Reservas_Y_Citas")
    
    # Vistas (Fila 1)
    v_ag = draw_component(ax, 1.8, 6.2, 2.3, 0.95, "View", "AgendarReserva_View", font_scale=0.85)
    v_ban = draw_component(ax, 4.8, 6.2, 2.3, 0.95, "View", "BandejaKanban_View", font_scale=0.85)
    v_canc = draw_component(ax, 7.8, 6.2, 2.3, 0.95, "View", "CancelacionReserva_View", font_scale=0.8)
    v_conv = draw_component(ax, 10.9, 6.2, 2.4, 0.95, "View", "ConversionReservaPOS_View", font_scale=0.75)
    v_disp = draw_component(ax, 14.1, 6.2, 2.4, 0.95, "View", "AgendaDisponibilidad_View", font_scale=0.75)
    
    # Controladores (Fila 2)
    c_ag = draw_component(ax, 1.8, 4.0, 2.3, 0.95, "Controller", "CTR_AgendarReserva", font_scale=0.85)
    c_ban = draw_component(ax, 4.8, 4.0, 2.3, 0.95, "Controller", "CTR_BandejaReservas", font_scale=0.85)
    c_canc = draw_component(ax, 7.8, 4.0, 2.3, 0.95, "Controller", "CTR_CancelarReserva", font_scale=0.85)
    c_conv = draw_component(ax, 10.9, 4.0, 2.3, 0.95, "Controller", "CTR_ConversionVenta", font_scale=0.85)
    c_disp = draw_component(ax, 14.1, 4.0, 2.4, 0.95, "Controller", "CTR_DisponibilidadHorarios", font_scale=0.78)
    
    # Entidades (Fila 3)
    e_res = draw_component(ax, 1.8, 1.5, 2.2, 0.95, "Entity", "CE_Reserva", font_scale=0.85)
    e_ires = draw_component(ax, 4.8, 1.5, 2.2, 0.95, "Entity", "CE_ItemReserva", font_scale=0.85)
    e_hor = draw_component(ax, 7.8, 1.5, 2.3, 0.95, "Entity", "CE_HorarioSucursal", font_scale=0.8)
    e_bloq = draw_component(ax, 10.9, 1.5, 2.2, 0.95, "Entity", "CE_BloqueoStock", font_scale=0.85)
    e_hist = draw_component(ax, 14.1, 1.5, 2.4, 0.95, "Entity", "CE_HistorialEstadoReserva", font_scale=0.75)
    
    # Ball & Socket
    draw_ball_socket(ax, v_ag, c_ag)
    draw_ball_socket(ax, v_ban, c_ban)
    draw_ball_socket(ax, v_canc, c_canc)
    draw_ball_socket(ax, v_conv, c_conv)
    draw_ball_socket(ax, v_disp, c_disp)
    
    # Colaboración
    draw_dep(ax, c_ag, c_disp, rad=0.15)
    
    # Dependencias a Entidades
    draw_dep(ax, c_ag, e_res)
    draw_dep(ax, c_ag, e_ires)
    draw_dep(ax, c_ag, e_bloq)
    draw_dep(ax, c_ban, e_res)
    draw_dep(ax, c_ban, e_hist)
    draw_dep(ax, c_canc, e_res)
    draw_dep(ax, c_canc, e_bloq)
    draw_dep(ax, c_conv, e_res)
    draw_dep(ax, c_conv, e_ires)
    draw_dep(ax, c_disp, e_hor)
    
    out = os.path.join(OUTPUT_DIR, "4_3_5_Subsistema_5_Reservas_Y_Citas.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 6. SUBSISTEMA 6: Envios_Y_Logistica
# =============================================================================
def render_subsistema_6():
    fig, ax = plt.subplots(figsize=(16, 8.2), dpi=200)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 6: Envios_Y_Logistica")
    
    # Vistas (Fila 1)
    v_desp = draw_component(ax, 1.8, 6.2, 2.3, 0.95, "View", "DespachoEnvios_View", font_scale=0.85)
    v_rast = draw_component(ax, 4.8, 6.2, 2.3, 0.95, "View", "RastreoPedido_View", font_scale=0.85)
    v_app = draw_component(ax, 7.8, 6.2, 2.3, 0.95, "View", "AppRepartidor_View", font_scale=0.85)
    v_zonas = draw_component(ax, 10.9, 6.2, 2.3, 0.95, "View", "ZonasTarifas_View", font_scale=0.85)
    v_rutas = draw_component(ax, 14.1, 6.2, 2.3, 0.95, "View", "AsignacionRutas_View", font_scale=0.85)
    
    # Controladores (Fila 2)
    c_desp = draw_component(ax, 1.8, 4.0, 2.3, 0.95, "Controller", "CTR_Despacho", font_scale=0.85)
    c_rast = draw_component(ax, 4.8, 4.0, 2.3, 0.95, "Controller", "CTR_RastreoEnvio", font_scale=0.85)
    c_cour = draw_component(ax, 7.8, 4.0, 2.3, 0.95, "Controller", "CTR_EntregaCourier", font_scale=0.85)
    c_zonas = draw_component(ax, 10.9, 4.0, 2.3, 0.95, "Controller", "CTR_ZonasTarifas", font_scale=0.85)
    c_rutas = draw_component(ax, 14.1, 4.0, 2.3, 0.95, "Controller", "CTR_AsignacionRutas", font_scale=0.85)
    
    # Entidades (Fila 3)
    e_guia = draw_component(ax, 1.8, 1.5, 2.2, 0.95, "Entity", "CE_GuiaEnvio", font_scale=0.85)
    e_track = draw_component(ax, 4.8, 1.5, 2.2, 0.95, "Entity", "CE_EventoTracking", font_scale=0.85)
    e_zona = draw_component(ax, 7.8, 1.5, 2.2, 0.95, "Entity", "CE_ZonaCobertura", font_scale=0.85)
    e_tar = draw_component(ax, 10.9, 1.5, 2.2, 0.95, "Entity", "CE_TarifaEnvio", font_scale=0.85)
    e_rep = draw_component(ax, 14.1, 1.5, 2.2, 0.95, "Entity", "CE_Repartidor", font_scale=0.85)
    
    # Ball & Socket
    draw_ball_socket(ax, v_desp, c_desp)
    draw_ball_socket(ax, v_rast, c_rast)
    draw_ball_socket(ax, v_app, c_cour)
    draw_ball_socket(ax, v_zonas, c_zonas)
    draw_ball_socket(ax, v_rutas, c_rutas)
    
    # Colaboración entre controladores
    draw_dep(ax, c_desp, c_rutas, rad=0.15)
    
    # Dependencias a Entidades
    draw_dep(ax, c_desp, e_guia)
    draw_dep(ax, c_desp, e_track)
    draw_dep(ax, c_rast, e_guia)
    draw_dep(ax, c_rast, e_track)
    draw_dep(ax, c_cour, e_guia)
    draw_dep(ax, c_cour, e_track)
    draw_dep(ax, c_cour, e_rep)
    draw_dep(ax, c_zonas, e_zona)
    draw_dep(ax, c_zonas, e_tar)
    draw_dep(ax, c_rutas, e_guia)
    draw_dep(ax, c_rutas, e_rep)
    
    out = os.path.join(OUTPUT_DIR, "4_3_6_Subsistema_6_Envios_Y_Logistica.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 7. SUBSISTEMA 7: Inteligente_Y_Analitica
# =============================================================================
def render_subsistema_7():
    fig, ax = plt.subplots(figsize=(16, 9.0), dpi=200)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9.0)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 7: Inteligente_Y_Analitica")
    
    # Vistas (Fila 1)
    v_vton = draw_component(ax, 1.8, 7.3, 2.3, 0.9, "View", "VestidorVirtualRA_View", font_scale=0.8)
    v_bot = draw_component(ax, 4.8, 7.3, 2.3, 0.9, "View", "ChatbotEstilismo_View", font_scale=0.8)
    v_voz = draw_component(ax, 7.8, 7.3, 2.3, 0.9, "View", "BusquedaVoz_View", font_scale=0.85)
    v_rep = draw_component(ax, 10.9, 7.3, 2.3, 0.9, "View", "ReportesGerenciales_View", font_scale=0.78)
    v_dash = draw_component(ax, 14.1, 7.3, 2.3, 0.9, "View", "DashboardGlobal_View", font_scale=0.8)
    
    # Controladores (Fila 2)
    c_vton = draw_component(ax, 1.8, 5.2, 2.3, 0.9, "Controller", "CTR_VestidorVirtual", font_scale=0.8)
    c_bot = draw_component(ax, 4.8, 5.2, 2.3, 0.9, "Controller", "CTR_ChatbotRecomendador", font_scale=0.75)
    c_voz = draw_component(ax, 7.8, 5.2, 2.3, 0.9, "Controller", "CTR_BusquedaVozNLP", font_scale=0.8)
    c_rep = draw_component(ax, 10.9, 5.2, 2.3, 0.9, "Controller", "CTR_ReportesBI", font_scale=0.85)
    c_dash = draw_component(ax, 14.1, 5.2, 2.3, 0.9, "Controller", "CTR_DashboardKPI", font_scale=0.85)
    
    # Capa Servicios / Librerías (Fila 2.5 - Estereotipos Corregidos)
    s_ar = draw_component(ax, 1.8, 3.2, 2.3, 0.85, "External Service", "ARCore_PoseDetection_API", font_scale=0.72)
    s_ai = draw_component(ax, 4.8, 3.2, 2.3, 0.85, "External Service", "Gemini_GenerativeAI_API", font_scale=0.72)
    s_stt = draw_component(ax, 7.8, 3.2, 2.3, 0.85, "External Service", "WebSpeech_STT_Engine", font_scale=0.75)
    s_pdf = draw_component(ax, 10.9, 3.2, 2.3, 0.85, "Library", "GeneradorReportes_PDF", font_scale=0.75)
    s_lake = draw_component(ax, 14.1, 3.2, 2.3, 0.85, "External Package", "DataLake_Transaccional", font_scale=0.75)
    
    # Entidades (Fila 3)
    e_vton = draw_component(ax, 1.8, 1.2, 2.3, 0.9, "Entity", "CE_CapturaVestidor", font_scale=0.8)
    e_bot = draw_component(ax, 4.8, 1.2, 2.3, 0.9, "Entity", "CE_SesionChatbot", font_scale=0.8)
    e_pref = draw_component(ax, 7.8, 1.2, 2.3, 0.9, "Entity", "CE_PerfilPreferencia", font_scale=0.8)
    e_sven = draw_component(ax, 10.9, 1.2, 2.3, 0.9, "Entity", "CE_SnapshotVentasBI", font_scale=0.78)
    e_sinv = draw_component(ax, 14.1, 1.2, 2.3, 0.9, "Entity", "CE_SnapshotInventarioBI", font_scale=0.75)
    
    # Ball & Socket Vistas -> Controladores
    draw_ball_socket(ax, v_vton, c_vton)
    draw_ball_socket(ax, v_bot, c_bot)
    draw_ball_socket(ax, v_voz, c_voz)
    draw_ball_socket(ax, v_rep, c_rep)
    draw_ball_socket(ax, v_dash, c_dash)
    
    # Colaboración Controladores
    draw_dep(ax, c_voz, c_bot)
    draw_dep(ax, c_rep, c_dash, rad=0.1)
    
    # Controladores -> Servicios/Librerías
    draw_dep(ax, c_vton, s_ar)
    draw_dep(ax, c_bot, s_ai)
    draw_dep(ax, c_voz, s_stt)
    draw_dep(ax, c_rep, s_pdf)
    draw_dep(ax, c_rep, s_lake)
    draw_dep(ax, c_dash, s_lake)
    
    # Controladores y Servicios -> Entidades
    draw_dep(ax, c_vton, e_vton, rad=0.25)
    draw_dep(ax, s_ai, e_bot)
    draw_dep(ax, s_ai, e_pref)
    draw_dep(ax, c_rep, e_sven, rad=0.25)
    draw_dep(ax, s_lake, e_sven)
    draw_dep(ax, s_lake, e_sinv)
    
    out = os.path.join(OUTPUT_DIR, "4_3_7_Subsistema_7_Inteligente_Y_Analitica.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 8. SUBSISTEMA 8: Notificaciones
# =============================================================================
def render_subsistema_8():
    fig, ax = plt.subplots(figsize=(15, 8.8), dpi=200)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.8)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.3. Implementación de la Arquitectura del Subsistema", "Subsistema 8: Notificaciones")
    
    # Vistas (Fila 1)
    v_notif = draw_component(ax, 2.0, 7.0, 2.4, 0.95, "View", "CentroNotificaciones_View", font_scale=0.78)
    v_alert = draw_component(ax, 5.5, 7.0, 2.4, 0.95, "View", "ConfiguracionAlertas_View", font_scale=0.78)
    v_mail = draw_component(ax, 9.2, 7.0, 2.4, 0.95, "View", "GestorPlantillasEmail_View", font_scale=0.75)
    v_cola = draw_component(ax, 13.0, 7.0, 2.4, 0.95, "View", "MonitorColaEnvios_View", font_scale=0.78)
    
    # Controladores (Fila 2)
    c_gest = draw_component(ax, 2.0, 4.8, 2.4, 0.95, "Controller", "CTR_GestorNotificaciones", font_scale=0.75)
    c_push = draw_component(ax, 5.5, 4.8, 2.3, 0.95, "Controller", "CTR_CanalPush", font_scale=0.85)
    c_email = draw_component(ax, 9.2, 4.8, 2.3, 0.95, "Controller", "CTR_CanalEmail", font_scale=0.85)
    c_disp = draw_component(ax, 13.0, 4.8, 2.4, 0.95, "Controller", "CTR_DespachadorCola", font_scale=0.8)
    
    # Servicios Externos (Fila 2.5)
    s_fcm = draw_component(ax, 5.5, 3.0, 2.4, 0.9, "External Service", "FirebaseCloudMessaging_FCM", font_scale=0.72)
    s_smtp = draw_component(ax, 9.2, 3.0, 2.4, 0.9, "External System", "ServidorSMTP_Transaccional", font_scale=0.72)
    s_redis = draw_component(ax, 13.0, 3.0, 2.4, 0.9, "Infrastructure", "Redis_MessageBroker", font_scale=0.75)
    
    # Entidades (Fila 3)
    e_notif = draw_component(ax, 2.0, 1.2, 2.2, 0.9, "Entity", "CE_Notificacion", font_scale=0.85)
    e_tok = draw_component(ax, 5.5, 1.2, 2.2, 0.9, "Entity", "CE_TokenDispositivo", font_scale=0.8)
    e_plant = draw_component(ax, 9.2, 1.2, 2.2, 0.9, "Entity", "CE_PlantillaEmail", font_scale=0.85)
    e_pref = draw_component(ax, 13.0, 1.2, 2.2, 0.9, "Entity", "CE_PreferenciaUsuario", font_scale=0.8)
    
    # Ball & Socket
    draw_ball_socket(ax, v_notif, c_gest)
    draw_ball_socket(ax, v_alert, c_gest)
    draw_ball_socket(ax, v_mail, c_email)
    draw_ball_socket(ax, v_cola, c_disp)
    
    # Dependencias entre controladores
    draw_dep(ax, c_gest, c_push)
    draw_dep(ax, c_gest, c_email)
    draw_dep(ax, c_gest, c_disp, rad=0.15)
    
    # Controladores a Servicios
    draw_dep(ax, c_push, s_fcm)
    draw_dep(ax, c_email, s_smtp)
    draw_dep(ax, c_disp, s_redis)
    
    # Entidades
    draw_dep(ax, c_gest, e_notif)
    draw_dep(ax, c_push, e_tok)
    draw_dep(ax, s_fcm, e_notif)
    draw_dep(ax, s_smtp, e_plant)
    draw_dep(ax, s_redis, e_pref)
    draw_dep(ax, c_email, e_plant)
    draw_dep(ax, c_disp, e_notif)
    
    out = os.path.join(OUTPUT_DIR, "4_3_8_Subsistema_8_Notificaciones.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

# =============================================================================
# 0. SISTEMA PRINCIPAL: Diagrama 4.2
# =============================================================================
def render_diagram_4_2():
    fig, ax = plt.subplots(figsize=(22.5, 16.5), dpi=200)
    ax.set_xlim(0, 22.5)
    ax.set_ylim(0, 16.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    
    draw_header(ax, "4.2. Implementación de la Arquitectura del Sistema")
    
    # Capa Superior: Clientes y Gateway (y=14.4)
    c_web = draw_component(ax, 2.2, 14.4, 2.4, 0.95, "frontend", "ClienteWeb_Angular", font_scale=0.8)
    c_mov = draw_component(ax, 5.0, 14.4, 2.4, 0.95, "mobile", "ClienteMovil_Flutter", font_scale=0.8)
    c_adm = draw_component(ax, 7.8, 14.4, 2.4, 0.95, "frontend", "PanelAdmin_Angular", font_scale=0.8)
    c_api = draw_component(ax, 10.6, 14.4, 2.4, 0.95, "gateway", "ApiRest_FastAPI", font_scale=0.8)
    
    # Barra colectora superior hacia API Gateway
    y_bus = 15.35
    ax.plot([c_web["center_x"], c_web["center_x"]], [c_web["top"], y_bus], color=COLOR_LINE, ls="--", lw=1.0)
    ax.plot([c_mov["center_x"], c_mov["center_x"]], [c_mov["top"], y_bus], color=COLOR_LINE, ls="--", lw=1.0)
    ax.plot([c_adm["center_x"], c_adm["center_x"]], [c_adm["top"], y_bus], color=COLOR_LINE, ls="--", lw=1.0)
    ax.plot([c_web["center_x"], c_api["center_x"]], [y_bus, y_bus], color=COLOR_LINE, ls="--", lw=1.0)
    ax.annotate("", xy=(c_api["center_x"], c_api["top"]), xytext=(c_api["center_x"], y_bus),
                arrowprops=dict(arrowstyle="->", linestyle="--", color=COLOR_LINE, lw=1.0), zorder=2)
    
    # Núcleo Central: main.py
    c_main = draw_component(ax, 6.0, 11.5, 2.6, 1.15, "principal", "main.py", font_scale=0.95)
    draw_dep(ax, c_api, c_main)
    
    # Tecnologías y Servicios Externos (Columna Derecha: 3 filas x 4 columnas)
    ext_components = [
        # Fila 1 (Frameworks y Librerías)
        ("framework", "FastAPI / Uvicorn", 13.5, 12.5),
        ("ORM", "SQLAlchemy 2.0", 15.9, 12.5),
        ("library", "Python-Jose / BCrypt", 18.3, 12.5),
        ("library", "ReportLab / PDF", 20.7, 12.5),
        # Fila 2 (Servicios Cloud)
        ("external service", "Google Gemini Pro AI", 13.5, 11.0),
        ("external service", "Google Maps Geocoding", 15.9, 11.0),
        ("external service", "Firebase Cloud Messaging", 18.3, 11.0),
        ("external service", "Pasarela Stripe / PayPal", 20.7, 11.0),
        # Fila 3 (Infraestructura / Sistemas Externos)
        ("infrastructure", "Redis Cache / Broker", 13.5, 9.5),
        ("cloud storage", "Cloudinary CDN Assets", 15.9, 9.5),
        ("external system", "SIN Facturación Virtual", 18.3, 9.5),
        ("external system", "Servidor SMTP Relay", 20.7, 9.5),
    ]
    
    for st, name, ex, ey in ext_components:
        b = draw_component(ax, ex, ey, 2.15, 0.9, st, name, font_scale=0.72)
        draw_dep(ax, c_main, b)
        
    # Los 8 Paquetes de Negocio (2 filas x 4 columnas, y=9.1 y y=7.4)
    pkg_row1 = [
        ("PAQUETE 1", "SEGURIDAD Y USUARIOS", 2.2),
        ("PAQUETE 2", "CATALOGO Y TIENDAS", 4.7),
        ("PAQUETE 3", "INVENTARIO Y PROVEEDORES", 7.3),
        ("PAQUETE 4", "VENTAS Y PAGOS", 9.9),
    ]
    pkg_row2 = [
        ("PAQUETE 5", "RESERVAS Y CITAS", 2.2),
        ("PAQUETE 6", "ENVIOS Y LOGISTICA", 4.7),
        ("PAQUETE 7", "INTELIGENTE Y ANALITICA", 7.3),
        ("PAQUETE 8", "NOTIFICACIONES", 9.9),
    ]
    
    for p_id, p_name, px in pkg_row1:
        p = draw_package(ax, px, 9.1, 2.25, 1.05, p_id, p_name)
        draw_dep(ax, c_main, p)
        
    for p_id, p_name, px in pkg_row2:
        p = draw_package(ax, px, 7.4, 2.25, 1.05, p_id, p_name)
        draw_dep(ax, c_main, p)
        
    # Gran Paquete Contenedor: Base de Datos PostgreSQL
    db_pkg = draw_package(ax, 11.2, 3.2, 21.0, 5.8, "Base de Datos PostgreSQL (FashionStore_DB)", title_pos="top")
    
    # Script Central
    c_sql = draw_component(ax, 11.2, 3.1, 2.8, 1.05, "script", "BD-FashionStore.sql\n(Tablas / Migrations)", font_scale=0.78)
    draw_dep(ax, c_main, c_sql)
    
    # 16 Tablas Físicas (8 a la izquierda, 8 a la derecha)
    tables_left = [
        "users & roles", "inventory & ledger",
        "audit_logs", "suppliers & purchases",
        "branches & employees", "orders & items",
        "products & variants", "payments & pos_cash"
    ]
    
    coords_left = [
        (2.4, 5.0), (5.5, 5.0),
        (2.4, 3.7), (5.5, 3.7),
        (2.4, 2.4), (5.5, 2.4),
        (2.4, 1.1), (5.5, 1.1),
    ]
    
    for t_name, (tx, ty) in zip(tables_left, coords_left):
        t = draw_component(ax, tx, ty, 2.4, 0.85, "table", t_name, font_scale=0.75)
        draw_dep(ax, c_sql, t)
        
    tables_right = [
        "invoices & tax_sin", "virtual_tryon_captures",
        "reservations & items", "chatbot_sessions",
        "shipments & events", "notifications & tokens",
        "shipping_zones_rates", "email_templates"
    ]
    
    coords_right = [
        (16.9, 5.0), (19.9, 5.0),
        (16.9, 3.7), (19.9, 3.7),
        (16.9, 2.4), (19.9, 2.4),
        (16.9, 1.1), (19.9, 1.1),
    ]
    
    for t_name, (tx, ty) in zip(tables_right, coords_right):
        t = draw_component(ax, tx, ty, 2.4, 0.85, "table", t_name, font_scale=0.75)
        draw_dep(ax, c_sql, t)
        
    out = os.path.join(OUTPUT_DIR, "4_2_Implementacion_Arquitectura_Sistema.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out

def main():
    print("="*75)
    print("Iniciando renderizado de los 9 diagramas de arquitectura UML...")
    print("="*75)
    
    generators = [
        ("Sistema Principal (4.2)", render_diagram_4_2),
        ("Subsistema 1: Seguridad_Y_Usuarios", render_subsistema_1),
        ("Subsistema 2: Catalogo_Y_Tiendas", render_subsistema_2),
        ("Subsistema 3: Inventario_Y_Proveedores", render_subsistema_3),
        ("Subsistema 4: Ventas_Y_Pagos", render_subsistema_4),
        ("Subsistema 5: Reservas_Y_Citas", render_subsistema_5),
        ("Subsistema 6: Envios_Y_Logistica", render_subsistema_6),
        ("Subsistema 7: Inteligente_Y_Analitica", render_subsistema_7),
        ("Subsistema 8: Notificaciones", render_subsistema_8),
    ]
    
    created = []
    for idx, (title, func) in enumerate(generators):
        out_path = func()
        created.append(out_path)
        print(f"[{idx+1}/9] OK: {title} -> {os.path.basename(out_path)}")
        
    print("\n" + "="*75)
    print(f"¡Éxito total! Se generaron {len(created)} diagramas en:")
    print(OUTPUT_DIR)
    print("="*75)

if __name__ == "__main__":
    main()
