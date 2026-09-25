# INFORME DE INVESTIGACIÓN TÉCNICA: EL SWITCH DE CAPA 2

---

## 1. INTRODUCCIÓN Y CONTEXTO EN EL MODELO OSI

El conmutador de red (*switch*) que opera en la Capa 2 del modelo OSI (Capa de Enlace de Datos / *Data Link Layer*) y bajo los estándares de la familia IEEE 802.3 (Ethernet) constituye el dispositivo fundamental de interconexión en redes de área local (LAN).

A diferencia de los repetidores y concentradores multipuerto (*hubs*) de Capa 1, que operan en el dominio puramente físico retransmitiendo señales eléctricas a todos sus puertos mediante difusión ciega, el switch de Capa 2 es un dispositivo de conmutación selectiva. Basa sus decisiones de reenvío en el análisis de las tramas Ethernet y, específicamente, en las direcciones físicas MAC (*Media Access Control*) de 48 bits (EUI-48).

```
+-------------------------------------------------------------+
| Modelo OSI - Nivel de Operación de Switch de Capa 2        |
+-------------------------------------------------------------+
| Capa 7: Aplicación                                          |
| Capa 6: Presentación                                        |
| Capa 5: Sesión                                              |
| Capa 4: Transporte (TCP / UDP)                              |
| Capa 3: Red (Direcciones IPv4 / IPv6, Enrutamiento)         |
| Capa 2: Enlace de Datos (Tramas Ethernet, MAC) <--- SWITCH |
| Capa 1: Física (Bits, Señales eléctricas / ópticas)        |
+-------------------------------------------------------------+
```

---

## 2. CARACTERÍSTICAS TÉCNICAS FUNDAMENTALES

### 2.1 Microsegmentación y Aislamiento de Dominios de Colisión
El switch elimina el problema de las colisiones en redes Ethernet compartidas (CSMA/CD) mediante la microsegmentación:
* **Dominio de colisión:** Cada puerto físico del switch representa un dominio de colisión independiente y aislado. Cuando un dispositivo final se conecta a un puerto del switch en modo *Full-Duplex*, la probabilidad de colisión se reduce a cero, ya que existen pares de transmisión (Tx) y recepción (Rx) independientes.
* **Dominio de broadcast:** Por defecto, todos los puertos del switch pertenecen a un único dominio de difusión (*broadcast*). Si un dispositivo emite una trama dirigida a la dirección MAC de difusión `FF:FF:FF:FF:FF:FF`, el switch la replica a través de todos los puertos activos de la misma VLAN, excepto el puerto de origen.

### 2.2 La Tabla de Conmutación o Tabla CAM (Content-Addressable Memory)
El núcleo lógico del switch es su tabla de reenvío, almacenada en una memoria asociativa de alta velocidad denominada CAM. Esta tabla asocia dinámicamente tres elementos:
1. Dirección MAC aprendida (48 bits en hexadecimal, ej. `001a.a93b.5c41`).
2. Puerto físico de entrada (ej. `GigabitEthernet0/1`).
3. Identificador de VLAN (VLAN ID).

#### Las 4 Funciones Lógicas del Switch:
* **Aprendizaje (*Learning*):** Al recibir una trama por un puerto, el switch examina la **dirección MAC origen**. Si no existe en la tabla CAM, la registra junto con el puerto de ingreso y su VLAN. Si ya existe, actualiza su temporizador de expiración (*aging timer*).
* **Inundación (*Flooding*):** Si la **dirección MAC destino** no está en la tabla CAM (*Unicast desconocido*), o si es una trama de *Broadcast* (`FF:FF:FF:FF:FF:FF`) o *Multicast*, el switch reenvía la trama por todos los puertos activos de esa VLAN, excepto el puerto por donde ingresó.
* **Reenvío (*Forwarding*):** Si la MAC destino se encuentra en la tabla CAM, el switch envía la trama única y exclusivamente por el puerto físico asociado a esa dirección MAC.
* **Filtrado (*Filtering*):** Si la MAC destino se encuentra asociada al mismo puerto físico por donde ingresó la trama (situación común si hay un hub conectado al puerto), el switch descarta la trama para no saturar el medio.
* **Envejecimiento (*Aging Time*):** Para evitar registrar entradas obsoletas de dispositivos desconectados o reubicados, las entradas dinámicas de la tabla CAM poseen un temporizador de caducidad. En conmutadores estándar, este valor es típicamente de **300 segundos** (5 minutos) de inactividad.

