import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:http/http.dart' as http;

import '../paquete_catalogo_y_tiendas/catalog_api.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';
import 'live_garment_engine.dart';

const _brand = Color(0xFFC66F5C);

/// [CU32] Espejo virtual en vivo: la prenda se queda puesta sobre el cuerpo.
///
/// Es la parte del probador que faltaba. Hasta ahora, "encender la cámara" en la app
/// abría el selector de fotos: había que sacarse una foto y esperar a que el servidor
/// devolviera una imagen fija. Aquí la cámara se queda abierta y la prenda acompaña a la
/// persona mientras se mueve, que es lo que se espera de un probador.
///
/// Todo el trabajo por fotograma ocurre en el teléfono: ML Kit detecta la pose y
/// [LiveGarmentPainter] deforma el recorte de la prenda sobre ella. Al servidor sólo se le
/// pide, una vez por prenda, el "rig" con sus medidas, y él lo tiene cacheado.
class LiveMirrorView extends StatefulWidget {
  final List<dynamic> products;
  final int? initialProductId;

  /// Talla calculada por biometría; ajusta cuánto ocupa la prenda sobre el cuerpo.
  final double fitScale;

  const LiveMirrorView({
    super.key,
    required this.products,
    this.initialProductId,
    this.fitScale = 1.0,
  });

  @override
  State<LiveMirrorView> createState() => _LiveMirrorViewState();
}

class _LiveMirrorViewState extends State<LiveMirrorView> with WidgetsBindingObserver {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  int _cameraIndex = 0;

  late final PoseDetector _poseDetector = PoseDetector(
    options: PoseDetectorOptions(mode: PoseDetectionMode.stream),
  );

  /// Un fotograma a la vez: sin esta guarda se encolan detecciones y la latencia crece
  /// hasta que la prenda va claramente por detrás del cuerpo.
  bool _busy = false;

  final PoseSmoother _smoother = PoseSmoother();
  List<LiveLandmark>? _landmarks;
  List<LiveLandmark>? _lastGoodLandmarks;
  int _lastPoseTimestamp = 0;
  Size? _rotatedImageSize;

  GarmentRig? _rig;
  ui.Image? _cutout;
  String _rigStatus = 'idle';
  int? _selectedProductId;

