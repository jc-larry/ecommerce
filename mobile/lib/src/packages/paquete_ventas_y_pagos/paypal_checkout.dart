import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';
import 'paypal_simulator_page.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);
const _paypalBlue = Color(0xFF003087);

/// Comprobante de un pago capturado por PayPal (real o simulado).
class PayPalPaymentResult {
  final String orderId;
  final String gatewayReference;
  final String? payerId;
  final String? payerEmail;
  final bool simulated;

  const PayPalPaymentResult({
    required this.orderId,
    required this.gatewayReference,
    this.payerId,
    this.payerEmail,
    required this.simulated,
  });
}

/// Error de la pasarela con un mensaje apto para mostrar al cliente.
class PayPalException implements Exception {
  final String message;
  const PayPalException(this.message);

  @override
  String toString() => message;
}

/// [CU18 / CU26] Pasarela PayPal en la app móvil (mismo backend que la web).
///
/// Flujo real (credenciales sandbox/live en el backend):
///   1. POST /payments/paypal/create-order → orden REST v2 + `approve_url`.
///   2. La ventana oficial de PayPal se abre dentro de la app; el cliente inicia sesión
///      con su cuenta (sandbox: cuenta "Personal" de pruebas) y aprueba.
///   3. PayPal redirige a `.../checkout/success` → la app lo detecta y pide al backend
///      POST /payments/paypal/capture-order. El Secret nunca llega al teléfono.
/// Con el simulador activo en el backend (por defecto), la orden es simulada y se aprueba en
/// [PayPalSimulatorPage] iniciando sesión con la cuenta del simulador; luego se captura igual.
class PayPalCheckout {
  static const Duration _timeout = Duration(seconds: 20);
  static const double defaultExchangeRate = 6.96;

  /// webview_flutter solo existe en Android, iOS y macOS; en Windows, Linux o web la ventana
  /// embebida no se puede crear y PayPal se abre en el navegador del sistema.
  static bool get supportsEmbeddedWindow =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.android ||
          defaultTargetPlatform == TargetPlatform.iOS ||
          defaultTargetPlatform == TargetPlatform.macOS);

  static Future<Map<String, String>> _headers() async {
    final token = await AuthService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static String _detail(http.Response r, String fallback) {
    try {
      final body = jsonDecode(utf8.decode(r.bodyBytes));
      final d = body is Map ? body['detail'] : null;
      if (d is String && d.isNotEmpty) return d;
    } catch (_) {}
    return fallback;
  }

  /// Tipo de cambio Bs → USD que usa el backend (para mostrar el monto en dólares).
  static Future<double> exchangeRate() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/config'))
          .timeout(_timeout);
      if (r.statusCode == 200) {
        final rate = (jsonDecode(r.body)['exchange_rate_bob_usd'] as num?)?.toDouble();
        if (rate != null && rate > 0) return rate;
      }
    } catch (_) {}
    return defaultExchangeRate;
  }

  /// Comprobante a partir de la respuesta de `/capture-order`. Su `id` es el que el backend
  /// verifica luego en el checkout y en las reservas.
  static PayPalPaymentResult _resultFromCapture(Map<String, dynamic> cap, String orderId) {
    final payer = (cap['payer'] as Map?) ?? const {};
    return PayPalPaymentResult(
      orderId: cap['id']?.toString() ?? orderId,
      gatewayReference: cap['gateway_reference']?.toString() ?? 'PAYPAL:$orderId',
      payerId: payer['payer_id']?.toString(),
      payerEmail: payer['email_address']?.toString(),
      simulated: cap['simulated'] == true,
    );
  }

  /// Ejecuta el cobro completo por PayPal. Devuelve null si el cliente cancela.
  /// Lanza [PayPalException] si PayPal o el backend rechazan el pago o si expira el tiempo.
  static Future<PayPalPaymentResult?> pay(
    BuildContext context, {
    required double amountBob,
    required String description,
    int remainingSeconds = 300,
  }) async {
    final navigator = Navigator.of(context);

    // 1. Crear la orden en el backend (que a su vez la crea en PayPal).
    final Map<String, dynamic> order;
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/create-order'),
            headers: await _headers(),
            body: jsonEncode({'amount_bob': double.parse(amountBob.toStringAsFixed(2)), 'description': description}),
          )
          .timeout(_timeout);
      if (r.statusCode != 200) {
        throw PayPalException(_detail(r, 'No se pudo iniciar el pago con PayPal.'));
      }
      order = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
    } on PayPalException {
      rethrow;
    } catch (_) {
      throw const PayPalException('No se pudo conectar con el servidor para iniciar el pago.');
    }

    final orderId = order['id']?.toString() ?? '';
    final simulated = order['simulated'] == true;
    final approveUrl = order['approve_url']?.toString();
    final amountUsd = (order['amount_usd'] as num?)?.toDouble() ?? 0;

    // Simulador: la ventana tipo PayPal hace login, aprobación y cobro, y devuelve la captura.
    if (simulated) {
      final cap = await navigator.push<Map<String, dynamic>>(MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => PayPalSimulatorPage(
          orderId: orderId,
          amountUsd: amountUsd,
          amountBob: amountBob,
          description: description,
          initialRemainingSeconds: remainingSeconds,
        ),
      ));
      if (cap == null) return null;
      if (cap['timeout'] == true) {
        throw PayPalException(
          cap['error']?.toString() ?? 'La sesión de pago de 5 minutos ha expirado. Stock liberado.',
        );
      }
      return _resultFromCapture(cap, orderId);
    }

    // 2. Aprobación del comprador en PayPal real.
    if (approveUrl == null || approveUrl.isEmpty) {
      throw const PayPalException('PayPal no devolvió el enlace de aprobación.');
    }
    final approved = await navigator.push<bool>(MaterialPageRoute(
      builder: (_) => supportsEmbeddedWindow
          ? PayPalApprovalPage(approveUrl: approveUrl, amountUsd: amountUsd, initialRemainingSeconds: remainingSeconds)
          : _ExternalApprovalPage(approveUrl: approveUrl, amountUsd: amountUsd),
    ));
    if (approved != true) return null;

    // 3. Captura de los fondos (lado servidor).
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/capture-order'),
            headers: await _headers(),
            body: jsonEncode({'paypal_order_id': orderId}),
          )
          .timeout(_timeout);
      if (r.statusCode != 200) {
        throw PayPalException(_detail(
          r,
          'PayPal no confirmó el pago. Si no terminaste de aprobarlo en PayPal, vuelve a intentarlo.',
        ));
      }
      return _resultFromCapture(jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>, orderId);
    } on PayPalException {
      rethrow;
    } catch (_) {
      throw const PayPalException('No se pudo confirmar el pago con el servidor.');
    }
  }
}