### 2.3 Capacidad de Conmutación (Switching Fabric) y Tasa de Reenvío
* **Ancho de banda de conmutación (*Backplane / Fabric Bandwidth*):** Velocidad máxima teórica a la que el bus interno del switch puede transferir datos entre puertos simultáneamente. Para conmutar a tasa de línea (*non-blocking* o sin bloqueo), el cálculo estándar para un switch de 24 puertos Gigabit Full-Duplex es:
  $$\text{Capacidad} = 24 \text{ puertos} \times 1 \text{ Gbps} \times 2 \text{ (Full-Duplex)} + \text{Uplinks} = 48 \text{ Gbps} + \text{Uplinks}$$
* **Tasa de reenvío (*Forwarding Rate* en Mpps):** Cantidad de paquetes o tramas de 64 bytes que los circuitos ASIC (*Application-Specific Integrated Circuit*) del switch pueden procesar y enrutar por segundo.

---

## 3. MODOS DE OPERACIÓN Y REENVÍO DE TRAMAS

El método mediante el cual la circuitería interna procesa y conmuta las tramas entrantes define la latencia y la tolerancia a errores de la red. Existen tres modos principales:

```
Trama Ethernet 802.3:
+-----------+-----+-------------+------------+----------+-----------+-----+
| Preámbulo | SFD | MAC Destino | MAC Origen | Tipo/Len |   Datos   | FCS |
|  7 bytes  | 1 B |   6 bytes   |  6 bytes   | 2 bytes  | 46-1500 B | 4 B |
+-----------+-----+-------------+------------+----------+-----------+-----+
                    ^                          ^                      ^
                    |                          |                      |
Cut-Through --------+                          |                      |
Fragment-Free ---------------------------------+ (Primeros 64 bytes)  |
Store-and-Forward ----------------------------------------------------+
```

### 3.1 Almacenamiento y Reenvío (*Store-and-Forward*)
* **Mecanismo:** El switch recibe y almacena la trama completa en su búfer de memoria. Antes de reenviarla, ejecuta una verificación de redundancia cíclica (*CRC - Cyclic Redundancy Check*) recalculando el campo FCS (*Frame Check Sequence*) de 4 bytes ubicado al final de la trama.
* **Ventajas:** Máxima integridad de datos. Se descartan automáticamente tramas truncadas (*runts* menores a 64 bytes), tramas gigantes (*giants* mayores al MTU) y tramas alteradas por colisiones o ruido eléctrico.
* **Desventajas:** Mayor latencia de conmutación, proporcional al tamaño de la trama (entre 15 y 100 microsegundos).
* **Uso actual:** Es el modo estándar por defecto en la inmensa mayoría de conmutadores de acceso corporativo.

### 3.2 Conmutación Rápida / Directa (*Cut-Through / Fast-Forward*)
* **Mecanismo:** El switch lee únicamente los primeros **6 bytes** de la trama correspondiente a la dirección MAC de destino. Inmediatamente después de consultar la tabla CAM y determinar el puerto de salida, inicia la transmisión de la trama hacia dicho puerto, aun cuando el resto del cuerpo de la trama todavía continúa ingresando por el puerto de origen.
* **Ventajas:** Latencia extremadamente reducida (típicamente inferior a 5 microsegundos), independiente del tamaño de la trama.
* **Desventajas:** No valida el FCS. Si la trama está dañada, el switch la retransmite íntegramente hacia el destino, consumiendo ancho de banda innecesario en los enlaces subsiguientes.
* **Uso actual:** Entornos de centros de datos de ultra baja latencia, finanzas algorítmicas (*High-Frequency Trading*) y redes de almacenamiento SAN.

