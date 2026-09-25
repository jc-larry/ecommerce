# ACTUALIZACIÓN INTEGRAL DE DIAGRAMAS DE SECUENCIA Y TRAZABILIDAD EN CÓDIGO (CU01 A CU40)

**Proyecto:** FashionStore – Sistema de Comercio Electrónico y Gestión de Moda  
**Materia:** Sistemas de Información II (SI 2) – Semestre 2-2026  
**Fecha de Actualización:** 22 de Septiembre de 2026  
**Documento Canónico de Referencia:** `media_1790089623158.pdf` (Especificación Oficial de 25 Páginas)  
**Especificación Detallada de Diagramas:** [`documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md`](file:///documentos/DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md)

---

## 1. RESUMEN EJECUTIVO DE LA ACTUALIZACIÓN

En cumplimiento con los requerimientos formales de la asignatura y la revisión de diagramas del proyecto, se ejecutó una **actualización, sincronización y auditoría bidireccional completa** entre:
1. **Los 40 Diagramas de Secuencia Canónicos** descritos en la documentación del sistema.
2. **Las marcas de trazabilidad y comentarios de código fuente** en los controladores y routers del Backend (FastAPI / SQLAlchemy).

### Objetivos Alcanzados:
- **Numeración Secuencial Estricta y Continua (100% Sin Omisiones ni Saltos):**
  - **Diagramas de Secuencia:** Se auditaron y corrigieron todos los mensajes y flechas de respuesta (`-->>`) en los 40 diagramas Mermaid. **Total de mensajes sin número en los diagramas: 0**. Cada interacción cuenta con su identificador secuencial explícito (`1:`, `2:`, `3:`, ..., y alternativas `5a:`, `6a:`).
  - **Trazabilidad en Código Fuente:** Los 40 Casos de Uso (`CU01` a `CU40`) inician obligatoriamente en el **`Paso 1`** en su punto de entrada y mantienen una secuencia entera ininterrumpida (`1, 2, 3, 4, ...`) sin huecos ni mezclas.
- **Estandarización UML 2.5 + BCE:** Todos los diagramas utilizan el patrón de arquitectura de análisis *Boundary-Control-Entity* (BCE) con los estereotipos formales:
  - `IU_*` (Interfaces de Usuario: Web, Móvil, POS, etc.)
  - `CTR_*` (Controladores lógicos de aplicación / Routers)
  - `CE_*` (Entidades de dominio y persistencia de base de datos)
  - Fragmentos combinados formales de UML 2.5 (`alt` para flujos alternos/excepciones, `loop` para iteraciones, `opt` para condicionales opcionales y `rect` para agrupaciones visuales de transacciones ACID).
- **Resolución Definitiva de Búsquedas en el IDE (Trazabilidad Limpia):** Al buscar cualquier código de caso de uso (ej. `DSC012`, `DSC016`, `DSC019`, `DSC029`, `DSC040`) en el explorador del IDE (VS Code / Antigravity IDE), **los resultados aparecen agrupados en su archivo correspondiente, en riguroso orden ascendente desde el Paso 1 hasta el Paso N**, permitiendo una lectura fluida e inmediata para defensas y auditorías.

---

## 2. FORMATO ESTÁNDAR DE TRAZABILIDAD EN CÓDIGO FUENTE

Cada punto de ejecución en el código fuente sigue rigurosamente el formato estándar:

```python
# [CUXX - Paso Y] / [DSCXX - Paso Y] +metodo_o_accion(argumentos)
```

En caso de bifurcaciones, excepciones o bucles definidos en el diagrama de secuencia, la etiqueta indica explícitamente el fragmento UML 2.5:

```python
# [CUXX - Paso Y] / [DSCXX - Paso Y] [alt: Condicion] +accion()
# [CUXX - Paso Y] / [DSCXX - Paso Y] [loop: Coleccion] +accion()
```

---

## 3. MATRIZ DE TRAZABILIDAD AUDITADA (40 CASOS DE USO)

La siguiente tabla resume el estado auditado de los 40 Casos de Uso.  
**Criterios de Aprobación:**
- **Inicia en Paso 1:** Indica si el primer paso registrado en el backend es `Paso 1` (100% de cumplimiento).
- **Secuencia Continua:** Indica que no existen números salteados (0 gaps).
- **Flechas Sin Número en Diagrama:** 0 flechas sin número.

| CU | Código DSC | Nombre del Caso de Uso | Paquete Backend | Pasos en Código | Inicia Paso 1 | Gaps | Flechas Diagrama |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **CU01** | `DSC001` | Iniciar sesión y autenticación JWT | `paquete_seguridad_usuarios` | 1..6 | Sí | 0 | 100% numeradas |
| **CU02** | `DSC002` | Cerrar sesión y revocación token | `paquete_seguridad_usuarios` | 1..5 | Sí | 0 | 100% numeradas |
| **CU03** | `DSC003` | Recuperar credenciales (enlace 5 min) | `paquete_seguridad_usuarios` | 1..11 | Sí | 0 | 100% numeradas |
| **CU04** | `DSC004` | Registro de clientes (auto-registro) | `paquete_seguridad_usuarios` | 1..7 | Sí | 0 | 100% numeradas |
| **CU05** | `DSC005` | Gestión de usuarios del sistema y roles | `paquete_seguridad_usuarios` | 1..6 | Sí | 0 | 100% numeradas |
| **CU06** | `DSC006` | Gestión de sucursales físicas | `paquete_catalogo_y_tiendas/branches` | 1..8 | Sí | 0 | 100% numeradas |
| **CU07** | `DSC007` | Registrar prenda con variantes y fotos | `paquete_catalogo_y_tiendas` | 1..7 | Sí | 0 | 100% numeradas |
| **CU08** | `DSC008` | Gestión de proveedores de confección | `paquete_inventario_y_proveedores` | 1..6 | Sí | 0 | 100% numeradas |
| **CU09** | `DSC009` | Asignación de empleados a sucursal | `paquete_catalogo_y_tiendas/branches` | 1..6 | Sí | 0 | 100% numeradas |
| **CU10** | `DSC010` | Registro de compras a proveedores | `paquete_inventario_y_proveedores/merchandise` | 1..10 | Sí | 0 | 100% numeradas |
| **CU11** | `DSC011` | Navegación de catálogo, ofertas y reseñas | `paquete_catalogo_y_tiendas` | 1..5 | Sí | 0 | 100% numeradas |
| **CU12** | `DSC012` | Búsqueda facetada y stock por sucursales | `paquete_catalogo_y_tiendas` | 1..8 | Sí | 0 | 100% numeradas |
| **CU13** | `DSC013` | Gestión de cupones y promociones | `paquete_ventas_y_pagos` | 1..8 | Sí | 0 | 100% numeradas |
| **CU14** | `DSC014` | Valoración, reseñas y lista de deseos | `paquete_catalogo_y_tiendas` | 1..13 | Sí | 0 | 100% numeradas |
| **CU15** | `DSC015` | Transferencia de mercadería inter-sucursal | `paquete_inventario_y_proveedores/merchandise` | 1..9 | Sí | 0 | 100% numeradas |
| **CU16** | `DSC016` | Alertas de stock mínimo y máximo | `paquete_inventario_y_proveedores/merchandise` | 1..12 | Sí | 0 | 100% numeradas |
| **CU17** | `DSC017` | Gestión de carrito de compra digital | `paquete_ventas_y_pagos` | 1..10 | Sí | 0 | 100% numeradas |
| **CU18** | `DSC018` | Venta digital / Checkout (Tienda vs. Delivery + Pasarela) | `paquete_ventas_y_pagos` | 1..11 | Sí | 0 | 100% numeradas |
| **CU19** | `DSC019` | Venta presencial en mostrador POS | `paquete_ventas_y_pagos` | 1..18 | Sí | 0 | 100% numeradas |
| **CU20** | `DSC020` | Emisión y generación de factura PDF (IVA 13%) | `paquete_ventas_y_pagos` | 1..5 | Sí | 0 | 100% numeradas |
| **CU21** | `DSC021` | Generar cotización formal en PDF | `paquete_ventas_y_pagos` | 1..9 | Sí | 0 | 100% numeradas |
| **CU22** | `DSC022` | Devolución de mercadería y garantías | `paquete_ventas_y_pagos` | 1..6 | Sí | 0 | 100% numeradas |
| **CU23** | `DSC023` | Apertura, arqueo y cierre de caja/turno | `paquete_ventas_y_pagos` | 1..9 | Sí | 0 | 100% numeradas |
| **CU24** | `DSC024` | Historial y seguimiento de compras | `paquete_ventas_y_pagos` | 1..6 | Sí | 0 | 100% numeradas |
| **CU25** | `DSC025` | Conversión de reserva a venta POS en tienda | `paquete_reservas_y_citas` | 1..7 | Sí | 0 | 100% numeradas |
| **CU26** | `DSC026` | Reserva online de prendas con seña PayPal | `paquete_reservas_y_citas` | 1..4 | Sí | 0 | 100% numeradas |
| **CU27** | `DSC027` | Bandeja de reservas y vencimientos | `paquete_reservas_y_citas` | 1..6 | Sí | 0 | 100% numeradas |
| **CU28** | `DSC028` | Cancelación de reserva y liberación stock | `paquete_reservas_y_citas` | 1..5 | Sí | 0 | 100% numeradas |
| **CU29** | `DSC029` | Despacho y entrega por repartidores | `paquete_envios_y_logistica/delivery_persons` | 1..4 | Sí | 0 | 100% numeradas |
| **CU30** | `DSC030` | Rastreo de envío en tiempo real | `paquete_envios_y_logistica` | 1..8 | Sí | 0 | 100% numeradas |
| **CU31** | `DSC031` | Zonas de cobertura y tarifas por anillos/km | `paquete_envios_y_logistica` | 1..12 | Sí | 0 | 100% numeradas |
| **CU32** | `DSC032` | Probador virtual VTON con IA y recomendación | `paquete_inteligente_y_analitica` | 1..5 | Sí | 0 | 100% numeradas |
| **CU33** | `DSC033` | Chatbot asistente de compras y moda con IA | `paquete_inteligente_y_analitica` | 1..4 | Sí | 0 | 100% numeradas |
| **CU34** | `DSC034` | Búsqueda por comando de voz y NLP | `paquete_inteligente_y_analitica` | 1..4 | Sí | 0 | 100% numeradas |
| **CU35** | `DSC035` | Reportes gerenciales (Kardex, CSV, voz TTS) | `paquete_inteligente_y_analitica` | 1..6 | Sí | 0 | 100% numeradas |
| **CU36** | `DSC036` | Bitácora de auditoría inmutable | `paquete_inteligente_y_analitica` | 1..4 | Sí | 0 | 100% numeradas |
| **CU37** | `DSC037` | Valoración de inventario CPP / Costo Promedio | `paquete_inventario_y_proveedores/merchandise` | 1..7 | Sí | 0 | 100% numeradas |
| **CU38** | `DSC038` | Ajustes de stock con afectación al libro mayor | `paquete_inventario_y_proveedores/merchandise` | 1..7 | Sí | 0 | 100% numeradas |
| **CU39** | `DSC039` | Dashboard gerencial con KPIs en tiempo real | `paquete_inteligente_y_analitica` | 1..4 | Sí | 0 | 100% numeradas |
| **CU40** | `DSC040` | Notificaciones multi-canal (In-app, Email, Push) | `paquete_notificaciones` | 1..4 | Sí | 0 | 100% numeradas |

---

## 4. AUDITORÍA AUTOMATIZADA Y VERIFICACIÓN

Para comprobar de forma automática que no existen casos omitidos ni números saltados, se ejecutan las siguientes pruebas de verificación:

### 4.1. Verificación de Diagramas de Secuencia (Mermaid):
```python
# Comprueba que 0 flechas carecen de número en DOCUMENTACION_40_CASOS_DE_USO_DIAGRAMAS_SECUENCIA.md
# Resultado verificado: Total unnumbered messages: 0
```

### 4.2. Verificación de Código Fuente Backend:
```python
# Comprueba que el 100% de los 40 Casos de Uso:
# 1. Total encontrados: 40/40
# 2. Sin Paso 1: [] (0 casos)
# 3. Con saltos o huecos (gaps): 0 casos
```

### 4.3. Ejemplo Visual en el IDE (Búsqueda por `DSC012`):
Al abrir el explorador de búsqueda del IDE y tipear `DSC012`:
```
routers.py (backend/app/packages/paquete_catalogo_y_tiendas)
  # [CU12 - Paso 1] / [DSC012 - Paso 1] +ingresar_criterios_busqueda()
  # [CU12 - Paso 2] / [DSC012 - Paso 2] +buscar_y_filtrar_catalogo(filtros)
  # [CU12 - Paso 3] / [DSC012 - Paso 3] +select_products_with_facets()
  # [CU12 - Paso 4] / [DSC012 - Paso 4] +verificar_stock_sucursales(sucursal_id)
  # [CU12 - Paso 5] / [DSC012 - Paso 5] +Retornar catálogo facetado
  # [CU12 - Paso 6] / [DSC012 - Paso 6] +get_availability_by_branch(product_id)
  # [CU12 - Paso 7] / [DSC012 - Paso 7] +select_branches_inventory(product_id)
  # [CU12 - Paso 8] / [DSC012 - Paso 8] +Retornar desglose por sucursales con badges
```
La secuencia es perfectamente correlativa, sin saltos numéricos, y refleja con exactitud la especificación canónica del proyecto.