/// Ventana oficial de PayPal (sandbox o live) embebida en la app.
/// Devuelve true cuando PayPal redirige al return_url (pago aprobado) y false si se cancela.
class PayPalApprovalPage extends StatefulWidget {
  final String approveUrl;
  final double amountUsd;
  final int initialRemainingSeconds;

  const PayPalApprovalPage({
    super.key,
    required this.approveUrl,
    required this.amountUsd,
    this.initialRemainingSeconds = 300,
  });

  @override
  State<PayPalApprovalPage> createState() => _PayPalApprovalPageState();
}

class _PayPalApprovalPageState extends State<PayPalApprovalPage> {
  late final WebViewController _controller;
  int _progress = 0;
  bool _finished = false;
  bool _loadError = false;
  Timer? _countdownTimer;
  late int _remainingSeconds;

  /// El backend configura return_url = .../checkout/success y cancel_url = .../checkout/cancel.
  bool _handleUrl(String url) {
    if (_finished) return true;
    if (url.contains('/checkout/success')) {
      _finish(true);
      return true;
    }
    if (url.contains('/checkout/cancel')) {
      _finish(false);
      return true;
    }
    return false;
  }

  void _finish(bool approved) {
    _finished = true;
    if (mounted) Navigator.of(context).pop(approved);
  }

