import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// Motor de colocación de prenda sobre la cámara en vivo (CU32 - Probador RA).
///
/// Es el equivalente en Dart del motor de la web, y responde al mismo objetivo: que la
/// clienta encienda la cámara y la prenda se le quede puesta, acompañándola cuando se
/// mueve. Eso obliga a resolverlo **en el teléfono**: mandar fotogramas al servidor
/// devuelve una espera y una foto fija, que es justo lo que había antes.
///
/// Las medidas de la prenda (dónde caen su pecho, su bajo y sus mangas) las calcula el
/// backend una sola vez y llegan en un [GarmentRig]; aquí sólo se proyectan sobre el
/// cuerpo detectado.
///
/// A diferencia de la web, el dibujado usa [Canvas.drawVertices] con un [ui.ImageShader]:
/// Flutter mapea la textura sobre los triángulos de forma nativa, así que no hay que
/// recortar triángulo a triángulo y no aparecen costuras entre las filas de la malla.

/// Una fila del perfil medido del torso, en fracciones del recorte.
class GarmentRigRow {
  final double y;
  final double cx;
  final double half;

  const GarmentRigRow({required this.y, required this.cx, required this.half});

  factory GarmentRigRow.fromJson(Map<String, dynamic> json) => GarmentRigRow(
        y: (json['y'] as num).toDouble(),
        cx: (json['cx'] as num).toDouble(),
        half: (json['half'] as num).toDouble(),
      );
}

class GarmentRigTorso {
  final List<GarmentRigRow> rows;
  final double shoulderY;
  final double hemY;
  final double lengthRatio;
  final double chestHalf;

  const GarmentRigTorso({
    required this.rows,
    required this.shoulderY,
    required this.hemY,
    required this.lengthRatio,
    required this.chestHalf,
  });

  factory GarmentRigTorso.fromJson(Map<String, dynamic> json) => GarmentRigTorso(
        rows: (json['rows'] as List)
            .map((e) => GarmentRigRow.fromJson(e as Map<String, dynamic>))
            .toList(),
        shoulderY: (json['shoulder_y'] as num).toDouble(),
        hemY: (json['hem_y'] as num).toDouble(),
        lengthRatio: (json['length_ratio'] as num).toDouble(),
        chestHalf: (json['chest_half'] as num).toDouble(),
      );
}

class GarmentRigSleeves {
  final double y0;
  final double y1;
  final double leftX0;
  final double leftX1;
  final double rightX0;
  final double rightX1;

  const GarmentRigSleeves({
    required this.y0,
    required this.y1,
    required this.leftX0,
    required this.leftX1,
    required this.rightX0,
    required this.rightX1,
  });

  factory GarmentRigSleeves.fromJson(Map<String, dynamic> json) {
    final left = json['left'] as Map<String, dynamic>;
    final right = json['right'] as Map<String, dynamic>;
    return GarmentRigSleeves(
      y0: (json['y0'] as num).toDouble(),
      y1: (json['y1'] as num).toDouble(),
      leftX0: (left['x0'] as num).toDouble(),
      leftX1: (left['x1'] as num).toDouble(),
      rightX0: (right['x0'] as num).toDouble(),
      rightX1: (right['x1'] as num).toDouble(),
    );
  }
}

class GarmentRigBottom {
  final GarmentRigRow waist;
  final double crotchY;
  final GarmentRigRow hem;

  const GarmentRigBottom({
    required this.waist,
    required this.crotchY,
    required this.hem,
  });

  factory GarmentRigBottom.fromJson(Map<String, dynamic> json) => GarmentRigBottom(
        waist: GarmentRigRow.fromJson(json['waist'] as Map<String, dynamic>),
        crotchY: (json['crotch_y'] as num).toDouble(),
        hem: GarmentRigRow.fromJson(json['hem'] as Map<String, dynamic>),
      );
}

/// Medidas reales de una prenda, calculadas por el backend sobre su recorte sin fondo.
class GarmentRig {
  final String cutoutUrl;
  final double width;
  final double height;
  final String kind;
  final String sleeve;
  final GarmentRigTorso? torso;
  final GarmentRigSleeves? sleeves;
  final GarmentRigBottom? bottom;

  const GarmentRig({
    required this.cutoutUrl,
    required this.width,
    required this.height,
    required this.kind,
    required this.sleeve,
    this.torso,
    this.sleeves,
    this.bottom,
  });