### 3.3 Libre de Fragmentos (*Fragment-Free*)
* **Mecanismo:** Diseñado como un compromiso técnico entre los dos métodos anteriores. El switch lee y almacena los primeros **64 bytes** de la trama antes de reenviarla.
* **Fundamento:** En las redes Ethernet basadas en contienda, el 99% de las colisiones ocurren dentro de los primeros 64 bytes (la longitud mínima de una trama legal o ranura de colisión). Al verificar 64 bytes, el switch descarta los fragmentos generados por colisiones tempranas sin necesidad de esperar a que termine de llegar una trama grande de 1518 bytes.
* **Ventajas:** Menor latencia que *Store-and-Forward* y descarte de tramas defectuosas por colisión.

---

## 4. PUERTOS DISPONIBLES EN UN SWITCH DE CAPA 2

Un switch profesional cuenta con diferentes tipos de interfaces físicas especializadas:

| Tipo de Puerto | Conector Físico | Estándar / Velocidad | Función Principal |
| :--- | :--- | :--- | :--- |
| **Fast Ethernet** | RJ-45 | IEEE 802.3u (100BASE-TX) 100 Mbps | Conexión de terminales finales heredadas, impresoras de red y sensores. |
| **Gigabit Ethernet** | RJ-45 | IEEE 802.3ab (1000BASE-T) 1 Gbps | Conexión estándar de PCs, servidores, puntos de acceso Wi-Fi y telefonía IP. Soporta *Auto-MDIX* (auto-detección de cable cruzado/directo). |
| **Uplink SFP** | Ranura modular SFP | IEEE 802.3z (1000BASE-SX / LX) 1 Gbps | Enlace ascendente hacia switches de distribución o núcleo usando transceptores ópticos multimodo o monomodo. |
| **Uplink SFP+** | Ranura modular SFP+ | IEEE 802.3ae (10GBASE-SR / LR) 10 Gbps | Enlace troncal de alta capacidad o conexión directa por cobre con cables DAC (*Direct Attach Copper*). |
| **Puerto de Consola** | RJ-45 / Mini-USB / Type-C | RS-232 / Emulación Serie (9600 baudios) | Acceso de administración fuera de banda (*Out-of-Band - OOB*) para configuración inicial sin depender de la red IP. |
| **Puertos PoE / PoE+** | RJ-45 | IEEE 802.3af (15.4 W) / IEEE 802.3at (30 W) | Transmisión simultánea de datos y energía eléctrica sobre los mismos pares de cobre para alimentar dispositivos remotos. |

---

## 5. CONFIGURACIÓN Y ADMINISTRACIÓN DE UN SWITCH

### 5.1 Niveles y Modos de la Interfaz de Línea de Comandos (CLI)
Los switches administrables (como los basados en Cisco IOS) estructuran su configuración de forma jerárquica:

1. **Modo Usuario (`Switch>`):** Permite tareas de diagnóstico básicas de solo lectura (`ping`, `traceroute`, `show version`).
2. **Modo Privilegiado (`Switch#`):** Acceso completo al sistema operativo; permite ver configuraciones activas y ejecutar pruebas detalladas.
3. **Modo de Configuración Global (`Switch(config)#`):** Aplica directivas globales que afectan al comportamiento total del dispositivo.
4. **Modos de Subconfiguración Específicos:**
   - Interfaz: `Switch(config-if)#`
   - Rango de interfaces: `Switch(config-if-range)#`
   - VLAN: `Switch(config-vlan)#`
   - Línea de consola/vty: `Switch(config-line)#`

