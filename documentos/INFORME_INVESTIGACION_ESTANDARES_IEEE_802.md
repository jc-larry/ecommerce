# INFORME DE INVESTIGACIÓN TÉCNICA: ESTÁNDARES IEEE 802 (IEEE 802.11 E IEEE 802.15.1)

---

## 1. MARCO GENERAL DEL COMITÉ IEEE 802

El Comité de Estándares IEEE 802 normaliza las redes de área local (LAN), metropolitana (MAN) y personal (PAN). Dentro de este marco, el modelo de referencia divide la Capa de Enlace de Datos (Capa 2 del modelo OSI) en dos subcapas complementarias:

```
+-------------------------------------------------------------------------+
| Capa de Red (Capa 3 OSI: IPv4, IPv6)                                    |
+-------------------------------------------------------------------------+
| Capa de Enlace (Capa 2 OSI):                                            |
|   1. Subcapa LLC (IEEE 802.2 - Logical Link Control):                   |
|      - Multiplexación de protocolos de red, control de flujo y errores. |
|   2. Subcapa MAC (Medium Access Control):                               |
|      - Direccionamiento físico, delimitación de tramas y arbitraje.     |
|      +-------------------------+------------------------------------+   |
|      | IEEE 802.11 MAC (Wi-Fi) | IEEE 802.15.1 MAC (Bluetooth)     |   |
+------+-------------------------+------------------------------------+---+
| Capa Física (Capa 1 OSI):                                               |
|      | IEEE 802.11 PHY         | IEEE 802.15.1 PHY                  |
|      | DSSS / OFDM / OFDMA     | GFSK / DQPSK / 8DPSK con FHSS      |
+------+-------------------------+------------------------------------+---+
```

Esta modularidad permite que protocolos de capa de red (como IP) operen de forma transparente tanto sobre un enlace cableado Ethernet (802.3) como sobre enlaces inalámbricos Wi-Fi (802.11) o Bluetooth (802.15.1).

---

## 2. ESTÁNDAR IEEE 802.11 (WIRELESS LOCAL AREA NETWORK - WI-FI)

El estándar IEEE 802.11 especifica la subcapa de control de acceso al medio (MAC) y múltiples capas físicas (PHY) para comunicaciones inalámbricas en distancias medias (hasta 100 metros en interiores y 300 metros en exteriores).

### 2.1 Evolución Cronológica de las Enmiendas y Tecnologías

| Estándar | Año | Banda Espectral | Ancho de Canal | Modulación Máxima | Tasa Máxima Teórica | Tecnología Clave |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **802.11 Legacy** | 1997 | 2.4 GHz | 20 MHz | DSSS / FHSS | 2 Mbps | Primer estándar WLAN comercial. |
| **802.11b** | 1999 | 2.4 GHz | 20 MHz | HR-DSSS (CCK) | 11 Mbps | Popularización masiva del Wi-Fi en hogares. |
| **802.11a** | 1999 | 5 GHz | 20 MHz | OFDM | 54 Mbps | Banda limpia de 5 GHz sin interferencia de microondas. |
| **802.11g** | 2003 | 2.4 GHz | 20 MHz | OFDM | 54 Mbps | Compatibilidad regresiva con 802.11b a mayor velocidad. |
| **802.11n (Wi-Fi 4)** | 2009 | 2.4 y 5 GHz | 20 y 40 MHz | 64-QAM (OFDM) | 600 Mbps (4 streams) | Introducción de MIMO (*Multiple-Input Multiple-Output*). |
| **802.11ac (Wi-Fi 5)**| 2013 | 5 GHz | 20, 40, 80, 160 MHz | 256-QAM (OFDM) | 6.93 Gbps (8 streams)| Canales anchos y MU-MIMO en enlace descendente (*Downlink*). |
| **802.11ax (Wi-Fi 6/6E)**| 2020 | 2.4, 5 y 6 GHz | Hasta 160 MHz | 1024-QAM | 9.6 Gbps (8 streams) | OFDMA, MU-MIMO bidireccional y banda de 6 GHz (Wi-Fi 6E). |
| **802.11be (Wi-Fi 7)**| 2024 | 2.4, 5 y 6 GHz | Hasta 320 MHz | 4096-QAM | 46 Gbps (16 streams)| Multi-Link Operation (MLO) y canales de 320 MHz. |