  factory GarmentRig.fromJson(Map<String, dynamic> json) => GarmentRig(
        cutoutUrl: json['cutout_url'] as String,
        width: (json['width'] as num).toDouble(),
        height: (json['height'] as num).toDouble(),
        kind: json['kind'] as String,
        sleeve: json['sleeve'] as String,
        torso: json['torso'] == null
            ? null
            : GarmentRigTorso.fromJson(json['torso'] as Map<String, dynamic>),
        sleeves: json['sleeves'] == null
            ? null
            : GarmentRigSleeves.fromJson(json['sleeves'] as Map<String, dynamic>),
        bottom: json['bottom'] == null
            ? null
            : GarmentRigBottom.fromJson(json['bottom'] as Map<String, dynamic>),
      );
}

/// Punto de pose ya normalizado a fracciones [0..1] del fotograma.
class LiveLandmark {
  final double x;
  final double y;
  final double z;
  final double likelihood;

  const LiveLandmark(this.x, this.y, this.z, this.likelihood);
}

/// Índices de landmark, en el mismo orden que usa el motor de la web.
class BodyPoint {
  static const int leftShoulder = 11;
  static const int rightShoulder = 12;
  static const int leftElbow = 13;
  static const int rightElbow = 14;
  static const int leftWrist = 15;
  static const int rightWrist = 16;
  static const int leftHip = 23;
  static const int rightHip = 24;
  static const int leftKnee = 25;
  static const int rightKnee = 26;
  static const int leftAnkle = 27;
  static const int rightAnkle = 28;
}

/// El ancho de pecho no es la distancia entre los puntos de hombro que entrega la pose:
/// esos caen en el acromion, por fuera de la caja torácica. Sin este factor las prendas
/// salen visiblemente anchas.
const double _chestOverShoulderSpan = 0.92;

/// Filtro "One Euro": suaviza mucho con la persona quieta y casi nada cuando se mueve.
///
/// Una media exponencial de factor fijo obliga a elegir entre temblor y retardo visible;
/// este filtro decide solo a partir de la velocidad estimada del propio punto.
class _OneEuroFilter {
  final double minCutoff;
  final double beta;

  /// Frecuencia de corte del estimador de velocidad. No se expone: el mismo valor sirve
  /// para todos los puntos, y lo que se ajusta por punto es [minCutoff] y [beta].
  static const double _derivativeCutoff = 1.0;

  double? _previous;
  double _previousDerivative = 0;

  _OneEuroFilter({
    this.minCutoff = 1.0,
    this.beta = 0.08,
  });

  static double _alpha(double cutoff, double dt) {
    final tau = 1 / (2 * math.pi * cutoff);
    return 1 / (1 + tau / dt);
  }

  double filter(double value, double dt) {
    if (_previous == null) {
      _previous = value;
      return value;
    }
    final safeDt = dt.clamp(1 / 120, 0.2);
    final derivative = (value - _previous!) / safeDt;
    final alphaD = _alpha(_derivativeCutoff, safeDt);
    _previousDerivative += alphaD * (derivative - _previousDerivative);

    final cutoff = minCutoff + beta * _previousDerivative.abs();
    final alpha = _alpha(cutoff, safeDt);
    final smoothed = _previous! + alpha * (value - _previous!);
    _previous = smoothed;
    return smoothed;
  }

  void reset() {
    _previous = null;
    _previousDerivative = 0;
  }
}

/// Suavizador de un juego completo de landmarks.
class PoseSmoother {
  final Map<int, List<_OneEuroFilter>> _filters = {};
  int _lastTimestampMs = 0;

  List<LiveLandmark> smooth(List<LiveLandmark> landmarks, int timestampMs) {
    final dt = _lastTimestampMs == 0
        ? 1 / 30
        : (timestampMs - _lastTimestampMs) / 1000.0;
    _lastTimestampMs = timestampMs;

    return List<LiveLandmark>.generate(landmarks.length, (index) {
      final point = landmarks[index];
      final filters = _filters.putIfAbsent(
        index,
        () => [
          _OneEuroFilter(minCutoff: 1.0, beta: 0.08),
          _OneEuroFilter(minCutoff: 1.0, beta: 0.08),
          _OneEuroFilter(minCutoff: 3.0, beta: 0.05),
        ],
      );
      return LiveLandmark(
        filters[0].filter(point.x, dt),
        filters[1].filter(point.y, dt),
        point.z,
        filters[2].filter(point.likelihood, dt),
      );
    });
  }

