# -*- coding: utf-8 -*-
"""
Dataset Completo de Pruebas Funcionales de Caja Negra (5 Columnas)
Formato Oficial Exigido: M.Sc. Angélica Garzón (INF-412 - Sistemas de Información II)
Columnas: Paso | Acción | Resultado esperado | Estado (Satisfactorio/Fallido) | Precondición
"""

CICLO_1_PRUEBAS = [
    {
        "id": "CU01",
        "nombre": "Iniciar sesión",
        "descripcion": "Validar autenticación por credenciales, normalización de correo electrónico a minúsculas, emisión de token JWT y control de cuentas activas/inactivas.",
        "precondiciones": [
            "a) La base de datos relacional PostgreSQL y el backend FastAPI se encuentran operativos.",
            "b) El usuario debe encontrarse previamente registrado en la tabla users.",
            "c) El cliente web o app móvil tiene conectividad de red con el endpoint /api/v1/auth/login."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Ingresar correo con mayúsculas y minúsculas mixtas 'Cliente@GMAIL.com' y contraseña válida 'Password#2026'. Presionar 'Iniciar Sesión'.",
                "resultado": "HTTP 200 OK; el sistema normaliza el correo a 'cliente@gmail.com', valida el hash BCrypt, retorna JWT con claims de usuario/rol, inserta registro LOGIN en bitácora de auditoría y redirige a la vista inicial según su rol.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario activo registrado con correo 'cliente@gmail.com' y rol CLIENTE asignado."
            },
            {
                "id": "2",
                "accion": "Ingresar correo registrado 'cliente@gmail.com' y contraseña deliberadamente incorrecta 'ClaveInvalida999'.",
                "resultado": "HTTP 400 Bad Request con mensaje descriptivo 'Correo electrónico o contraseña incorrectos'; no se genera sesión ni token JWT; se audita intento fallido.",
                "estado": "Satisfactorio",
                "precondicion": "Cuenta de usuario existente en la base de datos."
            },
            {
                "id": "3",
                "accion": "Ingresar credenciales correctas de un usuario cuya cuenta fue desactivada administrativamente (is_active = false).",
                "resultado": "HTTP 403 Forbidden; el sistema bloquea el acceso informando 'La cuenta se encuentra desactivada. Contacte al administrador'; no se emite token.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario existente en la base de datos con campo is_active = false."
            },
            {
                "id": "4",
                "accion": "Enviar petición de inicio de sesión dejando los campos de correo y contraseña vacíos (payload nulo o strings vacíos).",
                "resultado": "HTTP 422 Unprocessable Entity; la validación de Pydantic rechaza la solicitud indicando los campos obligatorios faltantes; formulario marca bordes en rojo.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de inicio de sesión visible en pantalla."
            }
        ],
        "responsable": "Usuario / Cliente / Administrador",
        "adjunto": "Pantalla de Login (/login) y modal de autenticación web/móvil"
    },
    {
        "id": "CU02",
        "nombre": "Cerrar sesión",
        "descripcion": "Verificar revocación de sesión, inclusión del token JWT en la lista negra (blacklist), invalidación de peticiones y limpieza de credenciales locales.",
        "precondiciones": [
            "a) El usuario debe contar con una sesión activa y un token JWT válido.",
            "b) El cliente web o app móvil almacena el token en almacenamiento seguro (LocalStorage / SecureStorage).",
            "c) El servicio de autenticación y la lista de revocación de sesiones se encuentran operativos en el backend."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Con sesión activa en la aplicación, desplegar el menú de usuario en la barra superior, presionar 'Cerrar sesión' y confirmar el diálogo emergente.",
                "resultado": "El token queda registrado en la blacklist del servidor, se audita el evento LOGOUT con timestamp e IP, se eliminan los tokens de almacenamiento local y se redirige inmediatamente al login.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con token JWT válido y usuario autenticado."
            },
            {
                "id": "2",
                "accion": "Intentar invocar un endpoint protegido (ej. GET /api/v1/auth/me) reutilizando en el encabezado Authorization el token JWT previamente revocado.",
                "resultado": "HTTP 401 Unauthorized; el interceptor de seguridad valida la revocación del token y rechaza la petición sin exponer ninguna información del perfil.",
                "estado": "Satisfactorio",
                "precondicion": "Token JWT revocado en el paso anterior mediante logout exitoso."
            },
            {
                "id": "3",
                "accion": "Accionar 'Cerrar sesión' cuando el token JWT del cliente ya ha expirado por límite de tiempo de vida (TTL excedido).",
                "resultado": "El sistema limpia automáticamente los datos locales sin arrojar excepciones no controladas y muestra la pantalla de login de forma fluida.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión expirada por inactividad en el cliente."
            }
        ],
        "responsable": "Usuario Autenticado",
        "adjunto": "Menú superior de perfil de usuario y pantalla de redirección al Login"
    },
    {
        "id": "CU03",
        "nombre": "Recuperar credenciales",
        "descripcion": "Verificar restablecimiento de contraseña mediante enlace temporal, criptográficamente seguro, de un solo uso y con expiración máxima de 5 minutos.",
        "precondiciones": [
            "a) El servicio de correo electrónico SMTP transaccional debe estar configurado y activo.",
            "b) Conectividad operativa con la base de datos para la generación y validación de tokens de reseteo.",
            "c) El usuario debe tener acceso a la bandeja de entrada del correo asociado a su cuenta."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Ingresar correo registrado 'cliente@gmail.com' en /forgot-password, abrir el enlace temporal recibido por correo e introducir nueva contraseña válida 'NuevaClave#2026'.",
                "resultado": "Se muestra mensaje neutro de confirmación; se cifra la nueva contraseña con BCrypt; se anula el token utilizado y se registran RECOVER y RESET_PASSWORD en la bitácora.",
                "estado": "Satisfactorio",
                "precondicion": "Cuenta registrada y operativa en el sistema con correo accesible."
            },
            {
                "id": "2",
                "accion": "Solicitar recuperación ingresando una dirección de correo no registrada 'inexistente@correo.com'.",
                "resultado": "El sistema devuelve exactamente el mismo mensaje neutro de confirmación sin revelar si la cuenta existe o no, mitigando ataques de enumeración de usuarios.",
                "estado": "Satisfactorio",
                "precondicion": "Acceso a la vista pública de recuperación de contraseña."
            },
            {
                "id": "3",
                "accion": "Intentar usar un enlace de recuperación cuya vigencia superó los 5 minutos o que ya fue utilizado en el paso 1.",
                "resultado": "Se rechaza la operación mostrando el mensaje de alerta 'El enlace es inválido o expiró (5 minutos)'; no se modifica la contraseña.",
                "estado": "Satisfactorio",
                "precondicion": "Token de recuperación vencido o previamente invalidado en base de datos."
            }
        ],
        "responsable": "Usuario / Visitante",
        "adjunto": "Formulario de recuperación (/forgot-password) y plantilla de correo HTML recibido"
    },
    {
        "id": "CU04",
        "nombre": "Auto-registro de cliente",
        "descripcion": "Verificar el alta pública de cuentas de usuario con asignación automática y exclusiva del rol CLIENTE, normalización de datos y validación de contraseñas robustas.",
        "precondiciones": [
            "a) Formulario público de registro accesible en la tienda web o aplicación móvil.",
            "b) El rol CLIENTE debe estar previamente inicializado en la tabla roles.",
            "c) Base de datos lista para admitir transacciones de inserción."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Completar formulario con nombre 'María López', correo 'Maria.Lopez@Example.com', teléfono '70012345' y contraseña robusta 'Segura*2026'. Presionar 'Registrarme'.",
                "resultado": "HTTP 201 Created; se inserta usuario activo con correo en minúsculas 'maria.lopez@example.com', contraseña en BCrypt, asignación exclusiva del rol CLIENTE y auditoría REGISTER.",
                "estado": "Satisfactorio",
                "precondicion": "Correo electrónico no existente previamente en la base de datos."
            },
            {
                "id": "2",
                "accion": "Intentar registrar un nuevo usuario utilizando el mismo correo anterior pero con otra capitalización 'MARIA.LOPEZ@EXAMPLE.COM'.",
                "resultado": "HTTP 409 Conflict; el sistema detecta la duplicidad por índice único en minúsculas e informa 'El correo electrónico ya se encuentra registrado'.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario 'maria.lopez@example.com' registrado previamente."
            },
            {
                "id": "3",
                "accion": "Ingresar contraseña débil '12345' o confirmar con un valor discrepante 'Segura*2026' vs 'OtraCosa'.",
                "resultado": "Validación en cliente y servidor rechaza el envío; se indican los requisitos incumplidos y no se crea ningún registro en base de datos.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de registro abierto en pantalla."
            }
        ],
        "responsable": "Visitante / Nuevo Cliente",
        "adjunto": "Formulario de Registro de Usuario (/register)"
    },
    {
        "id": "CU05",
        "nombre": "Gestionar perfiles, roles y clientes",
        "descripcion": "Validar la creación administrativa de cuentas internas, asignación controlada de roles, modificación de datos y baja lógica de usuarios por el Superadmin.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN (Casa Matriz).",
            "b) Módulo de administración de usuarios y roles habilitado en el panel administrativo.",
            "c) Catálogo de roles cargado en el sistema (SUPERADMIN, ENCARGADO, CAJERO, REPARTIDOR, PROVEEDOR, CLIENTE)."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Como SUPERADMIN, acceder a /admin/users, crear un usuario interno 'Carlos Encargado' con rol ENCARGADO y contraseña inicial asignada.",
                "resultado": "Se guardan datos en users, se crea relación en user_roles, contraseña cifrada en BCrypt y se registra INSERT en auditoría.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión activa con privilegios de SUPERADMIN."
            },
            {
                "id": "2",
                "accion": "Editar el perfil de un usuario existente, cambiar sus roles y presionar el botón 'Desactivar cuenta'.",
                "resultado": "Se actualizan los campos, se aplica baja lógica estableciendo is_active = false sin destruir los datos históricos ni referencias, y se audita UPDATE.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario existente previamente en estado activo."
            },
            {
                "id": "3",
                "accion": "Intentar acceder al módulo /admin/users con un token correspondiente a un usuario con rol CLIENTE o CAJERO.",
                "resultado": "HTTP 403 Forbidden; el interceptor de roles bloquea el acceso de inmediato y no permite lectura ni escritura.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con un rol que carece de privilegios administrativos."
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Panel Administrativo de Usuarios y Asignación de Roles (/admin/users)"
    },
    {
        "id": "CU06",
        "nombre": "Gestionar sucursales",
        "descripcion": "Verificar el alta y mantenimiento de sucursales físicas (restringidas al departamento de Santa Cruz) y la asignación controlada de personal.",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN (Casa Matriz).",
            "b) Módulo de sucursales activo en el panel de control.",
            "c) Coordenadas geográficas y datos de contacto de la sucursal disponibles."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Registrar sucursal 'Sucursal Norte', dirección 'Av. Banzer 4to Anillo', ciudad 'Santa Cruz de la Sierra', teléfono '33445566' y coordenadas lat/long válidas.",
                "resultado": "La sucursal se guarda en branches con código generado; se valida pertenencia al departamento de Santa Cruz y se registra INSERT en auditoría.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN y datos geográficos válidos."
            },
            {
                "id": "2",
                "accion": "Asignar un usuario con rol ENCARGADO a la 'Sucursal Norte' recién registrada.",
                "resultado": "Se crea la relación en branch_employees, se valida que la sucursal no posea otro encargado activo y se registra la asignación en la bitácora.",
                "estado": "Satisfactorio",
                "precondicion": "Sucursal registrada y usuario con rol ENCARGADO disponible sin asignación previa."
            },
            {
                "id": "3",
                "accion": "Intentar registrar una sucursal con un nombre duplicado 'Sucursal Norte' o asignar un usuario con rol CLIENTE a la sucursal.",
                "resultado": "Se rechaza la operación; validación de unicidad de nombre y restricción de roles (únicamente ENCARGADO o CAJERO permitidos).",
                "estado": "Satisfactorio",
                "precondicion": "Sucursal existente con el mismo nombre en la base de datos."
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Módulo de Sucursales y Asignación de Tiendas (/admin/branches)"
    },
    {
        "id": "CU07",
        "nombre": "Gestionar catálogo",
        "descripcion": "Comprobar la parametrización de categorías, prendas y la creación estricta de variantes únicas por combinación de color, talla y SKU.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ADMINISTRADOR de catálogo.",
            "b) Categorías base, paletas de colores y tallas creadas en el sistema.",
            "c) Módulo de catálogo habilitado para carga de productos y fotografías."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Crear prenda 'Camisa Oxford Manga Larga' con categoría 'Camisas', y añadir 2 variantes: Azul/M con SKU 'CAM-OXF-AZ-M' y Blanco/L con SKU 'CAM-OXF-BL-L'.",
                "resultado": "Se persiste la jerarquía Prenda → Variantes con precios base y especificaciones técnicas; se genera auditoría INSERT.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión con rol SUPERADMIN y parámetros de color/talla disponibles."
            },
            {
                "id": "2",
                "accion": "Intentar registrar una tercera variante reutilizando el SKU 'CAM-OXF-AZ-M' o la misma combinación Azul + M para la misma prenda.",
                "resultado": "HTTP 409 Conflict; el sistema rechaza la variante duplicada por restricción de clave única sin alterar las demás variantes.",
                "estado": "Satisfactorio",
                "precondicion": "Variante previa con SKU 'CAM-OXF-AZ-M' registrada en catálogo."
            },
            {
                "id": "3",
                "accion": "Marcar la prenda activa como oculta/inactiva (is_active = false) desde el listado de productos.",
                "resultado": "Se actualiza el registro en base de datos; la prenda deja de mostrarse de inmediato en la tienda pública web y app móvil.",
                "estado": "Satisfactorio",
                "precondicion": "Prenda activa visible previamente en el catálogo público."
            }
        ],
        "responsable": "Administrador de Catálogo",
        "adjunto": "Formulario de Productos y Variantes (/admin/products)"
    },
    {
        "id": "CU08",
        "nombre": "Gestionar proveedores",
        "descripcion": "Verificar el mantenimiento del directorio de proveedores comerciales, validación de NIT único y datos de contacto.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN.",
            "b) Módulo de proveedores habilitado en el panel administrativo.",
            "c) Datos fiscales (NIT, razón social, dirección y teléfono) disponibles."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Como SUPERADMIN, registrar proveedor 'Textiles Andinos S.R.L.', NIT '1020304050', contacto 'Ing. Roberto Paz', teléfono '71020304'.",
                "resultado": "El proveedor se guarda con estado activo en suppliers, queda habilitado para órdenes de compra y se registra INSERT en auditoría.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN y NIT no existente en el sistema."
            },
            {
                "id": "2",
                "accion": "Intentar registrar un segundo proveedor comercial utilizando el mismo NIT '1020304050'.",
                "resultado": "El sistema rechaza la operación informando que el NIT ya se encuentra registrado por otra empresa proveedora.",
                "estado": "Satisfactorio",
                "precondicion": "Proveedor existente previamente con NIT '1020304050'."
            },
            {
                "id": "3",
                "accion": "Intentar crear o editar un proveedor utilizando una cuenta con rol CLIENTE o PROVEEDOR.",
                "resultado": "HTTP 403 Forbidden; únicamente Casa Matriz con rol SUPERADMIN tiene autorización para gestionar el directorio.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario autenticado con rol diferente de SUPERADMIN."
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Directorio de Proveedores (/admin/suppliers)"
    },
    {
        "id": "CU09",
        "nombre": "Gestionar empleados de sucursal",
        "descripcion": "Validar la creación de empleados y su asignación exclusiva a sucursales físicas (1 Encargado por sucursal).",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN.",
            "b) Al menos una sucursal física activa creada en la base de datos.",
            "c) Usuarios con rol ENCARGADO o CAJERO disponibles para asignación."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Crear empleado con rol ENCARGADO y vincularlo a la 'Sucursal Central'.",
                "resultado": "Se crea usuario, rol y relación en branch_employees; el empleado queda vinculado formalmente a sucursal y se audita INSERT.",
                "estado": "Satisfactorio",
                "precondicion": "Sucursal Central sin encargado activo asignado."
            },
            {
                "id": "2",
                "accion": "Intentar asignar un segundo usuario con rol ENCARGADO a la misma 'Sucursal Central'.",
                "resultado": "Se rechaza la operación informando que la sucursal ya cuenta con un Encargado activo (regla: 1 encargado por sucursal).",
                "estado": "Satisfactorio",
                "precondicion": "Sucursal Central con un encargado ya asignado."
            },
            {
                "id": "3",
                "accion": "Intentar realizar asignaciones de personal sin permisos o cuando no existen sucursales dadas de alta.",
                "resultado": "HTTP 403 para usuarios sin permiso, o mensaje de validación indicando que debe registrarse una sucursal previa.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario sin privilegios de administración."
            }
        ],
        "responsable": "Superadmin (Casa Matriz)",
        "adjunto": "Módulo de Empleados de Sucursal (/admin/branch-employees)"
    },
    {
        "id": "CU10",
        "nombre": "Registrar compras e ingresos de mercadería",
        "descripcion": "Verificar la transacción ACID de stock físico, actualización del libro mayor (ledger) y recálculo matemático del Costo Promedio Ponderado (CPP).",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN o ENCARGADO de la sucursal receptora.",
            "b) Existencia de proveedor activo y prendas con variantes en el catálogo.",
            "c) Base de datos con soporte transaccional para actualizar inventario y libro mayor simultáneamente."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Registrar dos ingresos consecutivos de la variante SKU 'CAM-OXF-AZ-M' en sucursal Central: primer ingreso de 1 unidad a Bs 10; segundo ingreso de 1 unidad a Bs 14.",
                "resultado": "Stock resultante 2 unidades; Costo Promedio Ponderado avg_cost = Bs 12 ((1*10 + 1*14)/2); se registran movimientos INGRESO en ledger con referencia OC-{id} y auditoría completa.",
                "estado": "Satisfactorio",
                "precondicion": "Variante registrada y sucursal receptora operativa."
            },
            {
                "id": "2",
                "accion": "Intentar registrar un ingreso de mercadería con cantidad <= 0 o costo unitario de compra <= 0.",
                "resultado": "Se rechaza la transacción por validación de reglas de negocio; no se persiste ningún cambio parcial en inventario ni contabilidad.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de compras abierto en pantalla."
            },
            {
                "id": "3",
                "accion": "Intentar registrar ingreso asociando un proveedor o sucursal inexistente, o intentar la operación con rol CAJERO.",
                "resultado": "HTTP 404 para entidades inexistentes o HTTP 403 para roles no autorizados; atomicidad de la base de datos preservada.",
                "estado": "Satisfactorio",
                "precondicion": "Petición HTTP con identificadores inexistentes o credenciales no autorizadas."
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Formulario de Ingreso de Mercadería (/admin/purchases/new)"
    },
    {
        "id": "CU11",
        "nombre": "Consultar catálogo (cliente)",
        "descripcion": "Validar la consulta pública, búsqueda y filtro de prendas activas sin requerir autenticación.",
        "precondiciones": [
            "a) Tienda web o app móvil desplegada y accesible al público.",
            "b) Existencia de al menos una prenda activa (is_active = true) con fotografías y precio cargado.",
            "c) Conectividad operativa con el backend de catálogo."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Como visitante anónimo, abrir la tienda principal (/tienda) en el navegador o app.",
                "resultado": "Se muestra la grilla de productos activos con imagen principal, nombre, categoría y precio en Bs, sin exigir autenticación.",
                "estado": "Satisfactorio",
                "precondicion": "Catálogo de productos con prendas activas en base de datos."
            },
            {
                "id": "2",
                "accion": "Escribir 'Oxford' en la barra de búsqueda y filtrar por la categoría 'Camisas'.",
                "resultado": "Se muestran únicamente las prendas activas que coinciden con ambos criterios; paginación preservada.",
                "estado": "Satisfactorio",
                "precondicion": "Prendas que coinciden con el texto 'Oxford' y categoría 'Camisas'."
            },
            {
                "id": "3",
                "accion": "Consultar el catálogo aplicando un filtro de categoría donde no existen prendas activas registradas.",
                "resultado": "Se muestra mensaje informativo 'No hay prendas disponibles por el momento' sin errores de renderizado.",
                "estado": "Satisfactorio",
                "precondicion": "Categoría sin productos activos asociados."
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Grilla de Catálogo Público (/tienda) y App Móvil"
    },
    {
        "id": "CU36",
        "nombre": "Consultar bitácora de auditoría",
        "descripcion": "Verificar la consulta inmutable y restringida de todas las operaciones auditadas en el sistema (INSERT, UPDATE, DELETE, LOGIN, LOGOUT).",
        "precondiciones": [
            "a) Sesión iniciada estrictamente con rol SUPERADMIN.",
            "b) Existencia de registros de auditoría almacenados en la tabla audit_logs.",
            "c) Módulo de auditoría habilitado en el menú de Casa Matriz."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Como SUPERADMIN, acceder a /admin/audit y filtrar los registros por tipo de acción 'INSERT'.",
                "resultado": "Se listan los registros en orden cronológico descendente con fecha/hora, usuario responsable, IP, tabla afectada y detalle de cambios; la bitácora es inalterable.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión activa de SUPERADMIN y operaciones previas auditadas en el sistema."
            },
            {
                "id": "2",
                "accion": "Intentar consultar la bitácora de auditoría con una cuenta con rol ENCARGADO, CAJERO o CLIENTE.",
                "resultado": "HTTP 403 Forbidden; el acceso es bloqueado rotundamente protegiendo la confidencialidad de la trazabilidad.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario autenticado con rol distinto de SUPERADMIN."
            }
        ],
        "responsable": "Superadmin (Auditor)",
        "adjunto": "Visor de Bitácora de Auditoría (/admin/audit)"
    },
    {
        "id": "CU37",
        "nombre": "Consultar valoración de inventario / capital invertido",
        "descripcion": "Comprobar el cálculo del capital invertido utilizando el Costo Promedio Ponderado de las existencias reales.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN o ENCARGADO de sucursal.",
            "b) Existencia de stock físico y costos unitarios registrados en inventory.",
            "c) Algoritmo de Costo Promedio Ponderado operativo."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Consultar valoración de inventario tras los ingresos del CU10 (1 unidad a Bs 10 y 1 unidad a Bs 14).",
                "resultado": "avg_cost = Bs 12, cantidad = 2, valor total = Bs 24 y capital invertido = Bs 24; se comprueba que el sistema no utiliza el último costo sino el costo medio ponderado.",
                "estado": "Satisfactorio",
                "precondicion": "Movimientos de compra del CU10 consolidados en inventario."
            },
            {
                "id": "2",
                "accion": "Filtrar la valoración seleccionando una sucursal específica 'Sucursal Central'.",
                "resultado": "Se calculan únicamente el stock, costo promedio, valor total y capital perteneciente a dicha sucursal física.",
                "estado": "Satisfactorio",
                "precondicion": "Inventario distribuido en sucursales físicas."
            },
            {
                "id": "3",
                "accion": "Consultar valoración de una sucursal recién creada sin existencias, o consultar sin permisos.",
                "resultado": "Inventario vacío muestra capital invertido Bs 0 y mensaje correspondiente; consulta sin permiso retorna HTTP 403.",
                "estado": "Satisfactorio",
                "precondicion": "Sucursal sin stock registrado en la base de datos."
            }
        ],
        "responsable": "Superadmin / Encargado de Sucursal",
        "adjunto": "Reporte de Valoración de Inventario y Capital (/admin/inventory/valuation)"
    },
    {
        "id": "CU38",
        "nombre": "Gestionar ajustes de inventario",
        "descripcion": "Validar el registro de mermas, daños, pérdidas y conteos físicos con trazabilidad, salida de stock y preservación del costo promedio ponderado.",
        "precondiciones": [
            "a) Sesión iniciada como SUPERADMIN o ENCARGADO de la sucursal.",
            "b) La variante de prenda debe contar con inventario activo en la sucursal seleccionada.",
            "c) Catálogo de motivos de ajuste estándar disponible (merma, daño, pérdida, corrección)."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Con stock 2 y avg_cost = Bs 12, registrar un ajuste por merma de -1 unidad indicando motivo 'Prenda rota en exhibición'.",
                "resultado": "Stock se reduce a 1; se registra movimiento AJUSTE con código AJU-{id}, unit_cost = Bs 12, avg_cost se mantiene inalterado en Bs 12 y se audita INSERT.",
                "estado": "Satisfactorio",
                "precondicion": "Variante con stock disponible de 2 unidades y costo medio de Bs 12."
            },
            {
                "id": "2",
                "accion": "Intentar registrar una salida por ajuste mayor al stock disponible (intentar descontar 5 unidades teniendo stock 1).",
                "resultado": "HTTP 400 Bad Request 'Stock insuficiente para realizar el ajuste'; la operación se cancela sin modificar inventario ni ledger.",
                "estado": "Satisfactorio",
                "precondicion": "Variante con stock actual de 1 unidad."
            },
            {
                "id": "3",
                "accion": "Registrar ajuste con cantidad cero, sobre variante inexistente o con rol CAJERO.",
                "resultado": "Rechazo de cantidad cero; HTTP 404 para variante inexistente y HTTP 403 para roles sin autorización.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de ajustes abierto con datos inválidos."
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
        "descripcion": "Validar búsqueda múltiple combinada (precio, talla, color, ocasión) y consulta de disponibilidad de stock por sucursal física.",
        "precondiciones": [
            "a) Catálogo público accesible en versión web o app móvil.",
            "b) Prendas activas con variantes y stock distribuido en sucursales físicas.",
            "c) Conectividad operativa con el backend de catálogo e inventario."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Como visitante, filtrar catálogo por rango de precio [50–200 Bs], talla M, color 'Negro' y ocasión 'Formal'.",
                "resultado": "Se listan únicamente las prendas activas que cumplen todos los criterios; cada variante detalla stock por sucursal (stock > 0 = 'Disponible', 0 = 'Agotado').",
                "estado": "Satisfactorio",
                "precondicion": "Prendas activas registradas con atributos de talla, color y ocasión."
            },
            {
                "id": "2",
                "accion": "Filtrar únicamente por ocasión 'Casual' sin marcar ningún otro filtro.",
                "resultado": "Se muestran todas las prendas activas etiquetadas como Casual; paginación fluida y sin errores de validación.",
                "estado": "Satisfactorio",
                "precondicion": "Prendas activas asociadas a la ocasión 'Casual'."
            },
            {
                "id": "3",
                "accion": "Buscar por texto 'camisa' combinado simultáneamente con filtro de color 'Blanco'.",
                "resultado": "El resultado corresponde a la intersección lógica (búsqueda textual Y filtro color); se muestra disponibilidad por sucursal.",
                "estado": "Satisfactorio",
                "precondicion": "Existencia de camisas blancas en la base de datos."
            },
            {
                "id": "4",
                "accion": "Consultar disponibilidad de una variante específica en la sucursal 'Central'.",
                "resultado": "El endpoint devuelve stock_actual y costo promedio de esa variante en esa sucursal; HTTP 404 si no existe inventario.",
                "estado": "Satisfactorio",
                "precondicion": "Variante registrada en catálogo con existencias en sucursal Central."
            },
            {
                "id": "5",
                "accion": "Introducir un rango de precios inválido donde el precio mínimo es mayor al precio máximo (ej. Min: 300, Max: 100).",
                "resultado": "HTTP 422 Unprocessable Entity 'El precio mínimo no puede ser mayor al máximo'; la interfaz advierte del error al usuario.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de filtros avanzado abierto en pantalla."
            },
            {
                "id": "6",
                "accion": "Ejecutar búsqueda general sin especificar ningún parámetro ni filtro.",
                "resultado": "Devuelve el catálogo general completo paginado según la configuración estándar del sistema.",
                "estado": "Satisfactorio",
                "precondicion": "Catálogo general con productos activos."
            }
        ],
        "responsable": "Visitante / Cliente",
        "adjunto": "Filtros Avanzados y Panel de Stock por Sucursal (/tienda)"
    },
    {
        "id": "CU13",
        "nombre": "Gestionar promociones: cupones y ofertas de temporada",
        "descripcion": "Verificar creación, validación temporal y aplicación de cupones de descuento y campañas automáticas de temporada.",
        "precondiciones": [
            "a) Sesión iniciada con rol SUPERADMIN en Casa Matriz.",
            "b) Módulo de promociones habilitado en el panel administrativo.",
            "c) Catálogo de prendas y categorías disponibles para asociar descuentos."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Como SUPERADMIN, crear cupón 'DESCUENTO20' (20 % de descuento, uso único por cliente, vigencia 7 días).",
                "resultado": "Cupón guardado con código único, fechas starts_at y ends_at válidas; se registra INSERT en auditoría.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN."
            },
            {
                "id": "2",
                "accion": "Crear campaña 'Black Friday' (15 % sobre categoría 'Abrigos', rango 2026-11-25 a 2026-11-30).",
                "resultado": "Campaña creada y asociada a la categoría; fechas validadas y auditoría INSERT generada.",
                "estado": "Satisfactorio",
                "precondicion": "Categoría 'Abrigos' existente en catálogo."
            },
            {
                "id": "3",
                "accion": "Aplicar cupón 'DESCUENTO20' en el carrito de compras con productos elegibles.",
                "resultado": "Total recalculado con el descuento; cupón registrado en coupon_usages para ese cliente evitando reuso posterior.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente con carrito activo y cupón vigente no utilizado previamente."
            },
            {
                "id": "4",
                "accion": "Intentar aplicar un cupón con fecha expirada o que ya fue utilizado previamente por el mismo cliente.",
                "resultado": "HTTP 400 Bad Request 'El cupón no es válido o ya fue utilizado'; el total del carrito se mantiene sin alteraciones.",
                "estado": "Satisfactorio",
                "precondicion": "Cupón expirado o previamente redimido por el usuario."
            },
            {
                "id": "5",
                "accion": "Consultar carrito durante la vigencia de una campaña automática de temporada (sin código).",
                "resultado": "El descuento por categoría se aplica de forma transparente en GET /cart y en checkout sin requerir acción del cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Campaña de temporada activa en la fecha actual."
            },
            {
                "id": "6",
                "accion": "Intentar crear un cupón con porcentaje de descuento >= 100 % o <= 0 %.",
                "resultado": "HTTP 422 por validación de rango permitido; el cupón no se persiste en base de datos.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de cupones abierto en panel administrativo."
            },
            {
                "id": "7",
                "accion": "Editar campaña existente modificando porcentaje y rango de vigencia.",
                "resultado": "Modificaciones guardadas en base de datos; auditoría UPDATE registrada; cupones existentes no afectados.",
                "estado": "Satisfactorio",
                "precondicion": "Campaña registrada previamente."
            },
            {
                "id": "8",
                "accion": "Intentar gestionar promociones con un usuario sin rol SUPERADMIN.",
                "resultado": "HTTP 403 Forbidden y acceso bloqueado al módulo.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario con rol no autorizado (ej. CLIENTE o CAJERO)."
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
            "b) Prendas activas existentes en el catálogo.",
            "c) Rol SUPERADMIN con acceso al panel de moderación de comentarios."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Cliente crea lista 'Regalos Navidad' y añade 3 prendas del catálogo.",
                "resultado": "Lista guardada con is_public = false; ítems vinculados en wishlist_items; auditoría INSERT.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente con sesión iniciada y prendas disponibles en tienda."
            },
            {
                "id": "2",
                "accion": "Cliente activa el toggle público (is_public = true) y obtiene enlace /wishlist/{public_token}.",
                "resultado": "Enlace accesible para cualquier usuario sin login; visualiza prendas, fotos y precios sin permitir edición.",
                "estado": "Satisfactorio",
                "precondicion": "Lista de deseos creada por el cliente."
            },
            {
                "id": "3",
                "accion": "Mover una prenda desde la lista 'Favoritos' hacia 'Regalos Navidad'.",
                "resultado": "El ítem actualiza su wishlist_id de destino sin duplicarse; auditoría UPDATE.",
                "estado": "Satisfactorio",
                "precondicion": "Dos listas de deseos creadas con prendas asignadas."
            },
            {
                "id": "4",
                "accion": "Cliente elimina una lista que contiene prendas agregadas.",
                "resultado": "Se elimina la lista y sus ítems asociados en cascada; auditoría DELETE registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Lista de deseos con ítems en base de datos."
            },
            {
                "id": "5",
                "accion": "Cliente envía reseña de 4 estrellas y comentario en prenda con moderación habilitada.",
                "resultado": "Reseña guardada con status = 'PENDIENTE'; no visible públicamente; se genera alerta para moderación.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente autenticado en la ficha de detalle de producto."
            },
            {
                "id": "6",
                "accion": "SUPERADMIN aprueba la reseña pendiente en el panel de moderación.",
                "resultado": "Status pasa a 'APROBADA'; se publica en la ficha del producto y recalcula el promedio y conteo de votos; auditoría UPDATE.",
                "estado": "Satisfactorio",
                "precondicion": "Reseña en estado PENDIENTE y sesión de SUPERADMIN."
            },
            {
                "id": "7",
                "accion": "SUPERADMIN rechaza reseña especificando motivo 'Contenido inapropiado'.",
                "resultado": "Status pasa a 'RECHAZADA' con motivo almacenado; no se publica ni altera el rating promedio; auditoría UPDATE.",
                "estado": "Satisfactorio",
                "precondicion": "Reseña pendiente en panel de moderación."
            },
            {
                "id": "8",
                "accion": "Cliente edita su reseña que ya se encontraba aprobada.",
                "resultado": "La nueva versión queda en estado PENDIENTE (re-moderación); la versión anterior sigue visible hasta su nueva aprobación.",
                "estado": "Satisfactorio",
                "precondicion": "Reseña previamente aprobada y publicada."
            },
            {
                "id": "9",
                "accion": "Cliente reseña una prenda perteneciente a un pedido previamente entregado.",
                "resultado": "Se asigna automáticamente verified_purchase = true y se muestra la insignia de 'Compra verificada'.",
                "estado": "Satisfactorio",
                "precondicion": "Orden previa entregada al mismo cliente con esa prenda."
            },
            {
                "id": "10",
                "accion": "Usuario vota 'Útil' en una reseña ajena aprobada.",
                "resultado": "Contador de votos útiles incrementado; se valida un único voto por usuario por reseña; auditoría INSERT en review_votes.",
                "estado": "Satisfactorio",
                "precondicion": "Reseña aprobada publicada en la tienda."
            },
            {
                "id": "11",
                "accion": "Comercio (SUPERADMIN o ENCARGADO) responde formalmente a una reseña aprobada.",
                "resultado": "Respuesta institucional registrada y visible debajo de la reseña; auditoría INSERT.",
                "estado": "Satisfactorio",
                "precondicion": "Reseña aprobada con rol de comercio autenticado."
            }
        ],
        "responsable": "Cliente / Superadmin (Moderador)",
        "adjunto": "Módulo de Wishlists (/tienda/favoritos) y Panel de Moderación (/admin/reviews)"
    },
    {
        "id": "CU15",
        "nombre": "Gestionar inventario general y transferencias entre sucursales",
        "descripcion": "Verificar la vista consolidada de stock, el flujo de transferencias entre sucursales y trigger de actualización en tiempo real.",
        "precondiciones": [
            "a) Existencia de al menos dos sucursales físicas activas.",
            "b) Sesión iniciada con rol ENCARGADO de sucursal origen o SUPERADMIN.",
            "c) Stock disponible mayor a cero en la sucursal de origen."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "SUPERADMIN consulta el inventario general consolidado de todas las sucursales.",
                "resultado": "Tabla consolidada: variante, stock por sucursal, stock global total y costo medio ponderado; paginación y búsqueda por SKU operativas.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN."
            },
            {
                "id": "2",
                "accion": "ENCARGADO de sucursal 'Central' inicia transferencia de 5 unidades de SKU 'CAM-OXF-AZ-M' a sucursal 'Norte'.",
                "resultado": "Se crea transfer_order en estado PENDIENTE; stock de origen queda bloqueado/reservado (-5 unidades disponibles), destino sin cambios; auditoría registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Sucursal Central con stock disponible >= 5 unidades."
            },
            {
                "id": "3",
                "accion": "ENCARGADO de sucursal 'Norte' recibe la transferencia y confirma recepción.",
                "resultado": "Estado pasa a RECIBIDA; stock origen descuenta 5 definitivamente, destino suma 5; avg_cost destino recalculado ponderado con costo origen; movimientos TRANSFERENCIA_SALIDA y ENTRADA en ledger.",
                "estado": "Satisfactorio",
                "precondicion": "Transferencia en estado PENDIENTE recibida físicamente en destino."
            },
            {
                "id": "4",
                "accion": "Cancelar una transferencia en estado PENDIENTE antes de su recepción.",
                "resultado": "Estado pasa a CANCELADA; stock de origen queda desbloqueado (+5 disponible) sin movimientos contables en ledger; auditoría registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Transferencia en estado PENDIENTE."
            },
            {
                "id": "5",
                "accion": "Intentar transferir una cantidad superior al stock disponible (origen tiene 3, intenta transferir 5).",
                "resultado": "HTTP 400 Bad Request 'Stock insuficiente para transferir'; no se realiza ningún cambio.",
                "estado": "Satisfactorio",
                "precondicion": "Stock en origen menor a la cantidad solicitada."
            },
            {
                "id": "6",
                "accion": "Intentar registrar una transferencia donde la sucursal de origen es igual a la de destino.",
                "resultado": "HTTP 422 'Origen y destino deben ser distintos'; la solicitud es rechazada.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de transferencia con sucursales idénticas."
            },
            {
                "id": "7",
                "accion": "Consultar kardex de movimientos de una variante en una sucursal específica.",
                "resultado": "Lista cronológica de INGRESO, AJUSTE, VENTA, TRANSFERENCIA_SALIDA/ENTRADA con fecha, cantidad, costo unitario y stock resultante.",
                "estado": "Satisfactorio",
                "precondicion": "Variante con historial de transacciones en la sucursal."
            },
            {
                "id": "8",
                "accion": "Venta en terminal POS descuenta stock: verificar actualización inmediata del consolidado general.",
                "resultado": "Stock de sucursal -1 inmediato; inventario general refleja el cambio sin necesidad de recargar manualmente.",
                "estado": "Satisfactorio",
                "precondicion": "Venta completada en mostrador POS."
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Módulo de Transferencias de Stock (/admin/inventory/transfers)"
    },
    {
        "id": "CU16",
        "nombre": "Configurar y notificar alertas de stock",
        "descripcion": "Validar umbrales por variante/sucursal y generación automática de alertas por stock bajo o alto.",
        "precondiciones": [
            "a) Sesión de SUPERADMIN o ENCARGADO.",
            "b) Variantes de prendas registradas con existencias en sucursal.",
            "c) Módulo de alertas y notificaciones del sistema activo."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "SUPERADMIN define stock mínimo = 5 y stock máximo = 100 para variante SKU 'CAM-OXF-AZ-M' en sucursal Central.",
                "resultado": "Umbrales guardados en inventory_alerts; auditoría INSERT registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN."
            },
            {
                "id": "2",
                "accion": "Ingreso de mercadería (CU10) hace que el stock pase de 4 a 10 unidades (cruza mínimo hacia arriba).",
                "resultado": "Alerta 'STOCK_BAJO' resuelta automáticamente; notificación en panel del ENCARGADO emitida.",
                "estado": "Satisfactorio",
                "precondicion": "Alerta previa de stock bajo activa para la variante."
            },
            {
                "id": "3",
                "accion": "Venta o ajuste hace que el stock baje de 6 a 4 unidades (cruza mínimo hacia abajo).",
                "resultado": "Alerta 'STOCK_BAJO' creada con estado ACTIVA; visible en dashboard de alertas; auditoría INSERT en alert_logs.",
                "estado": "Satisfactorio",
                "precondicion": "Stock actual por encima del umbral mínimo antes del descuento."
            },
            {
                "id": "4",
                "accion": "Ingreso masivo hace que el stock supere el máximo configurado (100 a 110 unidades).",
                "resultado": "Alerta 'STOCK_ALTO' creada; notificación a SUPERADMIN para revisar rotación de mercadería.",
                "estado": "Satisfactorio",
                "precondicion": "Stock que supera el umbral máximo configurado."
            },
            {
                "id": "5",
                "accion": "Intentar editar umbrales configurando stock mínimo > stock máximo.",
                "resultado": "HTTP 422 'El stock mínimo no puede ser mayor al máximo'; configuración rechazada.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de configuración de umbrales abierto."
            },
            {
                "id": "6",
                "accion": "Consultar alertas activas filtradas por sucursal y severidad.",
                "resultado": "Lista paginada con estado (ACTIVA/RESUELTA), fecha, variante, stock actual y umbral.",
                "estado": "Satisfactorio",
                "precondicion": "Alertas generadas previamente en el sistema."
            }
        ],
        "responsable": "Superadmin / Encargado de Sucursal",
        "adjunto": "Configuración de Umbrales y Dashboard de Alertas (/admin/alerts)"
    },
    {
        "id": "CU17",
        "nombre": "Gestionar carrito de compra digital",
        "descripcion": "Verificar operaciones CRUD del carrito, bloqueo automático por stock cero y persistencia entre sesiones.",
        "precondiciones": [
            "a) Tienda digital operativa con productos en stock.",
            "b) Almacenamiento local o sesión de base de datos activa para persistencia.",
            "c) Catálogo de productos en línea."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Cliente autenticado añade 2 unidades de una variante con stock disponible 10.",
                "resultado": "Ítem en carrito con quantity = 2, subtotal correcto; respuesta incluye available_stock = 10.",
                "estado": "Satisfactorio",
                "precondicion": "Variante con stock disponible mayor o igual a 2 unidades."
            },
            {
                "id": "2",
                "accion": "Añadir la misma variante: cantidad total en carrito pasa a 3.",
                "resultado": "Ítem actualiza quantity = 3 (no duplica fila en BD); subtotal recalculado.",
                "estado": "Satisfactorio",
                "precondicion": "Variante previamente agregada al carrito con 2 unidades."
            },
            {
                "id": "3",
                "accion": "Intentar añadir 11 unidades (supera stock disponible de 10).",
                "resultado": "HTTP 400 'Stock disponible insuficiente (máx. 10)'; el carrito permanece sin cambios.",
                "estado": "Satisfactorio",
                "precondicion": "Cantidad solicitada superior a la existencia física en almacén."
            },
            {
                "id": "4",
                "accion": "Una variante pasa a stock 0 por venta de otro usuario mientras permanece en el carrito.",
                "resultado": "Al consultar GET /cart, el ítem se marca con blocked = true y available_stock = 0; se inhabilita el botón de checkout.",
                "estado": "Satisfactorio",
                "precondicion": "Variante en carrito cuyas existencias se agotaron en base de datos."
            },
            {
                "id": "5",
                "accion": "Cliente elimina un ítem específico del carrito.",
                "resultado": "Ítem removido de cart_items; totales recalculados; auditoría DELETE registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Carrito con al menos un ítem agregado."
            },
            {
                "id": "6",
                "accion": "Accionar la opción 'Vaciar carrito completo'.",
                "resultado": "Todos los ítems son borrados; el carrito queda vacío; totales generales en cero.",
                "estado": "Satisfactorio",
                "precondicion": "Carrito con múltiples ítems agregados."
            },
            {
                "id": "7",
                "accion": "Carrito persiste tras cerrar sesión y volver a iniciarla con el mismo usuario en otro dispositivo.",
                "resultado": "Ítems y cantidades recuperados íntegramente desde la base de datos relacional.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario autenticado con ítems en su carrito de compras."
            },
            {
                "id": "8",
                "accion": "Visitante anónimo añade prendas al carrito y posteriormente inicia sesión.",
                "resultado": "El carrito anónimo se fusiona (merge) con el del usuario autenticado sumando cantidades y respetando límites de stock.",
                "estado": "Satisfactorio",
                "precondicion": "Ítems en carrito de visitante anónimo y posterior inicio de sesión."
            }
        ],
        "responsable": "Cliente / Visitante",
        "adjunto": "Sidebar de Carrito y Resumen de Compra (/tienda/carrito)"
    },
    {
        "id": "CU18",
        "nombre": "Procesar venta / checkout con herencia de medios de pago",
        "descripcion": "Validar flujo completo de checkout digital con medios de pago múltiples (Tarjeta, QR, Efectivo, Crédito) e idempotencia.",
        "precondiciones": [
            "a) Cliente autenticado con carrito válido y stock confirmado.",
            "b) Pasarelas de pago configuradas en modo sandbox/prueba.",
            "c) Dirección de envío o sucursal de retiro seleccionada."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Cliente con carrito válido elige 'Envío a domicilio' y paga con Tarjeta en modo prueba.",
                "resultado": "Orden creada status = PAGADA; pago payment_method = TARJETA; stock descontado; factura electrónica generada (CU20) y enviada por email; auditoría INSERT en orders, payments e invoices.",
                "estado": "Satisfactorio",
                "precondicion": "Carrito con stock disponible y tarjeta de prueba válida."
            },
            {
                "id": "2",
                "accion": "Pago con QR (código generado, cliente escanea y confirma pago).",
                "resultado": "Orden status = PAGADA; pago payment_method = QR; reference_code guardado; flujo idéntico a tarjeta salvo medio.",
                "estado": "Satisfactorio",
                "precondicion": "Orden en checkout seleccionando modalidad QR."
            },
            {
                "id": "3",
                "accion": "Pago en Efectivo contraentrega o recojo en tienda.",
                "resultado": "Orden status = CONFIRMADA_PENDIENTE_PAGO; pago payment_method = EFECTIVO, status = PENDIENTE; factura NO emitida hasta confirmar cobro en POS (CU19).",
                "estado": "Satisfactorio",
                "precondicion": "Modalidad de pago contraentrega seleccionada."
            },
            {
                "id": "4",
                "accion": "Pago a Crédito comercial (cuenta corriente del cliente).",
                "resultado": "Se valida límite de crédito; orden status = CONFIRMADA; pago payment_method = CREDITO; nota de entrega emitida; deuda registrada en customer_credit.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente corporativo con línea de crédito aprobada y saldo disponible."
            },
            {
                "id": "5",
                "accion": "La pasarela de pagos retorna error card_declined.",
                "resultado": "Orden status = FALLIDA; pago status = RECHAZADO; stock no descontado; carrito intacto; error amigable al cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Tarjeta de prueba rechazada por fondos insuficientes."
            },
            {
                "id": "6",
                "accion": "Carrito con ítem bloqueado (stock 0) intenta procesar checkout.",
                "resultado": "HTTP 409 'Hay productos sin stock en su carrito'; checkout rechazado.",
                "estado": "Satisfactorio",
                "precondicion": "Carrito con al menos una prenda cuyo stock se agotó."
            },
            {
                "id": "7",
                "accion": "Validación de dirección de entrega obligatoria para 'Envío a domicilio'.",
                "resultado": "HTTP 422 si falta dirección de entrega; no se crea ninguna orden.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de checkout con campo de dirección en blanco."
            },
            {
                "id": "8",
                "accion": "Idempotencia: Reintento de envío con el mismo payment_intent_id.",
                "resultado": "No se duplica orden ni pago; el sistema retorna la orden existente previamente.",
                "estado": "Satisfactorio",
                "precondicion": "Petición HTTP con identificador de intento de pago duplicado."
            }
        ],
        "responsable": "Cliente",
        "adjunto": "Módulo de Checkout y Pasarelas de Pago (/tienda/checkout)"
    },
    {
        "id": "CU19",
        "nombre": "Procesar venta presencial en caja (POS)",
        "descripcion": "Verificar venta directa en mostrador por CAJERO: escaneo de productos, pago mixto y emisión de factura inmediata.",
        "precondiciones": [
            "a) Cajero o Encargado con sesión activa y turno de caja ABIERTA en su sucursal.",
            "b) Lector de código de barras o buscador de productos operativo.",
            "c) Stock físico disponible en la sucursal actual."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "CAJERO escanea o ingresa SKU 'CAM-OXF-AZ-M', cantidad 1, stock disponible 5.",
                "resultado": "Línea agregada al ticket; subtotal calculado; stock mostrado en tiempo real.",
                "estado": "Satisfactorio",
                "precondicion": "Turno de caja abierto y stock disponible en la sucursal."
            },
            {
                "id": "2",
                "accion": "Añadir un segundo artículo distinto al ticket de venta.",
                "resultado": "Ticket muestra ambas líneas, subtotal e impuestos actualizados.",
                "estado": "Satisfactorio",
                "precondicion": "Ticket con al menos una línea agregada previamente."
            },
            {
                "id": "3",
                "accion": "Pago mixto: 50 % en Efectivo + 50 % con Tarjeta en mostrador.",
                "resultado": "Dos registros en payments (EFECTIVO + TARJETA) vinculados a la misma order_id; suma = total; factura emitida.",
                "estado": "Satisfactorio",
                "precondicion": "Ticket de venta completado listo para cobro."
            },
            {
                "id": "4",
                "accion": "Cambiar talla de artículo ya agregado en ticket (devolución inmediata + nueva talla).",
                "resultado": "Línea original cantidad -1 (stock +1), línea nueva +1 (stock -1); cálculo neto en ledger; auditoría.",
                "estado": "Satisfactorio",
                "precondicion": "Artículo previamente cargado en el ticket de venta."
            },
            {
                "id": "5",
                "accion": "Aplicar cupón promocional vigente (CU13) en terminal POS.",
                "resultado": "Descuento aplicado en total; cupón marcado como usado; factura refleja descuento.",
                "estado": "Satisfactorio",
                "precondicion": "Cupón vigente presentado por el cliente en caja."
            },
            {
                "id": "6",
                "accion": "Venta sin cliente identificado (consumidor final sin NIT).",
                "resultado": "Orden customer_id = NULL; factura tipo 'Consumidor Final' (NIT genérico); IVA 13 % calculado.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente que solicita factura sin proporcionar NIT/CI."
            },
            {
                "id": "7",
                "accion": "Cancelar venta antes de procesar el pago del ticket.",
                "resultado": "Ticket descartado; stock no modificado; sin auditoría de venta.",
                "estado": "Satisfactorio",
                "precondicion": "Ticket en borrador sin cobrar."
            },
            {
                "id": "8",
                "accion": "Usuario con rol CLIENTE intenta acceder al terminal POS (/admin/pos).",
                "resultado": "HTTP 403 Forbidden; acceso restringido al personal de caja.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol CLIENTE."
            }
        ],
        "responsable": "Cajero de Sucursal",
        "adjunto": "Terminal POS de Mostrador (/admin/pos)"
    },
    {
        "id": "CU20",
        "nombre": "Emitir comprobante: factura y nota de entrega",
        "descripcion": "Verificar generación de factura fiscal con IVA 13% y código de control boliviano SIN, y notas de entrega.",
        "precondiciones": [
            "a) Transacción de venta confirmada y saldada (online o POS).",
            "b) Parámetros de dosificación y código de control SIN configurados.",
            "c) Módulo generador de PDF y código QR operativo."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Factura generada tras pago digital confirmado (CU18) o cobro en caja (CU19).",
                "resultado": "Registro en invoices: type = FACTURA, IVA = 13 %, control_code válido (algoritmo SIN), authorization_number, QR con datos fiscales; PDF generado y enviado por email.",
                "estado": "Satisfactorio",
                "precondicion": "Orden en estado PAGADA."
            },
            {
                "id": "2",
                "accion": "Nota de entrega para venta a crédito (CU18) o consumidor final sin NIT.",
                "resultado": "type = NOTA_ENTREGA; sin código de control SIN; IVA 13 % desglosado; PDF generado.",
                "estado": "Satisfactorio",
                "precondicion": "Orden corporativa a crédito confirmada."
            },
            {
                "id": "3",
                "accion": "Validar cálculo exacto de IVA: subtotal Bs 100 → IVA (13 %) Bs 13 → Total Bs 113.",
                "resultado": "Valores matemáticos exactos en base de datos y documento PDF; redondeo a 2 decimales.",
                "estado": "Satisfactorio",
                "precondicion": "Monto de venta con base imponible calculada."
            },
            {
                "id": "4",
                "accion": "Factura con múltiples medios de pago (pago mixto CU19).",
                "resultado": "Un solo comprobante por orden; detalle de pagos desglosado en el pie de la factura.",
                "estado": "Satisfactorio",
                "precondicion": "Venta procesada con cobro mixto en terminal POS."
            },
            {
                "id": "5",
                "accion": "Regenerar factura (reimpresión) sin duplicar registro en base de datos.",
                "resultado": "Mismo invoice_id; PDF idéntico; auditoría REPRINT registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Factura previamente emitida en el sistema."
            },
            {
                "id": "6",
                "accion": "Validar código de control con datos de prueba oficiales (vector de prueba SIN).",
                "resultado": "El código generado por el algoritmo coincide exactamente con el valor esperado oficial del SIN.",
                "estado": "Satisfactorio",
                "precondicion": "Llave de dosificación y datos fiscales del SIN cargados."
            },
            {
                "id": "7",
                "accion": "Control de acceso a facturas: cliente ve solo las suyas; SUPERADMIN visualiza todas.",
                "resultado": "Filtro estricto por customer_id en endpoints de cliente; sin filtro para rol SUPERADMIN.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada de cliente o administrador."
            }
        ],
        "responsable": "Sistema / Facturación / Cajero",
        "adjunto": "Factura Fiscal Electrónica con Código QR y Control SIN"
    },
    {
        "id": "CU21",
        "nombre": "Generar cotización",
        "descripcion": "Verificar creación de cotizaciones con validez limitada, versión PDF y conversión directa a orden.",
        "precondiciones": [
            "a) Sesión de SUPERADMIN, ENCARGADO o cliente corporativo registrado.",
            "b) Variantes de prendas en catálogo con precios vigentes.",
            "c) Módulo de cotizaciones disponible."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "SUPERADMIN/ENCARGADO crea cotización corporativa: 3 variantes, cantidades y precios vigentes.",
                "resultado": "Cotización status = BORRADOR, valid_until (7 días), ítems con precio unitario y subtotal; PDF con membrete institucional.",
                "estado": "Satisfactorio",
                "precondicion": "Personal administrativo con sesión activa."
            },
            {
                "id": "2",
                "accion": "Enviar cotización por email mediante enlace público (public_token).",
                "resultado": "Endpoint devuelve quote_id y public_token; enlace público accesible sin autenticación; email programado.",
                "estado": "Satisfactorio",
                "precondicion": "Cotización guardada en estado borrador."
            },
            {
                "id": "3",
                "accion": "Cliente acepta cotización mediante el enlace público.",
                "resultado": "Cotización status = ACEPTADA; se crea orden status = CONFIRMADA_PENDIENTE_PAGO copiando ítems; stock reservado por vigencia.",
                "estado": "Satisfactorio",
                "precondicion": "Cotización vigente consultada por el cliente."
            },
            {
                "id": "4",
                "accion": "Cotización expira sin haber recibido aceptación.",
                "resultado": "status = EXPIRADA; stock liberado automáticamente; notificación enviada a ventas.",
                "estado": "Satisfactorio",
                "precondicion": "Fecha límite valid_until superada."
            },
            {
                "id": "5",
                "accion": "Modificar cotización en estado BORRADOR (cambiar cantidad y precio).",
                "resultado": "Versión actualizada; historial en quote_versions registrado; PDF regenerado.",
                "estado": "Satisfactorio",
                "precondicion": "Cotización en estado BORRADOR."
            },
            {
                "id": "6",
                "accion": "Convertir cotización aceptada a venta presencial con pago en efectivo en terminal POS.",
                "resultado": "Flujo de venta POS completado usando los ítems de la cotización; factura emitida.",
                "estado": "Satisfactorio",
                "precondicion": "Cotización aceptada y cliente en mostrador."
            }
        ],
        "responsable": "Encargado de Ventas / Superadmin",
        "adjunto": "Módulo de Cotizaciones y Formato PDF (/admin/quotes)"
    },
    {
        "id": "CU22",
        "nombre": "Gestionar devoluciones y cambios de prendas",
        "descripcion": "Validar flujo de devolución (reembolso o nota de crédito) y cambio (talla/color) con trazabilidad de inventario.",
        "precondiciones": [
            "a) Orden entregada dentro del plazo legal permitido (30 días).",
            "b) Prenda sin uso y con etiquetas originales intactas.",
            "c) Sesión iniciada con rol ENCARGADO o SUPERADMIN para resolución de solicitudes."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Cliente solicita devolución de pedido entregado dentro de 30 días; ENCARGADO revisa y aprueba.",
                "resultado": "Solicitud status = APROBADA; stock +1 en sucursal origen; nota de crédito generada; reembolso según medio original.",
                "estado": "Satisfactorio",
                "precondicion": "Orden previa entregada al cliente."
            },
            {
                "id": "2",
                "accion": "Cambio de talla: Cliente devuelve talla M y solicita talla L de la misma prenda.",
                "resultado": "Solicitud type = CAMBIO; stock M +1, stock L -1 (reservado); si L no tiene stock retorna HTTP 409; al entregar orden actualizada.",
                "estado": "Satisfactorio",
                "precondicion": "Stock de la talla solicitada disponible en sucursal."
            },
            {
                "id": "3",
                "accion": "Devolución parcial de una orden que contiene 3 ítems (se devuelve únicamente 1 ítem).",
                "resultado": "Nota de crédito por valor proporcional; ítem devuelto marcado con returned = true; demás ítems intactos.",
                "estado": "Satisfactorio",
                "precondicion": "Orden con múltiples productos entregados."
            },
            {
                "id": "4",
                "accion": "Rechazar solicitud de devolución por prenda con signos de uso o fuera de plazo de 30 días.",
                "resultado": "status = RECHAZADA con rejection_reason registrado; stock no modificado; notificación al cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Solicitud de devolución recibida en sucursal."
            },
            {
                "id": "5",
                "accion": "Devolución de una compra efectuada a crédito corporativo.",
                "resultado": "La nota de crédito reduce la deuda en customer_credit; sin movimiento de efectivo físico; auditoría registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Compra original realizada bajo modalidad de crédito."
            },
            {
                "id": "6",
                "accion": "Validar permisos: usuario con rol CLIENTE intenta aprobar o rechazar devoluciones.",
                "resultado": "HTTP 403 Forbidden; el cliente solo puede solicitar, no aprobar.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol CLIENTE."
            }
        ],
        "responsable": "Encargado de Sucursal / Superadmin",
        "adjunto": "Módulo de Devoluciones y Cambios (/admin/returns)"
    },
    {
        "id": "CU23",
        "nombre": "Gestionar arqueo de caja",
        "descripcion": "Verificar apertura de caja con fondo inicial, consolidación por medios de pago y cierre con registro de diferencias.",
        "precondiciones": [
            "a) Usuario con rol CAJERO o ENCARGADO asignado a sucursal activa.",
            "b) No debe existir turno previo abierto para el mismo usuario en la sucursal.",
            "c) Módulo de tesorería y arqueo habilitado."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "CAJERO abre caja ingresando fondo inicial de Bs 500 (2 billetes de 200, 1 billete de 100).",
                "resultado": "Fila creada en cash_shifts con status = ABIERTA, opening_amount = 500 y detalle de denominaciones; auditoría OPEN_CASH.",
                "estado": "Satisfactorio",
                "precondicion": "Cajero sin turno previo abierto."
            },
            {
                "id": "2",
                "accion": "Operaciones del turno: Ventas en Efectivo Bs 1.200, Tarjeta Bs 800 y QR Bs 300.",
                "resultado": "Sistema acumula montos esperados: expected_cash = 1700 (500+1200), expected_card = 800, expected_qr = 300.",
                "estado": "Satisfactorio",
                "precondicion": "Turno de caja abierto y ventas registradas."
            },
            {
                "id": "3",
                "accion": "CAJERO cierra caja declarando en efectivo físico Bs 1.695 (diferencia de Bs -5).",
                "resultado": "status = CERRADA; declared_cash = 1695, difference = -5; difference_reason obligatorio registrado; auditoría CLOSE_CASH.",
                "estado": "Satisfactorio",
                "precondicion": "Turno de caja abierto listo para cierre."
            },
            {
                "id": "4",
                "accion": "Cierre de caja con diferencia positiva > 0 (sobrante de efectivo físico).",
                "resultado": "difference con valor positivo; razón documentada y alerta enviada a SUPERADMIN.",
                "estado": "Satisfactorio",
                "precondicion": "Monto físico superior a lo registrado en sistema."
            },
            {
                "id": "5",
                "accion": "Intentar cerrar turno de caja sin haber realizado apertura previa hoy.",
                "resultado": "HTTP 409 'No hay caja abierta para esta sucursal/usuario'.",
                "estado": "Satisfactorio",
                "precondicion": "No existe registro de caja abierta."
            },
            {
                "id": "6",
                "accion": "SUPERADMIN reabre un turno previamente cerrado para corrección de datos.",
                "resultado": "status = REABIERTA; nuevo cierre genera registro adicional; auditoría completa registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN y turno cerrado."
            },
            {
                "id": "7",
                "accion": "Consultar histórico de arqueos por sucursal y rango de fechas.",
                "resultado": "Lista detallada con apertura, cierre, montos esperados, declarados, diferencias y cajero responsable.",
                "estado": "Satisfactorio",
                "precondicion": "Turnos históricos registrados en la base de datos."
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
            "a) Cliente autenticado con compras registradas en su cuenta.",
            "b) Acceso a servicios de almacenamiento de facturas electrónicas.",
            "c) Módulo de compras accesible."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Cliente autenticado abre 'Mis compras'.",
                "resultado": "Lista paginada (10 por página): N° orden, fecha, total, estado (PAGADA, ENVIADA, ENTREGADA, CANCELADA), ítems (foto, nombre, talla, color, cant, precio), botón 'Ver factura'.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente con compras registradas en la base de datos."
            },
            {
                "id": "2",
                "accion": "Filtrar por estado 'ENTREGADA' y rango de fechas.",
                "resultado": "Se muestran solo las órdenes que coinciden; la paginación preserva los filtros seleccionados.",
                "estado": "Satisfactorio",
                "precondicion": "Existencia de compras con estado ENTREGADA."
            },
            {
                "id": "3",
                "accion": "Clic en 'Ver factura' sobre una orden pagada.",
                "resultado": "PDF de factura (CU20) se abre/descarga mediante URL firmada con expiración de 15 minutos.",
                "estado": "Satisfactorio",
                "precondicion": "Orden con factura electrónica emitida."
            },
            {
                "id": "4",
                "accion": "Orden con despacho a domicilio: mostrar seguimiento logístico.",
                "resultado": "Número de guía TRK, transportista asignado, estado actual (PREPARACIÓN/EN_CAMINO/ENTREGADO) y enlace directo a rastreo.",
                "estado": "Satisfactorio",
                "precondicion": "Orden procesada con modalidad de envío a domicilio."
            },
            {
                "id": "5",
                "accion": "Cliente intenta consultar una orden ajena manipulando el ID en la petición.",
                "resultado": "HTTP 403 / 404; el sistema restringe el acceso y no filtra información privada de terceros.",
                "estado": "Satisfactorio",
                "precondicion": "ID de orden perteneciente a otro usuario."
            },
            {
                "id": "6",
                "accion": "Acceder al historial con un cliente nuevo sin compras registradas.",
                "resultado": "Mensaje 'No tiene compras registradas' con botón directo 'Ir a la tienda'.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario recién registrado sin pedidos."
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
        "descripcion": "Verificar la conversión en mostrador de una reserva previa a venta definitiva en terminal POS, cobrando el saldo restante, aplicando la seña, emitiendo factura y consolidando stock.",
        "precondiciones": [
            "a) Cajero o Encargado con sesión iniciada y turno de caja ABIERTA en la sucursal receptora.",
            "b) Existencia de una reserva en estado PENDING o CONFIRMED asignada a la sucursal del usuario.",
            "c) El cliente se presenta físicamente en la sucursal dentro del horario de tolerancia estipulado."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Cajero busca reserva por código 'RES-{id}' en la pestaña 'Reservas' del POS y procesa cobro del saldo restante (Total - Seña 50% abonada).",
                "resultado": "La reserva pasa a COMPLETED; se genera orden status = PAGADA; la seña se imputa al total; se emite factura fiscal CU20; el stock reservado pasa a salida definitiva por venta y se asocia al arqueo de caja.",
                "estado": "Satisfactorio",
                "precondicion": "Reserva con seña previa del 50% en estado CONFIRMED y turno de caja ABIERTA."
            },
            {
                "id": "2",
                "accion": "Cobro con modificación de artículos en tienda: El cliente decide descartar 1 prenda reservada y cambiar la talla de otra.",
                "resultado": "El cajero ajusta los ítems en el POS; la prenda descartada se libera de inmediato al stock disponible de la sucursal; se recalcula el saldo exacto a pagar y se emite factura final por las prendas efectivamente adquiridas.",
                "estado": "Satisfactorio",
                "precondicion": "Reserva en mostrador con prendas físicas en probador."
            },
            {
                "id": "3",
                "accion": "Intentar procesar la conversión de una reserva cuando la caja de la sucursal se encuentra CERRADA.",
                "resultado": "HTTP 409 Conflict 'Debe abrir una caja antes de procesar conversiones de reserva en el POS'; la transacción no se ejecuta.",
                "estado": "Satisfactorio",
                "precondicion": "Cajero sin turno de caja abierto en la sucursal."
            },
            {
                "id": "4",
                "accion": "Intentar cobrar una reserva perteneciente a otra sucursal física o una reserva ya completada/cancelada.",
                "resultado": "HTTP 400 / 404 informando que la reserva no pertenece a la sucursal actual o no se encuentra en estado apto para cobro.",
                "estado": "Satisfactorio",
                "precondicion": "Reserva asociada a sucursal distinta a la del cajero."
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
                "id": "1",
                "accion": "Cliente selecciona sucursal 'Central', fecha y hora futura válida, añade 3 prendas al probador y abona la seña del 50% vía PayPal / Tarjeta / QR.",
                "resultado": "Se crea registro en reservations (status = PENDING), ítems en reservation_items; el stock de las 3 prendas se aparta en la sucursal (-3 disponible, +3 reservado); se genera confirmación con código de cita y se notifica al cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente autenticado con prendas seleccionadas y stock disponible en la sucursal elegida."
            },
            {
                "id": "2",
                "accion": "Intentar agendar una reserva añadiendo 6 prendas al probador.",
                "resultado": "El sistema valida la regla de negocio y bloquea el avance mostrando 'El límite máximo por reserva en probador es de 5 prendas'.",
                "estado": "Satisfactorio",
                "precondicion": "Formulario de agendamiento con 6 prendas añadidas."
            },
            {
                "id": "3",
                "accion": "Intentar agendar cita en fecha pasada, fuera del horario de atención comercial o en día feriado.",
                "resultado": "HTTP 422 Unprocessable Entity 'La fecha y hora deben corresponder al horario habilitado de la sucursal'.",
                "estado": "Satisfactorio",
                "precondicion": "Selección de horario fuera del calendario laboral de la sucursal."
            },
            {
                "id": "4",
                "accion": "Intentar reservar una variante cuyo stock físico en la sucursal seleccionada es igual a 0.",
                "resultado": "HTTP 400 Bad Request 'Stock insuficiente en la sucursal seleccionada para una o más prendas elegidas'.",
                "estado": "Satisfactorio",
                "precondicion": "Variante seleccionada sin inventario en esa sucursal física."
            }
        ],
        "responsable": "Cliente",
        "adjunto": "Formulario de Reserva y Cita (/tienda/reservas/nueva) y Vista Móvil (reserve_fitting_view.dart)"
    },
    {
        "id": "CU27",
        "nombre": "Gestionar bandeja de reservas entrantes (Kanban de probador: preparar / atender)",
        "descripcion": "Validar la administración visual mediante tablero Kanban de las reservas en probador físico por el personal de tienda, gestionando alistamiento, llamadas y tolerancia de citas.",
        "precondiciones": [
            "a) Usuario con sesión activa y rol ENCARGADO o CAJERO en la sucursal correspondiente.",
            "b) Módulo de Reservas y Probador habilitado en el panel administrativo (/admin/reservations).",
            "c) Existencia de reservas agendadas en la sucursal física."
        ],
        "pasos": [
            {
                "id": "1",
                "accion": "Encargado abre el tablero Kanban clasificado en columnas: Pendientes, En Preparación, Listo en Probador, En Prueba y Completadas.",
                "resultado": "Las tarjetas reflejan cliente, hora de cita, conteo de prendas, seña abonada y estado de alistamiento de manera ordenada y visual.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol ENCARGADO y reservas activas en la sucursal."
            },
            {
                "id": "2",
                "accion": "Personal aparta físicamente las prendas en tienda y mueve la tarjeta de 'Pendiente' a 'Listo en Probador'.",
                "resultado": "La tarjeta se reubica de columna; se actualiza el estado en backend y se dispara notificación in-app y correo al cliente informándole que su probador está preparado.",
                "estado": "Satisfactorio",
                "precondicion": "Reserva en estado Pendiente con prendas apartadas en mostrador."
            },
            {
                "id": "3",
                "accion": "Verificar tolerancia de citas: El cliente no se presenta pasados 15 minutos de la hora agendada.",
                "resultado": "El sistema marca la reserva automáticamente como LATE (Atrasado) con alerta visual; al alcanzar 30 minutos de retraso pasa a NO_SHOW y el stock apartado se libera a disponible.",
                "estado": "Satisfactorio",
                "precondicion": "Cita agendada cuyo horario fue superado por más de 15 y 30 minutos."
            },
            {
                "id": "4",
                "accion": "Usuario con rol CLIENTE intenta ingresar a la ruta /admin/reservations.",
                "resultado": "HTTP 403 Forbidden; módulo restringido estrictamente al personal de sucursal.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol CLIENTE."
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
                "id": "1",
                "accion": "Cliente cancela su cita desde 'Mis Reservas' con más de 24 horas de antelación al horario pautado.",
                "resultado": "La reserva cambia a status = CANCELLED; las prendas apartadas regresan inmediatamente al stock disponible de la sucursal (+unidades en available); se emite comprobante de anulación y se registra en bitácora.",
                "estado": "Satisfactorio",
                "precondicion": "Reserva activa con más de 24 horas previas a la hora de la cita."
            },
            {
                "id": "2",
                "accion": "Encargado de tienda cancela una reserva por fuerza mayor o solicitud expresa en mostrador registrando el motivo.",
                "resultado": "Status pasa a CANCELLED_BY_STORE; inventario liberado en la sucursal; notificación automática enviada al cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Personal con rol ENCARGADO autenticado."
            },
            {
                "id": "3",
                "accion": "Intentar cancelar una reserva que ya fue completada (COMPLETED) o que ya se encuentra cancelada.",
                "resultado": "HTTP 400 Bad Request 'La reserva ya fue procesada o cancelada con anterioridad; no puede modificarse'.",
                "estado": "Satisfactorio",
                "precondicion": "Reserva con estado terminal COMPLETED o CANCELLED."
            },
            {
                "id": "4",
                "accion": "Un cliente intenta cancelar una reserva perteneciente a otro usuario mediante manipulación de parámetros.",
                "resultado": "HTTP 403 / 404; el sistema restringe la operación exclusivamente al titular de la cita.",
                "estado": "Satisfactorio",
                "precondicion": "Petición con identificador de reserva ajena."
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
                "id": "1",
                "accion": "Encargado genera el despacho de una orden pagada desde /admin/shipments.",
                "resultado": "Se crea registro en shipments con guía única TRK-{hash}, estado READY_FOR_PICKUP y evento inicial registrado en shipment_tracking_events.",
                "estado": "Satisfactorio",
                "precondicion": "Orden en estado PAGADA con despacho a domicilio pendiente."
            },
            {
                "id": "2",
                "accion": "Repartidor consulta la bolsa de envíos disponibles (GET /logistics/shipments/available) y toma el pedido (claim).",
                "resultado": "El envío se asigna al repartidor; su estado cambia a ASSIGNED y desaparece de la bolsa pública para otros choferes.",
                "estado": "Satisfactorio",
                "precondicion": "Repartidor autenticado con disponibilidad activa y paquetes en bolsa."
            },
            {
                "id": "3",
                "accion": "Repartidor actualiza el estado del paquete a IN_TRANSIT (En camino al domicilio).",
                "resultado": "Se actualiza el estado del envío, se registra marca de tiempo y coordenadas GPS, y se envía notificación in-app al cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Envío en estado ASSIGNED bajo custodia del repartidor."
            },
            {
                "id": "4",
                "accion": "Repartidor confirma entrega exitosa adjuntando obligatoriamente la fotografía de evidencia y nombre del receptor.",
                "resultado": "Envío pasa a DELIVERED; orden pasa a ENTREGADA; la fotografía se almacena en el servidor y se vincula al registro de entrega; auditoría de confirmación registrada.",
                "estado": "Satisfactorio",
                "precondicion": "Repartidor en domicilio de entrega con archivo de foto de evidencia."
            },
            {
                "id": "5",
                "accion": "Repartidor reporta entrega fallida por ausencia del cliente o dirección no encontrada.",
                "resultado": "Envío cambia a FAILED_ATTEMPT; se guarda el motivo del fallo y se habilita la reprogramación de visita notificando al cliente.",
                "estado": "Satisfactorio",
                "precondicion": "Envío en tránsito no concretado por fuerza mayor."
            },
            {
                "id": "6",
                "accion": "Intentar confirmar la entrega del paquete sin adjuntar la fotografía de evidencia requerida.",
                "resultado": "HTTP 422 Unprocessable Entity 'La fotografía de evidencia es obligatoria para confirmar la entrega del paquete'.",
                "estado": "Satisfactorio",
                "precondicion": "Confirmación de entrega enviada con campo de foto vacío."
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
                "id": "1",
                "accion": "Visitante ingresa un código de seguimiento válido (ej. TRK-8F2A19BC) en la barra de rastreo público.",
                "resultado": "Se despliega la línea de tiempo completa del envío (Alistado, Asignado, En camino, Entregado), sucursal de origen y fecha estimada sin necesidad de iniciar sesión.",
                "estado": "Satisfactorio",
                "precondicion": "Guía de seguimiento TRK válida registrada en logística."
            },
            {
                "id": "2",
                "accion": "Cliente consulta el rastreo de su paquete desde su historial de compras autenticado (/tienda/mis-compras).",
                "resultado": "Visualiza el seguimiento en tiempo real, nombre del repartidor asignado, eventos con hora exacta y la fotografía de entrega al completarse.",
                "estado": "Satisfactorio",
                "precondicion": "Cliente con orden despachada asociada a su cuenta."
            },
            {
                "id": "3",
                "accion": "Ingresar un código de rastreo inexistente o con formato incorrecto en el buscador.",
                "resultado": "Se muestra mensaje descriptivo 'No se encontró ningún envío asociado al código de seguimiento ingresado'.",
                "estado": "Satisfactorio",
                "precondicion": "Código de seguimiento inválido ingresado en el buscador."
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
                "id": "1",
                "accion": "Como SUPERADMIN, crear una nueva zona de cobertura configurando radio en kilómetros (0 a 5 km = Bs 15, 5 a 15 km = Bs 25, tiempo estimado 45 min).",
                "resultado": "La zona se almacena en delivery_zones, se dibuja el polígono/radio en el mapa interactivo Leaflet y se registra auditoría INSERT.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN (Casa Matriz)."
            },
            {
                "id": "2",
                "accion": "Cliente cotiza tarifa de envío introduciendo su dirección y coordenadas geográficas en el checkout.",
                "resultado": "El endpoint calculate-rate computa la distancia haversine respecto a la sucursal más cercana y retorna la tarifa exacta y tiempo de entrega estimado.",
                "estado": "Satisfactorio",
                "precondicion": "Dirección de cliente dentro de radio de cobertura registrado."
            },
            {
                "id": "3",
                "accion": "Cotizar envío para una ubicación situada fuera del radio de cobertura máximo configurado.",
                "resultado": "El sistema advierte de forma transparente 'La dirección indicada se encuentra fuera del área de cobertura de delivery'.",
                "estado": "Satisfactorio",
                "precondicion": "Coordenadas fuera del perímetro de delivery activo."
            },
            {
                "id": "4",
                "accion": "Usuario con rol CLIENTE o CAJERO intenta modificar las tarifas de zonas de delivery.",
                "resultado": "HTTP 403 Forbidden; edición restringida exclusivamente a Casa Matriz.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión con rol distinto de SUPERADMIN."
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
                "id": "1",
                "accion": "Usuario sube su fotografía corporal completa, especifica altura y contextura, y selecciona una prenda superior del catálogo.",
                "resultado": "El pipeline de IA detecta la pose anatómica, aísla la silueta, remueve las mangas de la vestimenta anterior y genera la imagen amoldada con ajuste proporcional realista.",
                "estado": "Satisfactorio",
                "precondicion": "Fotografía del usuario en plano general frontal con buena iluminación."
            },
            {
                "id": "2",
                "accion": "Recomendación biométrica de talla: Usuario ingresa sus medidas corporales de busto/tórax, cintura y cadera.",
                "resultado": "El algoritmo compara los datos con la tabla de patronaje de la prenda y recomienda la talla óptima (S, M, L, XL) informando el índice de ajuste.",
                "estado": "Satisfactorio",
                "precondicion": "Parámetros biométricos ingresados en centímetros."
            },
            {
                "id": "3",
                "accion": "Usuario sube una fotografía con fondo complejo o saturado.",
                "resultado": "El servicio de eliminación de fondo (remove-background) segmenta con precisión la silueta del usuario preservando el rostro y cuello intactos.",
                "estado": "Satisfactorio",
                "precondicion": "Fotografía con fondo urbano o saturado cargada en el probador."
            },
            {
                "id": "4",
                "accion": "Subir archivo con extensión no válida (ej. .exe, .pdf) o con peso superior a 10 MB.",
                "resultado": "HTTP 415 o HTTP 400 informando que solo se admiten imágenes JPG, PNG o WebP de hasta 10 MB.",
                "estado": "Satisfactorio",
                "precondicion": "Selector de archivos abierto en el módulo de probador virtual."
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
                "id": "1",
                "accion": "Usuario consulta: 'Busco una combinación casual para una cena formal en la noche'.",
                "resultado": "El asistente identifica intenciones y ocasión, consulta el catálogo y responde con una recomendación estilística acompañada de tarjetas de prendas con foto, precio y enlace directo.",
                "estado": "Satisfactorio",
                "precondicion": "Widget de chatbot abierto en tienda web o pantalla móvil."
            },
            {
                "id": "2",
                "accion": "Usuario pregunta sobre políticas comerciales: '¿Cuáles son los costos de envío y el plazo de devolución?'.",
                "resultado": "El chatbot responde con precisión informando las tarifas por zona de delivery y el plazo de 30 días para cambios.",
                "estado": "Satisfactorio",
                "precondicion": "Servicio de respuestas frecuentes y políticas comerciales configurado."
            },
            {
                "id": "3",
                "accion": "Usuario realiza consulta con términos en plural o diminutivos: 'poleritas negras talla M'.",
                "resultado": "El analizador lematiza los términos (polera, negro, M) y recupera las variantes exactas con stock disponible.",
                "estado": "Satisfactorio",
                "precondicion": "Catálogo con variantes de poleras negras talla M en inventario."
            },
            {
                "id": "4",
                "accion": "Enviar mensaje vacío o cadena de caracteres incomprensible.",
                "resultado": "El asistente responde amablemente guiando al usuario con opciones interactivas sugeridas (Novedades, Ocasión, Ofertas).",
                "estado": "Satisfactorio",
                "precondicion": "Entrada de texto del chatbot activa."
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
                "id": "1",
                "accion": "Usuario presiona el icono de micrófono y pronuncia: 'Busco vestido de fiesta rojo menor a 250 bolivianos'.",
                "resultado": "El sistema captura el audio, transcribe el texto, extrae entidades (categoría: vestido, ocasión: fiesta, color: rojo, precio_máx: 250), aplica los filtros y despliega la lista coincidente.",
                "estado": "Satisfactorio",
                "precondicion": "Micrófono con permisos concedidos y servicio de voz activo."
            },
            {
                "id": "2",
                "accion": "Usuario dicta una búsqueda rápida por voz: 'camisas blancas'.",
                "resultado": "Reconocimiento inmediato y redirección a la grilla de productos con el filtro de categoría camisa y color blanco aplicado.",
                "estado": "Satisfactorio",
                "precondicion": "Pronunciación clara frente al micrófono."
            },
            {
                "id": "3",
                "accion": "Usuario deniega los permisos de acceso al micrófono en el dispositivo.",
                "resultado": "La interfaz captura el evento e informa educadamente: 'Permiso de micrófono requerido para utilizar la búsqueda por voz'.",
                "estado": "Satisfactorio",
                "precondicion": "Permisos de micrófono bloqueados en el navegador o sistema operativo."
            },
            {
                "id": "4",
                "accion": "Presionar el micrófono y permanecer en silencio absoluto durante la grabación.",
                "resultado": "El temporizador de silencio (1.5 segundos) finaliza la captura automáticamente sin bloquear la pantalla.",
                "estado": "Satisfactorio",
                "precondicion": "Grabación de audio iniciada sin detección de ondas de voz."
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
                "id": "1",
                "accion": "Generar Kardex físico-valorado seleccionando sucursal y rango de fechas con cálculo de Costo Promedio Ponderado.",
                "resultado": "Se despliega la tabla detallada de entradas, salidas, saldos y costo medio; botón de exportación CSV genera archivo descargable con datos exactos.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN y transacciones en el periodo."
            },
            {
                "id": "2",
                "accion": "Generar reporte de productos más vendidos (Top Selling) por categoría y volumen facturado.",
                "resultado": "Gráfica interactiva y tabla con ranking de variantes, unidades vendidas, ingresos brutos y rotación.",
                "estado": "Satisfactorio",
                "precondicion": "Órdenes de venta pagadas registradas en el sistema."
            },
            {
                "id": "3",
                "accion": "Presionar el botón de lectura ejecutiva por voz (Text-to-Speech) del resumen gerencial.",
                "resultado": "La síntesis de voz reproduce claramente en audio los indicadores clave del periodo (ventas totales, pedidos y rendimiento de inventario).",
                "estado": "Satisfactorio",
                "precondicion": "Dispositivo con salida de audio y navegador compatible con Web Speech Synthesis."
            },
            {
                "id": "4",
                "accion": "Usuario con rol CAJERO o CLIENTE intenta consultar los reportes gerenciales.",
                "resultado": "HTTP 403 Forbidden; acceso estrictamente reservado a la gerencia de Casa Matriz.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol distinto de SUPERADMIN."
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
                "id": "1",
                "accion": "SUPERADMIN accede al Dashboard Analítico Global.",
                "resultado": "Carga en tiempo real de tarjetas de KPIs (Ventas del mes, Ticket promedio, Margen bruto, Órdenes activas), gráfico de barras de ventas por sucursal y tendencias de ventas.",
                "estado": "Satisfactorio",
                "precondicion": "Sesión iniciada con rol SUPERADMIN."
            },
            {
                "id": "2",
                "accion": "Filtrar el dashboard analítico por diferentes periodos (Hoy, Últimos 7 días, Mes actual, Todo el año).",
                "resultado": "Todas las métricas y series temporales se recalculan dinámicamente según el intervalo seleccionado.",
                "estado": "Satisfactorio",
                "precondicion": "Rango de fechas seleccionado en el selector del panel."
            },
            {
                "id": "3",
                "accion": "Usuario con rol ENCARGADO o CAJERO intenta acceder a la ruta /admin/analytics-dashboard.",
                "resultado": "El guard de navegación redirige al dashboard operativo de su sucursal o deniega con HTTP 403.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario con rol no autorizado en Casa Matriz."
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
                "id": "1",
                "accion": "Se produce un evento relevante para el usuario (ej. compra confirmada o probador listo para cita).",
                "resultado": "Se incrementa el contador visual de la campana en la barra superior; el desplegable lista la notificación con título, mensaje, timestamp y enlace directo.",
                "estado": "Satisfactorio",
                "precondicion": "Usuario autenticado con evento de negocio generado en backend."
            },
            {
                "id": "2",
                "accion": "Hacer clic en una notificación para leerla y accionar la opción 'Marcar todas como leídas'.",
                "resultado": "El contador de no leídas se reinicia a 0; el campo is_read se actualiza a true en la base de datos.",
                "estado": "Satisfactorio",
                "precondicion": "Notificaciones no leídas presentes en la bandeja del usuario."
            },
            {
                "id": "3",
                "accion": "Disparo de correo electrónico transaccional de respaldo vía SMTP ante un cambio de estado crítico (ej. pedido despachado).",
                "resultado": "El correo llega a la bandeja de entrada del usuario con formato corporativo HTML y detalle completo de la operación.",
                "estado": "Satisfactorio",
                "precondicion": "Evento con canal de correo habilitado en el servicio de notificaciones."
            },
            {
                "id": "4",
                "accion": "Intentar consultar o modificar notificaciones de otro usuario inyectando un user_id ajeno.",
                "resultado": "El sistema restringe la consulta estrictamente al ID autenticado en el token JWT; deniega el acceso con HTTP 403.",
                "estado": "Satisfactorio",
                "precondicion": "Petición con token JWT intentando consultar recursos de otro usuario."
            }
        ],
        "responsable": "Usuario Autenticado (Cliente / Personal / Repartidor)",
        "adjunto": "Menú Desplegable de Notificaciones y Pantalla Móvil (notifications_view.dart)"
    }
]