### 5.2 Parámetros Esenciales de Configuración
* **Identificación del equipo:** Nombre de host (`hostname`) para identificación en la topología.
* **Seguridad de accesos:** Claves cifradas para el modo privilegiado (`enable secret`) y para las líneas de consola y acceso remoto seguro SSH (`line vty 0 15`).
* **Interfaz Virtual de Switch (SVI):** La interfaz lógica `interface vlan 1` (o una VLAN de gestión dedicada) donde se asigna una dirección IPv4 y su máscara, permitiendo la gestión remota del conmutador mediante SSH o SNMP.
* **Puerta de enlace predeterminada (`ip default-gateway`):** Necesaria para que el switch pueda responder a peticiones de administración originadas fuera de su propia subred local.

### 5.3 Segmentación Lógica por VLANs (IEEE 802.1Q)
El switch de Capa 2 divide un dominio de broadcast físico en múltiples dominios lógicos independientes:
* **Puertos de Acceso (*Access Ports*):** Pertenecen a una única VLAN y transmiten tramas estándar no etiquetadas (*untagged*). Se conectan a dispositivos finales.
* **Puertos Troncales (*Trunk Ports*):** Enlaces de interconexión entre switches o entre un switch y un router. Permiten el paso de tráfico de múltiples VLANs agregando una etiqueta de 4 bytes a la cabecera Ethernet según el estándar **IEEE 802.1Q** (incluyendo el campo VID de 12 bits para identificar hasta 4094 VLANs).

### 5.4 Seguridad de Puerto (*Port Security*)
Mecanismo de defensa en Capa 2 que mitiga ataques como el desbordamiento de la tabla CAM (*MAC Flooding*) o conexiones no autorizadas:
* Permite limitar la cantidad de direcciones MAC permitidas en un puerto físico.
* Permite fijar estáticamente las direcciones MAC o usar aprendizaje persistente (*Sticky MAC*).
* Modos de violación ante detección de intrusos:
  - `protect`: Descarta las tramas de la MAC no autorizada en silencio, no genera alertas ni bloquea el puerto.
  - `restrict`: Descarta las tramas, incrementa un contador de violación y genera un mensaje de log / trampa SNMP.
  - `shutdown`: Deshabilita administrativamente el puerto de inmediato cambiándolo al estado `err-disabled`. Requiere intervención del administrador o autorrecuperación temporizada.

---

## 6. COMANDOS FUNDAMENTALES DEL CLI (SINTAXIS REAL CISCO IOS)

### 6.1 Configuración Básica e Inicial
```text
Switch> enable
Switch# configure terminal
Switch(config)# hostname SW-ACCESO-01
SW-ACCESO-01(config)# enable secret ClaveSegura2026!
SW-ACCESO-01(config)# no ip domain-lookup
SW-ACCESO-01(config)# banner motd # ACCESO RESTRINGIDO - SOLO PERSONAL AUTORIZADO #
SW-ACCESO-01(config)# interface vlan 1
SW-ACCESO-01(config-if)# ip address 192.168.10.2 255.255.255.0
SW-ACCESO-01(config-if)# no shutdown
SW-ACCESO-01(config-if)# exit
SW-ACCESO-01(config)# ip default-gateway 192.168.10.1
```

### 6.2 Creación de VLANs y Asignación de Puertos
```text
SW-ACCESO-01(config)# vlan 10
SW-ACCESO-01(config-vlan)# name Ventas
SW-ACCESO-01(config-vlan)# exit
SW-ACCESO-01(config)# vlan 20
SW-ACCESO-01(config-vlan)# name Administracion
SW-ACCESO-01(config-vlan)# exit

! Asignacion de un rango de puertos en modo acceso a la VLAN 10
SW-ACCESO-01(config)# interface range FastEthernet 0/1 - 12
SW-ACCESO-01(config-if-range)# switchport mode access
SW-ACCESO-01(config-if-range)# switchport access vlan 10
SW-ACCESO-01(config-if-range)# no shutdown
SW-ACCESO-01(config-if-range)# exit
```

