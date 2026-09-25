import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../paquete_seguridad_usuarios/auth_service.dart';

// Paleta de la ventana de PayPal Checkout.
const _ppNavy = Color(0xFF003087);
const _ppSky = Color(0xFF009CDE);
const _ppBlue = Color(0xFF0070E0);
const _ppInk = Color(0xFF001435);
const _ppGrey = Color(0xFF545D68);
const _ppLine = Color(0xFFEAECED);
const _ppError = Color(0xFFD20000);

enum _SimStep { email, password, wallet, review, processing, done }

/// [CU18 / CU26] Simulador de PayPal Checkout en la app (mismo flujo que la web).
///
/// El comprador inicia sesión en dos pasos con la cuenta del simulador, ve "Estamos cargando
/// su cartera", revisa el pago y pulsa "Completar compra": el backend aprueba la orden
/// simulada (`/simulator/approve`) y la cobra (`/capture-order` con el token de aprobación).
/// Devuelve la respuesta de la captura, o null si el comprador cancela. Si algo falla, se
/// queda en la revisión con la sesión abierta para reintentar (no vuelve a pedir el login).
class PayPalSimulatorPage extends StatefulWidget {
  final String orderId;
  final double amountUsd;
  final double amountBob;
  final String description;
  final String merchantName;
  final int initialRemainingSeconds;

  const PayPalSimulatorPage({
    super.key,
    required this.orderId,
    required this.amountUsd,
    required this.amountBob,
    required this.description,
    this.merchantName = 'FashionStore Bolivia S.R.L.',
    this.initialRemainingSeconds = 300,
  });

  @override
  State<PayPalSimulatorPage> createState() => _PayPalSimulatorPageState();
}

class _PayPalSimulatorPageState extends State<PayPalSimulatorPage> {
  static const _timeout = Duration(seconds: 20);

  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _passFocus = FocusNode();

  _SimStep _step = _SimStep.email;
  bool _busy = false;
  bool _showPass = false;
  String? _error;
  Map<String, dynamic>? _payer;
  List<Map<String, dynamic>> _funding = const [];
  String _fundingId = 'BALANCE';
  Timer? _timer;
  Timer? _countdownTimer;
  late int _remainingSeconds;

