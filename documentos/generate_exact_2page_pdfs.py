import os
import subprocess
from pathlib import Path
import pypdf

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def get_browser_exe():
    if os.path.exists(CHROME_PATH):
        return CHROME_PATH
    if os.path.exists(EDGE_PATH):
        return EDGE_PATH
    raise RuntimeError("No se encontro navegador para PDF.")

def build_switch_html():
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe: El Switch de Capa 2</title>
<style>
  @page {
    size: letter;
    margin: 12mm 14mm 12mm 14mm;
  }
  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    color: #0f172a;
    background: #fff;
    font-size: 8.2pt;
    line-height: 1.28;
    margin: 0;
    padding: 0;
  }
  .header-box {
    border-bottom: 2px solid #0284c7;
    padding-bottom: 4px;
    margin-bottom: 6px;
  }
  h1 {
    font-size: 13.5pt;
    color: #0f172a;
    margin: 0 0 2px 0;
    text-transform: uppercase;
    font-weight: 800;
    letter-spacing: 0.3px;
  }
  .subtitle {
    font-size: 8pt;
    color: #475569;
    font-weight: 600;
  }
  h2 {
    font-size: 9.3pt;
    color: #0369a1;
    font-weight: 700;
    margin: 6px 0 2px 0;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 1px;
    text-transform: uppercase;
  }
  h3 {
    font-size: 8.5pt;
    color: #0f172a;
    font-weight: 700;
    margin: 4px 0 1px 0;
  }
  p {
    margin: 0 0 4px 0;
    text-align: justify;
  }
  ul {
    margin: 1px 0 4px 0;
    padding-left: 16px;
  }
  li {
    margin-bottom: 1.5px;
    text-align: justify;
  }
  strong {
    color: #0f172a;
  }
  .grid-2 {
    display: flex;
    gap: 10px;
  }
  .col {
    flex: 1;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 4px 0;
    font-size: 7.6pt;
  }
  th {
    background: #0369a1;
    color: #fff;
    font-weight: 700;
    padding: 3px 5px;
    border: 1px solid #0284c7;
    text-align: left;
  }
  td {
    padding: 2.5px 5px;
    border: 1px solid #cbd5e1;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background: #f8fafc;
  }
  code {
    font-family: 'Consolas', monospace;
    font-size: 7.8pt;
    background: #f1f5f9;
    padding: 0.5px 3px;
    border-radius: 2px;
    border: 1px solid #e2e8f0;
  }
  pre {
    font-family: 'Consolas', monospace;
    font-size: 7.2pt;
    background: #0f172a;
    color: #f8fafc;
    padding: 5px 7px;
    border-radius: 4px;
    margin: 3px 0 4px 0;
    line-height: 1.22;
  }
  .page-break {
    page-break-before: always;
  }
  .badge {
    display: inline-block;
    background: #e0f2fe;
    color: #0369a1;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 7.4pt;
  }
</style>
</head>
<body>

<!-- ==================== PLANA 1 ==================== -->
<div class="header-box">
  <h1>Informe de Investigación: El Switch de Capa 2</h1>
  <div class="subtitle">Conmutación Ethernet IEEE 802.3 · Operación de Capa de Enlace de Datos · Arquitectura y Configuración</div>
</div>

<h2>1. Definición y Características en la Capa de Enlace</h2>
<p>
El <strong>switch de Capa 2</strong> es el dispositivo neurálgico de interconexión en redes de área local (LAN), operando en la Capa de Enlace de Datos del modelo OSI bajo la familia de normas <strong>IEEE 802.3</strong>. A diferencia de un concentrador (<em>hub</em>) de Capa 1 que replica indiscriminadamente señales eléctricas en un único medio compartido, el switch conmuta tramas de forma selectiva hacia el puerto de destino basándose en las direcciones de hardware <strong>MAC</strong> de 48 bits (EUI-48).
</p>
<ul>
  <li><strong>Microsegmentación y Aislamiento de Colisiones:</strong> Cada puerto físico del switch conforma un <em>dominio de colisión independiente</em>. En enlaces <em>Full-Duplex</em> simultáneos con pares de transmisión (Tx) y recepción (Rx) aislados, las colisiones CSMA/CD se erradican por completo.</li>
  <li><strong>Dominio de Difusión Único:</strong> Por defecto, todos los puertos pertenecen a un mismo dominio de broadcast. Las tramas enviadas a la dirección universal <code>FF:FF:FF:FF:FF:FF</code> son replicadas hacia todos los puertos activos de la misma VLAN.</li>
  <li><strong>La Tabla CAM (Content-Addressable Memory):</strong> Es la base de datos de alta velocidad en silicio que vincula: <em>1) Dirección MAC aprendida</em>, <em>2) Puerto físico de entrada</em> y <em>3) Identificador de VLAN</em>.</li>
  <li><strong>Las 4 Funciones Lógicas del Switch:</strong>
    <strong>a) Aprendizaje (<em>Learning</em>):</strong> Lee la MAC origen de cada trama ingresante; si no existe en la CAM, la registra; si ya existe, reinicia su temporizador.
    <strong>b) Inundación (<em>Flooding</em>):</strong> Si la MAC destino es de difusión, multidifusión o no figura en la tabla (<em>unicast desconocido</em>), replica la trama por todos los puertos de esa VLAN salvo el de entrada.
    <strong>c) Reenvío (<em>Forwarding</em>):</strong> Si la MAC destino está registrada, conmuta la trama puntualmente hacia ese puerto físico.
    <strong>d) Filtrado (<em>Filtering</em>):</strong> Si la MAC destino coincide con el mismo segmento del puerto origen, descarta la trama sin retransmitir.
  </li>
  <li><strong>Envejecimiento (<em>Aging Timer</em>):</strong> Las entradas dinámicas expiran tras <strong>300 segundos</strong> (5 min) de inactividad para liberar memoria y reflejar cambios topológicos.</li>
  <li><strong>Métricas de Rendimiento:</strong> Capacidad de conmutación de la matriz interna (<em>Switching Fabric</em> en Gbps) calculada para modo sin bloqueo (<em>non-blocking</em>: $\text{Puertos} \times \text{Velocidad} \times 2$), y tasa de reenvío de tramas (<em>Forwarding Rate</em> en Mpps para paquetes de 64 bytes).</li>