  bool _mirror = true;
  double _fitScale = 1.0;
  String? _error;
  int _fps = 0;
  int _lastFrameStamp = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _fitScale = widget.fitScale;
    _selectedProductId = widget.initialProductId ??
        (widget.products.isNotEmpty ? widget.products.first['id'] as int? : null);
    _start();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    _poseDetector.close();
    _cutout?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;
    if (state == AppLifecycleState.inactive) {
      controller.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _startCamera();
    }
  }

  Future<void> _start() async {
    await _startCamera();
    if (_selectedProductId != null) {
      await _loadRig(_selectedProductId!);
    }
  }

  Future<void> _startCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isEmpty) {
        setState(() => _error = 'No se encontró ninguna cámara en el dispositivo.');
        return;
      }
      // El probador se usa de frente: se arranca con la cámara frontal si la hay.
      _cameraIndex = _cameras.indexWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
      );
      if (_cameraIndex < 0) _cameraIndex = 0;
      await _initController();
    } on CameraException catch (e) {
      setState(() => _error = 'No se pudo abrir la cámara: ${e.description}');
    } catch (e) {
      setState(() => _error = 'No se pudo abrir la cámara: $e');
    }
  }

  Future<void> _initController() async {
    await _controller?.dispose();
    final controller = CameraController(
      _cameras[_cameraIndex],
      ResolutionPreset.medium,
      enableAudio: false,
      // ML Kit acepta NV21 en Android y BGRA en iOS en un solo plano; pedirlo aquí evita
      // tener que recomponer los planos YUV a mano en cada fotograma.
      imageFormatGroup: Platform.isAndroid
          ? ImageFormatGroup.nv21
          : ImageFormatGroup.bgra8888,
    );
    _controller = controller;
    await controller.initialize();
    if (!mounted) return;
    await controller.startImageStream(_processFrame);
    setState(() {});
  }

  // ------------------------------------------------------------------
  // Detección de pose
  // ------------------------------------------------------------------

  static const Map<DeviceOrientation, int> _orientationDegrees = {
    DeviceOrientation.portraitUp: 0,
    DeviceOrientation.landscapeLeft: 90,
    DeviceOrientation.portraitDown: 180,
    DeviceOrientation.landscapeRight: 270,
  };

  Future<void> _processFrame(CameraImage image) async {
    if (_busy || !mounted) return;
    _busy = true;
    try {
      final input = _toInputImage(image);
      if (input == null) return;

      final poses = await _poseDetector.processImage(input);
      if (!mounted) return;

      final now = DateTime.now().millisecondsSinceEpoch;
      if (poses.isEmpty) {
        // Ventana de persistencia (900ms): si la persona se mueve o gira, el detector
        // puede omitir fotogramas puntuales por desenfoque de movimiento. No borramos
        // la prenda instantáneamente para evitar parpadeos y permitir movimiento natural.
        if (_lastGoodLandmarks != null && (now - _lastPoseTimestamp) < 900) {
          return;
        }
        _smoother.reset();
        _lastGoodLandmarks = null;
        setState(() => _landmarks = null);
        return;
      }

      if (_lastFrameStamp != 0) {
        final instant = 1000 / (now - _lastFrameStamp).clamp(1, 1000);
        _fps = (_fps * 0.9 + instant * 0.1).round();
      }
      _lastFrameStamp = now;
      _lastPoseTimestamp = now;

      final size = _rotatedImageSize!;
      final raw = _toLandmarkList(poses.first, size);
      final smoothed = _smoother.smooth(raw, now);
      _lastGoodLandmarks = smoothed;
      setState(() => _landmarks = smoothed);
    } catch (_) {
      // Un fotograma fallido no debe tumbar el probador; el siguiente lo reintenta.
    } finally {
      _busy = false;
    }
  }

  /// Convierte los puntos de ML Kit a fracciones [0..1] del fotograma ya rotado.
  ///
  /// El motor de dibujado trabaja en fracciones, igual que el de la web, para no depender
  /// de la resolución que entregue cada teléfono.
  List<LiveLandmark> _toLandmarkList(Pose pose, Size size) {
    return List<LiveLandmark>.generate(33, (index) {
      final type = PoseLandmarkType.values[index];
      final landmark = pose.landmarks[type];
      if (landmark == null) return const LiveLandmark(0, 0, 0, 0);
      return LiveLandmark(
        landmark.x / size.width,
        landmark.y / size.height,
        landmark.z,
        landmark.likelihood,
      );
    });
  }

  InputImage? _toInputImage(CameraImage image) {
    final camera = _cameras[_cameraIndex];
    final controller = _controller;
    if (controller == null) return null;

    InputImageRotation? rotation;
    if (Platform.isIOS) {
      rotation = InputImageRotationValue.fromRawValue(camera.sensorOrientation);
    } else {
      final compensation = _orientationDegrees[controller.value.deviceOrientation];
      if (compensation == null) return null;
      // La cámara frontal va espejada respecto de la trasera, así que la compensación de
      // rotación se suma en vez de restarse.
      final degrees = camera.lensDirection == CameraLensDirection.front
          ? (camera.sensorOrientation + compensation) % 360
          : (camera.sensorOrientation - compensation + 360) % 360;
      rotation = InputImageRotationValue.fromRawValue(degrees);
    }
    if (rotation == null) return null;

    final format = InputImageFormatValue.fromRawValue(image.format.raw);
    if (format == null) return null;
    if (image.planes.length != 1) return null;
    final plane = image.planes.first;

    // ML Kit devuelve los puntos en el espacio YA ROTADO: con 90° o 270° el alto y el
    // ancho se intercambian, y normalizar por el tamaño sin rotar descuadraba la prenda.
    final quarterTurn = rotation == InputImageRotation.rotation90deg ||
        rotation == InputImageRotation.rotation270deg;
    _rotatedImageSize = quarterTurn
        ? Size(image.height.toDouble(), image.width.toDouble())
        : Size(image.width.toDouble(), image.height.toDouble());

    return InputImage.fromBytes(
      bytes: plane.bytes,
      metadata: InputImageMetadata(
        size: Size(image.width.toDouble(), image.height.toDouble()),
        rotation: rotation,
        format: format,
        bytesPerRow: plane.bytesPerRow,
      ),
    );
  }

  // ------------------------------------------------------------------
  // Rig de la prenda
  // ------------------------------------------------------------------

  /// Pide al backend el recorte y las medidas de la prenda, una sola vez por prenda.
  Future<void> _loadRig(int productId) async {
    setState(() {
      _rigStatus = 'loading';
      _selectedProductId = productId;
    });
    try {
      final url = Uri.parse(
        '${AuthService.apiBaseUrl}/analytics/tryon/garment-rig/$productId',
      );
      final response = await http.get(url).timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) {
        setState(() => _rigStatus = 'failed');
        return;
      }
      final rig = GarmentRig.fromJson(
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>,
      );

      final imageResponse = await http
          .get(Uri.parse(CatalogApi.resolveImage(rig.cutoutUrl)))
          .timeout(const Duration(seconds: 30));
      if (imageResponse.statusCode != 200) {
        setState(() => _rigStatus = 'failed');
        return;
      }
      final decoded = await _decodeImage(imageResponse.bodyBytes);
      if (!mounted) return;

      _cutout?.dispose();
      setState(() {
        _rig = rig;
        _cutout = decoded;
        _rigStatus = 'ready';
      });
    } catch (_) {
      if (mounted) setState(() => _rigStatus = 'failed');
    }
  }

  Future<ui.Image> _decodeImage(Uint8List bytes) async {
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    return frame.image;
  }

  Future<void> _switchCamera() async {
    if (_cameras.length < 2) return;
    _cameraIndex = (_cameraIndex + 1) % _cameras.length;
    _smoother.reset();
    _lastGoodLandmarks = null;
    _lastPoseTimestamp = 0;
    setState(() => _landmarks = null);
    await _initController();
  }

  // ------------------------------------------------------------------
  // Interfaz
  // ------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text('Espejo en vivo'),
        actions: [
          IconButton(
            tooltip: 'Voltear espejo',
            icon: Icon(_mirror ? Icons.flip : Icons.flip_outlined),
            onPressed: () => setState(() => _mirror = !_mirror),
          ),
          IconButton(
            tooltip: 'Cambiar cámara',
            icon: const Icon(Icons.cameraswitch),
            onPressed: _switchCamera,
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(child: _buildStage()),
          _buildSizeSlider(),
          _buildGarmentStrip(),
        ],
      ),
    );
  }

  Widget _buildStage() {
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            _error!,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.white70),
          ),
        ),
      );
    }

    final controller = _controller;
    final imageSize = _rotatedImageSize;
    if (controller == null || !controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator(color: _brand));
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        // El fotograma se encaja entero dentro del escenario (sin recortar) y la prenda se
        // dibuja sobre ese mismo rectángulo: así preview y prenda no se pueden descuadrar.
        final frame = imageSize ?? const Size(3, 4);
        final scale = (constraints.maxWidth / frame.width)
            .clamp(0.0, constraints.maxHeight / frame.height);
        final drawWidth = frame.width * scale;
        final drawHeight = frame.height * scale;

        return Center(
          child: Transform(
            alignment: Alignment.center,
            // Espejo aplicado al conjunto: si sólo se volteara una capa, la prenda
            // aparecería en el lado contrario del cuerpo.
            transform: Matrix4.diagonal3Values(_mirror ? -1.0 : 1.0, 1.0, 1.0),
            child: SizedBox(
              width: drawWidth,
              height: drawHeight,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  controller.buildPreview(),
                  CustomPaint(
                    painter: LiveGarmentPainter(
                      rig: _rig,
                      cutout: _cutout,
                      landmarks: _landmarks,
                      layout: VideoLayout(
                        offsetX: 0,
                        offsetY: 0,
                        drawWidth: drawWidth,
                        drawHeight: drawHeight,
                      ),
                      fitScale: _fitScale,
                      opacity: 1.0,
                    ),
                  ),
                  if (_rigStatus == 'loading')
                    const Center(
                      child: Chip(
                        avatar: SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        label: Text('Preparando la prenda…'),
                      ),
                    ),
                  if (_landmarks == null && _rigStatus == 'ready')
                    const Align(
                      alignment: Alignment.bottomCenter,
                      child: Padding(
                        padding: EdgeInsets.only(bottom: 16),
                        child: Chip(label: Text('Colócate de cuerpo entero frente a la cámara')),
                      ),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildSizeSlider() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          const Icon(Icons.straighten, color: Colors.white54, size: 18),
          Expanded(
            child: Slider(
              value: _fitScale,
              min: 0.8,
              max: 1.3,
              activeColor: _brand,
              label: 'Ajuste ${(_fitScale * 100).round()} %',
              onChanged: (value) => setState(() => _fitScale = value),
            ),
          ),
          Text('$_fps fps', style: const TextStyle(color: Colors.white38, fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildGarmentStrip() {
    if (widget.products.isEmpty) return const SizedBox.shrink();
    return SizedBox(
      height: 92,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: widget.products.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final product = widget.products[index] as Map<String, dynamic>;
          final id = product['id'] as int?;
          final selected = id == _selectedProductId;
          final image = _productImage(product);
          return GestureDetector(
            onTap: id == null ? null : () => _loadRig(id),
            child: Container(
              width: 68,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: selected ? _brand : Colors.white24,
                  width: selected ? 2.5 : 1,
                ),
                color: Colors.white10,
              ),
              clipBehavior: Clip.antiAlias,
              child: image == null
                  ? const Icon(Icons.checkroom, color: Colors.white38)
                  : Image.network(image, fit: BoxFit.cover),
            ),
          );
        },
      ),
    );
  }

  String? _productImage(Map<String, dynamic> product) {
    final images = product['images'] as List?;
    if (images != null && images.isNotEmpty) {
      final primary = images.firstWhere(
        (i) => i['is_primary'] == true,
        orElse: () => images.first,
      );
      final raw = primary['image_url'] ?? primary['url'];
      if (raw != null && raw.toString().isNotEmpty) {
        return CatalogApi.resolveImage(raw.toString());
      }
    }
    final fallback = product['primary_image_url'] ?? product['image_url'];
    if (fallback != null && fallback.toString().isNotEmpty) {
      return CatalogApi.resolveImage(fallback.toString());
    }
    return null;
  }
}
