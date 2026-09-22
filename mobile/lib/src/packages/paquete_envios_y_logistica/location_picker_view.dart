import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);
const _gpsBlue = Color(0xFF1A73E8);

/// Centro de Santa Cruz de la Sierra: punto de partida si no hay GPS.
const defaultDeliveryCenter = LatLng(-17.7833, -63.1821);
const _userAgent = 'com.example.fashionstore_mobile';
const _tileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

// ---------------------------------------------------------------------------
// Utilidades compartidas (checkout y selector): GPS y geocodificación OSM.
// ---------------------------------------------------------------------------

/// Resultado de pedir la posición del teléfono.
class GpsResult {
  final LatLng? point;

  /// Mensaje listo para mostrar al cliente cuando no se obtuvo la posición.
  final String? error;

  /// `true` si el cliente debe ir a Ajustes (GPS apagado o permiso bloqueado).
  final bool needsSettings;

  /// `true` si hay que abrir los ajustes de ubicación del sistema (GPS apagado);
  /// `false` si hay que abrir los ajustes de la app (permiso bloqueado).
  final bool gpsOff;

  const GpsResult.ok(LatLng p)
      : point = p,
        error = null,
        needsSettings = false,
        gpsOff = false;
  const GpsResult.fail(String msg, {this.needsSettings = false, this.gpsOff = false})
      : point = null,
        error = msg;
}

/// Pide permiso (si hace falta) y obtiene la posición actual del teléfono.
Future<GpsResult> locateDevice() async {
  try {
    if (!await Geolocator.isLocationServiceEnabled()) {
      return const GpsResult.fail('El GPS del teléfono está apagado.', needsSettings: true, gpsOff: true);
    }
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.denied) {
      return const GpsResult.fail('No diste permiso de ubicación.');
    }
    if (perm == LocationPermission.deniedForever) {
      return const GpsResult.fail('El permiso de ubicación está bloqueado.', needsSettings: true);
    }
    // Primero la última posición conocida (instantánea) para no dejar el mapa vacío;
    // luego la posición precisa.
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 15),
        ),
      );
      return GpsResult.ok(LatLng(pos.latitude, pos.longitude));
    } on TimeoutException {
      final last = await Geolocator.getLastKnownPosition();
      if (last != null) return GpsResult.ok(LatLng(last.latitude, last.longitude));
      return const GpsResult.fail('No se obtuvo señal GPS a tiempo.');
    }
  } catch (_) {
    return const GpsResult.fail('No se pudo obtener tu ubicación.');
  }
}

/// Abre los ajustes adecuados según el motivo del fallo del GPS.
Future<void> openLocationSettingsFor(GpsResult r) async {
  if (r.gpsOff) {
    await Geolocator.openLocationSettings();
  } else {
    await Geolocator.openAppSettings();
  }
}

/// Dirección legible del punto (calle + número, barrio, ciudad) vía Nominatim.
Future<String?> reverseGeocode(LatLng p) async {
  try {
    final uri = Uri.https('nominatim.openstreetmap.org', '/reverse', {
      'format': 'jsonv2',
      'lat': p.latitude.toStringAsFixed(6),
      'lon': p.longitude.toStringAsFixed(6),
      'zoom': '18',
      'addressdetails': '1',
      'accept-language': 'es',
    });
    final r = await http.get(uri, headers: {'User-Agent': _userAgent}).timeout(const Duration(seconds: 10));
    if (r.statusCode != 200) return null;
    return _formatAddress(jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>);
  } catch (_) {
    return null;
  }
}

/// Dirección corta y legible en lugar del texto completo de OSM.
String? _formatAddress(Map<String, dynamic> data) {
  final a = (data['address'] as Map?)?.cast<String, dynamic>() ?? const {};
  final street = a['road'] ?? a['pedestrian'] ?? a['footway'];
  final area = a['neighbourhood'] ?? a['suburb'] ?? a['quarter'];
  final city = a['city'] ?? a['town'] ?? a['village'];
  final parts = <String>[
    if (street != null) '$street${a['house_number'] != null ? ' #${a['house_number']}' : ''}',
    if (area != null) area.toString(),
    if (city != null) city.toString(),
  ];
  if (parts.isNotEmpty) return parts.join(', ');
  return data['display_name']?.toString();
}

/// Lugar encontrado por el buscador del mapa.
class _PlaceResult {
  final String title;
  final String subtitle;
  final LatLng point;
  const _PlaceResult(this.title, this.subtitle, this.point);
}

