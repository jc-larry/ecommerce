# -*- coding: utf-8 -*-
"""
Datos de Casos de Prueba Funcionales de Caja Negra
Formato Oficial INF-412 - M.Sc. Angélica Garzón
"""

CICLO_1_PRUEBAS = [
    {
        "id": "CU01",
        "nombre": "Iniciar sesión",
        "descripcion": "Validar autenticación, normalización del correo y rechazo de credenciales no válidas.",
        "precondiciones": [
            "a) El sistema y la base de datos se encuentran operativos.",
            "b) El usuario debe estar previamente registrado en la tabla users.",
            "c) La cuenta del usuario debe encontrarse en estado activo (is_active = true)."
        ],
        "pasos": [
            {
                "id": "P-CU01-01",
                "accion": "Ingresar Cliente@GMAIL.com y contraseña válida.",
                "resultado": "HTTP 200 con JWT y roles; correo normalizado, registro LOGIN y redirección según rol.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU01-02",
                "accion": "Ingresar contraseña incorrecta.",
                "resultado": "HTTP 400 “Correo electrónico o contraseña incorrectos”; no se crea sesión.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU01-03",
                "accion": "Iniciar sesión con cuenta inactiva.",
                "resultado": "El acceso se rechaza e informa que la cuenta está desactivada.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Usuario / Cliente / Administrador",
        "adjunto": "Pantalla de Login (/login) y modal de autenticación"
    },
    {
        "id": "CU02",
        "nombre": "Cerrar sesión",
        "descripcion": "Verificar revocación de sesión, invalidación de tokens y limpieza de credenciales locales.",
        "precondiciones": [
            "a) El usuario debe contar con una sesión activa y un token JWT válido.",
            "b) El cliente web o aplicación móvil tiene almacenado el token en almacenamiento local (LocalStorage / SecureStorage).",
            "c) El servicio de autenticación y la lista de revocación de sesiones se encuentran operativos en el backend."
        ],
        "pasos": [
            {
                "id": "P-CU02-01",
                "accion": "Con sesión válida, seleccionar “Cerrar sesión” y confirmar la acción en el menú superior.",
                "resultado": "El token queda revocado, se registra LOGOUT en auditoría, se limpian credenciales locales y se redirige a la vista de login.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU02-02",
                "accion": "Intentar invocar un endpoint protegido (ej. GET /api/v1/auth/me) usando el JWT revocado.",
                "resultado": "Respuesta HTTP 401 Unauthorized; la petición es rechazada de inmediato.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU02-03",
                "accion": "Accionar 'Cerrar sesión' cuando el token ya ha expirado por tiempo.",
                "resultado": "Se limpian los datos locales de sesión y se muestra la pantalla de inicio de sesión sin bloquear la interfaz.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Usuario Autenticado",
        "adjunto": "Barra de navegación con menú de perfil y pantalla de Login"
    },
    {
        "id": "CU03",
        "nombre": "Recuperar credenciales",
        "descripcion": "Verificar restablecimiento de contraseña mediante enlace temporal, único y con expiración de 5 minutos.",
        "precondiciones": [
            "a) El servicio de correo electrónico SMTP transaccional debe estar configurado y en línea.",
            "b) Conexión activa con la base de datos para la generación y validación de tokens de recuperación.",
            "c) El usuario debe tener acceso a la bandeja de entrada del correo asociado a su cuenta."
        ],
        "pasos": [
            {
                "id": "P-CU03-01",
                "accion": "Solicitar recuperación con correo registrado, abrir el enlace recibido y definir una nueva contraseña válida.",
                "resultado": "Se muestra mensaje neutro, se actualiza la contraseña con BCrypt, se anula el token y se registran RECOVER y RESET_PASSWORD en bitácora.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU03-02",
                "accion": "Solicitar recuperación ingresando un correo no registrado en el sistema.",
                "resultado": "Se muestra el mismo mensaje neutro de confirmación sin revelar si el correo existe en la base de datos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU03-03",
                "accion": "Intentar usar un enlace de recuperación vencido (>5 minutos) o que ya fue utilizado previamente.",
                "resultado": "Se rechaza la operación con el mensaje “El enlace es inválido o expiró (5 minutos)”.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Usuario / Visitante",
        "adjunto": "Formulario de recuperación (/forgot-password) y plantilla de correo HTML"
    },
    {
        "id": "CU04",
        "nombre": "Auto-registro de cliente",
        "descripcion": "Verificar el alta pública de cuentas de usuario con asignación exclusiva del rol CLIENTE.",
        "precondiciones": [
            "a) El visitante se encuentra en la pantalla pública de registro de la plataforma.",
            "b) El rol CLIENTE debe estar previamente inicializado en la tabla roles.",
            "c) Conectividad activa con el backend y base de datos relacional."
        ],
        "pasos": [
            {
                "id": "P-CU04-01",
                "accion": "Enviar formulario con datos personales válidos y contraseña robusta.",
                "resultado": "Se crea usuario en estado activo, correo normalizado a minúsculas, contraseña cifrada en BCrypt, rol CLIENTE asignado y auditoría REGISTER.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU04-02",
                "accion": "Registrar un correo ya existente, variando mayúsculas y minúsculas.",
                "resultado": "Se rechaza el registro indicando que el correo electrónico ya se encuentra registrado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU04-03",
                "accion": "Ingresar contraseña débil (<8 caracteres o sin requisitos) o con confirmación discrepante.",
                "resultado": "Se indican los requisitos incumplidos mediante validación visual y no se persiste ningún usuario.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Nuevo Cliente",
        "adjunto": "Formulario de Registro Público (/register)"
    },
    {
        "id": "CU05",
        "nombre": "Gestionar perfiles, roles y clientes",
        "descripcion": "Validar la creación, edición, asignación de roles y baja lógica de usuarios por el Superadmin.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ADMINISTRADOR.",
            "b) Módulo de administración de usuarios y roles habilitado.",
            "c) Catálogo de roles disponible en el sistema (SUPERADMIN, ENCARGADO, CAJERO, REPARTIDOR, PROVEEDOR, CLIENTE)."
        ],
        "pasos": [
            {
                "id": "P-CU05-01",
                "accion": "Como SUPERADMIN, crear un usuario interno y asignarle uno o más roles del sistema.",
                "resultado": "Se guardan usuario y relaciones en user_roles, contraseña cifrada y se registra INSERT en auditoría.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU05-02",
                "accion": "Editar datos/roles de un usuario y proceder a desactivar su cuenta.",
                "resultado": "Se actualizan los campos, se aplica baja lógica (is_active = false) sin borrar registros y se audita UPDATE.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU05-03",
                "accion": "Intentar acceder al módulo de gestión de usuarios con un rol no autorizado (ej. CLIENTE o CAJERO).",
                "resultado": "Respuesta HTTP 403 Forbidden y ninguna modificación en base de datos.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Panel Administrativo de Usuarios y Roles (/admin/users)"
    },
    {
        "id": "CU06",
        "nombre": "Gestionar sucursales",
        "descripcion": "Verificar el alta de sucursales físicas (restringidas a Santa Cruz) y asignación válida de personal.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN (Casa Matriz).",
            "b) Módulo de sucursales activo en el panel de control.",
            "c) Coordenadas geográficas y datos de contacto disponibles."
        ],
        "pasos": [
            {
                "id": "P-CU06-01",
                "accion": "Registrar sucursal con nombre, dirección, teléfono y coordenadas en el departamento de Santa Cruz.",
                "resultado": "La sucursal se guarda con éxito, se asigna identificador y la operación queda auditada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU06-02",
                "accion": "Asignar un usuario con rol ENCARGADO o CAJERO a la sucursal creada.",
                "resultado": "Se crea la relación en branch_employees y se audita la asignación correctamente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU06-03",
                "accion": "Intentar registrar sucursal con nombre duplicado o asignar un usuario con rol no permitido.",
                "resultado": "Se rechaza la operación informando error de duplicidad o que el rol es incompatible.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Módulo de Sucursales (/admin/branches)"
    },
    {
        "id": "CU07",
        "nombre": "Gestionar catálogo",
        "descripcion": "Comprobar la parametrización y el registro de prendas con variantes únicas de color, talla y SKU.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ADMINISTRADOR de catálogo.",
            "b) Categorías base, paletas de colores y tallas previamente creadas.",
            "c) Módulo de catálogo habilitado para carga multimedia de prendas."
        ],
        "pasos": [
            {
                "id": "P-CU07-01",
                "accion": "Crear parámetros base y registrar una nueva prenda con variantes color + talla + SKU.",
                "resultado": "Se guarda la jerarquía Prenda → Variantes con precios y atributos, registrando INSERT en bitácora.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU07-02",
                "accion": "Intentar crear una variante con SKU duplicado o combinación producto + color + talla ya existente.",
                "resultado": "Se rechaza la variante duplicada por restricción de unicidad sin alterar el catálogo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU07-03",
                "accion": "Desactivar u ocultar una prenda activa del catálogo.",
                "resultado": "La prenda queda con is_active = false y deja de visualizarse inmediatamente en la tienda pública.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Administrador de Catálogo",
        "adjunto": "Formulario de Prendas y Variantes (/admin/products)"
    },
    {
        "id": "CU08",
        "nombre": "Gestionar proveedores",
        "descripcion": "Verificar el mantenimiento del directorio de proveedores comerciales y validación de NIT.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN.",
            "b) Módulo de proveedores habilitado en el panel administrativo.",
            "c) Datos fiscales y de contacto de la empresa proveedora a registrar."
        ],
        "pasos": [
            {
                "id": "P-CU08-01",
                "accion": "Como SUPERADMIN, registrar proveedor con NIT, razón social y contacto válidos.",
                "resultado": "El proveedor queda registrado, activo para órdenes de compra y se genera INSERT en auditoría.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU08-02",
                "accion": "Intentar registrar un segundo proveedor utilizando el mismo número de NIT.",
                "resultado": "Se rechaza la creación informando que el NIT ya se encuentra registrado en el sistema.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU08-03",
                "accion": "Intentar acceder o modificar proveedores con un rol distinto a SUPERADMIN.",
                "resultado": "Respuesta HTTP 403 Forbidden y ningún cambio en la base de datos.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin",
        "adjunto": "Directorio de Proveedores (/admin/suppliers)"
    },
    {
        "id": "CU09",
        "nombre": "Gestionar empleados de sucursal",
        "descripcion": "Validar la creación de empleados y su asignación controlada a sucursales físicas.",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN.",
            "b) Existencia de al menos una sucursal física activa en la base de datos.",
            "c) Usuarios creados con rol ENCARGADO o CAJERO disponibles para asignación."
        ],
        "pasos": [
            {
                "id": "P-CU09-01",
                "accion": "Crear empleado con rol ENCARGADO o CAJERO y asignarlo a una sucursal existente.",
                "resultado": "Se crea usuario, rol y vínculo en branch_employees, registrándose la auditoría correspondiente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU09-02",
                "accion": "Intentar reasignar al mismo empleado a la misma sucursal en la que ya está activo.",
                "resultado": "El sistema advierte que el usuario ya se encuentra asignado y evita duplicar la relación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU09-03",
                "accion": "Gestionar empleados sin permisos o intentar asignar cuando no existe ninguna sucursal creada.",
                "resultado": "HTTP 403 para usuarios sin permiso o mensaje de validación indicando que debe crearse una sucursal previa.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin",
        "adjunto": "Módulo de Personal de Sucursales (/admin/branch-employees)"
    },
    {
        "id": "CU10",
        "nombre": "Registrar compras e ingresos de mercadería",
        "descripcion": "Verificar la transacción ACID de stock, libro mayor y cálculo del Costo Promedio Ponderado (CPP).",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN o ENCARGADO de la sucursal receptora.",
            "b) Existencia de proveedor activo y prendas con variantes en el catálogo.",
            "c) Base de datos con soporte transaccional para actualizar inventario y ledger simultáneamente."
        ],
        "pasos": [
            {
                "id": "P-CU10-01",
                "accion": "Registrar dos ingresos consecutivos de la misma variante: 1 unidad a Bs 10 y 1 unidad a Bs 14.",
                "resultado": "Stock resultante 2, avg_cost = Bs 12, se registran detalles y movimientos INGRESO con referencia OC-{id}.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU10-02",
                "accion": "Intentar registrar ingreso con cantidad <= 0 o costo unitario <= 0.",
                "resultado": "Se rechaza la operación por validación y no se persiste ningún cambio parcial en la base de datos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU10-03",
                "accion": "Usar proveedor, sucursal o variante inexistente, o intentar la operación con rol de CAJERO.",
                "resultado": "HTTP 404 para entidades inexistentes o HTTP 403 para roles no autorizados; atomicidad preservada.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Formulario de Ingreso de Mercadería (/admin/purchases/new)"
    },
    {
        "id": "CU11",
        "nombre": "Consultar catálogo (cliente)",
        "descripcion": "Validar la consulta pública, búsqueda general y filtrado de prendas activas por categoría.",
        "precondiciones": [
            "a) Plataforma web o aplicación móvil accesible sin requerir autenticación previa.",
            "b) Existencia de prendas activas (is_active = true) con precios y fotografías registradas.",
            "c) Conectividad operativa con el backend de catálogo."
        ],
        "pasos": [
            {
                "id": "P-CU11-01",
                "accion": "Como visitante, abrir la tienda principal con productos activos registrados.",
                "resultado": "Se muestra la grilla de productos con foto principal, nombre, categoría y precio visible sin login.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU11-02",
                "accion": "Buscar por texto en la barra de búsqueda y seleccionar un filtro de categoría.",
                "resultado": "Se muestran únicamente las prendas activas que cumplen los criterios de coincidencia.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU11-03",
                "accion": "Consultar catálogo cuando no existen prendas activas en la categoría seleccionada.",
                "resultado": "Se muestra mensaje informativo “No hay prendas disponibles por el momento” sin generar errores.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Grilla de Catálogo Público (/tienda)"
    },
    {
        "id": "CU36",
        "nombre": "Consultar bitácora de auditoría",
        "descripcion": "Verificar la consulta inmutable y restringida de todas las acciones auditadas en el sistema.",
        "precondiciones": [
            "a) Sesión iniciada estrictamente con rol SUPERADMIN.",
            "b) Existencia de registros de auditoría almacenados en la tabla audit_logs.",
            "c) Módulo de auditoría habilitado en el menú de Casa Matriz."
        ],
        "pasos": [
            {
                "id": "P-CU36-01",
                "accion": "Como SUPERADMIN, consultar la bitácora del sistema y aplicar filtro por tipo de acción (INSERT, UPDATE, DELETE).",
                "resultado": "Se listan los registros en orden cronológico descendente con timestamp, usuario, IP, tabla y detalles; la información es inmutable.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU36-02",
                "accion": "Intentar consultar la bitácora de auditoría con un rol distinto de SUPERADMIN (ej. ENCARGADO o CLIENTE).",
                "resultado": "Respuesta HTTP 403 Forbidden; el acceso a la bitácora es denegado rotundamente.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin (Auditor)",
        "adjunto": "Visor de Auditoría (/admin/audit)"
    },
    {
        "id": "CU37",
        "nombre": "Consultar valoración de inventario / capital invertido",
        "descripcion": "Comprobar el cálculo del capital invertido utilizando el Costo Promedio Ponderado de las existencias.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ENCARGADO de sucursal.",
            "b) Existencia de registros de existencias en inventory con avg_cost calculado.",
            "c) Movimientos de entrada de mercadería registrados previamente."
        ],
        "pasos": [
            {
                "id": "P-CU37-01",
                "accion": "Consultar valoración tras dos ingresos de 1 unidad a Bs 10 y 1 unidad a Bs 14.",
                "resultado": "avg_cost = Bs 12, valor total = Bs 24 y capital invertido = Bs 24; se verifica que no se usa el último costo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU37-02",
                "accion": "Filtrar la valoración de inventario seleccionando una sucursal específica.",
                "resultado": "Se calculan únicamente el stock, costo promedio, valor total y capital perteneciente a dicha sucursal.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU37-03",
                "accion": "Consultar valoración de una sucursal sin inventario, o consultar sin rol autorizado.",
                "resultado": "Inventario vacío muestra capital Bs 0 con aviso informativo; consulta sin permiso retorna HTTP 403.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin / Encargado de Sucursal",
        "adjunto": "Reporte de Valoración de Inventario (/admin/inventory/valuation)"
    },
    {
        "id": "CU38",
        "nombre": "Gestionar ajustes de inventario",
        "descripcion": "Validar el registro de mermas, daños, pérdidas y correcciones con trazabilidad sin alterar el costo promedio.",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN o ENCARGADO de la sucursal.",
            "b) La variante de prenda debe contar con inventario activo en la sucursal seleccionada.",
            "c) Disponibilidad de motivos de ajuste estándar en el sistema."
        ],
        "pasos": [
            {
                "id": "P-CU38-01",
                "accion": "Con stock 5 y avg_cost = Bs 12, registrar un ajuste por merma de -1 unidad.",
                "resultado": "Stock resultante 4; movimiento AJUSTE con código AJU-{id}, unit_cost = Bs 12, avg_cost inalterado y auditoría INSERT.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU38-02",
                "accion": "Intentar registrar un ajuste de salida por una cantidad mayor al stock disponible (ej. salida 10 teniendo stock 4).",
                "resultado": "HTTP 400 “Stock insuficiente para realizar el ajuste”; no se altera el inventario ni el libro mayor.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU38-03",
                "accion": "Registrar ajuste con cantidad cero, sobre variante sin existencias o con rol no autorizado.",
                "resultado": "Rechazo de cantidad cero; HTTP 404 si la variante no existe en la sucursal y HTTP 403 si el rol no tiene permiso.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Modal de Ajustes de Inventario (/admin/inventory/adjustments)"
    }
]

CICLO_2_PRUEBAS = [
    {
        "id": "CU12",
        "nombre": "Buscar/filtrar catálogo avanzado y disponibilidad por sucursal",
        "descripcion": "Validar búsqueda combinada (precio, talla, color, ocasión) y consulta de disponibilidad de stock por sucursal.",
        "precondiciones": [
            "a) Catálogo público accesible en versión web o aplicación móvil.",
            "b) Existencia de prendas activas con variantes y stock distribuido en sucursales físicas.",
            "c) Conectividad operativa con los servicios de catálogo e inventario."
        ],
        "pasos": [
            {
                "id": "P-CU12-01",
                "accion": "Filtrar por rango de precio [50–200 Bs], talla M, color 'Negro' y ocasión 'Formal'.",
                "resultado": "Se listan solo prendas activas coincidentes con todos los filtros; cada variante detalla stock por sucursal (stock > 0 = 'Disponible', 0 = 'Agotado').",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU12-02",
                "accion": "Filtrar únicamente por ocasión 'Casual' sin especificar otros criterios.",
                "resultado": "Se muestran las prendas activas etiquetadas como Casual con paginación funcional y sin errores.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU12-03",
                "accion": "Buscar por término 'camisa' combinado simultáneamente con filtro de color 'Blanco'.",
                "resultado": "Resultado igual a la intersección (búsqueda textual Y filtro color); se muestra disponibilidad por sucursal.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU12-04",
                "accion": "Consultar disponibilidad de una variante específica en la sucursal 'Central'.",
                "resultado": "El endpoint devuelve stock_actual y costo de la variante en esa sucursal; HTTP 404 si no existe inventario.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU12-05",
                "accion": "Ingresar filtro con rango de precio inválido donde precio mínimo > precio máximo.",
                "resultado": "Respuesta HTTP 422 informando “El precio mínimo no puede ser mayor al máximo”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU12-06",
                "accion": "Ejecutar búsqueda sin ningún parámetro.",
                "resultado": "Devuelve el catálogo general completo paginado según configuración por defecto.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Barra lateral de filtros y panel de stock por sucursal (/tienda)"
    },
    {
        "id": "CU13",
        "nombre": "Gestionar promociones: cupones y ofertas de temporada",
        "descripcion": "Verificar creación, validación temporal y aplicación de cupones de descuento y campañas programadas.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN en Casa Matriz.",
            "b) Módulo de promociones habilitado en el panel administrativo.",
            "c) Catálogo de prendas y categorías disponibles para vinculación."
        ],
        "pasos": [
            {
                "id": "P-CU13-01",
                "accion": "Como SUPERADMIN, crear cupón 'DESCUENTO20' (20 % de descuento, uso único por cliente, vigencia 7 días).",
                "resultado": "Cupón guardado con código único, fechas válidas de inicio y fin; se registra INSERT en auditoría.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-02",
                "accion": "Crear campaña 'Black Friday' (15 % sobre categoría 'Abrigos', rango 2026-11-25 a 2026-11-30).",
                "resultado": "Campaña creada y asociada a la categoría; fechas validadas y auditoría INSERT generada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-03",
                "accion": "Aplicar cupón válido en el carrito de compras con artículos elegibles.",
                "resultado": "Total recalculado con el descuento; cupón registrado en coupon_usages para ese cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-04",
                "accion": "Intentar aplicar un cupón vencido o que ya fue utilizado previamente por el cliente.",
                "resultado": "HTTP 400 “El cupón no es válido o ya fue utilizado”; el total del carrito permanece inalterado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-05",
                "accion": "Consultar carrito durante la vigencia de una campaña automática de temporada (sin código).",
                "resultado": "El descuento por categoría se aplica automáticamente en el desglose sin intervención del cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-06",
                "accion": "Crear cupón ingresando porcentaje de descuento >= 100 % o <= 0 %.",
                "resultado": "Respuesta HTTP 422 por validación de rango; el cupón no se persiste.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-07",
                "accion": "Editar campaña existente modificando porcentaje y rango de vigencia.",
                "resultado": "Modificaciones guardadas en la base de datos, auditoría UPDATE registrada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU13-08",
                "accion": "Intentar gestionar promociones con un usuario sin rol SUPERADMIN.",
                "resultado": "HTTP 403 Forbidden y acceso bloqueado.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin (Marketing)",
        "adjunto": "Panel de Cupones y Campañas (/admin/promotions)"
    },
    {
        "id": "CU14",
        "nombre": "Wishlist múltiple compartible y moderación de reseñas",
        "descripcion": "Validar la gestión de listas de deseos múltiples compartibles y el flujo de moderación de reseñas de clientes.",
        "precondiciones": [
            "a) Cliente autenticado para crear wishlists y redactar reseñas.",
            "b) Existencia de prendas activas en el catálogo.",
            "c) Rol SUPERADMIN con acceso al panel de moderación de comentarios."
        ],
        "pasos": [
            {
                "id": "P-CU14-01",
                "accion": "Cliente crea lista 'Regalos Navidad' y añade 3 prendas del catálogo.",
                "resultado": "Lista guardada con is_public = false; ítems vinculados en wishlist_items; auditoría INSERT.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-02",
                "accion": "Cliente cambia la lista a pública (is_public = true) y copia el enlace con public_token.",
                "resultado": "Enlace accesible para cualquier usuario sin login; visualiza prendas, fotos y precios sin permitir edición.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-03",
                "accion": "Mover una prenda desde la lista 'Favoritos' hacia 'Regalos Navidad'.",
                "resultado": "El ítem actualiza su wishlist_id de destino sin duplicarse; auditoría UPDATE.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-04",
                "accion": "Cliente elimina una lista con prendas agregadas.",
                "resultado": "Se elimina la lista y sus ítems en cascada; auditoría DELETE registrada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-05",
                "accion": "Cliente publica reseña de 4 estrellas y comentario en prenda con moderación habilitada.",
                "resultado": "Reseña guardada con estado PENDIENTE; no visible públicamente hasta su aprobación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-06",
                "accion": "SUPERADMIN aprueba la reseña pendiente en el panel de moderación.",
                "resultado": "Estado cambia a APROBADA; se visualiza en la ficha del producto y recalcula el rating promedio.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-07",
                "accion": "SUPERADMIN rechaza reseña especificando motivo 'Contenido inapropiado'.",
                "resultado": "Estado cambia a RECHAZADA con motivo almacenado; no se publica ni afecta el promedio.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-08",
                "accion": "Cliente edita una reseña que ya había sido aprobada previamente.",
                "resultado": "La nueva versión pasa automáticamente a PENDIENTE para re-moderación; la anterior se preserva temporalmente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-09",
                "accion": "Cliente reseña una prenda perteneciente a una orden previamente entregada.",
                "resultado": "Se asigna automáticamente verified_purchase = true y se muestra insignia de 'Compra verificada'.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-10",
                "accion": "Usuario vota 'Útil' en una reseña aprobada de otro cliente.",
                "resultado": "Contador de votos útiles incrementado; se valida un único voto por usuario.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU14-11",
                "accion": "Comercio (SUPERADMIN o ENCARGADO) responde formalmente a una reseña aprobada.",
                "resultado": "Respuesta institucional registrada y visible debajo del comentario del cliente.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cliente / Superadmin (Moderador)",
        "adjunto": "Módulo de Wishlists (/tienda/favoritos) y Panel de Reseñas (/admin/reviews)"
    },
    {
        "id": "CU15",
        "nombre": "Gestionar inventario general y transferencias entre sucursales",
        "descripcion": "Verificar la vista consolidada de stock, el flujo de transferencias entre sucursales y actualización automática.",
        "precondiciones": [
            "a) Existencia de al menos dos sucursales físicas activas.",
            "b) Sesión iniciada con rol ENCARGADO de sucursal origen o SUPERADMIN.",
            "c) Stock disponible suficiente en la sucursal de origen."
        ],
        "pasos": [
            {
                "id": "P-CU15-01",
                "accion": "SUPERADMIN consulta el inventario general consolidado de todas las sucursales.",
                "resultado": "Tabla consolidada con variante, stock por sucursal, stock global total y costo medio con paginación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-02",
                "accion": "ENCARGADO de sucursal 'Central' inicia transferencia de 5 unidades de SKU CAM-BL-M a 'Norte'.",
                "resultado": "Se genera transfer_order en estado PENDIENTE; stock de origen queda retenido/reservado; auditoría INSERT.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-03",
                "accion": "ENCARGADO de sucursal 'Norte' confirma la recepción de la transferencia.",
                "resultado": "Estado pasa a RECIBIDA; stock origen descuenta 5 definitivamente, destino incrementa 5; se recalculan costos ponderados y se registran movimientos en ledger.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-04",
                "accion": "Cancelar una transferencia que se encuentra en estado PENDIENTE.",
                "resultado": "Estado pasa a CANCELADA; se desbloquea el stock en la sucursal de origen sin movimientos contables.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-05",
                "accion": "Intentar transferir una cantidad superior al stock disponible en origen (disponible 3, solicita 5).",
                "resultado": "HTTP 400 “Stock insuficiente para transferir”; la solicitud es rechazada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-06",
                "accion": "Intentar registrar una transferencia donde la sucursal origen es igual a la sucursal destino.",
                "resultado": "HTTP 422 “La sucursal de origen y destino deben ser distintas”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-07",
                "accion": "Consultar kardex de movimientos de una variante en una sucursal específica.",
                "resultado": "Listado cronológico de INGRESO, AJUSTE, VENTA, TRANSFERENCIA_SALIDA y TRANSFERENCIA_ENTRADA con stock acumulado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU15-08",
                "accion": "Venta en caja descuenta stock: verificar actualización inmediata del consolidado general.",
                "resultado": "Stock descontado en tiempo real; la vista general refleja el cambio sin inconsistencias.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Módulo de Transferencias de Inventario (/admin/inventory/transfers)"
    },
    {
        "id": "CU16",
        "nombre": "Configurar y notificar alertas de stock",
        "descripcion": "Validar la parametrización de umbrales por variante y la generación automática de alertas por stock bajo o alto.",
        "precondiciones": [
            "a) Sesión de SUPERADMIN o ENCARGADO.",
            "b) Variantes de prendas con registro de inventario en sucursal.",
            "c) Módulo de alertas y notificaciones del sistema activo."
        ],
        "pasos": [
            {
                "id": "P-CU16-01",
                "accion": "SUPERADMIN configura stock mínimo = 5 y stock máximo = 100 para variante SKU CAM-BL-M en sucursal Central.",
                "resultado": "Umbrales guardados en inventory_alerts; auditoría INSERT registrada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU16-02",
                "accion": "Ingreso de mercadería hace subir el stock de 4 a 10 unidades (superando el umbral mínimo).",
                "resultado": "Alerta 'STOCK_BAJO' se marca automáticamente como resuelta; notificación de actualización emitida.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU16-03",
                "accion": "Una venta disminuye el stock físico de 6 a 4 unidades (cruzando el límite mínimo hacia abajo).",
                "resultado": "Se genera alerta 'STOCK_BAJO' en estado ACTIVA y se notifica al panel del encargado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU16-04",
                "accion": "Ingreso masivo supera el stock máximo configurado (100 a 110 unidades).",
                "resultado": "Se genera alerta 'STOCK_ALTO' para advertir sobre posible sobrestock y baja rotación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU16-05",
                "accion": "Intentar configurar umbral con stock mínimo > stock máximo.",
                "resultado": "HTTP 422 “El stock mínimo no puede ser mayor al stock máximo”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU16-06",
                "accion": "Consultar listado de alertas filtradas por sucursal y nivel de severidad.",
                "resultado": "Se visualizan las alertas activas con fecha, variante, stock actual y umbral configurado.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin / Encargado de Sucursal",
        "adjunto": "Panel de Alertas de Stock (/admin/alerts)"
    },
    {
        "id": "CU17",
        "nombre": "Gestionar carrito de compra digital",
        "descripcion": "Verificar operaciones del carrito, control de stock disponible en tiempo real y persistencia entre sesiones.",
        "precondiciones": [
            "a) Tienda web o app móvil con catálogo de productos en línea.",
            "b) Artículos con stock disponible en la base de datos.",
            "c) Sesión activa de cliente o identificador temporal para visitante anónimo."
        ],
        "pasos": [
            {
                "id": "P-CU17-01",
                "accion": "Cliente autenticado añade 2 unidades de una variante con stock disponible 10.",
                "resultado": "Ítem agregado con quantity = 2, subtotal calculado y available_stock = 10 reflejado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-02",
                "accion": "Añadir 1 unidad adicional de la misma variante que ya estaba en el carrito.",
                "resultado": "La fila existente actualiza quantity = 3 sin duplicar filas; subtotal recalculado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-03",
                "accion": "Intentar agregar una cantidad que excede el stock disponible (ej. agregar 11 teniendo stock 10).",
                "resultado": "HTTP 400 “Stock disponible insuficiente (máximo 10)”; el carrito mantiene su cantidad previa.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-04",
                "accion": "Una prenda en el carrito queda con stock 0 por una venta externa simultánea.",
                "resultado": "Al consultar GET /cart, el ítem se marca con blocked = true y se deshabilita el botón de checkout.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-05",
                "accion": "Cliente elimina una prenda específica del carrito.",
                "resultado": "Ítem removido de cart_items; totales generales actualizados y auditoría registrada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-06",
                "accion": "Accionar la opción 'Vaciar carrito'.",
                "resultado": "Se eliminan todos los ítems; carrito queda en cero y muestra mensaje 'Carrito vacío'.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-07",
                "accion": "Cerrar sesión e iniciar nuevamente con el mismo usuario en otro dispositivo.",
                "resultado": "El carrito persiste íntegramente gracias al almacenamiento en base de datos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU17-08",
                "accion": "Visitante anónimo añade ítems al carrito y posteriormente inicia sesión.",
                "resultado": "Fusión automática (merge) del carrito anónimo con el del usuario respetando límites de stock.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cliente / Visitante",
        "adjunto": "Sidebar de Carrito y Pantalla de Carrito (/tienda/carrito)"
    },
    {
        "id": "CU18",
        "nombre": "Procesar venta / checkout con herencia de medios de pago",
        "descripcion": "Validar el flujo de checkout digital, procesamiento con pasarelas (Stripe, PayPal, QR, Efectivo) e idempotencia.",
        "precondiciones": [
            "a) Cliente autenticado con carrito de compras válido y con stock confirmado.",
            "b) Pasarelas de pago configuradas en modo sandbox/prueba (PayPal / Stripe / QR bancario).",
            "c) Dirección de entrega válida o selección de sucursal de retiro."
        ],
        "pasos": [
            {
                "id": "P-CU18-01",
                "accion": "Cliente selecciona 'Envío a domicilio' y realiza pago con Tarjeta de crédito en modo prueba.",
                "resultado": "Orden status = PAGADA; pago registrado con payment_method = TARJETA; stock descontado; factura electrónica generada (CU20) y enviada por correo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-02",
                "accion": "Procesar pago mediante código QR estático/dinámico generado por el sistema.",
                "resultado": "Orden status = PAGADA; payment_method = QR; reference_code persistido y flujo fiscal completado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-03",
                "accion": "Seleccionar modalidad 'Pago contraentrega en efectivo'.",
                "resultado": "Orden status = CONFIRMADA_PENDIENTE_PAGO; pago en estado PENDIENTE; factura fiscal retenida hasta cobro efectivo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-04",
                "accion": "Cliente corporativo procesa compra bajo modalidad 'Crédito'.",
                "resultado": "Se valida el límite de crédito disponible; orden CONFIRMADA, nota de entrega generada y deuda registrada en customer_credit.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-05",
                "accion": "La pasarela de pago retorna rechazo de tarjeta (card_declined).",
                "resultado": "Orden status = FALLIDA; pago RECHAZADO; inventario preservado; carrito intacto y aviso al usuario.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-06",
                "accion": "Intentar procesar checkout teniendo un ítem bloqueado por stock 0 en el carrito.",
                "resultado": "HTTP 409 Conflict “Existen productos sin stock suficiente”; proceso interrumpido.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-07",
                "accion": "Intentar checkout con modalidad 'Envío a domicilio' sin proporcionar dirección de entrega.",
                "resultado": "HTTP 422 Unprocessable Entity por validación de campos obligatorios.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU18-08",
                "accion": "Reintento de petición con el mismo payment_intent_id (idempotencia).",
                "resultado": "El sistema detecta la transacción previa y retorna la orden existente sin duplicar cobros ni pedidos.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cliente",
        "adjunto": "Módulo de Checkout (/tienda/checkout) y Pasarelas de Pago"
    },
    {
        "id": "CU19",
        "nombre": "Procesar venta presencial en caja (POS)",
        "descripcion": "Verificar la venta física directa en mostrador por Cajero: escaneo de productos, pago mixto y emisión de factura.",
        "precondiciones": [
            "a) Cajero o Encargado con sesión iniciada y turno de caja ABIERTA en su sucursal.",
            "b) Lector de código de barras o buscador de catálogo POS operativo.",
            "c) Existencia de existencias en el inventario de la sucursal actual."
        ],
        "pasos": [
            {
                "id": "P-CU19-01",
                "accion": "CAJERO busca o escanea SKU CAM-BL-M con cantidad 1 y stock disponible 5.",
                "resultado": "Línea añadida al ticket de venta; subtotal calculado y disponibilidad verificada en tiempo real.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-02",
                "accion": "Agregar una segunda prenda de distinta categoría y precio al ticket de venta.",
                "resultado": "Ticket refleja ambas líneas; subtotales e impuestos desglosados en el total general.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-03",
                "accion": "Registrar cobro con pago mixto: 50 % en Efectivo y 50 % con Tarjeta mediante terminal POS.",
                "resultado": "Dos registros vinculados a la orden en payments (EFECTIVO + TARJETA); total saldado y factura emitida.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-04",
                "accion": "Cambio de talla de un artículo ya escaneado antes de cerrar la venta.",
                "resultado": "Se quita la línea previa y se añade la nueva talla; cálculos y existencias se ajustan en mostrador.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-05",
                "accion": "Aplicar cupón promocional vigente presentado por el cliente en caja física.",
                "resultado": "Descuento aplicado al total, cupón marcado como utilizado y detalle reflejado en la factura.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-06",
                "accion": "Procesar venta a 'Consumidor Final' sin registrar NIT ni datos de cliente.",
                "resultado": "Orden registrada con customer_id nulo; factura emitida a Consumidor Final con NIT genérico e IVA 13 %.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-07",
                "accion": "Cancelar la venta en curso antes de proceder al cobro del ticket.",
                "resultado": "El ticket se descarta; no se afecta el inventario ni se registran movimientos en el libro mayor.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU19-08",
                "accion": "Usuario con rol CLIENTE intenta ingresar a la ruta del terminal POS.",
                "resultado": "HTTP 403 Forbidden; acceso restringido exclusivamente al personal de sucursal.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cajero de Sucursal",
        "adjunto": "Terminal POS de Mostrador (/admin/pos)"
    },
    {
        "id": "CU20",
        "nombre": "Emitir comprobante: factura y nota de entrega",
        "descripcion": "Verificar la generación fiscal de facturas con IVA 13%, código de control SIN y notas de entrega oficiales.",
        "precondiciones": [
            "a) Transacción de venta confirmada y saldada (online o POS).",
            "b) Parámetros de dosificación y llave de control fiscal registrados en el sistema.",
            "c) Módulo de renderizado PDF y generador de código QR operativo."
        ],
        "pasos": [
            {
                "id": "P-CU20-01",
                "accion": "Generar factura tras confirmación de pago digital o cobro en caja física.",
                "resultado": "Registro en invoices: type = FACTURA, IVA 13 %, código de control computarizado válido, número de autorización y código QR fiscal; PDF generado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU20-02",
                "accion": "Generar comprobante para venta corporativa a crédito o cliente sin exigencia de factura con NIT.",
                "resultado": "Comprobante type = NOTA_ENTREGA sin código de control SIN pero con desglose formal de ítems e importes; PDF generado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU20-03",
                "accion": "Validar cálculo exacto de impuestos: Subtotal Bs 100 -> IVA (13 %) = Bs 13, Total = Bs 113.",
                "resultado": "Cálculos matemáticos exactos en base de datos y documento PDF con redondeo a dos decimales.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU20-04",
                "accion": "Emitir factura de una venta procesada con múltiples medios de pago (pago mixto).",
                "resultado": "Un comprobante único generado con desglose detallado de los montos pagados en cada modalidad al pie del documento.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU20-05",
                "accion": "Solicitar reimpresión o regeneración de un comprobante emitido anteriormente.",
                "resultado": "Se retorna el mismo invoice_id y PDF idéntico sin duplicar registros en base de datos; auditoría REPRINT registrada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU20-06",
                "accion": "Verificar código de control mediante vector de prueba oficial del Servicio de Impuestos Nacionales.",
                "resultado": "El algoritmo AllegedRC4 genera un código de control que coincide exactamente con el vector de prueba oficial.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU20-07",
                "accion": "Comprobar permisos de acceso a facturas: cliente consulta sólo las suyas; SUPERADMIN visualiza todas.",
                "resultado": "Filtro estricto por user_id en endpoints del cliente; visualización global habilitada para administración.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Sistema / Cajero / Facturación",
        "adjunto": "Plantilla de Factura Oficial con Código de Control y QR"
    },
    {
        "id": "CU21",
        "nombre": "Generar cotización",
        "descripcion": "Verificar creación de cotizaciones con vigencia temporal, versión PDF y conversión directa a orden de compra.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN, ENCARGADO o cliente corporativo autenticado.",
            "b) Variantes de prendas en el catálogo con precios unitarios vigentes.",
            "c) Módulo de cotizaciones disponible."
        ],
        "pasos": [
            {
                "id": "P-CU21-01",
                "accion": "Crear cotización corporativa seleccionando 3 variantes, cantidades requeridas y plazo de validez de 7 días.",
                "resultado": "Cotización creada con status = BORRADOR, fecha de vencimiento valid_until calculada, subtotales y PDF con membrete institucional.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU21-02",
                "accion": "Enviar enlace público de cotización por correo electrónico al cliente.",
                "resultado": "Se genera token de acceso seguro; el destinatario puede visualizar la cotización sin requerir login.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU21-03",
                "accion": "El cliente acepta la cotización vigente mediante el enlace público.",
                "resultado": "Cotización pasa a ACEPTADA; se crea automáticamente una orden en estado CONFIRMADA_PENDIENTE_PAGO apartando stock por vigencia.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU21-04",
                "accion": "Vencimiento del plazo de la cotización sin haber recibido aceptación.",
                "resultado": "El estado cambia a EXPIRADA y el stock temporal reservado se libera de inmediato.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU21-05",
                "accion": "Modificar cantidades y precios de una cotización que permanece en estado BORRADOR.",
                "resultado": "Cotización actualizada; historial de versiones registrado y documento PDF regenerado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU21-06",
                "accion": "Convertir una cotización aceptada a venta en mostrador procesando pago en efectivo en terminal POS.",
                "resultado": "Flujo de venta completado usando los ítems cotizados; factura emitida y cotización cerrada.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Ventas / Superadmin",
        "adjunto": "Módulo de Cotizaciones y Formato PDF (/admin/quotes)"
    },
    {
        "id": "CU22",
        "nombre": "Gestionar devoluciones y cambios de prendas",
        "descripcion": "Validar el flujo de devolución (reembolso o nota de crédito) y cambio de prendas con reintegro al inventario.",
        "precondiciones": [
            "a) Existencia de una orden entregada con antigüedad menor o igual a 30 días calendario.",
            "b) Prenda devuelta sin signos de uso y con etiquetas originales intactas.",
            "c) Sesión iniciada con rol ENCARGADO o SUPERADMIN para resolución de solicitudes."
        ],
        "pasos": [
            {
                "id": "P-CU22-01",
                "accion": "Cliente solicita devolución de pedido entregado; ENCARGADO aprueba la solicitud tras inspección física.",
                "resultado": "Solicitud pasa a APROBADA; stock de la variante devuelta se incrementa (+1) en la sucursal; se emite nota de crédito y procesa reembolso.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU22-02",
                "accion": "Cambio de talla: Cliente devuelve talla M y solicita talla L de la misma prenda.",
                "resultado": "Solicitud type = CAMBIO; stock talla M incrementa en 1, talla L descuenta 1 en inventario; si no hay stock de L retorna HTTP 409.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU22-03",
                "accion": "Solicitar devolución parcial de 1 solo ítem perteneciente a una orden que contenía 3 prendas.",
                "resultado": "Se emite nota de crédito proporcional al ítem devuelto; los otros dos ítems de la orden permanecen sin alteraciones.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU22-04",
                "accion": "Rechazar solicitud de devolución debido a prenda usada o fuera del plazo legal de 30 días.",
                "resultado": "Estado pasa a RECHAZADA con motivo documentado; el stock no sufre alteraciones y se notifica al cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU22-05",
                "accion": "Procesar devolución de una compra efectuada a crédito corporativo.",
                "resultado": "La nota de crédito reduce directamente el saldo deudor del cliente en customer_credit sin mover efectivo de caja.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU22-06",
                "accion": "Usuario con rol CLIENTE intenta invocar directamente el endpoint de aprobación de devoluciones.",
                "resultado": "HTTP 403 Forbidden; la aprobación está restringida exclusivamente al personal autorizado.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Módulo de Devoluciones y Garantías (/admin/returns)"
    },
    {
        "id": "CU23",
        "nombre": "Gestionar arqueo de caja",
        "descripcion": "Verificar apertura de caja con fondo inicial, consolidación por medio de pago y cierre con registro de diferencias.",
        "precondiciones": [
            "a) Usuario con rol CAJERO o ENCARGADO asignado a una sucursal activa.",
            "b) No debe existir un turno de caja previamente abierto para el mismo usuario en la sucursal.",
            "c) Módulo de tesorería y arqueo habilitado."
        ],
        "pasos": [
            {
                "id": "P-CU23-01",
                "accion": "CAJERO realiza apertura de turno ingresando fondo inicial de Bs 500 desglosado por billetes y monedas.",
                "resultado": "Turno creado en cash_shifts con status = ABIERTA, opening_amount = 500 y auditoría OPEN_CASH.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU23-02",
                "accion": "Operaciones durante el turno: Ventas en Efectivo Bs 1.200, Tarjeta Bs 800 y QR Bs 300.",
                "resultado": "El sistema totaliza montos esperados: Efectivo esperado Bs 1.700 (500+1200), Tarjeta Bs 800 y QR Bs 300.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU23-03",
                "accion": "CAJERO realiza cierre de caja declarando en efectivo físico Bs 1.695 (faltante de Bs 5).",
                "resultado": "Turno pasa a CERRADA; declared_cash = 1695, difference = -5; justificación obligatoria registrada y auditoría CLOSE_CASH.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU23-04",
                "accion": "Realizar cierre de caja con sobrante de efectivo físico respecto a lo esperado.",
                "resultado": "difference con valor positivo registrado; motivo de sobrante documentado y alerta enviada a supervisión.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU23-05",
                "accion": "Intentar cerrar turno de caja cuando no existe ninguna caja abierta para el usuario.",
                "resultado": "HTTP 409 Conflict “No existe ningún turno de caja abierto para esta sucursal/usuario”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU23-06",
                "accion": "SUPERADMIN reabre un turno previamente cerrado para corrección justificada.",
                "resultado": "Status pasa a REABIERTA con justificación obligatoria y auditoría completa de reapertura.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU23-07",
                "accion": "Consultar historial de arqueos filtrando por sucursal, cajero y rango de fechas.",
                "resultado": "Reporte completo con montos de apertura, ventas por medio de pago, declaraciones y diferencias.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cajero / Encargado de Sucursal",
        "adjunto": "Módulo de Arqueos y Turnos de Caja (/admin/cash-shifts)"
    },
    {
        "id": "CU24",
        "nombre": "Consultar historial de compras",
        "descripcion": "Verificar el listado paginado de órdenes del cliente autenticado con estado en vivo, detalles y comprobantes.",
        "precondiciones": [
            "a) Cliente con sesión activa en plataforma web o aplicación móvil.",
            "b) Existencia de compras registradas asociadas a su cuenta de usuario.",
            "c) Acceso a servicios de almacenamiento de facturas electrónicas."
        ],
        "pasos": [
            {
                "id": "P-CU24-01",
                "accion": "Cliente autenticado accede al módulo 'Mis Compras'.",
                "resultado": "Se visualiza lista paginada de pedidos con número de orden, fecha, total, estado actual y botón 'Ver Factura'.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU24-02",
                "accion": "Aplicar filtros de búsqueda por estado 'ENTREGADA' y rango de fechas en el historial.",
                "resultado": "Se presentan únicamente los pedidos que cumplen con el criterio seleccionado manteniendo la paginación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU24-03",
                "accion": "Hacer clic en 'Ver Factura' sobre una orden pagada.",
                "resultado": "Se genera o descarga el documento PDF oficial de la factura electrónica mediante enlace seguro.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU24-04",
                "accion": "Consultar el detalle de una orden que cuenta con despacho a domicilio.",
                "resultado": "Se muestra el número de guía TRK, transportista asignado, estado logístico en vivo y enlace al rastreo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU24-05",
                "accion": "Intentar consultar el detalle de una orden perteneciente a otro cliente manipulando el ID en la URL.",
                "resultado": "Respuesta HTTP 403 o 404; el sistema protege la privacidad de los datos y no expone pedidos ajenos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU24-06",
                "accion": "Acceder a 'Mis Compras' con una cuenta recién registrada que no posee pedidos.",
                "resultado": "Se muestra vista informativa “Aún no tienes compras registradas” con botón para explorar la tienda.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cliente",
        "adjunto": "Módulo de Mis Compras (/tienda/mis-compras) y App Móvil"
    }
]

CICLO_3_PRUEBAS = [
    {
        "id": "CU25",
        "nombre": "Convertir reserva a venta confirmada en POS (cobro saldo en caja + factura)",
        "descripcion": "Verificar la conversión en mostrador de una reserva previa a venta definitiva en terminal POS, cobrando el saldo restante, aplicando la seña, emitiendo factura y liberando o consolidando stock.",
        "precondiciones": [
            "a) Cajero o Encargado con sesión iniciada y turno de caja ABIERTA en la sucursal receptora.",
            "b) Existencia de una reserva en estado PENDING o CONFIRMED asignada a la sucursal del usuario.",
            "c) El cliente se presenta físicamente en la sucursal dentro del horario de tolerancia estipulado."
        ],
        "pasos": [
            {
                "id": "P-CU25-01",
                "accion": "Cajero busca reserva por código RES-{id} en la pestaña 'Reservas' del POS y procesa cobro del saldo restante (Total - Seña 50%).",
                "resultado": "La reserva pasa a COMPLETED; se genera orden status = PAGADA; la seña previa se imputa al total; se emite factura fiscal CU20; el stock reservado se convierte en salida definitiva por venta y se asocia al arqueo de caja.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU25-02",
                "accion": "Cobro de reserva con modificación de artículos en tienda (el cliente decide no llevar 1 prenda y cambiar la talla de otra).",
                "resultado": "El cajero ajusta los ítems en el POS; la prenda descartada se libera de inmediato al stock disponible de la sucursal; se recalcula el saldo exacto a pagar y se emite la factura final por las prendas efectivamente adquiridas.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU25-03",
                "accion": "Intentar procesar la conversión de una reserva cuando la caja de la sucursal se encuentra CERRADA.",
                "resultado": "Respuesta HTTP 409 Conflict “Debe abrir una caja antes de procesar conversiones de reserva en el POS”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU25-04",
                "accion": "Intentar cobrar una reserva perteneciente a otra sucursal o una reserva ya completada/cancelada.",
                "resultado": "HTTP 400 / 404 informando que la reserva no pertenece a la sucursal actual o no se encuentra en estado apto para cobro.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cajero / Encargado de Sucursal",
        "adjunto": "Terminal POS → Pestaña Reservas (/admin/pos)"
    },
    {
        "id": "CU26",
        "nombre": "Agendar reserva de prendas para prueba física (seña 50%, hasta 5 prendas)",
        "descripcion": "Verificar la programación de citas en probador físico desde la web o app móvil, con pago obligatorio de seña del 50%, apartado automático de stock y límite máximo de 5 prendas.",
        "precondiciones": [
            "a) Cliente con sesión activa en plataforma web o aplicación móvil Flutter.",
            "b) Sucursal seleccionada con probadores físicos habilitados y agenda disponible en la fecha/hora elegida.",
            "c) Variantes de prendas seleccionadas con stock físico disponible > 0 en la sucursal destino."
        ],
        "pasos": [
            {
                "id": "P-CU26-01",
                "accion": "Cliente selecciona sucursal 'Central', fecha y hora futura válida, añade 3 prendas al probador y abona la seña del 50% vía PayPal / Tarjeta / QR.",
                "resultado": "Se crea registro en reservations (status = PENDING), ítems en reservation_items; el stock de las 3 prendas se bloquea/aparta en la sucursal (-3 disponible, +3 reservado); se genera confirmación con código de cita y se notifica al cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU26-02",
                "accion": "Intentar agendar una reserva añadiendo 6 prendas al probador.",
                "resultado": "El sistema valida la regla de negocio y bloquea el avance mostrando “El límite máximo por reserva en probador es de 5 prendas”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU26-03",
                "accion": "Intentar agendar cita en fecha pasada, fuera del horario de atención comercial o en día feriado.",
                "resultado": "HTTP 422 Unprocessable Entity “La fecha y hora deben corresponder al horario habilitado de la sucursal”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU26-04",
                "accion": "Intentar reservar una variante cuyo stock en la sucursal seleccionada es igual a 0.",
                "resultado": "HTTP 400 Bad Request “Stock insuficiente en la sucursal seleccionada para una o más prendas elegidas”.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cliente",
        "adjunto": "Formulario de Reserva y Cita (/tienda/reservas/nueva) y Vista Móvil (reserve_fitting_view.dart)"
    },
    {
        "id": "CU27",
        "nombre": "Gestionar bandeja de reservas entrantes (Kanban: preparar / atender)",
        "descripcion": "Validar la administración visual mediante tablero Kanban de las reservas en probador físico por el personal de tienda, gestionando alistamiento, llamadas y tolerancia de citas.",
        "precondiciones": [
            "a) Usuario con sesión activa y rol ENCARGADO o CAJERO en la sucursal correspondiente.",
            "b) Módulo de Reservas y Probador habilitado en el panel administrativo (/admin/reservations).",
            "c) Existencia de reservas agendadas en la sucursal física."
        ],
        "pasos": [
            {
                "id": "P-CU27-01",
                "accion": "Encargado abre el tablero Kanban clasificado en columnas: Pendientes, En Preparación, Listo en Probador, En Prueba y Completadas.",
                "resultado": "Las tarjetas reflejan cliente, hora de cita, conteo de prendas, seña abonada y estado de alistamiento de manera ordenada y visual.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU27-02",
                "accion": "Personal aparta físicamente las prendas en tienda y mueve la tarjeta de 'Pendiente' a 'Listo en Probador'.",
                "resultado": "La tarjeta se reubica de columna; se actualiza el estado en backend y se dispara notificación in-app y correo al cliente informándole que su probador está preparado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU27-03",
                "accion": "Verificar tolerancia de citas: El cliente no se presenta pasados 15 minutos de la hora agendada.",
                "resultado": "El sistema marca la reserva automáticamente como LATE (Atrasado) con alerta visual; al alcanzar 30 minutos de retraso pasa a NO_SHOW y el stock apartado se libera a disponible.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU27-04",
                "accion": "Usuario con rol CLIENTE intenta ingresar a la ruta /admin/reservations.",
                "resultado": "Respuesta HTTP 403 Forbidden; módulo restringido estrictamente al personal de sucursal.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Sucursal",
        "adjunto": "Tablero Kanban de Citas y Probador (/admin/reservations)"
    },
    {
        "id": "CU28",
        "nombre": "Cancelar reserva (libera el stock apartado)",
        "descripcion": "Validar la cancelación voluntaria o administrativa de una reserva en probador, con liberación inmediata del stock retenido y auditoría de motivos.",
        "precondiciones": [
            "a) Existencia de una reserva en estado PENDING o CONFIRMED en el sistema.",
            "b) Sesión iniciada por el cliente titular de la reserva o por el ENCARGADO/SUPERADMIN de la tienda.",
            "c) Solicitud dentro de los márgenes permitidos por la política de cancelaciones."
        ],
        "pasos": [
            {
                "id": "P-CU28-01",
                "accion": "Cliente cancela su cita desde 'Mis Reservas' con más de 24 horas de antelación al horario pautado.",
                "resultado": "La reserva cambia a status = CANCELLED; las prendas apartadas regresan inmediatamente al stock disponible de la sucursal (+unidades en available); se emite comprobante de anulación y se registra en bitácora.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU28-02",
                "accion": "Encargado de tienda cancela una reserva por fuerza mayor o solicitud expresa en mostrador registrando el motivo.",
                "resultado": "Status pasa a CANCELLED_BY_STORE; inventario liberado en la sucursal; notificación automática enviada al cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU28-03",
                "accion": "Intentar cancelar una reserva que ya fue completada (COMPLETED) o que ya se encuentra cancelada.",
                "resultado": "HTTP 400 Bad Request “La reserva ya fue procesada o cancelada con anterioridad; no puede modificarse”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU28-04",
                "accion": "Un cliente intenta cancelar una reserva perteneciente a otro usuario mediante manipulación de parámetros.",
                "resultado": "Respuesta HTTP 403 / 404; el sistema restringe la operación exclusivamente al titular de la cita.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Cliente / Encargado de Sucursal",
        "adjunto": "Vista Mis Reservas (/tienda/reservas) y App Móvil (reservations_view.dart)"
    },
    {
        "id": "CU29",
        "nombre": "Gestionar envíos a domicilio: despacho, bolsa de pedidos y portal del repartidor con foto de evidencia",
        "descripcion": "Verificar el ciclo logístico integral: empaquetado y despacho por el Encargado, toma de envíos desde la bolsa de pedidos por el Repartidor, actualización en ruta y entrega con fotografía de evidencia obligatoria.",
        "precondiciones": [
            "a) Existencia de una orden de venta pagada con modalidad 'Envío a domicilio'.",
            "b) Usuario con rol REPARTIDOR activo y habilitado en el sistema.",
            "c) Encargado de sucursal con sesión activa en el panel de despacho."
        ],
        "pasos": [
            {
                "id": "P-CU29-01",
                "accion": "Encargado genera el despacho de una orden pagada desde /admin/shipments.",
                "resultado": "Se crea registro en shipments con guía única TRK-{hash}, estado READY_FOR_PICKUP y evento inicial registrado en shipment_tracking_events.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU29-02",
                "accion": "Repartidor consulta la bolsa de envíos disponibles (GET /logistics/shipments/available) y toma el pedido (claim).",
                "resultado": "El envío se asigna al repartidor; su estado cambia a ASSIGNED y desaparece de la bolsa pública para otros choferes.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU29-03",
                "accion": "Repartidor actualiza el estado del paquete a IN_TRANSIT (En camino al domicilio).",
                "resultado": "Se actualiza el estado del envío, se registra la marca de tiempo y coordenadas GPS, y se envía notificación in-app al cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU29-04",
                "accion": "Repartidor confirma entrega exitosa adjuntando obligatoriamente la fotografía de evidencia y nombre del receptor.",
                "resultado": "Envío pasa a DELIVERED; orden pasa a ENTREGADA; la fotografía se almacena en el servidor y se vincula al registro de entrega; auditoría de confirmación registrada.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU29-05",
                "accion": "Repartidor reporta entrega fallida por ausencia del cliente o dirección no encontrada.",
                "resultado": "Envío cambia a FAILED_ATTEMPT; se guarda el motivo del fallo y se habilita la reprogramación de visita notificando al cliente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU29-06",
                "accion": "Intentar confirmar la entrega del paquete sin adjuntar la fotografía de evidencia requerida.",
                "resultado": "HTTP 422 Unprocessable Entity “La fotografía de evidencia es obligatoria para confirmar la entrega del paquete”.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Encargado de Sucursal / Repartidor",
        "adjunto": "Portal Web del Repartidor (/repartidor) y Pantalla Móvil (delivery_dashboard_view.dart)"
    },
    {
        "id": "CU30",
        "nombre": "Rastrear el estado de un envío (código TRK-...)",
        "descripcion": "Verificar la consulta pública y privada del seguimiento en tiempo real de paquetes mediante código de guía TRK, mostrando línea de tiempo y eventos.",
        "precondiciones": [
            "a) Existencia de un despacho activo con número de guía único asignado.",
            "b) Conexión a internet y disponibilidad de la interfaz pública de rastreo en web o app móvil."
        ],
        "pasos": [
            {
                "id": "P-CU30-01",
                "accion": "Visitante ingresa un código de seguimiento válido (ej. TRK-8F2A19BC) en la barra de rastreo público.",
                "resultado": "Se despliega la línea de tiempo completa del envío (Alistado, Asignado, En camino, Entregado), sucursal de origen y fecha estimada sin necesidad de iniciar sesión.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU30-02",
                "accion": "Cliente consulta el rastreo de su paquete desde su historial de compras autenticado (/tienda/mis-compras).",
                "resultado": "Visualiza el seguimiento en tiempo real, nombre del repartidor asignado, eventos con hora exacta y la fotografía de entrega al completarse.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU30-03",
                "accion": "Ingresar un código de rastreo inexistente o con formato incorrecto en el buscador.",
                "resultado": "Se muestra mensaje descriptivo “No se encontró ningún envío asociado al código de seguimiento ingresado”.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Pantalla Pública de Rastreo (/tienda/rastreo) y App Móvil (tracking_view.dart)"
    },
    {
        "id": "CU31",
        "nombre": "Gestionar zonas de cobertura y tarifas de envío (anillos por km)",
        "descripcion": "Verificar la configuración de zonas de entrega por anillos de kilometraje sobre mapa interactivo Leaflet y el cálculo dinámico de fletes por distancia.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ADMINISTRADOR (Casa Matriz).",
            "b) Módulo de logística y zonas de cobertura habilitado.",
            "c) Coordenadas base de sucursales despachadoras configuradas."
        ],
        "pasos": [
            {
                "id": "P-CU31-01",
                "accion": "Como SUPERADMIN, crear una nueva zona de cobertura configurando radio en kilómetros (0 a 5 km = Bs 15, 5 a 15 km = Bs 25, tiempo estimado 45 min).",
                "resultado": "La zona se almacena en delivery_zones, se dibuja el polígono/radio en el mapa interactivo Leaflet y se registra auditoría INSERT.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU31-02",
                "accion": "Cliente cotiza tarifa de envío introduciendo su dirección y coordenadas geográficas en el checkout.",
                "resultado": "El endpoint calculate-rate computa la distancia haversine respecto a la sucursal más cercana y retorna la tarifa exacta y tiempo de entrega estimado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU31-03",
                "accion": "Cotizar envío para una ubicación situada fuera del radio de cobertura máximo configurado.",
                "resultado": "El sistema advierte de forma transparente “La dirección indicada se encuentra fuera del área de cobertura de delivery”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU31-04",
                "accion": "Usuario con rol CLIENTE o CAJERO intenta modificar las tarifas de zonas de delivery.",
                "resultado": "Respuesta HTTP 403 Forbidden; edición restringida exclusivamente a Casa Matriz.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Mapa Interactivo de Zonas y Tarifas (/admin/delivery-zones)"
    },
    {
        "id": "CU32",
        "nombre": "Probador (vestidor) virtual con IA / RA y biometría anatómica",
        "descripcion": "Comprobar el amoldado anatómico fotorrealista de prendas sobre la silueta del usuario, segmentación agnóstica de pose y recomendación antropométrica de talla.",
        "precondiciones": [
            "a) Catálogo de prendas activas con fotografías frontales en alta resolución y máscaras de segmentación.",
            "b) Módulo de Inteligencia Artificial (servicios ONNX / FASHN / simulador anatómico) activo en el backend.",
            "c) Usuario o visitante con acceso a cámara fotográfica o galería de imágenes."
        ],
        "pasos": [
            {
                "id": "P-CU32-01",
                "accion": "Usuario sube su fotografía corporal completa, especifica altura y contextura, y selecciona una prenda superior del catálogo.",
                "resultado": "El pipeline de IA detecta la pose anatómica, aísla la silueta, remueve las mangas de la vestimenta anterior y genera la imagen amoldada con ajuste proporcional realista.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU32-02",
                "accion": "Recomendación biométrica de talla: Usuario ingresa sus medidas corporales de busto/tórax, cintura y cadera.",
                "resultado": "El algoritmo compara los datos con la tabla de patronaje de la prenda y recomienda la talla óptima (S, M, L, XL) informando el índice de ajuste.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU32-03",
                "accion": "Usuario sube una fotografía con fondo complejo o saturado.",
                "resultado": "El servicio de eliminación de fondo (remove-background) segmenta con precisión la silueta del usuario preservando el rostro y cuello intactos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU32-04",
                "accion": "Subir archivo con extensión no válida (ej. .exe, .pdf) o con peso superior a 10 MB.",
                "resultado": "Respuesta HTTP 415 o HTTP 400 informando que solo se admiten imágenes JPG, PNG o WebP de hasta 10 MB.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Módulo de Probador Virtual (/tienda/vestidor) y Pantalla Móvil (virtual_tryon_view.dart)"
    },
    {
        "id": "CU33",
        "nombre": "Asistente IA (chatbot) de recomendaciones y estilista virtual",
        "descripcion": "Verificar la atención automatizada con procesamiento de lenguaje natural, recomendación inteligente de conjuntos según ocasión y resolución de dudas.",
        "precondiciones": [
            "a) Servicio de Chatbot IA activo en el backend (/analytics/chatbot/message).",
            "b) Catálogo de productos con atributos de ocasión, estilo, categoría y colores debidamente registrados.",
            "c) Conectividad operativa con la base de datos de productos."
        ],
        "pasos": [
            {
                "id": "P-CU33-01",
                "accion": "Usuario consulta: “Busco una combinación casual para una cena formal en la noche”.",
                "resultado": "El asistente identifica intenciones y ocasión, consulta el catálogo y responde con una recomendación estilística acompañada de tarjetas de prendas con foto, precio y enlace directo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU33-02",
                "accion": "Usuario pregunta sobre políticas comerciales: “¿Cuáles son los costos de envío y el plazo de devolución?”.",
                "resultado": "El chatbot responde con precisión informando las tarifas por zona de delivery y el plazo de 30 días para cambios.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU33-03",
                "accion": "Usuario realiza consulta con términos en plural o diminutivos: “poleritas negras talla M”.",
                "resultado": "El analizador lematiza los términos (polera, negro, M) y recupera las variantes exactas con stock disponible.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU33-04",
                "accion": "Enviar mensaje vacío o cadena de caracteres incomprensible.",
                "resultado": "El asistente responde amablemente guiando al usuario con opciones interactivas sugeridas (Novedades, Ocasión, Ofertas).",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Widget Flotante de Chatbot en Tienda Web y Vista Móvil (chatbot_view.dart)"
    },
    {
        "id": "CU34",
        "nombre": "Búsqueda de prendas por voz con procesamiento NLP",
        "descripcion": "Validar el reconocimiento de voz por micrófono, transcripción y extracción semántica de entidades para filtrado instantáneo del catálogo.",
        "precondiciones": [
            "a) Dispositivo con hardware de micrófono disponible y permisos concedidos en el navegador o app móvil.",
            "b) Servicio de reconocimiento de voz y extracción NLP configurado en backend y frontend.",
            "c) Catálogo de prendas activo en el sistema."
        ],
        "pasos": [
            {
                "id": "P-CU34-01",
                "accion": "Usuario presiona el icono de micrófono y pronuncia: “Busco vestido de fiesta rojo menor a 250 bolivianos”.",
                "resultado": "El sistema captura el audio, transcribe el texto, extrae entidades (categoría: vestido, ocasión: fiesta, color: rojo, precio_máx: 250), aplica los filtros y despliega la lista coincidente.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU34-02",
                "accion": "Usuario dicta una búsqueda rápida por voz: “camisas blancas”.",
                "resultado": "Reconocimiento inmediato y redirección a la grilla de productos con el filtro de categoría camisa y color blanco aplicado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU34-03",
                "accion": "Usuario deniega los permisos de acceso al micrófono en el dispositivo.",
                "resultado": "La interfaz captura el evento e informa educadamente: “Permiso de micrófono requerido para utilizar la búsqueda por voz”.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU34-04",
                "accion": "Presionar el micrófono y permanecer en silencio absoluto durante la grabación.",
                "resultado": "El temporizador de silencio (1.5 segundos) finaliza la captura automáticamente sin bloquear la pantalla.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Botón de Micrófono en Barra de Búsqueda Web y Pantalla Móvil (catalogo_view.dart)"
    },
    {
        "id": "CU35",
        "nombre": "Reportes gerenciales (kardex, más vendidos, resumen ejecutivo, CSV, lectura por voz)",
        "descripcion": "Verificar la emisión de reportes analíticos para toma de decisiones: Kardex valorado con Costo Promedio Ponderado, ranking de ventas, exportación a CSV y síntesis de voz.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ADMINISTRADOR (Casa Matriz).",
            "b) Módulo de reportes gerenciales habilitado en el panel (/admin/reports).",
            "c) Registros históricos de compras, ventas y movimientos en el libro mayor de inventario."
        ],
        "pasos": [
            {
                "id": "P-CU35-01",
                "accion": "Generar Kardex físico-valorado seleccionando sucursal y rango de fechas con cálculo de Costo Promedio Ponderado.",
                "resultado": "Se despliega la tabla detallada de entradas, salidas, saldos y costo medio; botón de exportación CSV genera archivo descargable con datos exactos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU35-02",
                "accion": "Generar reporte de productos más vendidos (Top Selling) por categoría y volumen facturado.",
                "resultado": "Gráfica interactiva y tabla con ranking de variantes, unidades vendidas, ingresos brutos y rotación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU35-03",
                "accion": "Presionar el botón de lectura ejecutiva por voz (Text-to-Speech) del resumen gerencial.",
                "resultado": "La síntesis de voz reproduce claramente en audio los indicadores clave del periodo (ventas totales, pedidos y rendimiento de inventario).",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU35-04",
                "accion": "Usuario con rol CAJERO o CLIENTE intenta consultar los reportes gerenciales.",
                "resultado": "HTTP 403 Forbidden; acceso estrictamente reservado a la gerencia de Casa Matriz.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin (Gerencia General)",
        "adjunto": "Módulo de Reportes Gerenciales y Kardex (/admin/reports)"
    },
    {
        "id": "CU39",
        "nombre": "Dashboard global analítico y KPIs de ventas e inventario",
        "descripcion": "Comprobar la consolidación gráfica y métricas en tiempo real del negocio: ingresos, ticket medio, tasa de conversión, rotación y ventas por sucursal.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN (Casa Matriz).",
            "b) Datos transaccionales de ventas, clientes e inventario en la base de datos.",
            "c) Módulo de analítica y business intelligence habilitado (/admin/analytics-dashboard)."
        ],
        "pasos": [
            {
                "id": "P-CU39-01",
                "accion": "SUPERADMIN accede al Dashboard Analítico Global.",
                "resultado": "Carga en tiempo real de tarjetas de KPIs (Ventas del mes, Ticket promedio, Margen bruto, Órdenes activas), gráfico de barras de ventas por sucursal y gráfico de tendencias de ventas.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU39-02",
                "accion": "Filtrar el dashboard analítico por diferentes periodos (Hoy, Últimos 7 días, Mes actual, Todo el año).",
                "resultado": "Todas las métricas y series temporales se recalculan dinámicamente según el intervalo seleccionado.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU39-03",
                "accion": "Usuario con rol ENCARGADO o CAJERO intenta acceder a la ruta /admin/analytics-dashboard.",
                "resultado": "El guard de navegación redirige al dashboard operativo de su sucursal o deniega con HTTP 403.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Superadmin / Dirección Ejecutiva",
        "adjunto": "Dashboard Global Analítico de Negocio (/admin/analytics-dashboard)"
    },
    {
        "id": "CU40",
        "nombre": "Centro de notificaciones in-app y correos transaccionales",
        "descripcion": "Verificar la emisión, recepción en vivo y marcado de lectura de notificaciones del sistema ante eventos clave (compras, citas, envíos) y correos de respaldo.",
        "precondiciones": [
            "a) Usuario autenticado con sesión activa en web o aplicación móvil.",
            "b) Servicio de eventos de notificación in_app_notifications y cola SMTP habilitados.",
            "c) Eventos transaccionales en ejecución en el backend."
        ],
        "pasos": [
            {
                "id": "P-CU40-01",
                "accion": "Se produce un evento relevante para el usuario (ej. compra confirmada o probador listo para cita).",
                "resultado": "Se incrementa el contador visual de la campana en la barra superior; el desplegable lista la notificación con título, mensaje, timestamp y enlace directo.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU40-02",
                "accion": "Hacer clic en una notificación para leerla y accionar la opción 'Marcar todas como leídas'.",
                "resultado": "El contador de no leídas se reinicia a 0; el campo is_read se actualiza a true en la base de datos.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU40-03",
                "accion": "Disparo de correo electrónico transaccional de respaldo vía SMTP ante un cambio de estado crítico (ej. pedido despachado).",
                "resultado": "El correo llega a la bandeja de entrada del usuario con formato corporativo HTML y detalle completo de la operación.",
                "estado": "Satisfactorio"
            },
            {
                "id": "P-CU40-04",
                "accion": "Intentar consultar o modificar notificaciones de otro usuario inyectando un user_id ajeno.",
                "resultado": "El sistema restringe la consulta estrictamente al ID autenticado en el token JWT; deniega el acceso con HTTP 403.",
                "estado": "Satisfactorio"
            }
        ],
        "responsable": "Usuario Autenticado (Cliente / Personal / Repartidor)",
        "adjunto": "Menú Desplegable de Notificaciones y Pantalla Móvil (notifications_view.dart)"
    }
]