  @override
  void initState() {
    super.initState();
    _remainingSeconds = widget.initialRemainingSeconds;
    _startCountdown();
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
    if (_step == _SimStep.done) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.timer_off_outlined, color: _ppError),
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
          'Tu reserva de prendas ha sido liberada para otros clientes y '
          'no se ha realizado ningún cobro en tu cuenta.',
          style: TextStyle(fontSize: 14),
        ),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pop({
                'timeout': true,
                'error': 'Tiempo límite de pago expirado (5 minutos). Stock liberado.',
              });
            },
            style: FilledButton.styleFrom(backgroundColor: _ppNavy),
            child: const Text('Volver al Carrito'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _timer?.cancel();
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _passFocus.dispose();
    super.dispose();
  }

  String get _firstName => (_payer?['name'] as Map?)?['given_name']?.toString() ?? '';

  /// POST a `/payments/paypal/<path>` con el JWT del cliente.
  Future<http.Response> _post(String path, Map<String, dynamic> body) async {
    final token = await AuthService.getToken();
    return http
        .post(
          Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/$path'),
          headers: {
            'Content-Type': 'application/json',
            if (token != null) 'Authorization': 'Bearer $token',
          },
          body: jsonEncode(body),
        )
        .timeout(_timeout);
  }

  String _detail(http.Response r, String fallback) {
    try {
      final d = (jsonDecode(utf8.decode(r.bodyBytes)) as Map)['detail'];
      if (d is String && d.isNotEmpty) return d;
    } catch (_) {}
    return fallback;
  }

  void _nextFromEmail() {
    final email = _emailCtrl.text.trim();
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email)) {
      setState(() => _error = 'Introduzca una dirección de correo electrónico válida.');
      return;
    }
    setState(() {
      _error = null;
      _step = _SimStep.password;
    });
    _passFocus.requestFocus();
  }

  Future<void> _login() async {
    if (_passCtrl.text.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await _post('simulator/login', {'email': _emailCtrl.text.trim(), 'password': _passCtrl.text});
      if (!mounted) return;
      if (r.statusCode != 200) {
        setState(() {
          _busy = false;
          _passCtrl.clear();
          _error = _detail(r, 'No se pudo iniciar sesión. Inténtelo de nuevo.');
        });
        return;
      }
      final data = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
      setState(() {
        _busy = false;
        _payer = (data['payer'] as Map).cast<String, dynamic>();
        _funding = ((data['funding_sources'] as List?) ?? const [])
            .map((e) => (e as Map).cast<String, dynamic>())
            .toList();
        _step = _SimStep.wallet;
      });
      FocusScope.of(context).unfocus();
      // "¡Hola, …! Estamos cargando su cartera." como en PayPal.
      _timer = Timer(const Duration(milliseconds: 1600), () {
        if (mounted) setState(() => _step = _SimStep.review);
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = 'No se pudo conectar con PayPal. Revise su conexión.';
      });
    }
  }

  /// "Completar compra": el comprador aprueba la orden y el backend la cobra.
  Future<void> _completePurchase() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _step = _SimStep.processing;
    });
    try {
      final approve = await _post('simulator/approve', {
        'paypal_order_id': widget.orderId,
        'email': _emailCtrl.text.trim(),
        'password': _passCtrl.text,
      });
      if (!mounted) return;
      if (approve.statusCode != 200) {
        _failReview(_detail(approve, 'PayPal no pudo procesar el pago. No se realizó ningún cobro.'));
        return;
      }
      final token = (jsonDecode(utf8.decode(approve.bodyBytes)) as Map)['approval_token']?.toString();
      final capture = await _post('capture-order', {
        'paypal_order_id': widget.orderId,
        'approval_token': token,
      });
      if (!mounted) return;
      if (capture.statusCode != 200) {
        _failReview(_detail(capture, 'PayPal no confirmó el pago. No se realizó ningún cobro.'));
        return;
      }
      final result = (jsonDecode(utf8.decode(capture.bodyBytes)) as Map).cast<String, dynamic>();
      setState(() => _step = _SimStep.done);
      _timer = Timer(const Duration(milliseconds: 1300), () {
        if (mounted) Navigator.of(context).pop(result);
      });
    } catch (_) {
      if (mounted) _failReview('No se pudo conectar con PayPal. Revise su conexión.');
    }
  }

  /// Vuelve a la revisión con el error, manteniendo la sesión para reintentar.
  void _failReview(String msg) {
    setState(() {
      _busy = false;
      _step = _SimStep.review;
      _error = msg;
    });
  }

  bool get _locked => _step == _SimStep.processing || _step == _SimStep.done;

  void _cancel() {
    if (_locked) return;
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _cancel();
      },
      child: Scaffold(
        backgroundColor: Colors.white,
        body: SafeArea(
          child: Column(
            children: [
              _header(),
              _timerBar(),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    child: KeyedSubtree(key: ValueKey(_step), child: _body()),
                  ),
                ),
              ),
              _footer(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: _ppLine))),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.close, color: _ppGrey),
            onPressed: _locked ? null : _cancel,
            tooltip: 'Cerrar',
          ),
          const Spacer(),
          const _PayPalWordmark(),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: const Color(0xFFFFD140), borderRadius: BorderRadius.circular(10)),
            child: const Text('SANDBOX',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.6, color: Color(0xFF3D2D00))),
          ),
          const Spacer(),
          Row(
            children: [
              const Icon(Icons.shopping_cart_outlined, size: 18, color: _ppInk),
              const SizedBox(width: 4),
              Text('\$${widget.amountUsd.toStringAsFixed(2)}',
                  style: const TextStyle(fontWeight: FontWeight.w700, color: _ppInk)),
            ],
          ),
          const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _timerBar() {
    final isUrgent = _remainingSeconds <= 60;
    final minutes = (_remainingSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (_remainingSeconds % 60).toString().padLeft(2, '0');
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
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
            size: 16,
            color: isUrgent ? _ppError : _ppNavy,
          ),
          const SizedBox(width: 6),
          Text(
            isUrgent
                ? '¡Tiempo a punto de expirar!: $minutes:$seconds'
                : 'Tiempo para completar tu pago: $minutes:$seconds',
            style: TextStyle(
              color: isUrgent ? _ppError : _ppNavy,
              fontSize: 12.5,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _footer() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: const BoxDecoration(color: Color(0xFFF7F9FA), border: Border(top: BorderSide(color: _ppLine))),
      child: const Text(
        'Privacidad  ·  Legal  ·  Contacto\nSimulador de pagos · sin cobro real',
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 11, color: Color(0xFF6C7378), height: 1.5),
      ),
    );
  }

  Widget _body() {
    switch (_step) {
      case _SimStep.email:
        return _emailStep();
      case _SimStep.password:
        return _passwordStep();
      case _SimStep.wallet:
        return _center([
          const _WalletLoader(),
          const SizedBox(height: 24),
          Text('¡Hola, $_firstName!',
              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w500, color: _ppInk)),
          const SizedBox(height: 4),
          const Text('Estamos cargando su cartera.',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: _ppInk)),
        ]);
      case _SimStep.review:
        return _reviewStep();
      case _SimStep.processing:
        return _center(const [
          SizedBox(width: 56, height: 56, child: CircularProgressIndicator(strokeWidth: 4, color: _ppBlue)),
          SizedBox(height: 18),
          Text('Procesando su pago…', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w600, color: _ppInk)),
          SizedBox(height: 4),
          Text('No cierre esta ventana.', style: TextStyle(color: _ppGrey)),
        ]);
      case _SimStep.done:
        return _center([
          Container(
            width: 64,
            height: 64,
            decoration: const BoxDecoration(color: Color(0xFF017A36), shape: BoxShape.circle),
            child: const Icon(Icons.check, color: Colors.white, size: 38),
          ),
          const SizedBox(height: 16),
          const Text('Pago completado', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w600, color: _ppInk)),
          const SizedBox(height: 4),
          Text('Pagó \$${widget.amountUsd.toStringAsFixed(2)} USD a ${widget.merchantName}.',
              textAlign: TextAlign.center, style: const TextStyle(color: _ppGrey)),
          const SizedBox(height: 4),
          Text('Regresando a ${widget.merchantName}…',
              textAlign: TextAlign.center, style: const TextStyle(color: _ppGrey, fontSize: 12)),
        ]);
    }
  }

  Widget _center(List<Widget> children) => SizedBox(
        height: 360,
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: children),
      );

  Widget _emailStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('Pagar con PayPal',
            textAlign: TextAlign.center, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w500, color: _ppInk)),
        const SizedBox(height: 6),
        const Text('Introduzca su correo electrónico para empezar.',
            textAlign: TextAlign.center, style: TextStyle(color: _ppGrey)),
        const SizedBox(height: 20),
        if (_error != null) _errorBox(_error!),
        _PayPalField(
          controller: _emailCtrl,
          label: 'Correo electrónico o número de celular',
          keyboardType: TextInputType.emailAddress,
          hasError: _error != null,
          onSubmitted: (_) => _nextFromEmail(),
        ),
        _linkLeft('¿Olvidó su correo electrónico?'),
        _primaryButton('Siguiente', _nextFromEmail),
        const SizedBox(height: 20),
        const Row(children: [
          Expanded(child: Divider(color: Color(0xFFCBD2D6))),
          Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('o', style: TextStyle(color: _ppGrey))),
          Expanded(child: Divider(color: Color(0xFFCBD2D6))),
        ]),
        const SizedBox(height: 16),
        SizedBox(
          height: 48,
          child: OutlinedButton(
            onPressed: null,
            style: OutlinedButton.styleFrom(
              shape: const StadiumBorder(),
              side: const BorderSide(color: Color(0x88001435), width: 2),
            ),
            child: const Text('Pagar con tarjeta de débito o crédito',
                style: TextStyle(fontWeight: FontWeight.w700, color: Color(0x88001435))),
          ),
        ),
        _cancelLink(),
      ],
    );
  }

  Widget _passwordStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('Pagar con PayPal',
            textAlign: TextAlign.center, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w500, color: _ppInk)),
        const SizedBox(height: 10),
        Wrap(
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          children: [
            Text(_emailCtrl.text.trim(), style: const TextStyle(fontSize: 15, color: _ppInk)),
            GestureDetector(
              onTap: () => setState(() {
                _passCtrl.clear();
                _error = null;
                _step = _SimStep.email;
              }),
              child: const Text('Cambiar', style: TextStyle(color: _ppBlue, fontWeight: FontWeight.w700)),
            ),
          ],
        ),
        const SizedBox(height: 18),
        if (_error != null) _errorBox(_error!),
        _PayPalField(
          controller: _passCtrl,
          focusNode: _passFocus,
          label: 'Contraseña',
          obscure: !_showPass,
          hasError: _error != null,
          onSubmitted: (_) => _login(),
          suffix: IconButton(
            icon: Icon(_showPass ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: _ppGrey),
            onPressed: () => setState(() => _showPass = !_showPass),
          ),
        ),
        _linkLeft('¿Olvidó su contraseña?'),
        _primaryButton('Iniciar sesión', _login, loading: _busy),
        _cancelLink(),
      ],
    );
  }

  Widget _reviewStep() {
    final email = _payer?['email_address']?.toString() ?? '';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            CircleAvatar(
              radius: 22,
              backgroundColor: _ppNavy,
              child: Text(_firstName.isNotEmpty ? _firstName[0].toUpperCase() : '?',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 18)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Hola, $_firstName',
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: _ppInk)),
                  Text(email, style: const TextStyle(fontSize: 12, color: _ppGrey)),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_error != null) _errorBox(_error!),
        _sectionTitle('Pagar a'),
        Row(
          children: [
            Expanded(child: Text(widget.merchantName, style: const TextStyle(fontSize: 15, color: _ppInk))),
            Text('\$${widget.amountUsd.toStringAsFixed(2)} USD',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: _ppInk)),
          ],
        ),
        const SizedBox(height: 2),
        Text('${widget.description} · ≈ Bs. ${widget.amountBob.toStringAsFixed(2)}',
            style: const TextStyle(fontSize: 12, color: _ppGrey)),
        const SizedBox(height: 14),
        _sectionTitle('Pagar con'),
        for (final f in _funding) _fundingTile(f),
        const SizedBox(height: 4),
        _primaryButton(_error != null ? 'Intentar de nuevo' : 'Completar compra', _completePurchase,
            loading: _busy, height: 52),
        const SizedBox(height: 12),
        Text(
          'Al pulsar Completar compra, autoriza a ${widget.merchantName} a cobrar '
          '\$${widget.amountUsd.toStringAsFixed(2)} USD en su cuenta PayPal.',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: _ppGrey),
        ),
        _cancelLink(),
      ],
    );
  }

  Widget _sectionTitle(String t) => Container(
        padding: const EdgeInsets.only(top: 12, bottom: 8),
        decoration: const BoxDecoration(border: Border(top: BorderSide(color: _ppLine))),
        child: Text(t, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: _ppGrey)),
      );

  Widget _fundingTile(Map<String, dynamic> f) {
    final id = f['id']?.toString() ?? '';
    final on = _fundingId == id;
    return GestureDetector(
      onTap: () => setState(() => _fundingId = id),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: on ? _ppBlue : const Color(0xFFCBD2D6), width: on ? 2 : 1),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 26,
              decoration: BoxDecoration(color: const Color(0xFFF1F5FB), borderRadius: BorderRadius.circular(4)),
              child: Icon(id == 'BALANCE' ? Icons.account_balance_wallet : Icons.credit_card,
                  size: 16, color: _ppNavy),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(f['label']?.toString() ?? '',
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: _ppInk)),
                  Text(f['detail']?.toString() ?? '', style: const TextStyle(fontSize: 12, color: _ppGrey)),
                ],
              ),
            ),
            if (on) const Icon(Icons.check_circle, color: _ppBlue, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _errorBox(String msg) => Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFFFFF4F4),
          border: Border.all(color: const Color(0xFFF5C2C2)),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.error, color: Color(0xFFA30000), size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(msg, style: const TextStyle(color: Color(0xFFA30000), fontSize: 13))),
          ],
        ),
      );

  Widget _linkLeft(String t) => Align(
        alignment: Alignment.centerLeft,
        child: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(t, style: const TextStyle(color: _ppBlue, fontWeight: FontWeight.w700, fontSize: 14)),
        ),
      );

  Widget _cancelLink() => Padding(
        padding: const EdgeInsets.only(top: 12),
        child: TextButton(
          onPressed: _cancel,
          child: Text('Cancelar y regresar a ${widget.merchantName}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: _ppBlue, fontWeight: FontWeight.w700)),
        ),
      );

  Widget _primaryButton(String label, VoidCallback onTap, {bool loading = false, double height = 48}) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: SizedBox(
        height: height,
        child: ElevatedButton(
          onPressed: loading ? null : onTap,
          style: ElevatedButton.styleFrom(
            backgroundColor: _ppBlue,
            disabledBackgroundColor: const Color(0xFF7FB6EE),
            foregroundColor: Colors.white,
            shape: const StadiumBorder(),
            elevation: 0,
          ),
          child: loading
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 3, color: Colors.white))
              : Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        ),
      ),
    );
  }
}