/// Busca lugares por nombre (mercados, colegios, plazas, calles…) cerca del punto dado.
Future<List<_PlaceResult>> _searchPlaces(String query, LatLng near) async {
  // Caja de ~40 km alrededor del mapa: prioriza resultados de la ciudad del cliente.
  const d = 0.35;
  final uri = Uri.https('nominatim.openstreetmap.org', '/search', {
    'format': 'jsonv2',
    'q': query,
    'countrycodes': 'bo',
    'limit': '6',
    'accept-language': 'es',
    'viewbox': '${near.longitude - d},${near.latitude + d},${near.longitude + d},${near.latitude - d}',
  });
  final r = await http.get(uri, headers: {'User-Agent': _userAgent}).timeout(const Duration(seconds: 10));
  if (r.statusCode != 200) return const [];
  final list = jsonDecode(utf8.decode(r.bodyBytes)) as List<dynamic>;
  return list.map((e) {
    final m = e as Map<String, dynamic>;
    final display = (m['display_name'] ?? '').toString();
    final comma = display.indexOf(',');
    final title = (m['name']?.toString().isNotEmpty ?? false)
        ? m['name'].toString()
        : (comma > 0 ? display.substring(0, comma) : display);
    final subtitle = comma > 0 ? display.substring(comma + 1).trim() : '';
    return _PlaceResult(
      title,
      subtitle,
      LatLng(double.parse(m['lat'].toString()), double.parse(m['lon'].toString())),
    );
  }).toList();
}

// ---------------------------------------------------------------------------
// Widgets
// ---------------------------------------------------------------------------

/// Pin de entrega dibujado de modo que su punta inferior caiga sobre la coordenada.
class _Pin extends StatelessWidget {
  final double size;
  const _Pin({this.size = 48});

  @override
  Widget build(BuildContext context) =>
      Icon(Icons.location_on, color: _brand, size: size, shadows: const [Shadow(blurRadius: 6, color: Colors.black26)]);
}

/// Mapa pequeño y sin gestos que muestra un punto de entrega (checkout y repartidor).
/// Sin gestos para que no robe el scroll de la pantalla que lo contiene.
class DeliveryPointPreview extends StatelessWidget {
  final LatLng point;
  final double height;

  /// Si es `false` se muestra el mapa sin pin (aún no hay punto elegido).
  final bool showPin;
  const DeliveryPointPreview({super.key, required this.point, this.height = 150, this.showPin = true});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: SizedBox(
        height: height,
        child: IgnorePointer(
          child: FlutterMap(
            key: ValueKey('$point$showPin'),
            options: MapOptions(initialCenter: point, initialZoom: showPin ? 16 : 13),
            children: [
              TileLayer(urlTemplate: _tileUrl, userAgentPackageName: _userAgent),
              if (showPin)
                MarkerLayer(markers: [
                  Marker(
                    point: point,
                    width: 40,
                    height: 40,
                    // La punta inferior del pin debe coincidir con la coordenada,
                    // tanto al elegirla como al mostrársela al repartidor.
                    alignment: Alignment.topCenter,
                    child: const _Pin(size: 40),
                  ),
                ]),
            ],
          ),
        ),
      ),
    );
  }
}

/// Punto de entrega elegido por el cliente.
class DeliveryLocation {
  final LatLng point;
  final String? address;
  const DeliveryLocation(this.point, this.address);
}

/// [CU29] Mapa para marcar el punto exacto de entrega del delivery.
///
/// Funciona como las apps de delivery: el pin queda fijo en el centro y el cliente mueve el
/// mapa hasta dejarlo sobre su puerta. Abre en la ubicación GPS del teléfono (punto azul),
/// y trae un buscador de lugares para quien no conoce su dirección exacta: basta con
/// buscar algo cercano (un mercado, un colegio, una plaza) y arrastrar el mapa desde ahí.
class LocationPickerView extends StatefulWidget {
  final DeliveryLocation? initial;
  const LocationPickerView({super.key, this.initial});

  @override
  State<LocationPickerView> createState() => _LocationPickerViewState();
}

class _LocationPickerViewState extends State<LocationPickerView> {
  final _mapController = MapController();
  final _searchCtrl = TextEditingController();
  final _searchFocus = FocusNode();

  /// Punto bajo el pin central (centro del mapa).
  late LatLng _center;

  /// Posición GPS real del teléfono (punto azul), si se obtuvo.
  LatLng? _myPosition;
  String? _address;
  bool _locating = false;
  bool _resolvingAddress = false;
  bool _dragging = false;
  bool _mapReady = false;
  GpsResult? _gpsFailure;

  /// Hasta obtener GPS o que el cliente mueva el mapa, el centro no es un punto elegido.
  bool _hasChosenPoint = false;

  int _geocodeSeq = 0;
  Timer? _geocodeDebounce;