### 2.2 Bandas de Frecuencia y Distribución de Canales

#### Banda de 2.4 GHz (2.400 - 2.4835 GHz)
* Espacio espectral reducido y altamente congestionado.
* Se subdivide en 11 canales en América (FCC) y 13 en Europa (ETSI), espaciados cada 5 MHz pero con un ancho de canal estándar de 20 MHz.
* **Canales no superpuestos:** Únicamente los canales **1 (2412 MHz), 6 (2437 MHz) y 11 (2462 MHz)** presentan aislamiento espectral completo entre sí, evitando la interferencia de canal adyacente.

```
Espectro 2.4 GHz y canales no superpuestos:
     Canal 1             Canal 6             Canal 11
   /---------\         /---------\         /---------\
  /     |     \       /     |     \       /     |     \
-/------|------\-----/------|------\-----/------|------\---
 2402  2412  2422   2427  2437  2447   2452  2462  2472  (MHz)
```

#### Banda de 5 GHz (5.150 - 5.850 GHz)
* Ofrece hasta 25 canales de 20 MHz no superpuestos.
* Permite unión de canales (*Channel Bonding*) para formar bloques de 40, 80 y 160 MHz.
* Dividida en sub-bandas: UNII-1 (interiores), UNII-2/UNII-2 Extended (requieren DFS - *Dynamic Frequency Selection* para evitar interferencias con radares meteorológicos y militares) y UNII-3 (exteriores).

#### Banda de 6 GHz (5.925 - 7.125 GHz)
* Introducida con Wi-Fi 6E y Wi-Fi 7; aporta **1200 MHz de espectro continuo libre de interferencias**.
* Habilita hasta 14 canales ultra anchos de 80 MHz o 7 canales de 160 MHz sin coexistencia obligada con estándares antiguos (no hay dispositivos 802.11b/g/n en 6 GHz).

### 2.3 Mecanismo de Control de Acceso al Medio: CSMA/CA

En redes inalámbricas no es viable emplear CSMA/CD (usado en Ethernet cableado) porque los transceptores de radio no pueden transmitir con alta potencia y detectar al mismo tiempo una señal colisionante débil recibida por la misma antena (*problema de colisión no detectable localmente*).

Por ello, IEEE 802.11 implementa **CSMA/CA (*Carrier Sense Multiple Access with Collision Avoidance*)**:

```
Mecanismo de Retardo y Acceso al Medio CSMA/CA:
Medio ocupado
======|====================|---- SIFS ---|-- DIFS --|-- Random Backoff --| Transmite Trama
      |                    |             |          |  [Slot][Slot][Slot]|
      +--------------------+-------------+----------+--------------------+
```

1. **Detección de Portadora Física (*Physical Carrier Sense*):** La tarjeta de red inalámbrica escucha el canal en el aire mediante el mecanismo CCA (*Clear Channel Assessment*). Si la energía de radiofrecuencia supera un umbral, el medio se considera ocupado.
2. **Detección de Portadora Virtual (*Virtual Carrier Sense*):** Cada trama 802.11 incluye en su cabecera un campo llamado **Duration/ID**. Los demás nodos que escuchan la trama extraen este valor y programan un temporizador interno denominado **NAV (*Network Allocation Vector*)**. Mientras el contador NAV no llega a cero, el nodo asume que el medio está ocupado sin necesidad de muestrear la antena.
3. **Temporizadores Intertrama (*Interframe Spaces - IFS*):**
   - **SIFS (*Short IFS*):** Período de espera más corto. Utilizado para tramas de máxima prioridad (Respuestas ACK, tramas CTS).
   - **PIFS (*PCF IFS*):** Prioridad media para el modo de acceso centralizado sin contienda.
   - **DIFS (*DCF IFS*):** Período de espera mínimo obligatorio que debe guardar una estación antes de poder transmitir datos ordinarios en contienda.