  @override
  void initState() {
    super.initState();
    _remainingSeconds = widget.initialRemainingSeconds;
    _startCountdown();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onNavigationRequest: (req) =>
            _handleUrl(req.url) ? NavigationDecision.prevent : NavigationDecision.navigate,
        // Respaldo: algunas redirecciones del servidor no pasan por onNavigationRequest.
        onPageStarted: _handleUrl,
        onProgress: (p) {
          if (mounted) setState(() => _progress = p);
        },
        onWebResourceError: (err) {
          // Solo la página principal: los recursos secundarios de PayPal fallan a menudo sin importar.
          if (err.isForMainFrame == true && mounted && !_finished) setState(() => _loadError = true);
        },
      ))
      ..loadRequest(Uri.parse(widget.approveUrl));
  }

  void _startCountdown() {
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      if (_remainingSeconds <= 1) {
        timer.cancel();
        setState(() => _remainingSeconds = 0);
        _handleTimeout();
      } else {
        setState(() => _remainingSeconds--);
      }
    });
  }

  void _handleTimeout() {
    if (_finished) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.timer_off_outlined, color: Colors.red),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Sesión Expirada (5 min)',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
          ],
        ),
        content: const Text(
          'El tiempo de 5 minutos para completar el pago ha expirado. '
          'La reserva de prendas ha sido liberada automáticamente.',
          style: TextStyle(fontSize: 14),
        ),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _finish(false);
            },
            style: FilledButton.styleFrom(backgroundColor: _paypalBlue),
            child: const Text('Volver al Carrito'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Widget _timerBar() {
    final isUrgent = _remainingSeconds <= 60;
    final minutes = (_remainingSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (_remainingSeconds % 60).toString().padLeft(2, '0');
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: isUrgent ? const Color(0xFFFFF0F0) : const Color(0xFFEFF6FF),
        border: Border(
          bottom: BorderSide(
            color: isUrgent ? const Color(0xFFFFB4B4) : const Color(0xFFC7DCFA),
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            isUrgent ? Icons.warning_amber_rounded : Icons.timer_outlined,
            size: 15,
            color: isUrgent ? const Color(0xFFD20000) : _paypalBlue,
          ),
          const SizedBox(width: 6),
          Text(
            isUrgent
                ? '¡Tiempo a punto de expirar!: $minutes:$seconds'
                : 'Tiempo restante de reserva: $minutes:$seconds',
            style: TextStyle(
              color: isUrgent ? const Color(0xFFD20000) : _paypalBlue,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop && !_finished) _finish(false);
      },
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.white,
          foregroundColor: _paypalBlue,
          leading: IconButton(icon: const Icon(Icons.close), onPressed: () => _finish(false)),
          title: Text(
            'PayPal · \$${widget.amountUsd.toStringAsFixed(2)} USD',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          bottom: _progress < 100
              ? PreferredSize(
                  preferredSize: const Size.fromHeight(3),
                  child: LinearProgressIndicator(value: _progress / 100, minHeight: 3, color: _paypalBlue),
                )
              : null,
        ),
        body: Column(
          children: [
            _timerBar(),
            Expanded(
              child: _loadError
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.wifi_off, size: 48, color: _muted),
                            const SizedBox(height: 12),
                            const Text(
                              'No se pudo cargar PayPal. Revisa tu conexión a internet.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: _ink),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: () {
                                setState(() => _loadError = false);
                                _controller.loadRequest(Uri.parse(widget.approveUrl));
                              },
                              child: const Text('Reintentar'),
                            ),
                          ],
                        ),
                      ),
                    )
                  : WebViewWidget(controller: _controller),
            ),
          ],
        ),
      ),
    );
  }
}

/// PayPal en el navegador del sistema (plataformas sin ventana embebida).
/// El navegador no avisa a la app al terminar, así que el cliente confirma con un botón y
/// el backend captura: si no aprobó en PayPal, la captura falla y no se cobra nada.
class _ExternalApprovalPage extends StatefulWidget {
  final String approveUrl;
  final double amountUsd;
  const _ExternalApprovalPage({required this.approveUrl, required this.amountUsd});

  @override
  State<_ExternalApprovalPage> createState() => _ExternalApprovalPageState();
}

class _ExternalApprovalPageState extends State<_ExternalApprovalPage> {
  bool _opened = false;

  @override
  void initState() {
    super.initState();
    _open();
  }

  Future<void> _open() async {
    bool ok = false;
    try {
      ok = await launchUrl(Uri.parse(widget.approveUrl), mode: LaunchMode.externalApplication);
    } catch (_) {}
    if (!mounted) return;
    setState(() => _opened = ok);
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo abrir el navegador para PayPal.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: _paypalBlue,
        leading: IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context, false)),
        title: Text('PayPal · \$${widget.amountUsd.toStringAsFixed(2)} USD',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.open_in_browser, size: 56, color: _paypalBlue),
            const SizedBox(height: 16),
            Text(
              _opened
                  ? 'Se abrió PayPal en tu navegador. Inicia sesión con tu cuenta, aprueba el pago '
                      'y luego vuelve aquí y toca "Ya aprobé el pago".'
                  : 'Abriendo PayPal en tu navegador…',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 14, color: _ink, height: 1.4),
            ),
            const Spacer(),
            SizedBox(
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFFC439),
                  foregroundColor: _paypalBlue,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                ),
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Ya aprobé el pago', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: _open, child: const Text('Abrir PayPal de nuevo')),
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar', style: TextStyle(color: _brand)),
            ),
          ],
        ),
      ),
    );
  }
}