### 6.3 Configuración de Puerto Troncal (Trunk 802.1Q)
```text
SW-ACCESO-01(config)# interface GigabitEthernet 0/1
SW-ACCESO-01(config-if)# description ENLACE_TRONCAL_A_CORE
SW-ACCESO-01(config-if)# switchport mode trunk
SW-ACCESO-01(config-if)# switchport trunk native vlan 99
SW-ACCESO-01(config-if)# switchport trunk allowed vlan 10,20,99
SW-ACCESO-01(config-if)# no shutdown
SW-ACCESO-01(config-if)# exit
```

### 6.4 Implementación de Port Security
```text
SW-ACCESO-01(config)# interface FastEthernet 0/5
SW-ACCESO-01(config-if)# switchport mode access
SW-ACCESO-01(config-if)# switchport port-security
SW-ACCESO-01(config-if)# switchport port-security maximum 1
SW-ACCESO-01(config-if)# switchport port-security mac-address sticky
SW-ACCESO-01(config-if)# switchport port-security violation shutdown
SW-ACCESO-01(config-if)# exit
```

### 6.5 Comandos de Verificación, Diagnóstico y Estado
Los siguientes comandos de modo privilegiado son esenciales para auditar el funcionamiento del switch:

```text
! 1. Ver la tabla de direcciones MAC aprendidas en memoria CAM
SW-ACCESO-01# show mac address-table
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    001b.d4c2.8101    DYNAMIC     Fa0/1
  10    001b.d4c2.8105    DYNAMIC     Fa0/5
  20    0050.7966.6803    DYNAMIC     Fa0/15
  99    0008.e3ff.fd90    DYNAMIC     Gi0/1
Total Mac Addresses for this module: 4

! 2. Resumen rapido del estado de todas las interfaces fisicas
SW-ACCESO-01# show interfaces status
Port      Name               Status       Vlan       Duplex  Speed Type
Fa0/1     PC-USUARIO-01      connected    10         a-full  a-100 10/100BaseTX
Fa0/2                        notconnect   10           auto   auto 10/100BaseTX
Fa0/5     PC-GERENCIA        connected    10         a-full  a-100 10/100BaseTX
Gi0/1     ENLACE_TRONCAL     connected    trunk        full   1000 1000BaseTX

! 3. Validar VLANs activas y puertos asociados
SW-ACCESO-01# show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/13, Fa0/14, Gi0/2
10   Ventas                           active    Fa0/1, Fa0/2, Fa0/3, Fa0/4, Fa0/5
20   Administracion                   active    Fa0/15, Fa0/16, Fa0/17
99   Gestion                          active    

! 4. Verificar politica de Port Security en una interfaz
SW-ACCESO-01# show port-security interface FastEthernet 0/5
Port Security              : Enabled
Port Status                : Secure-up
Violation Mode             : Shutdown
Aging Time                 : 0 mins
Max MAC Addresses          : 1
Total MAC Addresses        : 1
Configured MAC Addresses   : 0
Sticky MAC Addresses       : 1
Last Source Address:Vlan   : 001b.d4c2.8105:10
Security Violation Count   : 0

! 5. Guardar los cambios de memoria RAM a memoria NVRAM
SW-ACCESO-01# copy running-config startup-config
Destination filename [startup-config]? 
Building configuration...
[OK]
```

---

## 7. ANÁLISIS DE UN SWITCH COMERCIAL: CISCO CATALYST C1000-24T-4G-L

### 7.1 Identificación y Propósito
* **Fabricante:** Cisco Systems, Inc.
* **Línea de producto:** Cisco Catalyst 1000 Series Switches.
* **Modelo exacto:** `C1000-24T-4G-L`.
* **Segmento:** Switch de acceso empresarial de Capa 2 fija para pequeñas y medianas empresas (PyMEs), sucursales bancarias y cableados de piso corporativos.