4. **Ventana de Contienda y Retroceso Aleatorio (*Random Backoff*):** Si el canal permanece libre tras el período DIFS, la estación no transmite de inmediato para evitar colisiones simultáneas. Selecciona un número entero aleatorio dentro de una ventana de contienda:
   $$\text{Backoff} = \text{Random}(0, CW) \times \text{Slot Time}$$
   El contador decrece por cada ranura (*Slot Time*) que el canal sigue libre. Cuando llega a cero, el nodo transmite. Si ocurre una colisión (falta de ACK), el valor de la ventana $CW$ se duplica exponencialmente ($CW_{min} \rightarrow CW_{max}$).
5. **Protocolo RTS/CTS y Problema del Nodo Oculto:**
   - En una topología inalámbrica, dos estaciones (A y C) pueden estar dentro del rango de cobertura del Punto de Acceso (B), pero fuera del rango de cobertura mutuo (A no escucha a C). Si ambas transmiten hacia B simultáneamente, causan colisión (*Hidden Node Problem*).
   - Solución: Antes de transmitir datos grandes, A envía una trama corta **RTS (*Request to Send*)**. El AP responde con una trama **CTS (*Clear to Send*)** que tiene suficiente potencia para ser escuchada por A y por C. El CTS contiene un valor NAV que bloquea la transmisión de C, permitiendo que A transmita sin colisiones.

```
Problema del Nodo Oculto y Resolución RTS/CTS:
   +-------+               +-------+               +-------+
   |  (A)  | -----RTS----> |  (B)  | <----NAV----- |  (C)  |
   | Est.1 | <----CTS----- | Access| -----CTS----> | Est.2 |
   |       | =====Data===> | Point |  (Bloqueado)  |       |
   +-------+               +-------+               +-------+
   (Fuera de alcance mutuo pero ambas conectadas a B)
```

### 2.4 Topologías de Red en 802.11

* **BSS (*Basic Service Set*):** Bloque básico de una red en modo infraestructura. Compuesto por un único Punto de Acceso (AP) y los clientes inalámbricos asociados a él. El identificador físico es el **BSSID**, que coincide con la dirección MAC de radio del AP.
* **ESS (*Extended Service Set*):** Unión de dos o más BSS interconectados mediante una red cableada troncal denominada Sistema de Distribución (DS). Permite a los clientes compartir un mismo nombre lógico de red (**SSID**) y realizar itinerancia (*roaming*) transparente entre puntos de acceso sin perder la conectividad de Capa 3.
* **IBSS (*Independent Basic Service Set*):** Modo *Ad-Hoc* o de comunicación directa punto a punto entre terminales inalámbricos sin intermediación de un AP central.

### 2.5 Seguridad y Cifrado en Redes 802.11