  void reset() {
    _filters.clear();
    _lastTimestampMs = 0;
  }
}

/// Rectángulo que ocupa el fotograma dentro del lienzo, en píxeles lógicos.
class VideoLayout {
  final double offsetX;
  final double offsetY;
  final double drawWidth;
  final double drawHeight;

  const VideoLayout({
    required this.offsetX,
    required this.offsetY,
    required this.drawWidth,
    required this.drawHeight,
  });
}

/// Acumula los triángulos de la prenda y los pinta en una sola llamada.
class _MeshBuilder {
  final List<Offset> positions = [];
  final List<Offset> textureCoordinates = [];

  void quad(List<Offset> source, List<Offset> target) {
    _triangle(source[0], source[1], source[2], target[0], target[1], target[2]);
    _triangle(source[0], source[2], source[3], target[0], target[2], target[3]);
  }

  void _triangle(Offset s0, Offset s1, Offset s2, Offset d0, Offset d1, Offset d2) {
    positions..add(d0)..add(d1)..add(d2);
    textureCoordinates..add(s0)..add(s1)..add(s2);
  }

  bool get isEmpty => positions.isEmpty;
}

/// Pinta la prenda deformada sobre el cuerpo detectado en cada fotograma.
class LiveGarmentPainter extends CustomPainter {
  final GarmentRig? rig;
  final ui.Image? cutout;
  final List<LiveLandmark>? landmarks;
  final VideoLayout layout;

  /// Ajuste de talla del usuario (1 = medida calculada por biometría).
  final double fitScale;
  final double opacity;

  const LiveGarmentPainter({
    required this.rig,
    required this.cutout,
    required this.landmarks,
    required this.layout,
    this.fitScale = 1.0,
    this.opacity = 1.0,
  });

  bool get _ready => rig != null && cutout != null && landmarks != null;

  /// ¿Se ven los puntos que la prenda necesita para colocarse?
  ///
  /// Sólo los hombros son imprescindibles en prendas superiores: si la persona está tan
  /// cerca que las caderas no entran en cuadro, se estiman desde los hombros (misma
  /// geometría que `withVirtualHips` en la web) y la prenda no desaparece.
  List<LiveLandmark>? _resolveBody(List<LiveLandmark> points) {
    if (points.length < 33) return null;
    if (rig!.kind == 'bottom') {
      final ok = [BodyPoint.leftHip, BodyPoint.rightHip, BodyPoint.leftKnee, BodyPoint.rightKnee]
          .every((index) => points[index].likelihood > 0.25);
      return ok ? points : null;
    }
    final left = points[BodyPoint.leftShoulder];
    final right = points[BodyPoint.rightShoulder];
    // Umbral permisivo (0.20) para mantener el seguimiento continuo incluso durante
    // movimientos rápidos o desenfoque natural de la cámara.
    if (left.likelihood <= 0.20 || right.likelihood <= 0.20) return null;

    final hipsVisible = points[BodyPoint.leftHip].likelihood > 0.35 &&
        points[BodyPoint.rightHip].likelihood > 0.35;
    final shoulderY = (left.y + right.y) / 2;
    final hipY = (points[BodyPoint.leftHip].y + points[BodyPoint.rightHip].y) / 2;
    if (hipsVisible && hipY > shoulderY + 0.05) return points;
    return _withVirtualHips(points, layout.drawWidth / math.max(1.0, layout.drawHeight));
  }