```
Panel Frontal - Cisco Catalyst C1000-24T-4G-L:
+-------------------------------------------------------------------------------+
| [CISCO]                                                                       |
|  [Sys/Stat]   1  3  5  7  9 11 13 15 17 19 21 23      [25] [27] (Uplink SFP)  |
|               [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ]     [  ] [  ]              |
|  (Consola)    [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ]     [  ] [  ]              |
|   RJ45/USB    2  4  6  8 10 12 14 16 18 20 22 24      [26] [28] (Uplink SFP)  |
|               24x 10/100/1000 Mbps RJ-45              4x 1G SFP Dedicados     |
+-------------------------------------------------------------------------------+
```

### 7.2 Especificaciones Técnicas de Hardware y Rendimiento

| Parámetro Técnico | Especificación de Fábrica |
| :--- | :--- |
| **Puertos de Acceso Descendentes** | 24 puertos 10/100/1000BASE-T Gigabit Ethernet (RJ-45). |
| **Puertos de Enlace Ascendente (*Uplinks*)** | 4 puertos SFP dedicados de 1 Gbps (no compartidos / non-combo). |
| **Capacidad de Conmutación (*Switching Bandwidth*)** | **56 Gbps** a velocidad de línea sin bloqueo. |
| **Tasa de Reenvío (*Forwarding Performance*)** | **41.67 Mpps** (Millones de paquetes por segundo para tramas de 64 bytes). |
| **Tamaño de la Tabla de Direcciones MAC** | Hasta **16,000 entradas dinámicas** en memoria CAM. |
| **Procesador Central (CPU)** | Procesador ARM v7 Dual-Core a 800 MHz. |
| **Memoria RAM** | 512 MB DRAM. |
| **Memoria Flash Interna** | 256 MB para almacenamiento de imágenes Cisco IOS y archivos de volcado. |
| **Búfer de Paquetes** | 1.5 MB de asignación dinámica compartida entre todos los puertos. |
| **Soporte de Tramas Jumbo** | Hasta 10,240 bytes (10.2 KB). |
| **Nivel de Ruido Acústico** | **0 dB (Diseño Fanless - Sin ventilador)**. Refrigeración por convección pasiva, ideal para oficinas sin cuarto de servidores. |
| **Consumo de Potencia** | 23.6 W al 100% de carga de tráfico. |
| **Dimensiones Físicas** | 4.39 cm de alto (1U estándar para rack de 19"), 44.5 cm de ancho, 25.6 cm de profundidad. Peso: 2.78 kg. |

### 7.3 Capacidades de Software y Protocolos Soportados
* **Sistema Operativo:** Cisco IOS Software clásico (empaquetado LAN Lite de alta estabilidad).
* **Gestión de VLANs:** Hasta 256 VLANs activas simultáneas con IDs configurables de 1 a 4094.
* **Control de Bucles en Capa 2:** Spanning Tree Protocol compatible con IEEE 802.1D (STP), IEEE 802.1w (Rapid STP) e IEEE 802.1s (Multiple STP), con protecciones añadidas como *BPDU Guard*, *Root Guard* y *Loop Guard*.
* **Agregación de Enlaces:** LACP (*Link Aggregation Control Protocol* - IEEE 802.3ad) hasta con 8 puertos por canal EtherChannel.
* **Seguridad de Red y Autenticación:** 
  - Soporte de 802.1X para autenticación de dispositivos mediante servidor RADIUS/TACACS+.
  - *DHCP Snooping* para prevenir la conexión de servidores DHCP no autorizados (*Rogue DHCP*).
  - *Dynamic ARP Inspection (DAI)* para mitigar ataques de envenenamiento de tablas ARP (*Man-in-the-Middle*).
* **Calidad de Servicio (QoS):** 8 colas de salida de hardware por puerto, priorización CoS 802.1p y algoritmos de cola *Shaped Round Robin (SRR)*.