/// Logotipo tipográfico de PayPal (sin imágenes externas).
class _PayPalWordmark extends StatelessWidget {
  const _PayPalWordmark();

  @override
  Widget build(BuildContext context) {
    return const Text.rich(
      TextSpan(children: [
        TextSpan(
          text: 'P ',
          style: TextStyle(color: _ppNavy, shadows: [Shadow(color: _ppSky, offset: Offset(3, -2))]),
        ),
        TextSpan(text: 'Pay', style: TextStyle(color: _ppNavy)),
        TextSpan(text: 'Pal', style: TextStyle(color: _ppSky)),
      ]),
      style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, fontStyle: FontStyle.italic, letterSpacing: -0.5),
    );
  }
}

/// Campo con etiqueta flotante y borde azul al enfocar, como los de PayPal.
class _PayPalField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final FocusNode? focusNode;
  final bool obscure;
  final bool hasError;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onSubmitted;
  final Widget? suffix;

  const _PayPalField({
    required this.controller,
    required this.label,
    this.focusNode,
    this.obscure = false,
    this.hasError = false,
    this.keyboardType,
    this.onSubmitted,
    this.suffix,
  });

  @override
  Widget build(BuildContext context) {
    OutlineInputBorder border(Color c, [double w = 1]) =>
        OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: BorderSide(color: c, width: w));
    return TextField(
      controller: controller,
      focusNode: focusNode,
      obscureText: obscure,
      keyboardType: keyboardType,
      autocorrect: false,
      enableSuggestions: false,
      textInputAction: TextInputAction.go,
      onSubmitted: onSubmitted,
      style: const TextStyle(fontSize: 16, color: _ppInk),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: _ppGrey),
        floatingLabelStyle: const TextStyle(color: _ppGrey),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 20),
        enabledBorder: border(hasError ? _ppError : const Color(0xFF929496)),
        focusedBorder: border(hasError ? _ppError : _ppBlue, 2),
        suffixIcon: suffix,
      ),
    );
  }
}

/// Anillo giratorio con la mano saludando de la pantalla "Estamos cargando su cartera".
class _WalletLoader extends StatefulWidget {
  const _WalletLoader();

  @override
  State<_WalletLoader> createState() => _WalletLoaderState();
}

class _WalletLoaderState extends State<_WalletLoader> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 96,
      height: 96,
      child: Stack(
        alignment: Alignment.center,
        children: [
          RotationTransition(
            turns: _c,
            child: const SizedBox(
              width: 96,
              height: 96,
              child: CircularProgressIndicator(value: 0.75, strokeWidth: 3, color: Color(0xFF283A8F)),
            ),
          ),
          const Text('✋', style: TextStyle(fontSize: 38)),
        ],
      ),
    );
  }
}