  /// Copia de los landmarks con las caderas estimadas desde los hombros y su inclinación.
  List<LiveLandmark> _withVirtualHips(List<LiveLandmark> points, double aspect) {
    final left = points[BodyPoint.leftShoulder];
    final right = points[BodyPoint.rightShoulder];
    // Los landmarks van normalizados por eje (x por el ancho, y por el alto): x e y no tienen
    // la misma escala. Se calcula en unidades de alto (x·aspect, y) y se devuelve a normalizado.
    final dx = (left.x - right.x) * aspect;
    final dy = left.y - right.y;
    final span = math.sqrt(dx * dx + dy * dy);
    if (span < 1e-6) return points;

    // Perpendicular a los hombros, hacia abajo de la imagen.
    var downX = -dy / span;
    var downY = dx / span;
    if (downY < 0) {
      downX = -downX;
      downY = -downY;
    }
    // Medido: 1.55-1.58 anchos de hombro entre hombros y caderas (737 personas + vídeo de prueba).
    const torsoOverSpan = 1.55;
    const hipWidth = 0.6;
    final drop = span * torsoOverSpan;
    final midX = (left.x + right.x) / 2 * aspect;
    final midY = (left.y + right.y) / 2;
    final z = (left.z + right.z) / 2;
    final likelihood = math.min(left.likelihood, right.likelihood);

    final result = List<LiveLandmark>.from(points);
    result[BodyPoint.leftHip] = LiveLandmark(
        (midX + dx * hipWidth / 2 + downX * drop) / aspect, midY + dy * hipWidth / 2 + downY * drop, z, likelihood);
    result[BodyPoint.rightHip] = LiveLandmark(
        (midX - dx * hipWidth / 2 + downX * drop) / aspect, midY - dy * hipWidth / 2 + downY * drop, z, likelihood);
    return result;
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (!_ready) return;
    final points = _resolveBody(landmarks!);
    if (points == null) return;

    Offset toScreen(int index) => Offset(
          layout.offsetX + points[index].x * layout.drawWidth,
          layout.offsetY + points[index].y * layout.drawHeight,
        );

    final mesh = _MeshBuilder();
    if (rig!.kind == 'bottom') {
      _buildBottom(mesh, toScreen);
    } else {
      _buildTop(mesh, toScreen);
    }
    if (mesh.isEmpty) return;

    final paint = Paint()
      ..shader = ui.ImageShader(
        cutout!,
        TileMode.clamp,
        TileMode.clamp,
        Matrix4.identity().storage,
        filterQuality: FilterQuality.high,
      )
      ..color = Color.fromRGBO(255, 255, 255, opacity.clamp(0.0, 1.0))
      ..isAntiAlias = true
      ..filterQuality = FilterQuality.high;

    final vertices = ui.Vertices(
      VertexMode.triangles,
      mesh.positions,
      textureCoordinates: mesh.textureCoordinates,
    );
    // BlendMode.modulate preserva el 100% de la saturación y color original de la prenda
    // sin blanquearla ni lavarla con blanco como ocurría con srcOver.
    canvas.drawVertices(vertices, BlendMode.modulate, paint);
  }

  // ------------------------------------------------------------------
  // Prendas superiores, vestidos y abrigos
  // ------------------------------------------------------------------

  void _buildTop(_MeshBuilder mesh, Offset Function(int) toScreen) {
    final torso = rig!.torso;
    if (torso == null || torso.rows.length < 2) return;

    final shoulderLeft = toScreen(BodyPoint.leftShoulder);
    final shoulderRight = toScreen(BodyPoint.rightShoulder);
    final hipMid = (toScreen(BodyPoint.leftHip) + toScreen(BodyPoint.rightHip)) / 2;
    final shoulderMid = (shoulderLeft + shoulderRight) / 2;

    // Base horizontal tomada de la línea de hombros: la prenda gira y se inclina con el
    // cuerpo en lugar de quedarse siempre horizontal.
    final across = _normalize(shoulderLeft - shoulderRight);
    final down = _normalize(hipMid - shoulderMid);
    if (across == null || down == null) return;

    final shoulderSpan = (shoulderLeft - shoulderRight).distance;
    final bodyChestHalf = shoulderSpan * _chestOverShoulderSpan * fitScale / 2;
    if (bodyChestHalf < 4) return;

    final pixelsPerUnit = bodyChestHalf / math.max(0.01, torso.chestHalf);
    final torsoLengthPx = _resolveTorsoLength(
      rig!.kind,
      torso.lengthRatio,
      bodyChestHalf,
      (hipMid - shoulderMid).distance,
    );
    final spanY = math.max(1e-4, torso.hemY - torso.shoulderY);

    // La costura de hombro se apoya un poco por encima de la línea de hombros de la pose:
    // ese punto marca el acromion y el tejido lo cubre.
    final anchor = shoulderMid + down * (-bodyChestHalf * 0.12);

    // Las mangas van primero: la costura del hombro queda cubierta por el torso, que es
    // como cae la prenda de verdad.
    if (rig!.sleeve != 'none' && rig!.sleeves != null) {
      _buildSleeves(mesh, toScreen, pixelsPerUnit);
    }

    final leftEdges = <Offset>[];
    final rightEdges = <Offset>[];
    final sourceLeft = <Offset>[];
    final sourceRight = <Offset>[];

    for (final row in torso.rows) {
      final progress = (row.y - torso.shoulderY) / spanY;
      final rowCenter = anchor +
          down * (progress * torsoLengthPx) +
          across * ((row.cx - 0.5) * pixelsPerUnit);
      final halfPx = row.half * pixelsPerUnit;
      leftEdges.add(rowCenter + across * halfPx);
      rightEdges.add(rowCenter - across * halfPx);
      sourceLeft.add(Offset((row.cx - row.half) * rig!.width, row.y * rig!.height));
      sourceRight.add(Offset((row.cx + row.half) * rig!.width, row.y * rig!.height));
    }

    for (var i = 0; i < leftEdges.length - 1; i++) {
      mesh.quad(
        [sourceLeft[i], sourceRight[i], sourceRight[i + 1], sourceLeft[i + 1]],
        [leftEdges[i], rightEdges[i], rightEdges[i + 1], leftEdges[i + 1]],
      );
    }
  }