1. **WEP (*Wired Equivalent Privacy* - 1999):** Obsoleto y vulnerable. Empleaba el algoritmo de flujo RC4 con una clave estática concatenada a un Vector de Inicialización (IV) de apenas 24 bits transmitido en texto claro. Su escasa longitud provoca la reutilización cíclica de claves, permitiendo descifrar la contraseña en minutos mediante recolección de paquetes (*ataques FMS y PTW*).
2. **WPA (*Wi-Fi Protected Access* - 2003):** Medida de contingencia basada en TKIP (*Temporal Key Integrity Protocol*). Incrementó el IV a 48 bits e introdujo mezcla dinámica de claves por paquete y verificación de integridad MIC (*Michael*).
3. **WPA2 (IEEE 802.11i - 2004):** Estándar corporativo maduro. Reemplazó RC4 por el estándar de cifrado en bloque **AES (*Advanced Encryption Standard*)** con una longitud de clave de 128 bits operando en modo **CCMP (*Counter Mode with Cipher Block Chaining Message Authentication Code Protocol*)**. Provee confidencialidad, integridad y autenticación de origen robustas.
4. **WPA3 (2018):** Reemplaza el enlace de cuatro vías (*4-way handshake*) de clave compartida pre-compartida (PSK) por el protocolo **SAE (*Simultaneous Authentication of Equals*)** basado en intercambio Diffie-Hellman contra curvas elípticas. Es inmune a ataques de diccionario fuera de línea (*offline dictionary attacks*) y garantiza el secreto hacia adelante (*Forward Secrecy*).

---

## 3. ESTÁNDAR IEEE 802.15.1 (WIRELESS PERSONAL AREA NETWORK - BLUETOOTH)

El estándar IEEE 802.15.1 define las especificaciones para Redes de Área Personal Inalámbricas (WPAN), orientadas al reemplazo de cables en distancias cortas (1 a 10 metros en dispositivos convencionales, ampliable hasta 100+ metros en aplicaciones industriales), bajo consumo de energía y coste reducido.

### 3.1 Origen y Transición al Bluetooth SIG
Desarrollado inicialmente en 1994 por Ericsson para eliminar el cableado serie RS-232 entre teléfonos y accesorios. En 2002, el IEEE formalizó las especificaciones base bajo el estándar **IEEE 802.15.1**. Posteriormente, la evolución del protocolo continuó bajo la dirección del consorcio industrial **Bluetooth Special Interest Group (Bluetooth SIG)**, manteniendo la compatibilidad arquitectónica de capas con IEEE 802.

### 3.2 Capa Física (PHY), Bandas y Modulación

Bluetooth opera en la banda industrial, científica y médica (ISM) no licenciada de **2.4 GHz (2400 a 2483.5 MHz)** en todo el mundo.

#### Arquitectura de Canales de RF:
* **Bluetooth Clásico (BR / EDR):** Divide el espectro en **79 canales** de radiofrecuencia con un espaciado de canal de **1 MHz** ($f = 2402 + k$ MHz, donde $k = 0, \dots, 78$).
* **Bluetooth Low Energy (BLE):** Divide el espectro en **40 canales** de radiofrecuencia espaciados por **2 MHz** ($f = 2402 + k \times 2$ MHz, donde $k = 0, \dots, 39$):
  - **3 Canales de Anuncio (*Advertising Channels* - 37, 38 y 39):** Ubicados estratégicamente en 2402 MHz, 2426 MHz y 2480 MHz, posicionándose en los huecos espectrales libres entre los canales 1, 6 y 11 de Wi-Fi para garantizar descubrimiento rápido y sin colisiones.
  - **37 Canales de Datos (*Data Channels* - 0 al 36):** Empleados para la transferencia bidireccional punto a punto una vez establecida la conexión.

```
Distribución de Canales BLE frente a Canales Wi-Fi en 2.4 GHz:
 Wi-Fi Ch.1 (2412)          Wi-Fi Ch.6 (2437)          Wi-Fi Ch.11 (2462)
 [============== ]          [==============]          [==============]
   ^                                  ^                                  ^
   |                                  |                                  |
 Canal 37                           Canal 38                           Canal 39
 (2402 MHz)                         (2426 MHz)                         (2480 MHz)
 (Canal de Anuncio BLE)             (Canal de Anuncio BLE)             (Canal de Anuncio BLE)
```

#### Esquemas de Modulación:
* **Basic Rate (BR):** Modulación digital por desplazamiento de frecuencia gaussiana (**GFSK**) con producto ancho de banda-tiempo $BT = 0.5$. Tasa de símbolos bruta de 1 Msímbolo/s (rendimiento bruto de **1 Mbps**).
* **Enhanced Data Rate (EDR):** 
  - $\pi/4$-DQPSK para tasas de **2 Mbps**.
  - 8DPSK para tasas de **3 Mbps**.