  List<_PlaceResult> _results = const [];
  bool _searching = false;
  String? _searchMessage;

  @override
  void initState() {
    super.initState();
    final init = widget.initial;
    _center = init?.point ?? defaultDeliveryCenter;
    _address = init?.address;
    _hasChosenPoint = init != null;
  }

  @override
  void dispose() {
    _geocodeDebounce?.cancel();
    _searchCtrl.dispose();
    _searchFocus.dispose();
    super.dispose();
  }

  void _onMapReady() {
    _mapReady = true;
    // Siempre se busca el GPS: aunque ya haya un punto, el punto azul orienta al cliente.
    _useMyLocation(auto: true);
  }

  /// [auto]: búsqueda inicial; solo centra el mapa si el cliente aún no eligió un punto
  /// (no le "arrebata" el mapa si ya empezó a moverlo).
  Future<void> _useMyLocation({bool auto = false}) async {
    if (_locating) return;
    setState(() => _locating = true);
    final r = await locateDevice();
    if (!mounted) return;
    setState(() {
      _locating = false;
      _gpsFailure = r.point == null ? r : null;
      if (r.point != null) _myPosition = r.point;
    });
    if (r.point != null && !(auto && _hasChosenPoint)) _moveTo(r.point!, zoom: 17.5);
  }

  void _moveTo(LatLng p, {double zoom = 17.5}) {
    if (_mapReady) _mapController.move(p, zoom);
    _onCenterSettled(p);
  }

  /// El mapa se movió (gesto o programático): el pin central marca un nuevo punto.
  /// Los movimientos programáticos (GPS, búsqueda, toque) se resuelven en [_moveTo].
  void _onPositionChanged(MapCamera camera, bool hasGesture) {
    _center = camera.center;
    if (!hasGesture) return;
    _hasChosenPoint = true;
    if (!_dragging || _address != null || _results.isNotEmpty) {
      setState(() {
        _dragging = true;
        _address = null;
        _results = const [];
      });
    }
    if (_searchFocus.hasFocus) _searchFocus.unfocus();
    // Nominatim admite como máximo 1 consulta por segundo: se espera a que el mapa se detenga.
    _geocodeDebounce?.cancel();
    _geocodeDebounce = Timer(const Duration(milliseconds: 800), () => _onCenterSettled(_center));
  }

  void _onCenterSettled(LatLng p) {
    _geocodeDebounce?.cancel();
    _center = p;
    _hasChosenPoint = true;
    if (mounted) setState(() => _dragging = false);
    _resolveAddress(p);
  }

  Future<void> _resolveAddress(LatLng p) async {
    final seq = ++_geocodeSeq;
    setState(() {
      _resolvingAddress = true;
      _address = null;
    });
    final found = await reverseGeocode(p);
    if (!mounted || seq != _geocodeSeq) return;
    setState(() {
      _address = found;
      _resolvingAddress = false;
    });
  }

  Future<void> _runSearch() async {
    final q = _searchCtrl.text.trim();
    if (q.length < 3) return;
    setState(() {
      _searching = true;
      _searchMessage = null;
    });
    List<_PlaceResult> found = const [];
    String? msg;
    try {
      found = await _searchPlaces(q, _myPosition ?? _center);
      if (found.isEmpty) msg = 'Sin resultados. Prueba con un lugar cercano (mercado, colegio, plaza).';
    } catch (_) {
      msg = 'No se pudo buscar. Revisa tu conexión.';
    }
    if (!mounted) return;
    setState(() {
      _searching = false;
      _results = found;
      _searchMessage = msg;
    });
  }

  void _selectResult(_PlaceResult r) {
    _searchFocus.unfocus();
    setState(() {
      _results = const [];
      _searchMessage = null;
    });
    _moveTo(r.point, zoom: 17.5);
  }

