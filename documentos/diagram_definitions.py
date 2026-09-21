# -*- coding: utf-8 -*-
"""
Definición exhaustiva y rigurosa de los 40 Casos de Uso (Ciclos 1, 2 y 3)
para el Análisis de Clases (Boundary - Control - Entity / BCE)
según PUDS y arquitectura de base de datos PostgreSQL de FashionStore.
"""

ALL_USE_CASES = [
    # =========================================================================
    # CICLO 1: FUNDACIONAL (15 CASOS DE USO)
    # =========================================================================
    {
        "id": "CU01",
        "title": "CU01: Iniciar sesión en la plataforma",
        "cycle": "Ciclo 1",
        "package": "seguridad_y_usuarios",
        "actor": "Usuario (Cliente / Personal)",
        "boundary": {
            "name": "IU_Login",
            "attributes": [
                "+lbl_titulo_bienvenida",
                "+txt_email_usuario",
                "+txt_password",
                "+btn_iniciar_sesion",
                "+link_olvide_clave",
                "+lbl_mensaje_error_auth"
            ],
            "methods": [
                "+ingresar_credenciales()",
                "+solicitar_inicio_sesion()",
                "+mostrar_error_credenciales()",
                "+redirigir_por_rol(rol)"
            ]
        },
        "controller": {
            "name": "CTR_Autenticacion",
            "methods": [
                "+autenticar_usuario(email, password)",
                "+verificar_hash_bcrypt(pass, hash)",
                "+generar_access_token_jwt(user_id, roles)",
                "+registrar_token_sesion(user_id, token)",
                "+validar_estado_activo(user_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.email",
                    "+users.password_hash",
                    "+users.first_name",
                    "+users.last_name",
                    "+users.is_active"
                ]
            },
            {
                "name": "CE_Role",
                "attributes": [
                    "+roles.id",
                    "+roles.name",
                    "+roles.description"
                ]
            },
            {
                "name": "CE_SessionToken",
                "attributes": [
                    "+session_tokens.id",
                    "+session_tokens.user_id",
                    "+session_tokens.token",
                    "+session_tokens.expires_at",
                    "+session_tokens.is_revoked"
                ]
            }
        ],
        "associations": [
            ("CE_User", "CE_Role"),
            ("CE_User", "CE_SessionToken")
        ]
    },
    {
        "id": "CU02",
        "title": "CU02: Cerrar sesión activa",
        "cycle": "Ciclo 1",
        "package": "seguridad_y_usuarios",
        "actor": "Usuario Autenticado",
        "boundary": {
            "name": "IU_BarraNavegacion",
            "attributes": [
                "+lbl_nombre_usuario_activo",
                "+avatar_usuario",
                "+btn_cerrar_sesion",
                "+modal_confirmacion_salida"
            ],
            "methods": [
                "+solicitar_cierre_sesion()",
                "+confirmar_salida()",
                "+limpiar_storage_local()",
                "+redirigir_login()"
            ]
        },
        "controller": {
            "name": "CTR_Autenticacion",
            "methods": [
                "+revocar_token_jwt(token)",
                "+marcar_sesion_inactiva(token)",
                "+auditar_evento_logout(user_id, ip)"
            ]
        },
        "entities": [
            {
                "name": "CE_SessionToken",
                "attributes": [
                    "+session_tokens.id",
                    "+session_tokens.user_id",
                    "+session_tokens.token",
                    "+session_tokens.is_revoked",
                    "+session_tokens.revoked_at"
                ]
            },
            {
                "name": "CE_AuditLog",
                "attributes": [
                    "+audit_logs.id",
                    "+audit_logs.user_id",
                    "+audit_logs.action",
                    "+audit_logs.ip_address",
                    "+audit_logs.created_at"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU03",
        "title": "CU03: Recuperar credenciales de acceso",
        "cycle": "Ciclo 1",
        "package": "seguridad_y_usuarios",
        "actor": "Usuario (Cliente / Personal)",
        "boundary": {
            "name": "IU_RecuperarClave",
            "attributes": [
                "+txt_email_recuperacion",
                "+btn_enviar_enlace",
                "+lbl_contador_reintento_5min",
                "+txt_nueva_password",
                "+txt_confirmar_password",
                "+btn_guardar_nueva_clave"
            ],
            "methods": [
                "+solicitar_enlace_restablecimiento()",
                "+validar_token_url(token)",
                "+enviar_nueva_password()",
                "+mostrar_confirmacion_exito()"
            ]
        },
        "controller": {
            "name": "CTR_RecuperacionClave",
            "methods": [
                "+validar_existencia_email(email)",
                "+generar_token_unSolo_uso(user_id, 5min)",
                "+enviar_correo_recuperacion(email, token)",
                "+verificar_expiracion_token(token)",
                "+actualizar_password_hash(token, new_pass)"
            ]
        },
        "entities": [
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.email",
                    "+users.password_hash",
                    "+users.reset_token",
                    "+users.reset_token_expires_at"
                ]
            },
            {
                "name": "CE_AuditLog",
                "attributes": [
                    "+audit_logs.id",
                    "+audit_logs.user_id",
                    "+audit_logs.action",
                    "+audit_logs.table_name",
                    "+audit_logs.created_at"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU04",
        "title": "CU04: Auto-registro de cliente en la plataforma",
        "cycle": "Ciclo 1",
        "package": "seguridad_y_usuarios",
        "actor": "Cliente Visitante",
        "boundary": {
            "name": "IU_RegistroCliente",
            "attributes": [
                "+txt_nombres",
                "+txt_apellidos",
                "+txt_email",
                "+txt_telefono",
                "+txt_password",
                "+chk_terminos_condiciones",
                "+btn_crear_cuenta"
            ],
            "methods": [
                "+ingresar_datos_registro()",
                "+validar_politica_contrasena()",
                "+enviar_formulario_registro()",
                "+mostrar_mensaje_bienvenida()"
            ]
        },
        "controller": {
            "name": "CTR_RegistroCliente",
            "methods": [
                "+validar_unicidad_email(email)",
                "+hashear_password_bcrypt(raw_pass)",
                "+insertar_usuario_cliente(datos)",
                "+asignar_rol_defecto_cliente(user_id)",
                "+iniciar_sesion_automatica(user_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.email",
                    "+users.password_hash",
                    "+users.first_name",
                    "+users.last_name",
                    "+users.phone",
                    "+users.is_active"
                ]
            },
            {
                "name": "CE_Role",
                "attributes": [
                    "+roles.id",
                    "+roles.name",
                    "+roles.description"
                ]
            },
            {
                "name": "CE_UserRole",
                "attributes": [
                    "+user_roles.user_id",
                    "+user_roles.role_id",
                    "+user_roles.assigned_at"
                ]
            }
        ],
        "associations": [
            ("CE_User", "CE_UserRole"),
            ("CE_Role", "CE_UserRole")
        ]
    },
    {
        "id": "CU05",
        "title": "CU05: Gestionar perfiles, roles y clientes",
        "cycle": "Ciclo 1",
        "package": "seguridad_y_usuarios",
        "actor": "Superadmin",
        "boundary": {
            "name": "IU_GestionUsuarios",
            "attributes": [
                "+tbl_listado_usuarios",
                "+txt_buscar_usuario",
                "+cmb_filtro_rol",
                "+modal_crear_editar_usuario",
                "+chk_roles_asignables",
                "+chk_estado_activo"
            ],
            "methods": [
                "+listar_usuarios()",
                "+abrir_formulario_edicion(id)",
                "+guardar_modificaciones()",
                "+asignar_roles_usuario(id, roles)",
                "+dar_baja_logica(id)"
            ]
        },
        "controller": {
            "name": "CTR_UsuariosRoles",
            "methods": [
                "+consultar_usuarios(filtros, limit, offset)",
                "+crear_usuario_administrativo(payload)",
                "+actualizar_datos_usuario(user_id, datos)",
                "+sincronizar_roles_usuario(user_id, roles_ids)",
                "+toggle_estado_activo(user_id, is_active)"
            ]
        },
        "entities": [
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.email",
                    "+users.first_name",
                    "+users.last_name",
                    "+users.phone",
                    "+users.is_active"
                ]
            },
            {
                "name": "CE_Role",
                "attributes": [
                    "+roles.id",
                    "+roles.name",
                    "+roles.description"
                ]
            },
            {
                "name": "CE_UserRole",
                "attributes": [
                    "+user_roles.user_id",
                    "+user_roles.role_id"
                ]
            },
            {
                "name": "CE_AuditLog",
                "attributes": [
                    "+audit_logs.id",
                    "+audit_logs.user_id",
                    "+audit_logs.action",
                    "+audit_logs.table_name"
                ]
            }
        ],
        "associations": [
            ("CE_User", "CE_UserRole"),
            ("CE_Role", "CE_UserRole")
        ]
    },
    {
        "id": "CU06",
        "title": "CU06: Gestionar sucursales de la cadena",
        "cycle": "Ciclo 1",
        "package": "catalogo_y_tiendas",
        "actor": "Superadmin",
        "boundary": {
            "name": "IU_GestionSucursales",
            "attributes": [
                "+tbl_sucursales",
                "+txt_nombre_sucursal",
                "+txt_codigo_sucursal",
                "+txt_direccion_fisica",
                "+txt_telefono_contacto",
                "+txt_latitud",
                "+txt_longitud",
                "+modal_selector_mapa_gps"
            ],
            "methods": [
                "+cargar_sucursales()",
                "+abrir_registro_sucursal()",
                "+seleccionar_punto_mapa(lat, lng)",
                "+guardar_sucursal()",
                "+toggle_sucursal_activa(id)"
            ]
        },
        "controller": {
            "name": "CTR_Sucursales",
            "methods": [
                "+listar_sucursales_cadena()",
                "+validar_codigo_sucursal_unico(code)",
                "+crear_sucursal(datos, coords)",
                "+actualizar_sucursal(branch_id, datos)",
                "+desactivar_sucursal(branch_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Branch",
                "attributes": [
                    "+branches.id",
                    "+branches.name",
                    "+branches.code",
                    "+branches.address",
                    "+branches.phone",
                    "+branches.latitude",
                    "+branches.longitude",
                    "+branches.is_active"
                ]
            },
            {
                "name": "CE_BranchEmployee",
                "attributes": [
                    "+branch_employees.id",
                    "+branch_employees.branch_id",
                    "+branch_employees.user_id",
                    "+branch_employees.is_active"
                ]
            }
        ],
        "associations": [
            ("CE_Branch", "CE_BranchEmployee")
        ]
    },
    {
        "id": "CU07",
        "title": "CU07: Gestionar catálogo de prendas",
        "cycle": "Ciclo 1",
        "package": "catalogo_y_tiendas",
        "actor": "Superadmin / Encargado",
        "boundary": {
            "name": "IU_GestionCatalogo",
            "attributes": [
                "+tbl_listado_prendas",
                "+txt_codigo_modelo",
                "+txt_nombre_prenda",
                "+txt_precio_base",
                "+txt_precio_oferta_compare",
                "+cmb_categoria",
                "+cmb_temporada",
                "+tbl_matriz_variantes_sku",
                "+uploader_galeria_fotos"
            ],
            "methods": [
                "+iniciar_nueva_prenda()",
                "+generar_matriz_tallas_colores()",
                "+subir_fotos_color(color_id)",
                "+guardar_ficha_prenda()",
                "+programar_precio_oferta(prod_id, precio)"
            ]
        },
        "controller": {
            "name": "CTR_Catalogo",
            "methods": [
                "+crear_producto_base(datos)",
                "+generar_variantes_sku(product_id, matriz)",
                "+asociar_imagenes_color(product_id, color_id, urls)",
                "+actualizar_precio_y_oferta(prod_id, base, compare)",
                "+validar_sku_unico(sku)"
            ]
        },
        "entities": [
            {
                "name": "CE_Product",
                "attributes": [
                    "+products.id",
                    "+products.category_id",
                    "+products.season_id",
                    "+products.code",
                    "+products.name",
                    "+products.base_price",
                    "+products.compare_at_price",
                    "+products.is_active"
                ]
            },
            {
                "name": "CE_ProductVariant",
                "attributes": [
                    "+product_variants.id",
                    "+product_variants.product_id",
                    "+product_variants.color_id",
                    "+product_variants.size_id",
                    "+product_variants.sku",
                    "+product_variants.barcode"
                ]
            },
            {
                "name": "CE_ProductImage",
                "attributes": [
                    "+product_images.id",
                    "+product_images.product_id",
                    "+product_images.color_id",
                    "+product_images.image_url",
                    "+product_images.is_primary"
                ]
            },
            {
                "name": "CE_Category",
                "attributes": [
                    "+categories.id",
                    "+categories.name",
                    "+categories.image_url"
                ]
            }
        ],
        "associations": [
            ("CE_Product", "CE_ProductVariant"),
            ("CE_Product", "CE_ProductImage"),
            ("CE_Product", "CE_Category")
        ]
    },
    {
        "id": "CU08",
        "title": "CU08: Gestionar proveedores de mercadería",
        "cycle": "Ciclo 1",
        "package": "inventario_y_proveedores",
        "actor": "Encargado de Almacén",
        "boundary": {
            "name": "IU_GestionProveedores",
            "attributes": [
                "+tbl_proveedores",
                "+txt_nit_proveedor",
                "+txt_razon_social",
                "+txt_nombre_contacto",
                "+txt_telefono",
                "+txt_email_pedidos",
                "+txt_direccion",
                "+modal_proveedor"
            ],
            "methods": [
                "+listar_proveedores()",
                "+abrir_registro_proveedor()",
                "+guardar_proveedor()",
                "+editar_contacto()",
                "+dar_baja_proveedor(id)"
            ]
        },
        "controller": {
            "name": "CTR_Proveedores",
            "methods": [
                "+consultar_proveedores(filtro)",
                "+validar_nit_unico(nit)",
                "+crear_proveedor(datos)",
                "+actualizar_proveedor(id, datos)",
                "+inactivar_proveedor(id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Supplier",
                "attributes": [
                    "+suppliers.id",
                    "+suppliers.nit",
                    "+suppliers.company_name",
                    "+suppliers.contact_name",
                    "+suppliers.phone",
                    "+suppliers.email",
                    "+suppliers.address",
                    "+suppliers.is_active"
                ]
            },
            {
                "name": "CE_PurchaseOrder",
                "attributes": [
                    "+purchase_orders.id",
                    "+purchase_orders.supplier_id",
                    "+purchase_orders.total_amount",
                    "+purchase_orders.status"
                ]
            }
        ],
        "associations": [
            ("CE_Supplier", "CE_PurchaseOrder")
        ]
    },
    {
        "id": "CU09",
        "title": "CU09: Gestionar empleados de sucursal",
        "cycle": "Ciclo 1",
        "package": "catalogo_y_tiendas",
        "actor": "Superadmin",
        "boundary": {
            "name": "IU_GestionEmpleados",
            "attributes": [
                "+tbl_personal_sucursal",
                "+cmb_sucursal_activa",
                "+txt_buscar_empleado_ci",
                "+cmb_rol_tienda",
                "+dt_fecha_contratacion",
                "+modal_asignar_sucursal"
            ],
            "methods": [
                "+filtrar_por_sucursal(branch_id)",
                "+abrir_asignacion_empleado()",
                "+vincular_a_sucursal()",
                "+cambiar_rol_sucursal(id, rol)",
                "+remover_de_sucursal(id)"
            ]
        },
        "controller": {
            "name": "CTR_Empleados",
            "methods": [
                "+listar_empleados_por_sucursal(branch_id)",
                "+validar_asignacion_unica(user_id)",
                "+vincular_personal(user_id, branch_id)",
                "+actualizar_rol_personal(user_id, new_role)",
                "+desvincular_personal(branch_employee_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_BranchEmployee",
                "attributes": [
                    "+branch_employees.id",
                    "+branch_employees.branch_id",
                    "+branch_employees.user_id",
                    "+branch_employees.hire_date",
                    "+branch_employees.is_active"
                ]
            },
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.first_name",
                    "+users.last_name",
                    "+users.email",
                    "+users.is_active"
                ]
            },
            {
                "name": "CE_Branch",
                "attributes": [
                    "+branches.id",
                    "+branches.name",
                    "+branches.code",
                    "+branches.address"
                ]
            }
        ],
        "associations": [
            ("CE_BranchEmployee", "CE_User"),
            ("CE_BranchEmployee", "CE_Branch")
        ]
    },
    {
        "id": "CU10",
        "title": "CU10: Registrar compras e ingresos de mercadería",
        "cycle": "Ciclo 1",
        "package": "inventario_y_proveedores",
        "actor": "Encargado de Almacén",
        "boundary": {
            "name": "IU_RecepcionMercaderia",
            "attributes": [
                "+cmb_proveedor_origen",
                "+cmb_sucursal_destino",
                "+txt_numero_factura_proveedor",
                "+tbl_lineas_ingreso",
                "+txt_sku_prenda",
                "+txt_cantidad_recibida",
                "+txt_costo_unitario_compra",
                "+lbl_total_orden_compra"
            ],
            "methods": [
                "+iniciar_ingreso_mercaderia()",
                "+escanear_o_buscar_sku(sku)",
                "+agregar_linea_compra(sku, cant, costo)",
                "+calcular_total_orden()",
                "+confirmar_recepcion_almacen()"
            ]
        },
        "controller": {
            "name": "CTR_ComprasIngresos",
            "methods": [
                "+crear_orden_compra_cabecera(supplier_id, branch_id, factura)",
                "+agregar_detalle_compra(po_id, variant_id, cant, costo)",
                "+calcular_nuevo_costo_promedio_cpp(variant_id, branch_id, cant, costo)",
                "+asentar_movimiento_kardex_ingreso(variant_id, branch_id, cant, costo)",
                "+incrementar_stock_fisico(variant_id, branch_id, cant)"
            ]
        },
        "entities": [
            {
                "name": "CE_PurchaseOrder",
                "attributes": [
                    "+purchase_orders.id",
                    "+purchase_orders.supplier_id",
                    "+purchase_orders.branch_id",
                    "+purchase_orders.invoice_number",
                    "+purchase_orders.total_amount",
                    "+purchase_orders.status",
                    "+purchase_orders.received_at"
                ]
            },
            {
                "name": "CE_PurchaseDetail",
                "attributes": [
                    "+purchase_details.id",
                    "+purchase_details.purchase_order_id",
                    "+purchase_details.product_variant_id",
                    "+purchase_details.quantity",
                    "+purchase_details.unit_cost",
                    "+purchase_details.subtotal"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.branch_id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.avg_cost"
                ]
            },
            {
                "name": "CE_InventoryLedger",
                "attributes": [
                    "+inventory_ledger.id",
                    "+inventory_ledger.product_variant_id",
                    "+inventory_ledger.branch_id",
                    "+inventory_ledger.movement_type",
                    "+inventory_ledger.quantity",
                    "+inventory_ledger.unit_cost"
                ]
            }
        ],
        "associations": [
            ("CE_PurchaseOrder", "CE_PurchaseDetail"),
            ("CE_Inventory", "CE_InventoryLedger")
        ]
    },
    {
        "id": "CU11",
        "title": "CU11: Consultar catálogo de prendas (Cliente)",
        "cycle": "Ciclo 1",
        "package": "catalogo_y_tiendas",
        "actor": "Cliente / Visitante",
        "boundary": {
            "name": "IU_CatalogoTienda",
            "attributes": [
                "+carrusel_categorias_circulares",
                "+grilla_lookbook_prendas",
                "+lbl_precio_base",
                "+lbl_precio_oferta_tachado",
                "+modal_detalle_producto",
                "+carrusel_fotos_color",
                "+swatches_selector_color",
                "+pills_selector_tallas",
                "+btn_guia_de_tallas",
                "+btn_toggle_favorito"
            ],
            "methods": [
                "+cargar_categorias_activas()",
                "+filtrar_por_categoria(cat_id)",
                "+abrir_detalle_prenda(id)",
                "+seleccionar_color(color_id)",
                "+seleccionar_talla(size_id)",
                "+ver_guia_tallas()"
            ]
        },
        "controller": {
            "name": "CTR_CatalogoPublico",
            "methods": [
                "+obtener_categorias_con_imagen()",
                "+obtener_prendas_destacadas(limit)",
                "+obtener_detalle_producto(prod_id)",
                "+obtener_variantes_por_color(prod_id, color_id)",
                "+consultar_galeria_color(prod_id, color_id)",
                "+verificar_disponibilidad_stock(prod_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Product",
                "attributes": [
                    "+products.id",
                    "+products.category_id",
                    "+products.code",
                    "+products.name",
                    "+products.base_price",
                    "+products.compare_at_price",
                    "+products.description"
                ]
            },
            {
                "name": "CE_ProductVariant",
                "attributes": [
                    "+product_variants.id",
                    "+product_variants.product_id",
                    "+product_variants.color_id",
                    "+product_variants.size_id",
                    "+product_variants.sku"
                ]
            },
            {
                "name": "CE_ProductImage",
                "attributes": [
                    "+product_images.id",
                    "+product_images.product_id",
                    "+product_images.color_id",
                    "+product_images.image_url",
                    "+product_images.is_primary"
                ]
            },
            {
                "name": "CE_Category",
                "attributes": [
                    "+categories.id",
                    "+categories.name",
                    "+categories.image_url"
                ]
            }
        ],
        "associations": [
            ("CE_Product", "CE_ProductVariant"),
            ("CE_Product", "CE_ProductImage"),
            ("CE_Product", "CE_Category")
        ]
    },
    {
        "id": "CU14",
        "title": "CU14: Reseñas y favoritos de prendas (Versión ligera)",
        "cycle": "Ciclo 1",
        "package": "catalogo_y_tiendas",
        "actor": "Cliente Autenticado",
        "boundary": {
            "name": "IU_ResenasFavoritos",
            "attributes": [
                "+btn_favorito_corazon",
                "+lbl_promedio_calificacion",
                "+selector_estrellas_1a5",
                "+txt_comentario_resena",
                "+tbl_resenas_prenda",
                "+modal_editar_resena"
            ],
            "methods": [
                "+toggle_favorito(product_id)",
                "+publicar_resena()",
                "+abrir_modal_editar_resena(id)",
                "+guardar_edicion_resena()",
                "+eliminar_resena(id)"
            ]
        },
        "controller": {
            "name": "CTR_ResenasFavoritos",
            "methods": [
                "+alternar_item_favorito(user_id, product_id)",
                "+validar_resena_unica(user_id, product_id)",
                "+crear_resena_ligera(user_id, product_id, rating, comment)",
                "+actualizar_resena(review_id, user_id, rating, comment)",
                "+calcular_rating_promedio(product_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_ProductReview",
                "attributes": [
                    "+product_reviews.id",
                    "+product_reviews.user_id",
                    "+product_reviews.product_id",
                    "+product_reviews.rating",
                    "+product_reviews.comment",
                    "+product_reviews.created_at"
                ]
            },
            {
                "name": "CE_WishlistItem",
                "attributes": [
                    "+wishlist_items.id",
                    "+wishlist_items.user_id",
                    "+wishlist_items.product_id",
                    "+wishlist_items.added_at"
                ]
            },
            {
                "name": "CE_Product",
                "attributes": [
                    "+products.id",
                    "+products.name",
                    "+products.base_price"
                ]
            }
        ],
        "associations": [
            ("CE_ProductReview", "CE_Product"),
            ("CE_WishlistItem", "CE_Product")
        ]
    },
    {
        "id": "CU36",
        "title": "CU36: Consultar bitácora de auditoría del sistema",
        "cycle": "Ciclo 1",
        "package": "seguridad_y_usuarios",
        "actor": "Superadmin",
        "boundary": {
            "name": "IU_BitacoraAuditoria",
            "attributes": [
                "+tbl_registros_auditoria",
                "+dt_rango_fechas",
                "+cmb_filtro_usuario",
                "+cmb_filtro_tabla",
                "+cmb_tipo_accion",
                "+modal_visor_diff_json",
                "+btn_exportar_csv"
            ],
            "methods": [
                "+cargar_eventos_auditoria()",
                "+filtrar_por_criterios()",
                "+ver_detalle_mutacion(log_id)",
                "+exportar_logs_auditoria()"
            ]
        },
        "controller": {
            "name": "CTR_Auditoria",
            "methods": [
                "+consultar_bitacora(filtros, limit, offset)",
                "+obtener_diff_valores(log_id)",
                "+formatear_json_mutacion(old_val, new_val)",
                "+generar_reporte_auditoria(filtros)"
            ]
        },
        "entities": [
            {
                "name": "CE_AuditLog",
                "attributes": [
                    "+audit_logs.id",
                    "+audit_logs.user_id",
                    "+audit_logs.action",
                    "+audit_logs.table_name",
                    "+audit_logs.record_id",
                    "+audit_logs.old_values",
                    "+audit_logs.new_values",
                    "+audit_logs.ip_address",
                    "+audit_logs.created_at"
                ]
            },
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.first_name",
                    "+users.last_name",
                    "+users.email"
                ]
            }
        ],
        "associations": [
            ("CE_AuditLog", "CE_User")
        ]
    },
    {
        "id": "CU37",
        "title": "CU37: Consultar valoración de inventario (CPP)",
        "cycle": "Ciclo 1",
        "package": "inventario_y_proveedores",
        "actor": "Superadmin / Encargado",
        "boundary": {
            "name": "IU_ValoracionInventario",
            "attributes": [
                "+cmb_sucursal_seleccionada",
                "+lbl_capital_total_invertido",
                "+lbl_total_prendas_stock",
                "+tbl_kardex_valorado",
                "+col_costo_promedio_ponderado",
                "+col_valor_total_linea",
                "+btn_exportar_balance_cpp"
            ],
            "methods": [
                "+consultar_balance_sucursal(branch_id)",
                "+filtrar_por_categoria(cat_id)",
                "+ver_kardex_historico_variante(variant_id)",
                "+exportar_reporte_cpp()"
            ]
        },
        "controller": {
            "name": "CTR_ValoracionInventario",
            "methods": [
                "+calcular_capital_invertido_sucursal(branch_id)",
                "+consultar_stock_y_costos_promedio(branch_id)",
                "+obtener_movimientos_kardex_variante(variant_id, branch_id)",
                "+generar_balance_valorado(branch_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.branch_id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.reserved_stock",
                    "+inventory.avg_cost"
                ]
            },
            {
                "name": "CE_InventoryLedger",
                "attributes": [
                    "+inventory_ledger.id",
                    "+inventory_ledger.product_variant_id",
                    "+inventory_ledger.branch_id",
                    "+inventory_ledger.movement_type",
                    "+inventory_ledger.quantity",
                    "+inventory_ledger.unit_cost",
                    "+inventory_ledger.balance_stock",
                    "+inventory_ledger.balance_avg_cost"
                ]
            },
            {
                "name": "CE_Branch",
                "attributes": [
                    "+branches.id",
                    "+branches.name",
                    "+branches.code"
                ]
            }
        ],
        "associations": [
            ("CE_Inventory", "CE_InventoryLedger"),
            ("CE_Inventory", "CE_Branch")
        ]
    },
    {
        "id": "CU38",
        "title": "CU38: Gestionar ajustes de inventario (Mermas y pérdidas)",
        "cycle": "Ciclo 1",
        "package": "inventario_y_proveedores",
        "actor": "Encargado de Sucursal",
        "boundary": {
            "name": "IU_AjustesInventario",
            "attributes": [
                "+cmb_sucursal_activa",
                "+txt_sku_variante",
                "+lbl_stock_actual_sistema",
                "+txt_cantidad_ajuste",
                "+cmb_motivo_merma",
                "+txt_justificacion_observacion",
                "+btn_confirmar_ajuste"
            ],
            "methods": [
                "+buscar_variante_para_ajuste(sku)",
                "+registrar_motivo_merma()",
                "+confirmar_disminucion_stock()",
                "+imprimir_acta_merma()"
            ]
        },
        "controller": {
            "name": "CTR_AjustesInventario",
            "methods": [
                "+validar_existencia_para_merma(branch_id, variant_id, cant)",
                "+asentar_movimiento_kardex_merma(branch_id, variant_id, cant, motivo)",
                "+disminuir_stock_fisico(variant_id, branch_id, cant)",
                "+registrar_auditoria_ajuste(user_id, variant_id, cant)"
            ]
        },
        "entities": [
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.branch_id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.avg_cost"
                ]
            },
            {
                "name": "CE_InventoryLedger",
                "attributes": [
                    "+inventory_ledger.id",
                    "+inventory_ledger.product_variant_id",
                    "+inventory_ledger.branch_id",
                    "+inventory_ledger.movement_type",
                    "+inventory_ledger.quantity",
                    "+inventory_ledger.unit_cost",
                    "+inventory_ledger.notes"
                ]
            },
            {
                "name": "CE_AuditLog",
                "attributes": [
                    "+audit_logs.id",
                    "+audit_logs.user_id",
                    "+audit_logs.action",
                    "+audit_logs.table_name"
                ]
            }
        ],
        "associations": [
            ("CE_Inventory", "CE_InventoryLedger")
        ]
    },

    # =========================================================================
    # CICLO 2: COMERCIAL Y TRANSACCIONAL (13 CASOS DE USO)
    # =========================================================================
    {
        "id": "CU12",
        "title": "CU12: Buscar y filtrar catálogo + disponibilidad por sucursal",
        "cycle": "Ciclo 2",
        "package": "catalogo_y_tiendas",
        "actor": "Cliente / Visitante",
        "boundary": {
            "name": "IU_FiltrosCatalogo",
            "attributes": [
                "+txt_barra_busqueda",
                "+slider_rango_precios",
                "+chk_tallas_disponibles",
                "+swatches_colores_filtro",
                "+cmb_ocasion_uso",
                "+cmb_sucursal_cercana",
                "+lbl_badge_stock_en_tienda",
                "+grilla_resultados_filtrados"
            ],
            "methods": [
                "+ejecutar_busqueda_texto(query)",
                "+aplicar_filtros_combinados()",
                "+seleccionar_sucursal_consulta(branch_id)",
                "+verificar_stock_sucursal(variant_id)",
                "+limpiar_filtros()"
            ]
        },
        "controller": {
            "name": "CTR_BusquedaCatalogo",
            "methods": [
                "+buscar_prendas_por_termino(query, page)",
                "+filtrar_por_atributos(precio_min, precio_max, sizes, colors, occasion)",
                "+consultar_stock_por_sucursal(product_id, branch_id)",
                "+obtener_sucursales_con_existencia(product_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Product",
                "attributes": [
                    "+products.id",
                    "+products.name",
                    "+products.base_price",
                    "+products.compare_at_price",
                    "+products.occasion"
                ]
            },
            {
                "name": "CE_ProductVariant",
                "attributes": [
                    "+product_variants.id",
                    "+product_variants.product_id",
                    "+product_variants.color_id",
                    "+product_variants.size_id",
                    "+product_variants.sku"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.branch_id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.reserved_stock"
                ]
            },
            {
                "name": "CE_Branch",
                "attributes": [
                    "+branches.id",
                    "+branches.name",
                    "+branches.address",
                    "+branches.is_active"
                ]
            }
        ],
        "associations": [
            ("CE_Product", "CE_ProductVariant"),
            ("CE_ProductVariant", "CE_Inventory"),
            ("CE_Inventory", "CE_Branch")
        ]
    },
    {
        "id": "CU13",
        "title": "CU13: Gestionar promociones: cupones y ofertas de temporada",
        "cycle": "Ciclo 2",
        "package": "catalogo_y_tiendas",
        "actor": "Superadmin",
        "boundary": {
            "name": "IU_GestionPromociones",
            "attributes": [
                "+tbl_cupones_activos",
                "+txt_codigo_cupon",
                "+cmb_tipo_descuento",
                "+txt_valor_descuento",
                "+txt_limite_usos",
                "+dt_vigencia_desde",
                "+dt_vigencia_hasta",
                "+tbl_ofertas_temporada"
            ],
            "methods": [
                "+crear_cupon_descuento()",
                "+programar_oferta_temporada()",
                "+activar_desactivar_cupon(id)",
                "+ver_reporte_usos_cupon(id)"
            ]
        },
        "controller": {
            "name": "CTR_Promociones",
            "methods": [
                "+registrar_cupon(codigo, tipo, valor, limites, vigencia)",
                "+validar_codigo_cupon_disponible(code, user_id, subtotal)",
                "+programar_promocion_temporada(categoria_id, porcentaje, rango)",
                "+aplicar_descuento_a_orden(order_id, coupon_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Coupon",
                "attributes": [
                    "+coupons.id",
                    "+coupons.code",
                    "+coupons.discount_type",
                    "+coupons.discount_value",
                    "+coupons.max_uses",
                    "+coupons.used_count",
                    "+coupons.valid_from",
                    "+coupons.valid_until",
                    "+coupons.is_active"
                ]
            },
            {
                "name": "CE_SeasonalPromotion",
                "attributes": [
                    "+seasonal_promotions.id",
                    "+seasonal_promotions.category_id",
                    "+seasonal_promotions.name",
                    "+seasonal_promotions.discount_percent",
                    "+seasonal_promotions.start_date",
                    "+seasonal_promotions.end_date",
                    "+seasonal_promotions.is_active"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU14_EXP",
        "title": "CU14+: Wishlists múltiples/compartibles y reseñas con moderación",
        "cycle": "Ciclo 2",
        "package": "catalogo_y_tiendas",
        "actor": "Cliente / Administrador",
        "boundary": {
            "name": "IU_WishlistResenasAvanzadas",
            "attributes": [
                "+tbl_listas_deseos_usuario",
                "+txt_nombre_nueva_lista",
                "+btn_generar_link_compartir",
                "+tbl_prendas_en_lista",
                "+panel_moderacion_resenas",
                "+btn_aprobar_resena",
                "+btn_rechazar_resena"
            ],
            "methods": [
                "+crear_lista_deseos_personalizada(nombre)",
                "+mover_prenda_a_lista(prod_id, list_id)",
                "+compartir_wishlist_token()",
                "+moderar_resena_cliente(review_id, estado)"
            ]
        },
        "controller": {
            "name": "CTR_WishlistResenasAvanzado",
            "methods": [
                "+crear_wishlist_grupo(user_id, nombre, is_public)",
                "+agregar_prenda_a_wishlist(wishlist_id, product_id)",
                "+generar_token_compartir(wishlist_id)",
                "+consultar_wishlist_por_token(token)",
                "+cambiar_estado_moderacion_resena(review_id, status)"
            ]
        },
        "entities": [
            {
                "name": "CE_Wishlist",
                "attributes": [
                    "+wishlists.id",
                    "+wishlists.user_id",
                    "+wishlists.name",
                    "+wishlists.share_token",
                    "+wishlists.is_public",
                    "+wishlists.created_at"
                ]
            },
            {
                "name": "CE_WishlistGroupItem",
                "attributes": [
                    "+wishlist_group_items.id",
                    "+wishlist_group_items.wishlist_id",
                    "+wishlist_group_items.product_id",
                    "+wishlist_group_items.added_at"
                ]
            },
            {
                "name": "CE_ProductReview",
                "attributes": [
                    "+product_reviews.id",
                    "+product_reviews.user_id",
                    "+product_reviews.product_id",
                    "+product_reviews.rating",
                    "+product_reviews.comment",
                    "+product_reviews.status"
                ]
            }
        ],
        "associations": [
            ("CE_Wishlist", "CE_WishlistGroupItem")
        ]
    },
    {
        "id": "CU15",
        "title": "CU15: Gestionar transferencias de mercadería entre sucursales",
        "cycle": "Ciclo 2",
        "package": "inventario_y_proveedores",
        "actor": "Encargado de Sucursal",
        "boundary": {
            "name": "IU_TransferenciasStock",
            "attributes": [
                "+cmb_sucursal_origen",
                "+cmb_sucursal_destino",
                "+tbl_prendas_a_transferir",
                "+txt_sku_variante",
                "+txt_cantidad_transferir",
                "+lbl_estado_transferencia",
                "+btn_despachar_transferencia",
                "+btn_recibir_y_confirmar"
            ],
            "methods": [
                "+crear_solicitud_transferencia()",
                "+agregar_variante_transferencia(sku, cant)",
                "+despachar_mercaderia(transfer_id)",
                "+confirmar_recepcion_tienda(transfer_id)"
            ]
        },
        "controller": {
            "name": "CTR_TransferenciasStock",
            "methods": [
                "+crear_orden_transferencia(origen_id, destino_id)",
                "+validar_stock_disponible_origen(origen_id, variant_id, cant)",
                "+despachar_transferencia(transfer_id)",
                "+mover_stock_a_transito(variant_id, origen_id, cant)",
                "+completar_transferencia_destino(transfer_id)",
                "+asentar_kardex_transferencia(variant_id, origen, destino, cant)"
            ]
        },
        "entities": [
            {
                "name": "CE_StockTransfer",
                "attributes": [
                    "+stock_transfers.id",
                    "+stock_transfers.origin_branch_id",
                    "+stock_transfers.dest_branch_id",
                    "+stock_transfers.status",
                    "+stock_transfers.requested_at",
                    "+stock_transfers.completed_at"
                ]
            },
            {
                "name": "CE_StockTransferDetail",
                "attributes": [
                    "+stock_transfer_details.id",
                    "+stock_transfer_details.transfer_id",
                    "+stock_transfer_details.product_variant_id",
                    "+stock_transfer_details.quantity",
                    "+stock_transfer_details.unit_cost"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.branch_id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.transit_stock"
                ]
            }
        ],
        "associations": [
            ("CE_StockTransfer", "CE_StockTransferDetail")
        ]
    },
    {
        "id": "CU16",
        "title": "CU16: Configurar y notificar alertas de stock (mínimo/máximo)",
        "cycle": "Ciclo 2",
        "package": "inventario_y_proveedores",
        "actor": "Encargado de Sucursal",
        "boundary": {
            "name": "IU_AlertasStock",
            "attributes": [
                "+tbl_configuracion_umbrales",
                "+txt_sku_variante",
                "+txt_stock_minimo_alerta",
                "+txt_stock_maximo_capacidad",
                "+tbl_alertas_disparadas",
                "+btn_guardar_umbrales"
            ],
            "methods": [
                "+consultar_umbrales_sucursal()",
                "+actualizar_umbral_min_max(variant_id, min, max)",
                "+ver_alertas_stock_critico()"
            ]
        },
        "controller": {
            "name": "CTR_AlertasStock",
            "methods": [
                "+configurar_umbrales(branch_id, variant_id, min, max)",
                "+verificar_niveles_stock(branch_id, variant_id)",
                "+disparar_alerta_quiebre_stock(branch_id, variant_id, stock_actual)",
                "+notificar_encargado_reposicion(branch_id, mensaje)"
            ]
        },
        "entities": [
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.branch_id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.min_stock_alert",
                    "+inventory.max_stock_capacity"
                ]
            },
            {
                "name": "CE_InAppNotification",
                "attributes": [
                    "+in_app_notifications.id",
                    "+in_app_notifications.user_id",
                    "+in_app_notifications.title",
                    "+in_app_notifications.message",
                    "+in_app_notifications.is_read"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU17",
        "title": "CU17: Gestionar carrito de compra digital",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cliente",
        "boundary": {
            "name": "IU_CarritoCompras",
            "attributes": [
                "+drawer_carrito_lateral",
                "+tbl_items_carrito",
                "+lbl_foto_miniatura_prenda",
                "+lbl_talla_color_seleccionado",
                "+txt_cantidad_item",
                "+btn_incrementar_decrementar",
                "+btn_eliminar_item",
                "+lbl_subtotal_carrito",
                "+btn_continuar_checkout"
            ],
            "methods": [
                "+abrir_carrito()",
                "+agregar_item_carrito(variant_id, cant)",
                "+modificar_cantidad(item_id, nueva_cant)",
                "+eliminar_item_carrito(item_id)",
                "+proceder_al_checkout()"
            ]
        },
        "controller": {
            "name": "CTR_CarritoCompras",
            "methods": [
                "+obtener_o_crear_carrito(user_id, session_token)",
                "+validar_stock_para_carrito(variant_id, cant)",
                "+agregar_variante_carrito(cart_id, variant_id, cant)",
                "+actualizar_cantidad_item(item_id, cant)",
                "+remover_item(item_id)",
                "+calcular_subtotal_carrito(cart_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Cart",
                "attributes": [
                    "+carts.id",
                    "+carts.user_id",
                    "+carts.session_token",
                    "+carts.updated_at"
                ]
            },
            {
                "name": "CE_CartItem",
                "attributes": [
                    "+cart_items.id",
                    "+cart_items.cart_id",
                    "+cart_items.product_variant_id",
                    "+cart_items.quantity",
                    "+cart_items.unit_price"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.id",
                    "+inventory.product_variant_id",
                    "+inventory.physical_stock",
                    "+inventory.reserved_stock"
                ]
            }
        ],
        "associations": [
            ("CE_Cart", "CE_CartItem")
        ]
    },
    {
        "id": "CU18",
        "title": "CU18: Procesar venta / checkout con herencia de medios de pago",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cliente",
        "boundary": {
            "name": "IU_CheckoutOnline",
            "attributes": [
                "+tbl_resumen_pedido",
                "+txt_cupon_descuento",
                "+btn_aplicar_cupon",
                "+cmb_metodo_entrega",
                "+radio_medios_pago_sti",
                "+panel_pago_tarjeta",
                "+panel_pago_qr",
                "+panel_pago_paypal",
                "+lbl_total_a_pagar",
                "+btn_confirmar_pedido"
            ],
            "methods": [
                "+iniciar_checkout()",
                "+aplicar_codigo_cupon(codigo)",
                "+seleccionar_medio_pago(tipo_pago)",
                "+procesar_pago_y_confirmar()"
            ]
        },
        "controller": {
            "name": "CTR_CheckoutVenta",
            "methods": [
                "+crear_orden_desde_carrito(cart_id, user_id, delivery_type)",
                "+bloquear_stock_temporal(order_id)",
                "+aplicar_cupon_a_orden(order_id, coupon_code)",
                "+procesar_pago_polimorfico(order_id, payment_data)",
                "+asentar_orden_pagada(order_id)",
                "+descontar_stock_definitivo(order_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.channel",
                    "+orders.status",
                    "+orders.subtotal",
                    "+orders.discount_amount",
                    "+orders.total_amount",
                    "+orders.created_at"
                ]
            },
            {
                "name": "CE_OrderItem",
                "attributes": [
                    "+order_items.id",
                    "+order_items.order_id",
                    "+order_items.product_variant_id",
                    "+order_items.quantity",
                    "+order_items.unit_price"
                ]
            },
            {
                "name": "CE_Payment",
                "attributes": [
                    "+payments.id",
                    "+payments.order_id",
                    "+payments.payment_type",
                    "+payments.amount",
                    "+payments.status",
                    "+payments.transaction_ref"
                ]
            }
        ],
        "associations": [
            ("CE_Order", "CE_OrderItem"),
            ("CE_Order", "CE_Payment")
        ]
    },
    {
        "id": "CU19",
        "title": "CU19: Procesar venta presencial en caja (POS)",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cajero",
        "boundary": {
            "name": "IU_PuntoDeVentaPOS",
            "attributes": [
                "+lbl_sesion_caja_activa",
                "+txt_sku_scanner",
                "+tbl_grilla_articulos",
                "+txt_cantidad_articulo",
                "+lbl_subtotal_venta",
                "+txt_cliente_nit_ci",
                "+txt_cliente_nombre",
                "+cmb_tipo_pago",
                "+txt_monto_recibido",
                "+lbl_cambio_vuelto",
                "+lbl_total_cobrar"
            ],
            "methods": [
                "+escanear_sku()",
                "+eliminar_item_grilla()",
                "+abrir_modal_cobro()",
                "+confirmar_venta_pos()",
                "+imprimir_ticket_fiscal()",
                "+limpiar_pantalla()"
            ]
        },
        "controller": {
            "name": "CTR_POS",
            "methods": [
                "+buscar_variante_y_stock(branch_id, sku)",
                "+procesar_venta_pos(session_id, payload)",
                "+validar_sesion_cajero_abierta(session_id)",
                "+descontar_inventario_inmediato(branch_id, items)",
                "+asentar_libro_mayor(branch_id, order_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_CashShift",
                "attributes": [
                    "+cash_shifts.id",
                    "+cash_shifts.cashier_id",
                    "+cash_shifts.branch_id",
                    "+cash_shifts.status"
                ]
            },
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.branch_id",
                    "+orders.channel",
                    "+orders.status",
                    "+orders.total_amount",
                    "+orders.cash_shift_id",
                    "+orders.created_at"
                ]
            },
            {
                "name": "CE_OrderItem",
                "attributes": [
                    "+order_items.id",
                    "+order_items.order_id",
                    "+order_items.product_variant_id",
                    "+order_items.quantity",
                    "+order_items.unit_price"
                ]
            },
            {
                "name": "CE_Invoice",
                "attributes": [
                    "+invoices.id",
                    "+invoices.order_id",
                    "+invoices.doc_type",
                    "+invoices.total",
                    "+invoices.control_code",
                    "+invoices.customer_nit",
                    "+invoices.customer_name"
                ]
            }
        ],
        "associations": [
            ("CE_Order", "CE_OrderItem"),
            ("CE_Order", "CE_Invoice"),
            ("CE_Order", "CE_CashShift")
        ]
    },
    {
        "id": "CU20",
        "title": "CU20: Emitir factura y nota de entrega (IVA 13%)",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Sistema / CTR_Ventas",
        "boundary": {
            "name": "IU_VisorComprobantes",
            "attributes": [
                "+lbl_tipo_documento",
                "+lbl_numero_autorizacion_sin",
                "+lbl_codigo_control",
                "+img_codigo_qr_fiscal",
                "+tbl_lineas_tributarias",
                "+lbl_monto_iva_13",
                "+lbl_literal_bolivianos",
                "+canvas_visor_pdf"
            ],
            "methods": [
                "+descargar_pdf()",
                "+imprimir_documento()",
                "+enviar_correo()"
            ]
        },
        "controller": {
            "name": "CTR_Facturacion",
            "methods": [
                "+solicitar_emision(order_id, nit, razon)",
                "+consultar_monto_orden(order_id)",
                "+calcular_valores_fiscales(total, tax_rate)",
                "+generar_codigo_control_v7(nit, no_fac, aut, fecha, total, llave)",
                "+generar_cadena_qr_tributaria(invoice)",
                "+insertar_comprobante_fiscal(invoice_data)"
            ]
        },
        "entities": [
            {
                "name": "CE_Invoice",
                "attributes": [
                    "+invoices.id",
                    "+invoices.order_id",
                    "+invoices.doc_type",
                    "+invoices.tax_rate",
                    "+invoices.subtotal",
                    "+invoices.tax_amount",
                    "+invoices.total",
                    "+invoices.control_code",
                    "+invoices.customer_nit",
                    "+invoices.customer_name",
                    "+invoices.issued_at"
                ]
            },
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.branch_id",
                    "+orders.status",
                    "+orders.created_at"
                ]
            }
        ],
        "associations": [
            ("CE_Invoice", "CE_Order")
        ]
    },
    {
        "id": "CU21",
        "title": "CU21: Generar cotización formal",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cajero / Cliente",
        "boundary": {
            "name": "IU_GenerarCotizacion",
            "attributes": [
                "+txt_cliente_nombre",
                "+txt_cliente_nit_ci",
                "+txt_cliente_email",
                "+tbl_prendas_cotizadas",
                "+lbl_subtotal_cotizado",
                "+lbl_vigencia_dias_garantizada",
                "+btn_generar_cotizacion_pdf"
            ],
            "methods": [
                "+iniciar_cotizacion()",
                "+agregar_prenda_cotizada(sku, cant)",
                "+calcular_totales_cotizacion()",
                "+emitir_cotizacion_formal()",
                "+descargar_cotizacion_pdf()"
            ]
        },
        "controller": {
            "name": "CTR_Cotizaciones",
            "methods": [
                "+crear_cotizacion(cliente_datos, vigencia_dias)",
                "+agregar_linea_cotizacion(quotation_id, variant_id, cant)",
                "+calcular_total_garantizado(quotation_id)",
                "+generar_token_descarga_cotizacion(quotation_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Quotation",
                "attributes": [
                    "+quotations.id",
                    "+quotations.user_id",
                    "+quotations.total_amount",
                    "+quotations.valid_until",
                    "+quotations.status",
                    "+quotations.created_at"
                ]
            },
            {
                "name": "CE_QuotationItem",
                "attributes": [
                    "+quotation_items.id",
                    "+quotation_items.quotation_id",
                    "+quotation_items.product_variant_id",
                    "+quotation_items.quantity",
                    "+quotation_items.unit_price"
                ]
            }
        ],
        "associations": [
            ("CE_Quotation", "CE_QuotationItem")
        ]
    },
    {
        "id": "CU22",
        "title": "CU22: Gestionar devoluciones y cambios de prendas",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cajero",
        "boundary": {
            "name": "IU_Devoluciones",
            "attributes": [
                "+txt_buscar_orden_id",
                "+lbl_datos_orden_original",
                "+tbl_prendas_orden",
                "+cmb_tipo_operacion",
                "+cmb_motivo",
                "+cmb_variante_reemplazo_id",
                "+txt_cantidad",
                "+cmb_destino_stock",
                "+lbl_monto_reembolso"
            ],
            "methods": [
                "+buscar_orden()",
                "+seleccionar_item_devolver()",
                "+procesar_operacion()",
                "+imprimir_comprobante()"
            ]
        },
        "controller": {
            "name": "CTR_Devoluciones",
            "methods": [
                "+consultar_orden_y_prendas(order_id)",
                "+verificar_regla_garantia_30_dias(order_date)",
                "+registrar_operacion_devolucion(payload, cashier_id)",
                "+reintegrar_stock_o_merma(branch_id, variant_id)",
                "+asentar_kardex_devolucion(branch_id, variant_id)",
                "+descontar_efectivo_sesion_caja(cashier_id, refund)"
            ]
        },
        "entities": [
            {
                "name": "CE_CashShift",
                "attributes": [
                    "+cash_shifts.id",
                    "+cash_shifts.cashier_id",
                    "+cash_shifts.difference",
                    "+cash_shifts.status"
                ]
            },
            {
                "name": "CE_OrderReturn",
                "attributes": [
                    "+order_returns.id",
                    "+order_returns.return_number",
                    "+order_returns.order_id",
                    "+order_returns.processed_by_id",
                    "+order_returns.return_type",
                    "+order_returns.reason",
                    "+order_returns.refund_amount",
                    "+order_returns.status",
                    "+order_returns.created_at"
                ]
            },
            {
                "name": "CE_OrderReturnItem",
                "attributes": [
                    "+order_return_items.id",
                    "+order_return_items.return_id",
                    "+order_return_items.variant_id",
                    "+order_return_items.quantity",
                    "+order_return_items.replacement_variant_id"
                ]
            },
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.total_amount",
                    "+orders.created_at"
                ]
            }
        ],
        "associations": [
            ("CE_OrderReturn", "CE_OrderReturnItem"),
            ("CE_OrderReturn", "CE_Order")
        ]
    },
    {
        "id": "CU23",
        "title": "CU23: Gestionar arqueo de caja (Apertura y cierre)",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cajero",
        "boundary": {
            "name": "IU_ArqueoCaja",
            "attributes": [
                "+lbl_estado_turno",
                "+lbl_cajero_nombre",
                "+txt_monto_inicial_efectivo",
                "+txt_monto_declarado_ciego",
                "+lbl_monto_sistema_calculado",
                "+lbl_diferencia_sobrante_faltante",
                "+txt_observaciones_cierre",
                "+tbl_resumen_medios_pago"
            ],
            "methods": [
                "+abrir_turno_caja()",
                "+registrar_cierre_ciego()",
                "+imprimir_reporte_arqueo()",
                "+firmar_arqueo()"
            ]
        },
        "controller": {
            "name": "CTR_Arqueo",
            "methods": [
                "+abrir_sesion_caja(cashier_id, branch_id, amount)",
                "+verificar_sin_sesion_previa(cashier_id)",
                "+cerrar_turno_caja(shift_id, declared_amount, notes)",
                "+calcular_total_ventas_efectivo(shift_id)",
                "+calcular_total_devoluciones_efectivo(shift_id)",
                "+calcular_diferencia_caja(sistema, declarado)"
            ]
        },
        "entities": [
            {
                "name": "CE_OrderReturn",
                "attributes": [
                    "+order_returns.id",
                    "+order_returns.order_id",
                    "+order_returns.refund_amount",
                    "+order_returns.status"
                ]
            },
            {
                "name": "CE_CashShift",
                "attributes": [
                    "+cash_shifts.id",
                    "+cash_shifts.cashier_id",
                    "+cash_shifts.branch_id",
                    "+cash_shifts.opening_amount",
                    "+cash_shifts.closing_amount_declared",
                    "+cash_shifts.closing_amount_system",
                    "+cash_shifts.difference",
                    "+cash_shifts.status",
                    "+cash_shifts.opened_at",
                    "+cash_shifts.closed_at",
                    "+cash_shifts.notes"
                ]
            },
            {
                "name": "CE_Payment",
                "attributes": [
                    "+payments.id",
                    "+payments.order_id",
                    "+payments.payment_type",
                    "+payments.amount",
                    "+payments.status",
                    "+payments.cash_received",
                    "+payments.cash_change"
                ]
            }
        ],
        "associations": [
            ("CE_CashShift", "CE_Payment")
        ]
    },
    {
        "id": "CU24",
        "title": "CU24: Consultar historial de compras (Cliente)",
        "cycle": "Ciclo 2",
        "package": "ventas_y_pagos",
        "actor": "Cliente",
        "boundary": {
            "name": "IU_HistorialCompras",
            "attributes": [
                "+lbl_nombre_cliente",
                "+tbl_listado_pedidos",
                "+cmb_filtro_estado",
                "+dt_filtro_fechas",
                "+modal_detalle_pedido",
                "+lbl_numero_orden",
                "+tbl_prendas_adquiridas",
                "+lbl_medio_pago",
                "+lbl_total_pagado",
                "+link_descarga_factura_url"
            ],
            "methods": [
                "+abrir_mis_compras()",
                "+ver_detalle_pedido(id)",
                "+descargar_factura_pdf(id)",
                "+solicitar_devolucion(id)",
                "+cerrar_modal()"
            ]
        },
        "controller": {
            "name": "CTR_Historial",
            "methods": [
                "+consultar_historial(user_id, limit, offset)",
                "+consultar_detalle_pedido(order_id, user_id)",
                "+obtener_factura_asociada(order_id)",
                "+verificar_pertenencia(order_id, user_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.branch_id",
                    "+orders.channel",
                    "+orders.status",
                    "+orders.subtotal",
                    "+orders.discount_amount",
                    "+orders.total_amount",
                    "+orders.created_at"
                ]
            },
            {
                "name": "CE_OrderItem",
                "attributes": [
                    "+order_items.id",
                    "+order_items.order_id",
                    "+order_items.variant_id",
                    "+order_items.quantity",
                    "+order_items.unit_price"
                ]
            },
            {
                "name": "CE_Payment",
                "attributes": [
                    "+payments.id",
                    "+payments.order_id",
                    "+payments.payment_type",
                    "+payments.amount",
                    "+payments.status"
                ]
            },
            {
                "name": "CE_Invoice",
                "attributes": [
                    "+invoices.id",
                    "+invoices.order_id",
                    "+invoices.doc_type",
                    "+invoices.total",
                    "+invoices.control_code",
                    "+invoices.issued_at"
                ]
            }
        ],
        "associations": [
            ("CE_Order", "CE_OrderItem"),
            ("CE_Order", "CE_Payment"),
            ("CE_Order", "CE_Invoice")
        ]
    },

    # =========================================================================
    # CICLO 3: OMNICANAL, LOGÍSTICA E IA (13 CASOS DE USO)
    # =========================================================================
    {
        "id": "CU25",
        "title": "CU25: Convertir una reserva en venta confirmada (POS)",
        "cycle": "Ciclo 3",
        "package": "ventas_y_pagos",
        "actor": "Cajero",
        "boundary": {
            "name": "IU_ConversionReservaVenta",
            "attributes": [
                "+txt_codigo_reserva_scanner",
                "+lbl_datos_cliente_cita",
                "+tbl_prendas_apartadas",
                "+chk_prendas_aprobadas_cliente",
                "+lbl_monto_sena_50_descontar",
                "+lbl_saldo_pendiente_cobrar",
                "+btn_cobrar_saldo_y_facturar"
            ],
            "methods": [
                "+escanear_codigo_reserva(cod)",
                "+marcar_prendas_compradas()",
                "+descontar_sena_previa()",
                "+completar_venta_pos_reserva()",
                "+liberar_stock_prendas_rechazadas()"
            ]
        },
        "controller": {
            "name": "CTR_ConversionReserva",
            "methods": [
                "+consultar_reserva_por_codigo(code)",
                "+validar_estado_reserva_vigente(res_id)",
                "+crear_orden_desde_reserva(res_id, items_comprados)",
                "+aplicar_descuento_sena(order_id, deposit_amount)",
                "+cambiar_estado_reserva(res_id, 'COMPLETADA')",
                "+desbloquear_stock_items_no_comprados(res_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Reservation",
                "attributes": [
                    "+reservations.id",
                    "+reservations.customer_id",
                    "+reservations.branch_id",
                    "+reservations.reservation_code",
                    "+reservations.deposit_amount",
                    "+reservations.status",
                    "+reservations.appointment_date",
                    "+reservations.appointment_time"
                ]
            },
            {
                "name": "CE_ReservationItem",
                "attributes": [
                    "+reservation_items.id",
                    "+reservation_items.reservation_id",
                    "+reservation_items.variant_id",
                    "+reservation_items.quantity",
                    "+reservation_items.unit_price"
                ]
            },
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.branch_id",
                    "+orders.total_amount",
                    "+orders.status"
                ]
            }
        ],
        "associations": [
            ("CE_Reservation", "CE_ReservationItem"),
            ("CE_Reservation", "CE_Order")
        ]
    },
    {
        "id": "CU26",
        "title": "CU26: Agendar reserva de prendas para prueba física",
        "cycle": "Ciclo 3",
        "package": "reservas_y_citas",
        "actor": "Cliente (Móvil)",
        "boundary": {
            "name": "IU_AgendarCitaProbador",
            "attributes": [
                "+cmb_sucursal_cita",
                "+calendar_selector_fecha",
                "+grid_horarios_disponibles",
                "+tbl_prendas_a_probar_max5",
                "+lbl_monto_sena_50_porciento",
                "+panel_pago_sena_qr_tarjeta",
                "+btn_confirmar_reserva_cita"
            ],
            "methods": [
                "+seleccionar_sucursal(branch_id)",
                "+consultar_horarios_libres(fecha)",
                "+agregar_prenda_reserva(variant_id)",
                "+procesar_pago_sena()",
                "+generar_comprobante_reserva()"
            ]
        },
        "controller": {
            "name": "CTR_AgendamientoReservas",
            "methods": [
                "+consultar_probadores_disponibles(branch_id, fecha)",
                "+validar_limite_maximo_5_prendas(items_count)",
                "+bloquear_stock_para_reserva(branch_id, variant_id)",
                "+registrar_pago_sena_50(user_id, amount)",
                "+crear_reserva_cita(user_id, branch_id, fecha, slot)",
                "+generar_codigo_reserva_unico()"
            ]
        },
        "entities": [
            {
                "name": "CE_Reservation",
                "attributes": [
                    "+reservations.id",
                    "+reservations.customer_id",
                    "+reservations.branch_id",
                    "+reservations.reservation_code",
                    "+reservations.deposit_amount",
                    "+reservations.status",
                    "+reservations.appointment_date",
                    "+reservations.appointment_time",
                    "+reservations.expires_at"
                ]
            },
            {
                "name": "CE_ReservationItem",
                "attributes": [
                    "+reservation_items.id",
                    "+reservation_items.reservation_id",
                    "+reservation_items.variant_id",
                    "+reservation_items.quantity",
                    "+reservation_items.unit_price"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.branch_id",
                    "+inventory.variant_id",
                    "+inventory.stock_actual",
                    "+inventory.stock_reservado"
                ]
            }
        ],
        "associations": [
            ("CE_Reservation", "CE_ReservationItem")
        ]
    },
    {
        "id": "CU27",
        "title": "CU27: Gestionar bandeja de reservas entrantes de sucursal",
        "cycle": "Ciclo 3",
        "package": "reservas_y_citas",
        "actor": "Personal de Sucursal",
        "boundary": {
            "name": "IU_BandejaReservasTienda",
            "attributes": [
                "+tbl_citas_del_dia",
                "+lbl_contador_citas_pendientes",
                "+badge_estado_cita",
                "+modal_checklist_separacion",
                "+btn_marcar_prendas_listas",
                "+btn_marcar_asistencia_cliente",
                "+btn_marcar_no_show_inasistencia"
            ],
            "methods": [
                "+cargar_citas_programadas()",
                "+ver_detalle_prendas_separar(res_id)",
                "+confirmar_prendas_en_probador(res_id)",
                "+registrar_llegada_cliente(res_id)",
                "+cancelar_por_inasistencia_30min(res_id)"
            ]
        },
        "controller": {
            "name": "CTR_BandejaReservas",
            "methods": [
                "+obtener_citas_sucursal(branch_id, fecha)",
                "+cambiar_estado_reserva(res_id, 'LISTA_EN_PROBADOR')",
                "+registrar_asistencia_cita(res_id)",
                "+ejecutar_no_show_vencida(res_id)",
                "+liberar_stock_reservado(res_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Reservation",
                "attributes": [
                    "+reservations.id",
                    "+reservations.customer_id",
                    "+reservations.branch_id",
                    "+reservations.reservation_code",
                    "+reservations.status",
                    "+reservations.appointment_date",
                    "+reservations.appointment_time"
                ]
            },
            {
                "name": "CE_ReservationItem",
                "attributes": [
                    "+reservation_items.id",
                    "+reservation_items.reservation_id",
                    "+reservation_items.variant_id",
                    "+reservation_items.quantity"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.branch_id",
                    "+inventory.variant_id",
                    "+inventory.stock_reservado"
                ]
            }
        ],
        "associations": [
            ("CE_Reservation", "CE_ReservationItem")
        ]
    },
    {
        "id": "CU28",
        "title": "CU28: Cancelar reserva de prendas (Libera stock)",
        "cycle": "Ciclo 3",
        "package": "reservas_y_citas",
        "actor": "Cliente / Encargado",
        "boundary": {
            "name": "IU_CancelarReserva",
            "attributes": [
                "+card_datos_reserva_activa",
                "+lbl_politica_cancelacion_aviso",
                "+cmb_motivo_cancelacion",
                "+txt_observacion_motivo",
                "+btn_confirmar_cancelacion"
            ],
            "methods": [
                "+solicitar_cancelacion_cita()",
                "+validar_plazo_minimo_2_horas()",
                "+confirmar_anulacion()",
                "+ver_constancia_anulacion()"
            ]
        },
        "controller": {
            "name": "CTR_CancelacionReserva",
            "methods": [
                "+verificar_tiempo_cancelacion(res_id, 2_horas)",
                "+anular_reserva(res_id, motivo)",
                "+desbloquear_stock_inventario(branch_id, items)",
                "+procesar_reembolso_o_retencion_sena(res_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Reservation",
                "attributes": [
                    "+reservations.id",
                    "+reservations.customer_id",
                    "+reservations.branch_id",
                    "+reservations.status",
                    "+reservations.deposit_amount"
                ]
            },
            {
                "name": "CE_ReservationItem",
                "attributes": [
                    "+reservation_items.id",
                    "+reservation_items.reservation_id",
                    "+reservation_items.variant_id",
                    "+reservation_items.quantity"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.branch_id",
                    "+inventory.variant_id",
                    "+inventory.stock_reservado"
                ]
            }
        ],
        "associations": [
            ("CE_Reservation", "CE_ReservationItem")
        ]
    },
    {
        "id": "CU29",
        "title": "CU29: Gestionar envíos y logística de despacho (Delivery)",
        "cycle": "Ciclo 3",
        "package": "envios_y_logistica",
        "actor": "Encargado de Despacho / Repartidor",
        "boundary": {
            "name": "IU_DespachoEnvios",
            "attributes": [
                "+tbl_pedidos_listos_despacho",
                "+cmb_repartidor_asignado",
                "+lbl_direccion_destino_gps",
                "+txt_codigo_tracking",
                "+btn_asignar_hoja_ruta",
                "+btn_iniciar_recorrido_repartidor",
                "+uploader_foto_entrega_evidencia"
            ],
            "methods": [
                "+listar_pedidos_por_despachar()",
                "+asignar_pedido_repartidor(order_id, rep_id)",
                "+iniciar_ruta_entrega(shipment_id)",
                "+adjuntar_foto_comprobante_entrega()",
                "+confirmar_entrega_final(shipment_id)"
            ]
        },
        "controller": {
            "name": "CTR_DespachoEnvios",
            "methods": [
                "+crear_envio_despacho(order_id, delivery_person_id)",
                "+generar_codigo_tracking_unico()",
                "+actualizar_estado_envio(shipment_id, 'EN_CAMINO')",
                "+registrar_evento_tracking(shipment_id, estado, coords)",
                "+completar_entrega_con_foto(shipment_id, foto_url)"
            ]
        },
        "entities": [
            {
                "name": "CE_Shipment",
                "attributes": [
                    "+shipments.id",
                    "+shipments.order_id",
                    "+shipments.delivery_person_id",
                    "+shipments.tracking_number",
                    "+shipments.status",
                    "+shipments.shipping_cost",
                    "+shipments.delivered_at"
                ]
            },
            {
                "name": "CE_DeliveryPerson",
                "attributes": [
                    "+delivery_persons.id",
                    "+delivery_persons.user_id",
                    "+delivery_persons.vehicle_type",
                    "+delivery_persons.vehicle_plate",
                    "+delivery_persons.phone",
                    "+delivery_persons.is_available"
                ]
            },
            {
                "name": "CE_ShipmentTrackingEvent",
                "attributes": [
                    "+shipment_tracking_events.id",
                    "+shipment_tracking_events.shipment_id",
                    "+shipment_tracking_events.status",
                    "+shipment_tracking_events.photo_url",
                    "+shipment_tracking_events.created_at"
                ]
            }
        ],
        "associations": [
            ("CE_Shipment", "CE_DeliveryPerson"),
            ("CE_Shipment", "CE_ShipmentTrackingEvent")
        ]
    },
    {
        "id": "CU30",
        "title": "CU30: Consultar y rastrear estado de un pedido o envío",
        "cycle": "Ciclo 3",
        "package": "envios_y_logistica",
        "actor": "Cliente",
        "boundary": {
            "name": "IU_TrackingEnvio",
            "attributes": [
                "+txt_buscar_numero_tracking",
                "+timeline_estados_hitos",
                "+lbl_repartidor_nombre_telefono",
                "+mapa_posicion_en_tiempo_real",
                "+img_foto_entrega_comprobante",
                "+badge_estado_actual"
            ],
            "methods": [
                "+ingresar_codigo_tracking(code)",
                "+consultar_hitos_recorrido()",
                "+ver_ubicacion_repartidor_mapa()",
                "+descargar_comprobante_entrega()"
            ]
        },
        "controller": {
            "name": "CTR_TrackingEnvio",
            "methods": [
                "+consultar_envio_por_tracking(code)",
                "+obtener_linea_tiempo_eventos(shipment_id)",
                "+obtener_geoposicion_repartidor(delivery_person_id)",
                "+verificar_pertenencia_o_token(shipment_id, user_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_Shipment",
                "attributes": [
                    "+shipments.id",
                    "+shipments.order_id",
                    "+shipments.tracking_number",
                    "+shipments.status",
                    "+shipments.recipient_name",
                    "+shipments.delivery_address"
                ]
            },
            {
                "name": "CE_ShipmentTrackingEvent",
                "attributes": [
                    "+shipment_tracking_events.id",
                    "+shipment_tracking_events.shipment_id",
                    "+shipment_tracking_events.status",
                    "+shipment_tracking_events.location",
                    "+shipment_tracking_events.description",
                    "+shipment_tracking_events.photo_url"
                ]
            },
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.user_id",
                    "+orders.total_amount",
                    "+orders.status"
                ]
            }
        ],
        "associations": [
            ("CE_Shipment", "CE_ShipmentTrackingEvent"),
            ("CE_Shipment", "CE_Order")
        ]
    },
    {
        "id": "CU31",
        "title": "CU31: Gestionar zonas de cobertura y tarifas de envío",
        "cycle": "Ciclo 3",
        "package": "envios_y_logistica",
        "actor": "Superadmin",
        "boundary": {
            "name": "IU_ZonasTarifasEnvio",
            "attributes": [
                "+tbl_zonas_cobertura",
                "+txt_nombre_zona",
                "+txt_radio_kilometros_anillo",
                "+txt_tarifa_base_envio",
                "+txt_tarifa_por_km_adicional",
                "+mapa_poligonos_zonas_gps",
                "+btn_guardar_zona"
            ],
            "methods": [
                "+listar_zonas_cobertura()",
                "+dibujar_anillo_cobertura(km, centro)",
                "+actualizar_tarifas(zona_id, base, km)",
                "+calcular_costo_envio_simulado(lat, lng)"
            ]
        },
        "controller": {
            "name": "CTR_ZonasTarifas",
            "methods": [
                "+crear_zona_cobertura(nombre, radio_km, tarifa_base)",
                "+calcular_tarifa_por_coordenadas(lat, lng, branch_id)",
                "+validar_direccion_dentro_cobertura(lat, lng)",
                "+actualizar_esquema_tarifario(zone_id, datos)"
            ]
        },
        "entities": [
            {
                "name": "CE_DeliveryZone",
                "attributes": [
                    "+delivery_zones.id",
                    "+delivery_zones.name",
                    "+delivery_zones.city",
                    "+delivery_zones.min_distance_km",
                    "+delivery_zones.max_distance_km",
                    "+delivery_zones.base_rate",
                    "+delivery_zones.estimated_hours",
                    "+delivery_zones.is_active"
                ]
            },
            {
                "name": "CE_Branch",
                "attributes": [
                    "+branches.id",
                    "+branches.name",
                    "+branches.latitude",
                    "+branches.longitude"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU32",
        "title": "CU32: Prueba en Vestidor Virtual (RA / VTON) y guardar capturas",
        "cycle": "Ciclo 3",
        "package": "inteligente_y_analitica",
        "actor": "Cliente (Móvil / Web)",
        "boundary": {
            "name": "IU_VestidorVirtual",
            "attributes": [
                "+canvas_camara_video_vivo",
                "+uploader_foto_cuerpo_entero",
                "+carousel_prendas_catalogo_3d",
                "+btn_probar_prenda_ia",
                "+lbl_indicador_ajuste_calce",
                "+visor_captura_fotorrealista",
                "+btn_guardar_en_galeria",
                "+btn_compartir_redes"
            ],
            "methods": [
                "+iniciar_camara_o_subir_foto()",
                "+seleccionar_prenda_para_prueba(prod_id)",
                "+procesar_simulacion_tryon()",
                "+guardar_captura_generada()",
                "+descargar_foto_render()"
            ]
        },
        "controller": {
            "name": "CTR_VestidorVirtual",
            "methods": [
                "+iniciar_sesion_tryon(user_id, source)",
                "+extraer_puntos_pose_mediapipe(imagen_o_frame)",
                "+generar_mascara_agnostica_anatomica(cuerpo, prenda_tipo)",
                "+ejecutar_deformacion_gmm(prenda_img, pose)",
                "+generar_fusion_tom_fashn(cuerpo_img, prenda_deformada)",
                "+almacenar_captura_resultado(session_id, imagen_url, metricas)"
            ]
        },
        "entities": [
            {
                "name": "CE_VirtualTryonSession",
                "attributes": [
                    "+virtual_tryon_sessions.id",
                    "+virtual_tryon_sessions.user_id",
                    "+virtual_tryon_sessions.session_token",
                    "+virtual_tryon_sessions.channel",
                    "+virtual_tryon_sessions.status",
                    "+virtual_tryon_sessions.started_at"
                ]
            },
            {
                "name": "CE_VirtualTryonItem",
                "attributes": [
                    "+virtual_tryon_items.id",
                    "+virtual_tryon_items.session_id",
                    "+virtual_tryon_items.product_id",
                    "+virtual_tryon_items.variant_id",
                    "+virtual_tryon_items.tested_size",
                    "+virtual_tryon_items.fit_feedback"
                ]
            },
            {
                "name": "CE_VirtualTryonCapture",
                "attributes": [
                    "+virtual_tryon_captures.id",
                    "+virtual_tryon_captures.session_id",
                    "+virtual_tryon_captures.user_id",
                    "+virtual_tryon_captures.product_id",
                    "+virtual_tryon_captures.photo_url",
                    "+virtual_tryon_captures.generation_model"
                ]
            }
        ],
        "associations": [
            ("CE_VirtualTryonSession", "CE_VirtualTryonItem"),
            ("CE_VirtualTryonSession", "CE_VirtualTryonCapture")
        ]
    },
    {
        "id": "CU33",
        "title": "CU33: Asistente inteligente de recomendaciones y Chatbot",
        "cycle": "Ciclo 3",
        "package": "inteligente_y_analitica",
        "actor": "Cliente",
        "boundary": {
            "name": "IU_ChatbotAsistente",
            "attributes": [
                "+floating_widget_chat",
                "+area_mensajes_conversacion",
                "+txt_mensaje_entrada",
                "+btn_enviar_mensaje",
                "+cards_prendas_sugeridas",
                "+btn_consultar_talla_ideal"
            ],
            "methods": [
                "+abrir_chat_asistente()",
                "+enviar_mensaje_texto(msg)",
                "+solicitar_recomendacion_look(ocasion)",
                "+calcular_talla_sugerida(medidas)"
            ]
        },
        "controller": {
            "name": "CTR_ChatbotRecomendador",
            "methods": [
                "+analizar_intencion_mensaje(user_text)",
                "+generar_respuesta_asistente(intent, context)",
                "+recomendar_prendas_similares(user_id, preferencias)",
                "+predecir_talla_optima(altura, peso, medidas)",
                "+persistir_mensaje_conversacion(user_id, rol, mensaje)"
            ]
        },
        "entities": [
            {
                "name": "CE_ChatbotConversation",
                "attributes": [
                    "+chatbot_conversations.id",
                    "+chatbot_conversations.user_id",
                    "+chatbot_conversations.session_token",
                    "+chatbot_conversations.sender",
                    "+chatbot_conversations.message",
                    "+chatbot_conversations.intent",
                    "+chatbot_conversations.metadata_json",
                    "+chatbot_conversations.created_at"
                ]
            },
            {
                "name": "CE_Product",
                "attributes": [
                    "+products.id",
                    "+products.name",
                    "+products.base_price",
                    "+products.category_id"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU34",
        "title": "CU34: Búsqueda de prendas mediante comandos de voz (NLP)",
        "cycle": "Ciclo 3",
        "package": "inteligente_y_analitica",
        "actor": "Cliente (Móvil)",
        "boundary": {
            "name": "IU_BusquedaPorVoz",
            "attributes": [
                "+btn_microfono_pulsar_hablar",
                "+onda_visual_audio_activa",
                "+lbl_texto_reconocido_stt",
                "+lbl_intencion_extraida",
                "+grilla_resultados_voz"
            ],
            "methods": [
                "+iniciar_grabacion_voz()",
                "+detener_grabacion()",
                "+procesar_audio_a_texto()",
                "+aplicar_filtro_por_voz(texto_nlp)"
            ]
        },
        "controller": {
            "name": "CTR_VozNLP",
            "methods": [
                "+convertir_audio_a_texto_whisper(audio_bytes)",
                "+extraer_entidades_moda(texto: color, talla, prenda)",
                "+construir_consulta_catalogo(entidades_nlp)",
                "+retornar_prendas_coincidentes(criterios)"
            ]
        },
        "entities": [
            {
                "name": "CE_Product",
                "attributes": [
                    "+products.id",
                    "+products.name",
                    "+products.base_price",
                    "+products.category_id"
                ]
            },
            {
                "name": "CE_Color",
                "attributes": [
                    "+colors.id",
                    "+colors.name",
                    "+colors.hex_code"
                ]
            },
            {
                "name": "CE_Size",
                "attributes": [
                    "+sizes.id",
                    "+sizes.name"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU35",
        "title": "CU35: Generar reportes gerenciales (PDF / CSV / Voz)",
        "cycle": "Ciclo 3",
        "package": "inteligente_y_analitica",
        "actor": "Superadmin / Gerente",
        "boundary": {
            "name": "IU_ReportesGerenciales",
            "attributes": [
                "+cmb_tipo_reporte",
                "+dt_periodo_fechas",
                "+cmb_sucursal_reporte",
                "+tbl_previsualizacion_datos",
                "+btn_exportar_pdf",
                "+btn_exportar_csv",
                "+btn_comando_voz_reporte"
            ],
            "methods": [
                "+seleccionar_tipo_reporte()",
                "+generar_vista_previa()",
                "+exportar_documento_pdf()",
                "+exportar_archivo_csv()",
                "+solicitar_reporte_por_voz()"
            ]
        },
        "controller": {
            "name": "CTR_ReportesGerenciales",
            "methods": [
                "+obtener_kardex_general(fecha_ini, fecha_fin)",
                "+obtener_ranking_prendas_mas_vendidas(top_n)",
                "+obtener_ingresos_por_sucursal(periodo)",
                "+obtener_rendimiento_cajeros(branch_id)",
                "+compilar_reporte_pdf(datos, plantilla)",
                "+generar_csv_stream(datos)"
            ]
        },
        "entities": [
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.branch_id",
                    "+orders.total_amount",
                    "+orders.status",
                    "+orders.created_at"
                ]
            },
            {
                "name": "CE_OrderItem",
                "attributes": [
                    "+order_items.id",
                    "+order_items.order_id",
                    "+order_items.variant_id",
                    "+order_items.quantity",
                    "+order_items.unit_price"
                ]
            },
            {
                "name": "CE_InventoryLedger",
                "attributes": [
                    "+inventory_ledger.id",
                    "+inventory_ledger.branch_id",
                    "+inventory_ledger.variant_id",
                    "+inventory_ledger.movement_type",
                    "+inventory_ledger.quantity",
                    "+inventory_ledger.unit_cost"
                ]
            }
        ],
        "associations": [
            ("CE_Order", "CE_OrderItem")
        ]
    },
    {
        "id": "CU39",
        "title": "CU39: Consultar Dashboard global de ventas e inventario",
        "cycle": "Ciclo 3",
        "package": "inteligente_y_analitica",
        "actor": "Superadmin / Gerente",
        "boundary": {
            "name": "IU_DashboardGlobal",
            "attributes": [
                "+card_kpi_ventas_totales",
                "+card_kpi_pedidos_hoy",
                "+card_kpi_capital_inventario_cpp",
                "+card_kpi_citas_agendadas",
                "+chart_ventas_linea_tiempo",
                "+chart_distribucion_sucursales",
                "+tbl_ultimas_transacciones"
            ],
            "methods": [
                "+cargar_metricas_dashboard()",
                "+filtrar_por_sucursal_dashboard(id)",
                "+cambiar_rango_tiempo(dia, semana, mes)",
                "+actualizar_en_tiempo_real()"
            ]
        },
        "controller": {
            "name": "CTR_DashboardGlobal",
            "methods": [
                "+obtener_kpis_generales(periodo)",
                "+calcular_tendencia_ventas(rango)",
                "+obtener_ventas_por_sucursal()",
                "+calcular_capital_invertido_global()",
                "+contar_reservas_activas()"
            ]
        },
        "entities": [
            {
                "name": "CE_Order",
                "attributes": [
                    "+orders.id",
                    "+orders.branch_id",
                    "+orders.total_amount",
                    "+orders.status",
                    "+orders.created_at"
                ]
            },
            {
                "name": "CE_Inventory",
                "attributes": [
                    "+inventory.branch_id",
                    "+inventory.variant_id",
                    "+inventory.stock_actual",
                    "+inventory.stock_reservado",
                    "+inventory.avg_cost"
                ]
            },
            {
                "name": "CE_Reservation",
                "attributes": [
                    "+reservations.id",
                    "+reservations.branch_id",
                    "+reservations.status",
                    "+reservations.appointment_date",
                    "+reservations.appointment_time"
                ]
            }
        ],
        "associations": []
    },
    {
        "id": "CU40",
        "title": "CU40: Notificar en tiempo real (Push) y correos de confirmación",
        "cycle": "Ciclo 3",
        "package": "notificaciones",
        "actor": "Sistema / Worker",
        "boundary": {
            "name": "IU_BuzonNotificaciones",
            "attributes": [
                "+badge_contador_no_leidas",
                "+tbl_notificaciones_inapp",
                "+toast_alerta_push_flotante",
                "+btn_marcar_todas_leidas",
                "+btn_abrir_accion_notificacion"
            ],
            "methods": [
                "+escuchar_eventos_push()",
                "+mostrar_alerta_toast(titulo, msg)",
                "+marcar_leida(notification_id)",
                "+navegar_a_origen(url_target)"
            ]
        },
        "controller": {
            "name": "CTR_Notificaciones",
            "methods": [
                "+crear_notificacion_inapp(user_id, title, msg, tipo, ref_id)",
                "+enviar_push_firebase(user_id, payload)",
                "+enviar_correo_transaccional(email, template, variables)",
                "+marcar_notificacion_como_leida(notif_id)"
            ]
        },
        "entities": [
            {
                "name": "CE_InAppNotification",
                "attributes": [
                    "+in_app_notifications.id",
                    "+in_app_notifications.user_id",
                    "+in_app_notifications.title",
                    "+in_app_notifications.message",
                    "+in_app_notifications.notification_type",
                    "+in_app_notifications.reference_id",
                    "+in_app_notifications.is_read",
                    "+in_app_notifications.created_at"
                ]
            },
            {
                "name": "CE_User",
                "attributes": [
                    "+users.id",
                    "+users.email",
                    "+users.first_name"
                ]
            }
        ],
        "associations": [
            ("CE_InAppNotification", "CE_User")
        ]
    }
]