### 3.3 Salto de Frecuencia Adaptativo (AFH / FHSS)

Para mitigar la severa interferencia en la saturada banda de 2.4 GHz (generada por redes Wi-Fi, hornos de microondas y teléfonos inalámbricos), Bluetooth utiliza **Salto de Frecuencia por Espectro Ensanchado (*Frequency Hopping Spread Spectrum - FHSS*)**:

* La portadora conmuta de canal a una tasa nominal de **1600 saltos por segundo**.
* El intervalo de tiempo de cada ranura (*time slot*) es de **625 microsegundos** ($\mu\text{s}$).
* **AFH (*Adaptive Frequency Hopping*):** Los dispositivos evalúan permanentemente la tasa de error de paquete en cada canal. Si detectan que canales específicos sufren interferencias consistentes (por ejemplo, los ocupados por una red Wi-Fi en el canal 6), los marcan como defectuosos en un mapa de canales y reducen la secuencia de saltos pseudoaleatorios a un conjunto mínimo de canales limpios (mínimo 20 canales de los 79 disponibles).

```
Salto de Frecuencia Adaptativo en Bluetooth:
Canal RF
79 |       *
   |              *              *
   |   *
 6 |------- [Banda Wi-Fi detectada: Canales bloqueados por AFH] -------
   |                                            *
 1 |                  *
 0 +---|-------|------|------|------|------|------|---> Tiempo (Slots de 625 µs)
       t1      t2     t3     t4     t5     t6
```

### 3.4 Topologías de Red en IEEE 802.15.1

#### La Piconet
Es la unidad básica de red ad-hoc en Bluetooth.
* Está formada por **1 dispositivo Maestro (*Master*)** y hasta **7 dispositivos Esclavos activos (*Active Slaves*)**.
* El Maestro define el reloj maestro de sincronización y la secuencia pseudoaleatoria de salto de frecuencia para toda la piconet.
* Toda la comunicación es centralizada: los esclavos solo pueden transmitir cuando el maestro los sondea en una ranura temporal específica. La comunicación directa esclavo-esclavo no existe a nivel de enlace.
* Además de los 7 esclavos activos, una piconet puede mantener hasta 255 dispositivos en estado estacionado (*Parked State*), sincronizados con el reloj maestro pero sin asignación de ranuras de datos activas.

#### La Scatternet (Red Dispersa)
Se forma cuando dos o más piconets se interconectan compartiendo uno o más nodos miembros:
* Un dispositivo puede actuar como **Esclavo en múltiples piconets**, alternando su sincronización de salto de frecuencia entre ambos maestros mediante multiplexación por división de tiempo (TDM).
* Un dispositivo puede actuar como **Maestro en una piconet y como Esclavo en otra**.
* Un dispositivo **nunca** puede ser Maestro en dos piconets simultáneamente, ya que dos relojes maestros generarían desincronización de salto en el hardware de radio.

```
Estructura de Piconet y Scatternet:
  +---------------+                      +---------------+
  |   Esclavo 1   |                      |   Esclavo 4   |
  +-------+-------+                      +-------+-------+
          |                                      |
  +-------+-------+       +--------------+       |
  |  MAESTRO (A)  | <---> | NODO PUENTE  | <-----+
  +-------+-------+       | (Esclavo A / |       |
          |               | Esclavo B)   | +-----+-------+
  +-------+-------+       +--------------+ | MAESTRO (B)  |
  |   Esclavo 2   |                        +-----+-------+
  +---------------+                              |
                                           +-----+-------+
       [ PICONET 1 ]                       |   Esclavo 5 |
                                           +-------------+
                                                 |
                                            [ PICONET 2 ]
  +------------------------------------------------------+
  |              SCATTERNET CONSOLIDADA                  |
  +------------------------------------------------------+
```