</ul>

<h2>2. Modos de Operación y Reenvío de Tramas</h2>
<table>
  <thead>
    <tr>
      <th style="width:22%;">Modo de Conmutación</th>
      <th style="width:43%;">Mecanismo Operativo</th>
      <th style="width:35%;">Ventajas y Desventajas Técnicas</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Store-and-Forward<br/>(Almacenamiento y Reenvío)</strong></td>
      <td>Almacena la trama completa en su búfer de memoria y recalcula la suma de verificación <strong>CRC/FCS</strong> (4 bytes). Si el valor no coincide con el original, descarta la trama antes de conmutarla.</td>
      <td><strong>Ventaja:</strong> Máxima integridad; elimina tramas corruptas, <em>runts</em> (&lt;64 B) y <em>giants</em> (&gt;1518 B).<br/><strong>Desventaja:</strong> Mayor latencia (15 a 100 &mu;s, según tamaño).</td>
    </tr>
    <tr>
      <td><strong>Cut-Through<br/>(Conmutación Rápida)</strong></td>
      <td>Lee únicamente los primeros <strong>6 bytes</strong> de la trama (dirección MAC destino). Consulta la tabla CAM e inicia el reenvío hacia el puerto de salida de forma inmediata, mientras el resto de la trama aún entra.</td>
      <td><strong>Ventaja:</strong> Latencia mínima constante (&lt;5 &mu;s).<br/><strong>Desventaja:</strong> Reenvía tramas con errores de FCS y propaga ruido en la red. Empleado en datacenters de ultra baja latencia.</td>
    </tr>
    <tr>
      <td><strong>Fragment-Free<br/>(Libre de Fragmentos)</strong></td>
      <td>Compromiso intermedio: lee y almacena los primeros <strong>64 bytes</strong> de la trama (tamaño mínimo Ethernet donde ocurren las colisiones de medio en CSMA/CD) antes de iniciar la conmutación hacia el puerto destino.</td>
      <td><strong>Ventaja:</strong> Filtra eficazmente colisiones tempranas con menor latencia que Store-and-Forward.<br/><strong>Desventaja:</strong> No detecta corrupciones en el cuerpo de datos posterior.</td>
    </tr>
  </tbody>
</table>

<h2>3. Tipos de Puertos e Interfaces Físicas</h2>
<ul>
  <li><strong>Puertos de Acceso Fast Ethernet / Gigabit Ethernet (RJ-45):</strong> Interfaces estándar 10/100/1000BASE-T para clientes finales. Integran <em>Auto-MDIX</em> para detectar y corregir automáticamente el uso de cables directos o cruzados.</li>
  <li><strong>Puertos de Enlace Ascendente (Uplink SFP / SFP+):</strong> Ranuras modulares para transceptores ópticos 1G (SFP: 1000BASE-SX/LX) o 10G (SFP+: 10GBASE-SR/LR) hacia switches de distribución o núcleo, o cables DAC (Direct Attach Copper).</li>
  <li><strong>Puertos de Administración Fuera de Banda (Consola RJ-45 / Mini-USB / Type-C):</strong> Conexión serie local asíncrona a 9600 baudios para configuración inicial o rescate fuera de la red IP de producción (OOB - Out-of-Band).</li>
  <li><strong>Puertos PoE / PoE+ (Power over Ethernet):</strong> Cumplen estándares IEEE 802.3af (15.4 W) e IEEE 802.3at (30 W), inyectando corriente directa en los pares de cobre trenzado para energizar teléfonos IP, cámaras de vigilancia y puntos de acceso Wi-Fi sin fuentes externas.</li>
</ul>

<!-- ==================== PLANA 2 ==================== -->
<div class="page-break"></div>