  void _confirm() {
    Navigator.pop(context, DeliveryLocation(_center, _address));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false,
      appBar: AppBar(
        title: const Text('Ubicación de entrega', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
        backgroundColor: Colors.white,
        foregroundColor: _ink,
        elevation: 0,
      ),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _center,
              initialZoom: widget.initial != null ? 17.5 : 13,
              minZoom: 4,
              maxZoom: 19,
              // Sin rotación: un mapa girado confunde al elegir la puerta.
              interactionOptions: const InteractionOptions(flags: InteractiveFlag.all & ~InteractiveFlag.rotate),
              onMapReady: _onMapReady,
              onPositionChanged: _onPositionChanged,
              // Tocar un punto también sirve: el mapa se centra ahí.
              onTap: (_, latLng) => _moveTo(latLng, zoom: _mapController.camera.zoom),
            ),
            children: [
              TileLayer(urlTemplate: _tileUrl, userAgentPackageName: _userAgent),
              if (_myPosition != null)
                MarkerLayer(markers: [
                  Marker(
                    point: _myPosition!,
                    width: 22,
                    height: 22,
                    child: Container(
                      decoration: BoxDecoration(
                        color: _gpsBlue,
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 3),
                        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
                      ),
                    ),
                  ),
                ]),
              const RichAttributionWidget(
                attributions: [TextSourceAttribution('© OpenStreetMap contributors')],
              ),
            ],
          ),
          // Pin fijo en el centro: su punta marca exactamente el centro del mapa.
          IgnorePointer(
            child: Center(
              child: AnimatedSlide(
                duration: const Duration(milliseconds: 150),
                offset: Offset(0, _dragging ? -0.65 : -0.5),
                child: const _Pin(size: 52),
              ),
            ),
          ),
          Positioned(top: 12, left: 12, right: 12, child: _searchPanel()),
          Positioned(
            right: 12,
            bottom: 200,
            child: FloatingActionButton(
              heroTag: 'my_location',
              backgroundColor: Colors.white,
              foregroundColor: _brand,
              tooltip: 'Ir a mi ubicación actual',
              onPressed: _locating ? null : () => _useMyLocation(),
              child: _locating
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: _brand))
                  : const Icon(Icons.my_location),
            ),
          ),
          Positioned(left: 0, right: 0, bottom: 0, child: _bottomPanel()),
        ],
      ),
    );
  }

  Widget _searchPanel() {
    return Material(
      elevation: 3,
      borderRadius: BorderRadius.circular(12),
      color: Colors.white,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _searchCtrl,
            focusNode: _searchFocus,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _runSearch(),
            decoration: InputDecoration(
              hintText: 'Busca un lugar cercano (mercado, colegio, calle…)',
              hintStyle: const TextStyle(fontSize: 13),
              prefixIcon: const Icon(Icons.search, color: _brand),
              suffixIcon: _searching
                  ? const Padding(
                      padding: EdgeInsets.all(14),
                      child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                    )
                  : IconButton(icon: const Icon(Icons.arrow_forward), onPressed: _runSearch),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
          if (_searchMessage != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: Text(_searchMessage!, style: const TextStyle(color: _muted, fontSize: 12)),
            ),
          if (_results.isNotEmpty)
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 260),
              child: ListView.separated(
                shrinkWrap: true,
                padding: EdgeInsets.zero,
                itemCount: _results.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) {
                  final r = _results[i];
                  return ListTile(
                    dense: true,
                    leading: const Icon(Icons.place_outlined, color: _brand),
                    title: Text(r.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                    subtitle: Text(r.subtitle, maxLines: 2, overflow: TextOverflow.ellipsis),
                    onTap: () => _selectResult(r),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _bottomPanel() {
    final failure = _gpsFailure;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 12, offset: const Offset(0, -3))],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (failure != null)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: const Color(0xFFFFF4E5), borderRadius: BorderRadius.circular(10)),
                child: Row(
                  children: [
                    const Icon(Icons.gps_off, color: Color(0xFFB26A00), size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${failure.error} Busca un lugar cercano o mueve el mapa hasta tu puerta.',
                        style: const TextStyle(fontSize: 12, color: _ink),
                      ),
                    ),
                    TextButton(
                      onPressed: () async {
                        if (failure.needsSettings) {
                          await openLocationSettingsFor(failure);
                        } else {
                          await _useMyLocation();
                        }
                      },
                      child: Text(failure.needsSettings ? 'Activar' : 'Reintentar'),
                    ),
                  ],
                ),
              ),
            const Text(
              'Mueve el mapa hasta que el pin quede sobre tu puerta',
              style: TextStyle(fontSize: 12, color: _muted),
            ),
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.place_outlined, color: _brand),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        !_hasChosenPoint
                            ? (_locating ? 'Buscando tu ubicación…' : 'Aún no marcaste un punto.')
                            : (_dragging || _resolvingAddress)
                                ? 'Buscando la dirección…'
                                : (_address ?? 'Punto marcado en el mapa'),
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: _ink),
                      ),
                      if (_hasChosenPoint) ...[
                        const SizedBox(height: 2),
                        Text(
                          '${_center.latitude.toStringAsFixed(6)}, ${_center.longitude.toStringAsFixed(6)}',
                          style: const TextStyle(color: _muted, fontSize: 11),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 48,
              child: ElevatedButton.icon(
                onPressed: (_hasChosenPoint && !_dragging) ? _confirm : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _brand,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                icon: const Icon(Icons.check),
                label: const Text('Confirmar este punto', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