### 3.5 Evolución Técnica: Bluetooth Clásico frente a Bluetooth Low Energy (BLE)

La evolución del protocolo dio un giro radical con la versión 4.0, escindiendo el estándar en dos ramas operativas incompatibles en capa física pero unificadas en la aplicación:

1. **Bluetooth Clásico (BR/EDR - v1.0 a v3.0):**
   - Diseñado para flujos continuos de datos a media velocidad (audio inalámbrico analógico/digital, transferencia de archivos, sincronización serie).
   - Mantiene la conexión abierta permanentemente mediante enlaces síncronos orientados a conexión (SCO) o asíncronos sin conexión (ACL).
   - Consumo de corriente del orden de 20 a 40 mA en transmisión continua.

2. **Bluetooth Low Energy (BLE / Smart - v4.0 a v5.4):**
   - Diseñado desde cero para Internet de las Cosas (IoT), balizas (*beacons*), sensores médicos y wearables.
   - Paradigma de transmisión por ráfagas ultra cortas (milisegundos) y retorno inmediato a suspensión profunda (*deep sleep*).
   - Consumo de corriente en reposo inferior a **1 microamperio ($\mu\text{A}$)**, permitiendo que un dispositivo funcione durante años con una batería de botón tipo botón CR2032.
   - **Mejoras de Bluetooth 5.0 en adelante:**
     * **2M PHY:** Duplica la tasa de transferencia en el aire a 2 Mbps.
     * **Coded PHY:** Incorpora corrección de errores hacia adelante (**FEC** con codificación $S=2$ o $S=8$), cuadruplicando el alcance efectivo (superando 200 metros en línea de vista) a cambio de reducir la velocidad neta a 125 kbps o 500 kbps.
     * **Bluetooth Mesh:** Supera la limitación de la piconet al permitir redes malladas de miles de dispositivos mediante un mecanismo de inundación controlada (*managed flooding*).
     * **LE Audio y Códec LC3:** Transmisión de audio multicanal de alta calidad con la mitad del consumo de ancho de banda respecto al códec SBC clásico, e introducción de difusión pública de audio (*Auracast*).

### 3.6 Perfiles de Aplicación (Profiles)
Para garantizar la interoperabilidad de fabricantes, Bluetooth estandariza casos de uso completos:
* **Perfiles Clásicos:**
  - **A2DP (*Advanced Audio Distribution Profile*):** Transmisión unidireccional de audio estéreo de alta calidad (códecs SBC, AAC, LDAC, aptX).
  - **AVRCP (*Audio/Video Remote Control Profile*):** Control de reproducción (play, pause, pista siguiente/anterior).
  - **HFP / HSP (*Hands-Free Profile / Headset Profile*):** Enlace bidireccional monoaural para telefonía con canal de control de llamada.
  - **SPP (*Serial Port Profile*):** Emulación transparente de cables serie RS-232 sobre el protocolo RFCOMM.
* **Arquitectura de Perfiles BLE (GATT - Generic Attribute Profile):**
  - Toda la información se estructura de forma jerárquica en una base de datos cliente/servidor:
    $$\text{Servidor GATT} \rightarrow \text{Servicios (UUIDs)} \rightarrow \text{Características (Valores + Permisos)} \rightarrow \text{Descriptores}$$
  - Ejemplo: Un pulsioxímetro expone el servicio *Heart Rate Service* (`0x180D`), que contiene la característica *Heart Rate Measurement* (`0x2A37`), la cual envía notificaciones periódicas con los pulsos por minuto.

---

## 4. ANÁLISIS COMPARATIVO DIRECTO: IEEE 802.11 vs. IEEE 802.15.1