  /// Reproyecta cada manga sobre el brazo.
  ///
  /// En la foto de producto la manga sale en diagonal hacia fuera; sobre el cuerpo tiene
  /// que seguir el eje hombro→codo (manga corta) u hombro→codo→muñeca (manga larga).
  void _buildSleeves(
    _MeshBuilder mesh,
    Offset Function(int) toScreen,
    double pixelsPerUnit,
  ) {
    final sleeves = rig!.sleeves!;
    final long = rig!.sleeve == 'long';

    final arms = [
      // La caja izquierda del recorte corresponde al brazo que aparece a la izquierda de
      // la imagen, que en la pose es el hombro "derecho" del sujeto.
      [sleeves.leftX0, sleeves.leftX1, BodyPoint.rightShoulder.toDouble(),
        BodyPoint.rightElbow.toDouble(), BodyPoint.rightWrist.toDouble()],
      [sleeves.rightX0, sleeves.rightX1, BodyPoint.leftShoulder.toDouble(),
        BodyPoint.leftElbow.toDouble(), BodyPoint.leftWrist.toDouble()],
    ];

    for (final arm in arms) {
      final shoulder = toScreen(arm[2].toInt());
      final elbow = toScreen(arm[3].toInt());
      final wrist = toScreen(arm[4].toInt());

      final end = long ? wrist : Offset.lerp(shoulder, elbow, 0.5)!;
      final joint = long ? elbow : Offset.lerp(shoulder, end, 0.5)!;

      final halfWidth = math.max(4.0, (arm[1] - arm[0]) * pixelsPerUnit / 2);
      final midY = sleeves.y0 + (sleeves.y1 - sleeves.y0) * 0.5;

      // La manga se estrecha hacia el puño, como la propia manga y como el brazo.
      _sleeveSegment(mesh, shoulder, joint, halfWidth, halfWidth * 0.82,
          arm[0], arm[1], sleeves.y0, midY);
      _sleeveSegment(mesh, joint, end, halfWidth * 0.82, halfWidth * 0.66,
          arm[0], arm[1], midY, sleeves.y1);
    }
  }

  void _sleeveSegment(
    _MeshBuilder mesh,
    Offset from,
    Offset to,
    double halfFrom,
    double halfTo,
    double x0,
    double x1,
    double y0,
    double y1,
  ) {
    final axis = _normalize(to - from);
    if (axis == null) return;
    final perpendicular = Offset(-axis.dy, axis.dx);

    mesh.quad(
      [
        Offset(x0 * rig!.width, y0 * rig!.height),
        Offset(x1 * rig!.width, y0 * rig!.height),
        Offset(x1 * rig!.width, y1 * rig!.height),
        Offset(x0 * rig!.width, y1 * rig!.height),
      ],
      [
        from + perpendicular * -halfFrom,
        from + perpendicular * halfFrom,
        to + perpendicular * halfTo,
        to + perpendicular * -halfTo,
      ],
    );
  }

  // ------------------------------------------------------------------
  // Prendas inferiores
  // ------------------------------------------------------------------