<div class="header-box">
  <h1>Informe de Investigación: El Switch de Capa 2 (Continuación)</h1>
  <div class="subtitle">Configuración y Comandos CLI Cisco IOS · Análisis de Switch Comercial Cisco Catalyst C1000-24T-4G-L</div>
</div>

<h2>4. Configuración Lógica en un Switch de Capa 2</h2>
<p>
Los switches corporativos gestionables emplean una arquitectura de configuración estructurada en niveles jerárquicos: Modo Usuario (<code>Switch&gt;</code>), Modo Privilegiado (<code>Switch#</code>), Modo de Configuración Global (<code>Switch(config)#</code>) y modos de contexto (interfaz, VLAN, línea). Entre las directivas esenciales destacan:
</p>
<ul>
  <li><strong>Gestión Fuera de Banda y SVI:</strong> La Interfaz Virtual de Switch (<code>interface vlan 1</code> o VLAN de administración) asigna una IP/máscara para acceso SSH/SNMP, vinculada a una puerta de enlace (<code>ip default-gateway</code>) para enrutar la gestión fuera de la subred local.</li>
  <li><strong>Segmentación por VLANs (IEEE 802.1Q):</strong> Aisla el tráfico broadcast dividiendo un switch físico en múltiples redes lógicas. Los <em>puertos de acceso</em> transportan tráfico no etiquetado de una sola VLAN; los <em>puertos troncales (Trunk)</em> transportan múltiples VLANs insertando una etiqueta 802.1Q de 4 bytes (con VLAN ID de 12 bits para hasta 4094 identificadores).</li>
  <li><strong>Seguridad de Puerto (Port Security):</strong> Mitiga ataques de desbordamiento de memoria CAM (<em>MAC Flooding</em>) y conexiones clandestinas. Limita la cantidad de MACs por puerto, permite guardarlas automáticamente de forma persistente (<code>mac-address sticky</code>) y define políticas ante infracción: <code>shutdown</code> (apaga la interfaz al estado <em>err-disabled</em>), <code>restrict</code> (descarta paquetes y registra mensaje SNMP/Syslog) o <code>protect</code> (descarta paquetes silenciosamente).</li>
</ul>

<h2>5. Comandos Fundamentales del CLI (Sintaxis Real Cisco IOS)</h2>
<div class="grid-2">
  <div class="col">
    <h3>Configuración Inicial, VLANs y Troncales</h3>
<pre><code>! 1. Nombre, seguridad y SVI de gestion
Switch> enable
Switch# configure terminal
Switch(config)# hostname SW-ACC-01
SW-ACC-01(config)# enable secret AdminPass2026!
SW-ACC-01(config)# interface vlan 99
SW-ACC-01(config-if)# ip address 192.168.99.2 255.255.255.0
SW-ACC-01(config-if)# no shutdown
SW-ACC-01(config-if)# exit
SW-ACC-01(config)# ip default-gateway 192.168.99.1

! 2. Creacion de VLANs y asignacion de puertos de acceso
SW-ACC-01(config)# vlan 10
SW-ACC-01(config-vlan)# name Produccion
SW-ACC-01(config-vlan)# exit
SW-ACC-01(config)# interface range FastEthernet 0/1 - 12
SW-ACC-01(config-if-range)# switchport mode access
SW-ACC-01(config-if-range)# switchport access vlan 10
SW-ACC-01(config-if-range)# no shutdown
SW-ACC-01(config-if-range)# exit

! 3. Enlace Troncal 802.1Q y Port Security
SW-ACC-01(config)# interface GigabitEthernet 0/1
SW-ACC-01(config-if)# switchport mode trunk
SW-ACC-01(config-if)# switchport trunk allowed vlan 10,20,99
SW-ACC-01(config-if)# exit
SW-ACC-01(config)# interface FastEthernet 0/5
SW-ACC-01(config-if)# switchport mode access
SW-ACC-01(config-if)# switchport port-security
SW-ACC-01(config-if)# switchport port-security maximum 1
SW-ACC-01(config-if)# switchport port-security mac-address sticky
SW-ACC-01(config-if)# switchport port-security violation shutdown</code></pre>
  </div>
  <div class="col">
    <h3>Verificación, Diagnóstico y Salidas de Consola</h3>
<pre><code>! Visualizar tabla CAM (direcciones MAC aprendidas dinamicamente)
SW-ACC-01# show mac address-table
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    001b.d4c2.8105    DYNAMIC     Fa0/5
  10    00e0.f726.a112    DYNAMIC     Fa0/1
  99    0008.e3ff.fd90    DYNAMIC     Gi0/1
Total Mac Addresses for this module: 3

! Resumen de estado de interfaces y asignacion de VLANs
SW-ACC-01# show interfaces status
Port      Name               Status       Vlan       Duplex  Speed Type
Fa0/1     PC-USUARIO         connected    10         a-full  a-100 10/100BaseTX
Fa0/5     SERVER-LOCAL       connected    10         a-full  a-100 10/100BaseTX
Gi0/1     UPLINK-CORE        connected    trunk        full   1000 1000BaseTX

! Auditoria de politicas de Port Security
SW-ACC-01# show port-security interface Fa0/5
Port Security              : Enabled
Port Status                : Secure-up
Violation Mode             : Shutdown
Max MAC Addresses          : 1
Total MAC Addresses        : 1
Sticky MAC Addresses       : 1
Last Source Address:Vlan   : 001b.d4c2.8105:10
Security Violation Count   : 0

! Guardar cambios en la memoria NVRAM persistente
SW-ACC-01# copy running-config startup-config
Building configuration... [OK]</code></pre>
  </div>
</div>

<h2>6. Switch Comercial en Particular: Cisco Catalyst C1000-24T-4G-L</h2>
<table>
  <thead>
    <tr>
      <th style="width:25%;">Componente / Parámetro</th>
      <th style="width:40%;">Especificación Técnica de Fábrica</th>
      <th style="width:35%;">Relevancia Arquitectónica</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Fabricante y Modelo</strong></td>
      <td><strong>Cisco Systems</strong> · Catalyst <code>C1000-24T-4G-L</code></td>
      <td>Switch de acceso empresarial fijo de Capa 2 para oficinas corporativas y armarios de telecomunicaciones.</td>
    </tr>
    <tr>
      <td><strong>Puertos Físicos</strong></td>
      <td>24 puertos 10/100/1000BASE-T Gigabit Ethernet (RJ-45) + <strong>4 puertos SFP dedicados de 1 Gbps</strong> para enlaces ascendentes (no compartidos).</td>
      <td>Permite migrar a gigabit completo en el borde con enlaces ópticos directos a distribución sin sacrificar puertos RJ-45 de usuario.</td>
    </tr>
    <tr>
      <td><strong>Matriz de Conmutación y Reenvío</strong></td>
      <td>Capacidad de conmutación de <strong>56 Gbps</strong> con tasa de reenvío de <strong>41.67 Mpps</strong> (paquetes de 64 bytes).</td>
      <td>Rendimiento a velocidad de línea total (<em>non-blocking</em>) sin cuellos de botella bajo tráfico concurrente intensivo.</td>
    </tr>
    <tr>
      <td><strong>Capacidad de Memoria y CAM</strong></td>
      <td>Tabla de direcciones MAC de <strong>16,000 entradas</strong> · 512 MB de memoria RAM DRAM · 256 MB memoria Flash interna.</td>
      <td>Garantiza retención para infraestructuras con cientos de hosts y almacenamiento para dos imágenes de Cisco IOS Software.</td>
    </tr>
    <tr>
      <td><strong>CPU y Nivel Acústico</strong></td>
      <td>Procesador ARM v7 Dual-Core a 800 MHz · Diseño <strong>Fanless (0 dB acústico)</strong> con refrigeración pasiva por convección.</td>
      <td>Operación completamente silenciosa y confiable, sin piezas mecánicas móviles que sufran fallos de ventilación. Consumo: 23.6 W.</td>
    </tr>
    <tr>
      <td><strong>Protocolos y Funciones Lógicas</strong></td>
      <td>256 VLANs activas (IDs 1-4094), Spanning Tree (802.1D, 802.1w RSTP, 802.1s MSTP, BPDU Guard), DHCP Snooping, Dynamic ARP Inspection (DAI), IGMP Snooping v1/v2/v3, QoS SRR (8 colas).</td>
      <td>Ofrece robustez corporativa de capa de enlace protegiendo contra tormentas de broadcast, bucles de red y ataques Man-in-the-Middle.</td>
    </tr>
  </tbody>
</table>

</body>
</html>
"""

def build_ieee802_html():
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe: Estándares IEEE 802 (Wi-Fi y Bluetooth)</title>
<style>
  @page {
    size: letter;
    margin: 12mm 14mm 12mm 14mm;
  }
  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    color: #0f172a;
    background: #fff;
    font-size: 8.2pt;
    line-height: 1.28;
    margin: 0;
    padding: 0;
  }
  .header-box {
    border-bottom: 2px solid #0284c7;
    padding-bottom: 4px;
    margin-bottom: 6px;
  }
  h1 {
    font-size: 13.5pt;
    color: #0f172a;
    margin: 0 0 2px 0;
    text-transform: uppercase;
    font-weight: 800;
    letter-spacing: 0.3px;
  }
  .subtitle {
    font-size: 8pt;
    color: #475569;
    font-weight: 600;
  }
  h2 {
    font-size: 9.3pt;
    color: #0369a1;
    font-weight: 700;
    margin: 6px 0 2px 0;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 1px;
    text-transform: uppercase;
  }
  h3 {
    font-size: 8.5pt;
    color: #0f172a;
    font-weight: 700;
    margin: 4px 0 1px 0;
  }
  p {
    margin: 0 0 4px 0;
    text-align: justify;
  }
  ul {
    margin: 1px 0 4px 0;
    padding-left: 16px;
  }
  li {
    margin-bottom: 1.5px;
    text-align: justify;
  }
  strong {
    color: #0f172a;
  }
  .grid-2 {
    display: flex;
    gap: 10px;
  }
  .col {
    flex: 1;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 4px 0;
    font-size: 7.6pt;
  }
  th {
    background: #0369a1;
    color: #fff;
    font-weight: 700;
    padding: 3px 5px;
    border: 1px solid #0284c7;
    text-align: left;
  }
  td {
    padding: 2.5px 5px;
    border: 1px solid #cbd5e1;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background: #f8fafc;
  }
  code {
    font-family: 'Consolas', monospace;
    font-size: 7.8pt;
    background: #f1f5f9;
    padding: 0.5px 3px;
    border-radius: 2px;
    border: 1px solid #e2e8f0;
  }
  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<!-- ==================== PLANA 1 ==================== -->
<div class="header-box">
  <h1>Informe de Investigación: Estándares IEEE 802</h1>
  <div class="subtitle">Comunicaciones Inalámbricas · Estudio Técnico de IEEE 802.11 (Wi-Fi) e IEEE 802.15.1 (Bluetooth)</div>
</div>

<h2>1. Marco del Comité IEEE 802 y Desacoplamiento de Capas</h2>
<p>
El comité <strong>IEEE 802</strong> estandariza redes LAN, MAN y PAN estructurando la Capa de Enlace de Datos en dos subcapas: <strong>LLC (IEEE 802.2 - Control de Enlace Lógico)</strong>, encargada de la multiplexación hacia la Capa de Red (IP), y <strong>MAC (Control de Acceso al Medio)</strong>, adaptada a la naturaleza del medio físico. Los estándares <strong>IEEE 802.11</strong> (WLAN) e <strong>IEEE 802.15.1</strong> (WPAN) implementan subcapas MAC y capas físicas (PHY) específicas para transmisiones inalámbricas no guiadas.
</p>

<h2>2. Estándar IEEE 802.11 (Wireless Local Area Network - Wi-Fi)</h2>
<h3>2.1 Evolución Cronológica y Enmiendas Tecnológicas</h3>
<table>
  <thead>
    <tr>
      <th style="width:18%;">Estándar / Gen.</th>
      <th style="width:10%;">Año</th>
      <th style="width:15%;">Frecuencia</th>
      <th style="width:15%;">Ancho Canal</th>
      <th style="width:18%;">Modulación / PHY</th>
      <th style="width:12%;">Tasa Máx.</th>
      <th style="width:12%;">Innovación Clave</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>802.11b</strong></td>
      <td>1999</td>
      <td>2.4 GHz</td>
      <td>20 MHz</td>
      <td>DSSS / CCK</td>
      <td>11 Mbps</td>
      <td>Adopción masiva inicial.</td>
    </tr>
    <tr>
      <td><strong>802.11a / g</strong></td>
      <td>1999/03</td>
      <td>5 GHz / 2.4 GHz</td>
      <td>20 MHz</td>
      <td>OFDM (64 subportadoras)</td>
      <td>54 Mbps</td>
      <td>Salto a modulación OFDM.</td>
    </tr>
    <tr>
      <td><strong>802.11n (Wi-Fi 4)</strong></td>
      <td>2009</td>
      <td>2.4 y 5 GHz</td>
      <td>20 y 40 MHz</td>
      <td>64-QAM / MIMO</td>
      <td>600 Mbps</td>
      <td>MIMO espacial (hasta 4x4).</td>
    </tr>
    <tr>
      <td><strong>802.11ac (Wi-Fi 5)</strong></td>
      <td>2013</td>
      <td>5 GHz</td>
      <td>20, 40, 80, 160 MHz</td>
      <td>256-QAM</td>
      <td>6.93 Gbps</td>
      <td>Canales amplios, Downlink MU-MIMO.</td>
    </tr>
    <tr>
      <td><strong>802.11ax (Wi-Fi 6/6E)</strong></td>
      <td>2020</td>
      <td>2.4, 5 y 6 GHz</td>
      <td>Hasta 160 MHz</td>
      <td>1024-QAM / OFDMA</td>
      <td>9.6 Gbps</td>
      <td>OFDMA en subcanales (RU), banda 6 GHz.</td>
    </tr>
    <tr>
      <td><strong>802.11be (Wi-Fi 7)</strong></td>
      <td>2024</td>
      <td>2.4, 5 y 6 GHz</td>
      <td>Hasta 320 MHz</td>
      <td>4096-QAM / MLO</td>
      <td>46 Gbps</td>
      <td>Multi-Link Operation (MLO) simultáneo.</td>
    </tr>
  </tbody>
</table>

<h3>2.2 Espectro Electromagnético y Canales de Radiofrecuencia</h3>
<ul>
  <li><strong>Banda de 2.4 GHz (2.400 - 2.4835 GHz):</strong> Divide el espectro en 11 canales (América) espaciados cada 5 MHz con 20 MHz de ancho. Únicamente los canales <strong>1 (2412 MHz), 6 (2437 MHz) y 11 (2462 MHz)</strong> son completamente <em>no superpuestos</em>, siendo los únicos aptos para planificación sin interferencia de canal adyacente.</li>
  <li><strong>Banda de 5 GHz (5.150 - 5.850 GHz):</strong> Proporciona hasta 25 canales limpios de 20 MHz no superpuestos, permitiendo unión de canales (<em>channel bonding</em>) a 40, 80 y 160 MHz. Incorpora mecanismos <em>DFS (Dynamic Frequency Selection)</em> para coexistir con radares militares y climáticos.</li>
  <li><strong>Banda de 6 GHz (5.925 - 7.125 GHz):</strong> Aporta <strong>1200 MHz de espectro continuo nuevo</strong> exclusivo para Wi-Fi 6E y Wi-Fi 7, sin clientes heredados (<em>legacy</em>), habilitando hasta 7 canales ultra-anchos de 160 MHz o 3 de 320 MHz.</li>
</ul>

<h3>2.3 Mecanismo de Control de Acceso al Medio: CSMA/CA</h3>
<p>
Al no ser viable el esquema cableado CSMA/CD porque los transceptores de radio no pueden transmitir con alta potencia y detectar al mismo tiempo una señal colisionante débil entrante en la misma antena, 802.11 emplea <strong>CSMA/CA (Carrier Sense Multiple Access with Collision Avoidance)</strong>:
</p>
<ul>
  <li><strong>Detección de Portadora Física y Virtual:</strong> La física evalúa energía en la antena (CCA - <em>Clear Channel Assessment</em>). La virtual extrae el campo <em>Duration/ID</em> de las tramas ajenas y programa el temporizador interno <strong>NAV (Network Allocation Vector)</strong>, durante el cual el nodo pospone su transmisión.</li>
  <li><strong>Temporizaciones Intertrama:</strong> Prioriza tramas críticas mediante espacios temporales obligatorios: <strong>SIFS</strong> (el más corto, para ACKs/CTS), <strong>PIFS</strong> (control centralizado) y <strong>DIFS</strong> (período base que debe esperar cualquier estación antes de entrar a contienda).</li>
  <li><strong>Ventana de Contienda y Random Backoff:</strong> Si el canal sigue libre tras DIFS, el nodo descuenta ranuras de tiempo (<em>slots</em>) de un número aleatorio dentro de su ventana de contienda: $\text{Backoff} = \text{Random}(0, CW) \times \text{Slot Time}$. Si el temporizador expira sin tráfico, transmite. Si colisiona, la ventana se duplica exponencialmente ($CW_{min} \rightarrow CW_{max}$).</li>
  <li><strong>Resolución del Problema del Nodo Oculto mediante RTS/CTS:</strong> Cuando dos nodos distantes (A y C) ven al Punto de Acceso (B) pero no se ven entre sí, sus transmisiones simultáneas colisionan en B. El emisor mitiga esto enviando un marco corto <strong>RTS (Request to Send)</strong>; el AP responde con un <strong>CTS (Clear to Send)</strong> omnidireccional con un NAV que silencia a todos los nodos del área (incluyendo a C), asegurando la transmisión limpia de A.</li>
</ul>

<h3>2.4 Topologías y Seguridad en 802.11</h3>
<ul>
  <li><strong>Topologías:</strong> <strong>BSS</strong> (Modo Infraestructura con 1 AP y su BSSID/MAC), <strong>ESS</strong> (interconexión de múltiples BSS mediante un Sistema de Distribución cableado compartiendo SSID para roaming sin corte de sesión) e <strong>IBSS</strong> (Modo Ad-Hoc directo entre estaciones).</li>
  <li><strong>Evolución de Seguridad:</strong> <em>WEP</em> (inseguro por RC4 con IV estático de 24 bits), <em>WPA</em> (TKIP con mezcla dinámica), <em>WPA2</em> (estándar corporativo robusto basado en AES con CCMP de 128 bits) y <em>WPA3</em> (autenticación SAE contra ataques de diccionario fuera de línea y secreto hacia adelante).</li>
</ul>

<!-- ==================== PLANA 2 ==================== -->
<div class="page-break"></div>

<div class="header-box">
  <h1>Informe de Investigación: Estándares IEEE 802 (Continuación)</h1>
  <div class="subtitle">Estándar IEEE 802.15.1 (Bluetooth) · Comparativa Técnica Integral y Coexistencia Espectral</div>
</div>

<h2>3. Estándar IEEE 802.15.1 (Wireless Personal Area Network - Bluetooth)</h2>
<p>
El estándar <strong>IEEE 802.15.1</strong> normalizó la tecnología inalámbrica de área personal (WPAN) desarrollada inicialmente por Ericsson en 1994 para reemplazar cables serie RS-232 en distancias cortas (1 a 10 metros). Su desarrollo continuó bajo el consorcio industrial <strong>Bluetooth SIG (Special Interest Group)</strong>.
</p>

<h3>3.1 Capa Física (PHY), Espectro y Salto Adaptativo de Frecuencia (AFH)</h3>
<ul>
  <li><strong>Banda Espectral ISM de 2.4 GHz (2400 a 2483.5 MHz):</strong>
    - <strong>Bluetooth Clásico (BR/EDR):</strong> Segmenta la banda en <strong>79 canales de 1 MHz</strong>. Utiliza GFSK (Basic Rate a 1 Mbps) y $\pi/4$-DQPSK / 8DPSK (EDR a 2 y 3 Mbps).
    - <strong>Bluetooth Low Energy (BLE):</strong> Segmenta la banda en <strong>40 canales de 2 MHz</strong>. Destina <strong>3 canales de anuncio (37, 38 y 39)</strong> ubicados estratégicamente en 2402, 2426 y 2480 MHz (en los huecos espectrales libres entre los canales Wi-Fi 1, 6 y 11) para emparejamiento ultra rápido, y 37 canales para intercambio de datos.
  </li>
  <li><strong>Salto de Frecuencia por Espectro Ensanchado (FHSS / AFH):</strong> Conmuta de canal pseudoaleatoriamente a una tasa nominal de <strong>1600 saltos por segundo</strong> con ranuras de tiempo de <strong>625 &mu;s</strong>. El mecanismo <strong>AFH (Adaptive Frequency Hopping)</strong> monitoriza colisiones y excluye dinámicamente de su tabla de saltos los canales bloqueados por redes Wi-Fi concurrentes, utilizando un mínimo de 20 canales limpios.</li>
</ul>

<h3>3.2 Topologías de Red en IEEE 802.15.1</h3>
<div class="grid-2">
  <div class="col">
    <h3>Piconet (Red Elemental Estrella)</h3>
    <p>
    Formada por <strong>1 dispositivo Maestro (Master)</strong> y hasta <strong>7 dispositivos Esclavos activos (Active Slaves)</strong>. El Maestro impone su reloj interno para sincronizar la secuencia de salto de frecuencia de toda la red. La comunicación es estrictamente por sondeo (<em>polling</em>) Maestro-Esclavo; no existe transmisión directa entre dos esclavos. Permite hasta 255 nodos adicionales en reposo (<em>parked</em>).
    </p>
  </div>
  <div class="col">
    <h3>Scatternet (Red Dispersa Interconectada)</h3>
    <p>
    Surge al entrelazar dos o más Piconets mediante <em>nodos puente</em>. Un dispositivo puede ser esclavo en varias piconets, o actuar como maestro en una y esclavo en otra, alternando ranuras de tiempo (TDM). Ningún nodo puede ser maestro de dos piconets simultáneamente, ya que no puede sincronizar dos secuencias de reloj maestro a la vez.
    </p>
  </div>
</div>

<h3>3.3 Evolución: Bluetooth Clásico vs. Bluetooth Low Energy (BLE) y Perfiles</h3>
<ul>
  <li><strong>Bluetooth Clásico (v1.0 a v3.0):</strong> Orientado a flujos de datos sostenidos (audio continuo, sincronización). Requiere conexión permanente con consumo de 20 a 40 mA. Emplea perfiles estandarizados: <strong>A2DP</strong> (audio estéreo de alta fidelidad), <strong>AVRCP</strong> (control multimedia), <strong>HFP/HSP</strong> (manos libres) y <strong>SPP</strong> (emulación serie RS-232).</li>
  <li><strong>Bluetooth Low Energy (v4.0 a v5.4):</strong> Diseñado para IoT, sensores y balizas (<em>beacons</em>). Opera en ráfagas breves de milisegundos con corrientes en reposo menores a <strong>1 &mu;A</strong>, operando años con pilas botón CR2032. En Bluetooth 5.x añade <em>2M PHY</em> (2 Mbps), <em>Coded PHY</em> (alcance superior a 200 m con corrección FEC), redes en malla <em>Bluetooth Mesh</em>, y <em>LE Audio</em> con códec LC3 y difusión multicanal <em>Auracast</em>.</li>
  <li><strong>Arquitectura GATT (Generic Attribute Profile) en BLE:</strong> Estructura el intercambio de datos en una jerarquía de servidor: $\text{Servidor GATT} \rightarrow \text{Servicios (UUID)} \rightarrow \text{Características (Lectura/Escritura/Notificación)} \rightarrow \text{Descriptores}$.</li>
</ul>

<h2>4. Tabla Comparativa Directa: IEEE 802.11 vs. IEEE 802.15.1</h2>
<table>
  <thead>
    <tr>
      <th style="width:20%;">Criterio Técnico</th>
      <th style="width:40%;">IEEE 802.11 (Wi-Fi)</th>
      <th style="width:40%;">IEEE 802.15.1 (Bluetooth)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Alcance y Tipo de Red</strong></td>
      <td><strong>WLAN</strong> (Red de Área Local) · 30 a 100 m interior / 300 m exterior.</td>
      <td><strong>WPAN</strong> (Red de Área Personal) · 5 a 15 m (Clásico) / hasta 200 m (BLE Coded).</td>
    </tr>
    <tr>
      <td><strong>Bandas de Frecuencia</strong></td>
      <td>2.4 GHz, 5 GHz y 6 GHz (Wi-Fi 6E/7).</td>
      <td>2.4 GHz ISM exclusivamente (2400 a 2483.5 MHz).</td>
    </tr>
    <tr>
      <td><strong>Ancho de Canal de RF</strong></td>
      <td>20, 40, 80, 160 y 320 MHz.</td>
      <td>1 MHz (Bluetooth Clásico: 79 canales) / 2 MHz (BLE: 40 canales).</td>
    </tr>
    <tr>
      <td><strong>Throughput Máximo</strong></td>
      <td>Teórico: 11 Mbps (802.11b) a <strong>46 Gbps</strong> (802.11be) · Útil: 50 Mbps a 1.5 Gbps.</td>
      <td>Teórico: 1 a 3 Mbps (BR/EDR) / 2 Mbps (BLE) · Útil: 100 kbps a 2.1 Mbps.</td>
    </tr>
    <tr>
      <td><strong>Acceso al Medio y RF</strong></td>
      <td>CSMA/CA con contienda (DIFS/Backoff) · DSSS, OFDM, OFDMA.</td>
      <td>Sondeo Maestro/Esclavo en slots de 625 &mu;s · Salto Adaptativo (AFH/FHSS).</td>
    </tr>
    <tr>
      <td><strong>Consumo de Energía</strong></td>
      <td>Alto: 0.5 a 5 W en transmisión continua (demanda baterías recargables).</td>
      <td>Extremadamente bajo: &lt;50 mW en clásico; microvatios en BLE (&gt;1 año con pila botón).</td>
    </tr>
    <tr>
      <td><strong>Topología Predominante</strong></td>
      <td>Infraestructura estrella-árbol con APs enlazados a ESS con roaming.</td>
      <td>Estrella centralizada en Piconet (1M:7S), Scatternet y malla (Bluetooth Mesh).</td>
    </tr>
    <tr>
      <td><strong>Seguridad y Cifrado</strong></td>
      <td>WPA2 (AES-CCMP 128b) y WPA3 (SAE con curvas elípticas).</td>
      <td>Cifrado E0 (legado clásico) y AES-128 CCM (BLE).</td>
    </tr>
    <tr>
      <td><strong>Aplicaciones Típicas</strong></td>
      <td>Acceso de banda ancha a Internet, streaming 4K/8K, VoIP, transferencia masiva.</td>
      <td>Periféricos (ratón/teclado), audio personal A2DP, domótica, balizas, sensores IoT.</td>
    </tr>
  </tbody>
</table>

<h2>5. Coexistencia e Interferencia en la Banda Compartida de 2.4 GHz</h2>
<p>
Al operar simultáneamente en el mismo espectro de 2.4 GHz, ambos estándares implementan mecanismos para neutralizar la interferencia mutua: <strong>1) Aislamiento por Frecuencia:</strong> El salto adaptativo (AFH) de Bluetooth detecta la portadora estática de 20 MHz de una red Wi-Fi y desactiva esos canales, conmutando únicamente en frecuencias limpias. <strong>2) Coexistencia por Colaboración (PTA - Packet Traffic Arbitration):</strong> En dispositivos donde un mismo chip integra ambas radios (como smartphones), un bus de arbitraje por hardware prioriza paquetes de voz Bluetooth en microsegundos pausando brevemente la transmisión Wi-Fi, impidiendo la saturación del receptor.
</p>

</body>
</html>
"""

def generate_pdf(html_content, pdf_path, title):
    base_dir = Path(r"c:\Users\MARILYN\Documents\Carpeta Esther\Semestre 2-2026\SI 2\primer_parcial.1.0\documentos")
    temp_html = base_dir / f"temp_{pdf_path.stem}.html"
    
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    browser_exe = get_browser_exe()
    file_url = f"file:///{str(temp_html.resolve()).replace(chr(92), '/')}"
    
    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(pdf_path.resolve())}",
        file_url
    ]
    
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    if os.path.exists(temp_html):
        os.remove(temp_html)
        
    # Verificar cantidad de paginas con pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    print(f"[{pdf_path.name}] generado con exito: {num_pages} paginas (Tamano: {os.path.getsize(pdf_path)} bytes)")
    return num_pages

if __name__ == "__main__":
    base_dir = Path(r"c:\Users\MARILYN\Documents\Carpeta Esther\Semestre 2-2026\SI 2\primer_parcial.1.0\documentos")
    
    p1 = base_dir / "INFORME_INVESTIGACION_SWITCH_CAPA_2.pdf"
    pages1 = generate_pdf(build_switch_html(), p1, "Informe: El Switch de Capa 2")
    
    p2 = base_dir / "INFORME_INVESTIGACION_ESTANDARES_IEEE_802.pdf"
    pages2 = generate_pdf(build_ieee802_html(), p2, "Informe: Estandares IEEE 802")
    
    if pages1 == 2 and pages2 == 2:
        print("\n>>> EXITO TOTAL: Ambos informes tienen EXACTAMENTE 2 PLANAS (paginas) <<<")
    else:
        print(f"\n>>> ATENCION: Switch={pages1} paginas, IEEE802={pages2} paginas <<<")