| Parámetro de Ingeniería | IEEE 802.11 (Wi-Fi) | IEEE 802.15.1 (Bluetooth) |
| :--- | :--- | :--- |
| **Clasificación de Red** | WLAN (*Wireless Local Area Network*) | WPAN (*Wireless Personal Area Network*) |
| **Banda(s) de Operación** | 2.4 GHz, 5 GHz y 6 GHz | 2.4 GHz ISM exclusivamente |
| **Ancho de Canal de RF** | 20, 40, 80, 160 y hasta 320 MHz | 1 MHz (Clásico) / 2 MHz (BLE) |
| **Throughput Máximo Teórico** | De 11 Mbps (802.11b) a 46 Gbps (802.11be) | De 1 Mbps (BR) a 3 Mbps (EDR) / 2 Mbps (BLE) |
| **Throughput Útil Real Típico** | 50 Mbps - 1.5 Gbps (según entorno y norma) | 200 kbps - 2.1 Mbps (Clásico) / 100 kbps - 1.4 Mbps (BLE)|
| **Mecanismo de Arbitraje MAC**| CSMA/CA con contienda (DCF / EDCA) | Maestro/Esclavo polling con saltos FHSS (TDM) |
| **Técnica de Espectro** | DSSS, OFDM, OFDMA | Salto Adaptativo de Frecuencia (AFH / FHSS) |
| **Alcance Operativo Típico** | 30 a 100 metros (interior) / 300 m (exterior)| 5 a 15 metros (Clásico) / hasta 200 m (BLE Coded PHY)|
| **Consumo de Potencia** | Alto (0.5 W a 5 W en transmisión continua) | Extremadamente bajo (< 0.05 W en Clásico / microvatios en BLE)|
| **Duración de Batería Típica**| Horas a días (requiere baterías de litio grandes)| Meses a años con pilas de botón CR2032 (BLE) |
| **Topología Primaria** | Estrella extendida (Infraestructura AP con ESS)| Estrella en Piconet (1M:7S) / Malla (Bluetooth Mesh) |
| **Tamaño de MTU / Trama** | 1500 a 2304 bytes por trama | 339 bytes (DH5 Clásico) / 27 a 251 bytes (PDU BLE) |
| **Cifrado y Seguridad** | WPA2 (AES-CCMP) / WPA3 (SAE) | Cifrado E0 (Clásico legado) / AES-128 CCM (BLE) |
| **Escenarios de Aplicación** | Conectividad a Internet de banda ancha, streaming 4K/8K, transferencia de archivos masiva, telemetría de alta velocidad. | Accesorios de audio personal, periféricos (teclado/ratón), domótica, sensores biomédicos, telemetría IoT. |

---

## 5. CONVIVENCIA E INTERFERENCIA ESPECTRAL EN LA BANDA DE 2.4 GHz

Debido a que tanto IEEE 802.11 como IEEE 802.15.1 comparten la misma banda sin licencia de 2.4 GHz, la coexistencia de ambos protocolos en espacios cerrados demanda técnicas de aislamiento para evitar la degradación de throughput y latencia:

1. **Aislamiento en Frecuencia (AFH):** Bluetooth detecta la portadora estática de una red Wi-Fi en 20 MHz (que ocupa el equivalente a 22 canales Bluetooth contiguos) y excluye automáticamente dichos canales de su secuencia de salto, desplazando su comunicación a los canales de radio libres.
2. **Coexistencia Física por Colaboración (PTA - *Packet Traffic Arbitration*):** En dispositivos que integran radios Wi-Fi y Bluetooth en el mismo chip o tarjeta física (como smartphones o computadoras portátiles), un circuito lógico de arbitraje de tres o cuatro hilos coordina las antenas en tiempo real: prioriza los paquetes críticos de Bluetooth (como paquetes de voz HFP o sincronización de audio A2DP) pausando temporalmente la transmisión de paquetes Wi-Fi durante algunos microsegundos para evitar que el transmisor Wi-Fi sature el receptor Bluetooth.