  void _buildBottom(_MeshBuilder mesh, Offset Function(int) toScreen) {
    final bottom = rig!.bottom;
    if (bottom == null) return;

    final hipLeft = toScreen(BodyPoint.leftHip);
    final hipRight = toScreen(BodyPoint.rightHip);
    final halfLeg = math.max(6.0, (hipLeft - hipRight).distance * fitScale * 0.30);

    final waistY = bottom.waist.y * rig!.height;
    final crotchY = bottom.crotchY * rig!.height;
    final hemY = bottom.hem.y * rig!.height;
    final cx = bottom.waist.cx;
    final half = bottom.waist.half;

    // Cada pernera va por separado y en dos tramos, para que el pantalón se doble cuando
    // la persona flexiona las piernas.
    final legs = [
      [(cx - half) * rig!.width, cx * rig!.width, BodyPoint.rightHip.toDouble(),
        BodyPoint.rightKnee.toDouble(), BodyPoint.rightAnkle.toDouble()],
      [cx * rig!.width, (cx + half) * rig!.width, BodyPoint.leftHip.toDouble(),
        BodyPoint.leftKnee.toDouble(), BodyPoint.leftAnkle.toDouble()],
    ];

    for (final leg in legs) {
      final hip = toScreen(leg[2].toInt());
      final knee = toScreen(leg[3].toInt());
      final ankle = toScreen(leg[4].toInt());

      final axisUpper = _normalize(knee - hip);
      final axisLower = _normalize(ankle - knee);
      if (axisUpper == null || axisLower == null) continue;
      final perpUpper = Offset(-axisUpper.dy, axisUpper.dx);
      final perpLower = Offset(-axisLower.dy, axisLower.dx);

      mesh.quad(
        [
          Offset(leg[0], waistY),
          Offset(leg[1], waistY),
          Offset(leg[1], crotchY),
          Offset(leg[0], crotchY),
        ],
        [
          hip + perpUpper * -halfLeg,
          hip + perpUpper * halfLeg,
          knee + perpUpper * (halfLeg * 0.78),
          knee + perpUpper * (-halfLeg * 0.78),
        ],
      );
      mesh.quad(
        [
          Offset(leg[0], crotchY),
          Offset(leg[1], crotchY),
          Offset(leg[1], hemY),
          Offset(leg[0], hemY),
        ],
        [
          knee + perpLower * (-halfLeg * 0.78),
          knee + perpLower * (halfLeg * 0.78),
          ankle + perpLower * (halfLeg * 0.66),
          ankle + perpLower * (-halfLeg * 0.66),
        ],
      );
    }
  }

  @override
  bool shouldRepaint(covariant LiveGarmentPainter oldDelegate) {
    return oldDelegate.landmarks != landmarks ||
        oldDelegate.rig != rig ||
        oldDelegate.cutout != cutout ||
        oldDelegate.fitScale != fitScale ||
        oldDelegate.opacity != opacity;
  }
}

/// Decide cuánto baja la prenda por el cuerpo.
///
/// El largo **no** puede salir sólo de la foto de producto. El rig lo mide en anchos de
/// pecho de la propia prenda, y esa cifra depende del encuadre: en el catálogo hay fotos
/// ajustadas a la prenda y otras recortadas o con zoom, y la misma clase de prenda pasaba
/// de 1.25 a 2.05 según la foto. Anclar a ciegas a esa cifra deja blusas por medio muslo.
///
/// Lo que sí es fiable es el cuerpo: la distancia de hombros a caderas se mide en cada
/// fotograma. De ahí sale el largo objetivo por tipo de prenda. La medición de la foto se
/// conserva sólo para **acortar**: es lo que distingue un crop top de una camiseta normal,
/// y en eso sí es de fiar porque compara la prenda consigo misma.
double _resolveTorsoLength(
  String kind,
  double lengthRatio,
  double bodyChestHalf,
  double shoulderToHip,
) {
  final double target;
  switch (kind) {
    case 'dress':
      target = shoulderToHip * 1.85; // hasta la rodilla
      break;
    case 'outer':
      target = shoulderToHip * 1.18; // la chaqueta cubre la cadera
      break;
    default:
      target = shoulderToHip * 1.08; // el bajo cae justo bajo la cadera
  }
  final measured = lengthRatio * bodyChestHalf * 2;
  // El suelo evita que una medición mala colapse la prenda sobre el pecho.
  return math.min(target, math.max(measured, shoulderToHip * 0.55));
}

Offset? _normalize(Offset value) {
  final length = value.distance;
  if (length < 1e-6) return null;
  return value / length;
}
