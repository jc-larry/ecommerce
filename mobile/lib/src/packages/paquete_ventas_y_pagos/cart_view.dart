import 'package:flutter/material.dart';
import 'ventas_api.dart';
import 'cart_notifier.dart';
import 'paypal_checkout.dart';
import '../paquete_catalogo_y_tiendas/catalog_api.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';
import 'customer_orders_view.dart';
import '../paquete_envios_y_logistica/location_picker_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU17 / CU18 / CU20] Pantalla completa de Carrito Digital y Checkout Omnicanal Móvil.
class CartView extends StatefulWidget {
  const CartView({super.key});

  @override
  State<CartView> createState() => _CartViewState();
}

class _CartViewState extends State<CartView> {
  bool _loading = true;
  Map<String, dynamic>? _cart;
  final Set<int> _busyItems = {};
  int _loadSeq = 0;

  @override
  void initState() {
    super.initState();
    CartNotifier.changes.addListener(_onCartChanged);
    _loadCart();
  }

  @override
  void dispose() {
    CartNotifier.changes.removeListener(_onCartChanged);
    super.dispose();
  }

  void _onCartChanged() => _loadCart(silent: true);

  /// `silent` recarga sin reemplazar la lista por el spinner (evita parpadeos).
  Future<void> _loadCart({bool silent = false}) async {
    final seq = ++_loadSeq;
    if (!silent || _cart == null) setState(() => _loading = true);
    final c = await VentasApi.fetchCart();
    // Descarta respuestas viejas si llegó otra recarga mientras tanto.
    if (!mounted || seq != _loadSeq) return;
    setState(() {
      _cart = c;
      _loading = false;
    });
  }

  void _showMessage(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _updateQty(
      int itemId, int currentQty, int delta, int maxStock) async {
    if (_busyItems.contains(itemId)) return;
    final nextQty = currentQty + delta;
    if (nextQty > maxStock) {
      _showMessage('Stock máximo alcanzado ($maxStock unidades).');
      return;
    }
    if (nextQty <= 0) {
      await _removeItem(itemId);
      return;
    }

    setState(() => _busyItems.add(itemId));
    final res = await VentasApi.updateCartItem(itemId, nextQty);
    if (!mounted) return;
    setState(() {
      _busyItems.remove(itemId);
      if (res['ok'] == true) _cart = res['data'] as Map<String, dynamic>;
    });
    if (res['ok'] != true) {
      _showMessage(res['detail']?.toString() ?? 'Error al actualizar.');
    }
  }

  Future<void> _removeItem(int itemId) async {
    if (_busyItems.contains(itemId)) return;
    setState(() => _busyItems.add(itemId));
    final res = await VentasApi.removeCartItem(itemId);
    if (!mounted) return;
    setState(() {
      _busyItems.remove(itemId);
      if (res['ok'] == true) _cart = res['data'] as Map<String, dynamic>;
    });
    if (res['ok'] != true) {
      _showMessage(res['detail']?.toString() ?? 'No se pudo quitar la prenda.');
    }
  }

  Future<void> _clearCart() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Vaciar carrito'),
        content: const Text('¿Deseas quitar todas las prendas de tu carrito?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Vaciar', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (ok == true) {
      final res = await VentasApi.clearCart();
      if (!mounted) return;
      if (res['ok'] == true) {
        setState(() => _cart = res['data'] as Map<String, dynamic>);
      } else {
        _showMessage(
            res['detail']?.toString() ?? 'No se pudo vaciar el carrito.');
      }
    }
  }

  void _startCheckout() {
    if (_cart == null || (_cart!['items'] as List).isEmpty) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CheckoutSheet(
          cart: _cart!,
          onOrderCompleted: () {
            _loadCart();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = _cart != null ? (_cart!['items'] as List) : [];
    final subtotal =
        _cart != null ? (_cart!['subtotal'] as num).toDouble() : 0.0;
    final count = _cart != null ? (_cart!['items_count'] as int? ?? 0) : 0;

    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        title: const Text('Mi Carrito',
            style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
        backgroundColor: Colors.white,
        elevation: 0,
        actions: [
          if (items.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_sweep_outlined,
                  color: Colors.redAccent),
              tooltip: 'Vaciar carrito',
              onPressed: _clearCart,
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : items.isEmpty
              ? _emptyState()
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                              '$count ${count == 1 ? "prenda" : "prendas"} en total',
                              style: const TextStyle(
                                  color: _muted,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500)),
                          const Text('Envío a todo el país',
                              style: TextStyle(
                                  color: Colors.green,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (ctx, i) => _cartItemTile(items[i]),
                      ),
                    ),
                    _checkoutSummaryBar(subtotal),
                  ],
                ),
    );
  }

  Widget _emptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: _brand.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.shopping_bag_outlined,
                  size: 64, color: _brand),
            ),
            const SizedBox(height: 20),
            const Text(
              'Tu carrito está vacío',
              style: TextStyle(
                  fontSize: 18, fontWeight: FontWeight.bold, color: _ink),
            ),
            const SizedBox(height: 8),
            const Text(
              'Explora las últimas colecciones y añade las prendas que te encanten.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }

  Widget _cartItemTile(dynamic it) {
    final itemId = it['id'] as int;
    final name = it['product_name'] as String;
    final size = it['size'] as String;
    final color = it['color'] as String;
    final sku = it['sku'] as String;
    final price = (it['unit_price'] as num).toDouble();
    final itemSubtotal = (it['subtotal'] as num).toDouble();
    final qty = it['quantity'] as int;
    final maxStock = it['stock_available'] as int;
    final img = it['image_url'] as String?;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Imagen miniatura
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: SizedBox(
              width: 70,
              height: 70,
              child: img != null && img.isNotEmpty
                  ? Image.network(
                      CatalogApi.resolveImage(img),
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: const Color(0xFFEFE7E3),
                        child: const Icon(Icons.broken_image_outlined,
                            color: _muted),
                      ),
                    )
                  : Container(
                      color: const Color(0xFFEFE7E3),
                      child: const Icon(Icons.image_outlined, color: _muted),
                    ),
            ),
          ),
          const SizedBox(width: 12),
          // Info de prenda
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 14, color: _ink),
                ),
                const SizedBox(height: 2),
                Text(
                  '$size · $color · $sku',
                  style: const TextStyle(color: _muted, fontSize: 11),
                ),
                const SizedBox(height: 6),
                Text(
                  'Bs. ${price.toStringAsFixed(2)}',
                  style: const TextStyle(
                      color: _brand, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
          ),
          // Controles de cantidad
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _circleBtn(Icons.remove,
                      () => _updateQty(itemId, qty, -1, maxStock)),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: _busyItems.contains(itemId)
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: _brand))
                        : Text('$qty',
                            style: const TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 14)),
                  ),
                  _circleBtn(
                      Icons.add, () => _updateQty(itemId, qty, 1, maxStock)),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                'Bs. ${itemSubtotal.toStringAsFixed(2)}',
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 13, color: _ink),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _circleBtn(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: 28,
        height: 28,
        decoration: const BoxDecoration(
          color: Color(0xFFF6E3DD),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, size: 16, color: _brand),
      ),
    );
  }

  Widget _checkoutSummaryBar(double subtotal) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 16,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total a Pagar',
                    style: TextStyle(
                        fontSize: 15,
                        color: _muted,
                        fontWeight: FontWeight.w600)),
                Text(
                  'Bs. ${subtotal.toStringAsFixed(2)}',
                  style: const TextStyle(
                      fontSize: 22, fontWeight: FontWeight.bold, color: _brand),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: _startCheckout,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _brand,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16)),
                ),
                icon: const Icon(Icons.arrow_forward),
                label: const Text('Continuar al Checkout',
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// [CU18 / CU20] Pantalla de Checkout Polimórfico y Emisión de Factura Fiscal en Móvil.
class CheckoutSheet extends StatefulWidget {
  final Map<String, dynamic> cart;
  final VoidCallback onOrderCompleted;

  const CheckoutSheet({
    super.key,
    required this.cart,
    required this.onOrderCompleted,
  });

  @override
  State<CheckoutSheet> createState() => _CheckoutSheetState();
}

class _CheckoutSheetState extends State<CheckoutSheet> {
  bool _loading = false;
  List<dynamic> _branches = [];
  int? _selectedBranchId;

  // Entrega y Despacho (CU29, CU30, CU31)
  String _shippingMethod = 'DELIVERY'; // 'DELIVERY' | 'PICKUP'
  final _addressCtrl = TextEditingController();
  final _recipientNameCtrl = TextEditingController();
  final _recipientPhoneCtrl = TextEditingController();
  final _deliveryNotesCtrl = TextEditingController();
  DeliveryLocation? _deliveryLocation;
  // Última dirección sugerida por el mapa: solo se reemplaza si el cliente no la editó.
  String? _autoFilledAddress;
  // Ubicación automática por GPS al elegir delivery (el cliente la confirma o ajusta en el mapa).
  bool _autoLocating = false;
  GpsResult? _gpsFailure;
  List<dynamic> _zones = [];
  int? _selectedZoneId;
  double _shippingCost = 15.0; // Tarifa delivery por defecto

  // Cupón (CU13)
  final _couponCtrl = TextEditingController();
  double _discountAmount = 0.0;

  Future<void> _applyCoupon() async {
    final code = _couponCtrl.text.trim().toUpperCase();
    if (code.isEmpty || _blockedByPayPal()) return;
    final res = await CatalogApi.validateCoupon(code, _subtotal);
    if (!mounted) return;
    if (res['is_valid'] == true) {
      setState(() {
        _discountAmount = (res['discount_amount'] as num).toDouble();
        _error = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(
                '¡Cupón $code aplicado: -Bs. ${_discountAmount.toStringAsFixed(2)}!')),
      );
    } else {
      setState(() {
        _discountAmount = 0.0;
        _error = res['message'] ?? 'Cupón inválido o expirado.';
      });
    }
  }

  // Medio de pago (STI). Canal ONLINE: igual que la web, sin efectivo.
  String _paymentType = 'TARJETA'; // TARJETA, PAYPAL, QR
  String _cardBrand = 'VISA';
  final _cardHolderCtrl = TextEditingController();
  final _cardNumberCtrl = TextEditingController();
  final _cardExpiryCtrl = TextEditingController();
  final _cardCvvCtrl = TextEditingController();

  // PayPal: el cobro capturado se conserva para no cobrar dos veces si el checkout se reintenta.
  PayPalPaymentResult? _paypalResult;
  double? _paypalPaidBob;
  bool _paypalBusy = false;
  final _scrollCtrl = ScrollController();
  double _exchangeRate = PayPalCheckout.defaultExchangeRate;

  // Facturación fiscal IVA 13%
  String _docType = 'FACTURA'; // FACTURA, NOTA_ENTREGA
  final _nitCtrl = TextEditingController(text: '0');
  final _nameCtrl = TextEditingController();

  String? _error;
  Map<String, dynamic>? _successOrder;

  @override
  void initState() {
    super.initState();
    _loadBranches();
    _loadZones();
    _prefillUserData();
    if (_shippingMethod == 'DELIVERY') _autoLocate();
    PayPalCheckout.exchangeRate().then((r) {
      if (mounted) setState(() => _exchangeRate = r);
    });
  }

  Future<void> _prefillUserData() async {
    final u = await AuthService.getUser();
    if (u != null && mounted) {
      setState(() {
        final fullName =
            '${u['first_name'] ?? ''} ${u['last_name'] ?? ''}'.trim();
        if (_recipientNameCtrl.text.isEmpty && fullName.isNotEmpty) {
          _recipientNameCtrl.text = fullName;
        }
        if (_nameCtrl.text.isEmpty && fullName.isNotEmpty) {
          _nameCtrl.text = fullName;
        }
        if (_recipientPhoneCtrl.text.isEmpty && u['phone'] != null) {
          _recipientPhoneCtrl.text = u['phone'].toString();
        }
      });
    }
  }

  Future<void> _loadZones() async {
    final z = await VentasApi.fetchDeliveryZones();
    if (mounted) {
      setState(() {
        _zones = z;
        if (z.isNotEmpty) {
          final defaultZone = z.length > 1 ? z[1] : z[0];
          _selectedZoneId = defaultZone['id'] as int;
          _shippingCost = (defaultZone['base_rate'] as num).toDouble();
        }
      });
    }
  }

  @override
  void dispose() {
    _scrollCtrl.dispose();
    _couponCtrl.dispose();
    _nitCtrl.dispose();
    _nameCtrl.dispose();
    _addressCtrl.dispose();
    _recipientNameCtrl.dispose();
    _recipientPhoneCtrl.dispose();
    _deliveryNotesCtrl.dispose();
    _cardHolderCtrl.dispose();
    _cardNumberCtrl.dispose();
    _cardExpiryCtrl.dispose();
    _cardCvvCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadBranches() async {
    final b = await VentasApi.fetchBranches();
    if (mounted) {
      setState(() {
        _branches = b;
        if (b.isNotEmpty) {
          _selectedBranchId = b[0]['id'] as int;
        }
      });
    }
  }

  double get _subtotal => (widget.cart['subtotal'] as num).toDouble();
  double get _currentShippingCost =>
      _shippingMethod == 'DELIVERY' ? _shippingCost : 0.0;
  double get _total => (_subtotal - _discountAmount + _currentShippingCost)
      .clamp(0.0, double.infinity);
  double get _iva13 => _total * 0.13;
  double get _totalUsd => (_total / _exchangeRate * 100).roundToDouble() / 100;

  /// Muestra el error arriba del formulario y desplaza la vista hasta él (el botón de pago
  /// está al final: sin esto el cliente no ve por qué no pasó nada).
  void _showError(String msg) {
    setState(() {
      _error = msg;
      _loading = false;
    });
    if (_scrollCtrl.hasClients) {
      _scrollCtrl.animateTo(0, duration: const Duration(milliseconds: 350), curve: Curves.easeOut);
    }
  }

  /// Tras cobrar con PayPal el total queda fijo: cambiar envío o cupón lo descuadraría.
  bool _blockedByPayPal() {
    if (_paypalResult == null) return false;
    _showError('Ya pagaste Bs. ${_paypalPaidBob?.toStringAsFixed(2)} con PayPal. '
        'No puedes cambiar el envío ni el cupón; confirma tu pedido.');
    return true;
  }

  /// [CU18] Abre la ventana de PayPal y cobra el total actual (igual que el botón de la web).
  Future<bool> _payWithPayPal() async {
    if (_paypalResult != null) return true;
    if (_paypalBusy) return false;
    if (_total <= 0) {
      _showError('El total a pagar debe ser mayor a 0 Bs.');
      return false;
    }
    final amount = double.parse(_total.toStringAsFixed(2));
    setState(() {
      _paypalBusy = true;
      _error = null;
    });
    try {
      final result = await PayPalCheckout.pay(
        context,
        amountBob: amount,
        description: 'Compra Online FashionStore (${widget.cart['items_count'] ?? ''} prendas)',
      );
      if (!mounted) return false;
      setState(() => _paypalBusy = false);
      if (result == null) {
        _showError('Cancelaste el pago en PayPal. No se realizó ningún cobro.');
        return false;
      }
      setState(() {
        _paypalResult = result;
        _paypalPaidBob = amount;
      });
      return true;
    } on PayPalException catch (e) {
      if (!mounted) return false;
      setState(() => _paypalBusy = false);
      _showError(e.message);
      return false;
    }
  }

  Future<void> _processCheckout() async {
    if (_selectedBranchId == null) {
      _showError('Selecciona una sucursal de retiro o despacho.');
      return;
    }

    if (_shippingMethod == 'DELIVERY') {
      if (_deliveryLocation == null) {
        _showError('Marca en el mapa el punto donde recibirás tu pedido.');
        return;
      }
      if (_recipientPhoneCtrl.text.trim().isEmpty) {
        _showError('Por favor ingresa un teléfono de contacto para el repartidor.');
        return;
      }
    }

    // Validación de tarjeta (mismas reglas que la web).
    final cleanCard = _cardNumberCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (_paymentType == 'TARJETA') {
      if (_cardHolderCtrl.text.trim().length < 3) {
        _showError('Ingresa el nombre del titular de la tarjeta.');
        return;
      }
      if (cleanCard.length < 13) {
        _showError('Ingresa un número de tarjeta válido (mínimo 13 dígitos).');
        return;
      }
      if (!RegExp(r'^(0[1-9]|1[0-2])/\d{2}$').hasMatch(_cardExpiryCtrl.text.trim())) {
        _showError('Ingresa la fecha de vencimiento en formato MM/AA.');
        return;
      }
      if (_cardCvvCtrl.text.trim().length < 3) {
        _showError('Ingresa el código CVV (3 o 4 dígitos).');
        return;
      }
    }

    // [CU18] PayPal: primero se cobra en la pasarela; el backend verifica la orden antes de facturar.
    if (_paymentType == 'PAYPAL') {
      if (!await _payWithPayPal()) return;
      if (!mounted) return;
      if ((_total - (_paypalPaidBob ?? 0)).abs() > 0.01) {
        _showError('El total cambió después de pagar con PayPal. Vuelve a las opciones con las que pagaste.');
        return;
      }
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    final payload = <String, dynamic>{
      'channel': 'ONLINE',
      'branch_id': _selectedBranchId,
      'payment_type': _paymentType,
      'doc_type': _docType,
      'customer_nit': _nitCtrl.text.trim().isEmpty ? '0' : _nitCtrl.text.trim(),
      'customer_name': _nameCtrl.text.trim().isEmpty
          ? (_recipientNameCtrl.text.trim().isEmpty
              ? 'Consumidor Final'
              : _recipientNameCtrl.text.trim())
          : _nameCtrl.text.trim(),
      'shipping_method': _shippingMethod,
      'delivery_address':
          _shippingMethod == 'DELIVERY' ? _deliveryAddressText() : null,
      'recipient_name': _recipientNameCtrl.text.trim().isNotEmpty
          ? _recipientNameCtrl.text.trim()
          : null,
      'recipient_phone': _recipientPhoneCtrl.text.trim().isNotEmpty
          ? _recipientPhoneCtrl.text.trim()
          : null,
      'delivery_notes': _deliveryNotesCtrl.text.trim().isNotEmpty
          ? _deliveryNotesCtrl.text.trim()
          : null,
      'zone_id': _shippingMethod == 'DELIVERY' ? _selectedZoneId : null,
      if (_shippingMethod == 'DELIVERY' && _deliveryLocation != null) ...{
        'delivery_latitude': _deliveryLocation!.point.latitude,
        'delivery_longitude': _deliveryLocation!.point.longitude,
      },
      'shipping_cost': _currentShippingCost,
      if (_couponCtrl.text.trim().isNotEmpty)
        'coupon_code': _couponCtrl.text.trim().toUpperCase(),
    };

    if (_paymentType == 'TARJETA') {
      payload['card_payment'] = {
        'card_brand': _cardBrand,
        'card_last4': cleanCard.substring(cleanCard.length - 4),
        'gateway_reference':
            'AUTH-$_cardBrand-${DateTime.now().millisecondsSinceEpoch.toRadixString(36).toUpperCase()}',
      };
    } else if (_paymentType == 'PAYPAL') {
      final pp = _paypalResult!;
      payload['paypal_payment'] = {
        'paypal_order_id': pp.orderId,
        if (pp.payerId != null) 'paypal_payer_id': pp.payerId,
        if (pp.payerEmail != null) 'paypal_payer_email': pp.payerEmail,
      };
    } else if (_paymentType == 'QR') {
      payload['qr_payment'] = {
        'qr_reference':
            'QR-MOB-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}',
      };
    }

    final res = await VentasApi.checkout(payload);
    if (!mounted) return;

    if (res['ok']) {
      setState(() {
        _loading = false;
        _successOrder = res['data'];
      });
      widget.onOrderCompleted();
    } else {
      _showError(res['detail']?.toString() ?? 'Error al procesar el pago.');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_successOrder != null) {
      return _buildSuccessView();
    }

    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        title: const Text('Checkout & Pago',
            style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: _ink,
      ),
      body: SingleChildScrollView(
        controller: _scrollCtrl,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_error != null)
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.red.shade200)),
                child: Text(_error!,
                    style: TextStyle(color: Colors.red.shade800, fontSize: 13)),
              ),

            // 1. Método de Entrega (CU29, CU31)
            _sectionHeader(
                '1. Método de Entrega', Icons.local_shipping_outlined),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: () {
                      if (_shippingMethod == 'DELIVERY' || _blockedByPayPal()) return;
                      setState(() => _shippingMethod = 'DELIVERY');
                      _autoLocate();
                    },
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          vertical: 12, horizontal: 8),
                      decoration: BoxDecoration(
                        color: _shippingMethod == 'DELIVERY'
                            ? const Color(0xFFF6E3DD)
                            : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _shippingMethod == 'DELIVERY'
                              ? _brand
                              : const Color(0xFFE5DFDC),
                          width: _shippingMethod == 'DELIVERY' ? 2 : 1,
                        ),
                      ),
                      child: Column(
                        children: [
                          Icon(Icons.two_wheeler,
                              color: _shippingMethod == 'DELIVERY'
                                  ? _brand
                                  : _muted),
                          const SizedBox(height: 4),
                          Text(
                            'Envío a Domicilio',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: _shippingMethod == 'DELIVERY'
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                              fontSize: 12,
                              color:
                                  _shippingMethod == 'DELIVERY' ? _brand : _ink,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Delivery con Repartidor',
                            style: TextStyle(
                                fontSize: 10,
                                color: _shippingMethod == 'DELIVERY'
                                    ? _brand
                                    : _muted),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: InkWell(
                    onTap: () {
                      if (_shippingMethod == 'PICKUP' || _blockedByPayPal()) return;
                      setState(() => _shippingMethod = 'PICKUP');
                    },
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          vertical: 12, horizontal: 8),
                      decoration: BoxDecoration(
                        color: _shippingMethod == 'PICKUP'
                            ? const Color(0xFFF6E3DD)
                            : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _shippingMethod == 'PICKUP'
                              ? _brand
                              : const Color(0xFFE5DFDC),
                          width: _shippingMethod == 'PICKUP' ? 2 : 1,
                        ),
                      ),
                      child: Column(
                        children: [
                          Icon(Icons.storefront_outlined,
                              color: _shippingMethod == 'PICKUP'
                                  ? _brand
                                  : _muted),
                          const SizedBox(height: 4),
                          Text(
                            'Retiro en Tienda',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: _shippingMethod == 'PICKUP'
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                              fontSize: 12,
                              color:
                                  _shippingMethod == 'PICKUP' ? _brand : _ink,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Sin costo adicional',
                            style: TextStyle(
                                fontSize: 10,
                                color: _shippingMethod == 'PICKUP'
                                    ? _brand
                                    : _muted),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Formulario de dirección y datos de entrega
            if (_shippingMethod == 'DELIVERY') ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE5DFDC)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_zones.isNotEmpty) ...[
                      const Text('Zona de Entrega (Tarifa)',
                          style: TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                              color: _ink)),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFE5DFDC)),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<int>(
                            isExpanded: true,
                            value: _selectedZoneId,
                            items: _zones.map((z) {
                              return DropdownMenuItem<int>(
                                value: z['id'] as int,
                                child: Text(
                                    '${z['name']} (+Bs. ${(z['base_rate'] as num).toDouble().toStringAsFixed(2)})'),
                              );
                            }).toList(),
                            onChanged: (v) {
                              if (v != null && v != _selectedZoneId && !_blockedByPayPal()) {
                                final matched = _zones.firstWhere(
                                    (z) => z['id'] == v,
                                    orElse: () => null);
                                setState(() {
                                  _selectedZoneId = v;
                                  if (matched != null) {
                                    _shippingCost =
                                        (matched['base_rate'] as num)
                                            .toDouble();
                                  }
                                });
                              }
                            },
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],
                    _deliveryMapCard(),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _addressCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Dirección o referencia (opcional)',
                        hintText: 'Se completa desde el mapa; puedes corregirla',
                        prefixIcon:
                            Icon(Icons.location_on_outlined, color: _brand),
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _recipientNameCtrl,
                            decoration: const InputDecoration(
                              labelText: 'Recibe *',
                              hintText: 'Nombre y apellido',
                              prefixIcon:
                                  Icon(Icons.person_outline, color: _brand),
                              isDense: true,
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: _recipientPhoneCtrl,
                            keyboardType: TextInputType.phone,
                            decoration: const InputDecoration(
                              labelText: 'Teléfono *',
                              hintText: 'Celular de contacto',
                              prefixIcon:
                                  Icon(Icons.phone_outlined, color: _brand),
                              isDense: true,
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _deliveryNotesCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Notas para el Repartidor (opcional)',
                        hintText:
                            'Ej: Portón café, timbrar dos veces, dejar en portería',
                        prefixIcon: Icon(Icons.notes_outlined, color: _muted),
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              // Sucursal de preparación del pedido
              _sectionHeader('Sucursal de Preparación', Icons.store_outlined),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE5DFDC))),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<int>(
                    isExpanded: true,
                    value: _selectedBranchId,
                    items: _branches.map((b) {
                      return DropdownMenuItem<int>(
                        value: b['id'] as int,
                        child:
                            Text('${b['name']} (${b['city'] ?? "Santa Cruz"})'),
                      );
                    }).toList(),
                    onChanged: (v) => setState(() => _selectedBranchId = v),
                  ),
                ),
              ),
            ] else ...[
              // Retiro en Tienda: selección de sucursal de recojo
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE5DFDC))),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<int>(
                    isExpanded: true,
                    value: _selectedBranchId,
                    items: _branches.map((b) {
                      return DropdownMenuItem<int>(
                        value: b['id'] as int,
                        child:
                            Text('${b['name']} (${b['city'] ?? "Santa Cruz"})'),
                      );
                    }).toList(),
                    onChanged: (v) => setState(() => _selectedBranchId = v),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 20),

            // 2. Método de Pago Polimórfico (CU18)
            _sectionHeader('2. Medio de Pago', Icons.payment_outlined),
            Row(
              children: [
                _paymentTile('TARJETA', 'Tarjeta', Icons.credit_card),
                const SizedBox(width: 8),
                _paymentTile('PAYPAL', 'PayPal (USD)',
                    Icons.account_balance_wallet_outlined),
                const SizedBox(width: 8),
                _paymentTile('QR', 'QR Simple', Icons.qr_code),
              ],
            ),
            const SizedBox(height: 12),
            _paymentFields(),
            const SizedBox(height: 20),

            // 3. Comprobante Fiscal (CU20)
            _sectionHeader(
                '3. Comprobante Fiscal', Icons.receipt_long_outlined),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE5DFDC))),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: ChoiceChip(
                          label: const Text('Factura (IVA 13%)'),
                          selected: _docType == 'FACTURA',
                          selectedColor: const Color(0xFFF6E3DD),
                          onSelected: (s) =>
                              setState(() => _docType = 'FACTURA'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: ChoiceChip(
                          label: const Text('Nota de Entrega'),
                          selected: _docType == 'NOTA_ENTREGA',
                          selectedColor: const Color(0xFFF6E3DD),
                          onSelected: (s) =>
                              setState(() => _docType = 'NOTA_ENTREGA'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _nitCtrl,
                    decoration: const InputDecoration(
                      labelText: 'NIT o C.I.',
                      isDense: true,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Razón Social / Nombre',
                      isDense: true,
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // 4. Cupón de Descuento (CU13)
            _sectionHeader('4. Cupón de Descuento', Icons.percent_outlined),
            TextField(
              controller: _couponCtrl,
              textCapitalization: TextCapitalization.characters,
              onSubmitted: (_) => _applyCoupon(),
              decoration: InputDecoration(
                hintText: 'Ej: BIENVENIDA10',
                filled: true,
                fillColor: Colors.white,
                suffixIcon: IconButton(
                  icon: const Icon(Icons.check_circle, color: _brand),
                  onPressed: _applyCoupon,
                  tooltip: 'Aplicar cupón',
                ),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFE5DFDC))),
              ),
            ),
            const SizedBox(height: 24),

            // 5. Resumen Financiero
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFFE5DFDC))),
              child: Column(
                children: [
                  _summaryRow('Subtotal de prendas',
                      'Bs. ${_subtotal.toStringAsFixed(2)}'),
                  if (_discountAmount > 0)
                    _summaryRow('Descuento cupón',
                        '- Bs. ${_discountAmount.toStringAsFixed(2)}',
                        color: Colors.green),
                  if (_shippingMethod == 'DELIVERY')
                    _summaryRow('Costo de envío (Delivery)',
                        'Bs. ${_shippingCost.toStringAsFixed(2)}',
                        color: _brand)
                  else
                    _summaryRow('Retiro en sucursal', 'GRATIS',
                        color: Colors.green),
                  if (_docType == 'FACTURA')
                    _summaryRow('IVA Débito Fiscal (13%)',
                        'Bs. ${_iva13.toStringAsFixed(2)}',
                        isMuted: true),
                  const Divider(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('TOTAL GENERAL',
                          style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                              color: _ink)),
                      Text('Bs. ${_total.toStringAsFixed(2)}',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 20,
                              color: _brand)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Botón Confirmar Compra
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _loading || _paypalBusy ? null : _processCheckout,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _brand,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16)),
                ),
                icon: _loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Icon(Icons.check_circle_outline),
                label: Text(
                  _loading
                      ? 'Procesando...'
                      : _paymentType == 'PAYPAL' && _paypalResult == null
                          ? 'Pagar con PayPal (\$${_totalUsd.toStringAsFixed(2)} USD)'
                          : 'Confirmar y Pagar (Bs. ${_total.toStringAsFixed(2)})',
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Texto de dirección que se envía: lo escrito por el cliente, o la dirección sugerida
  /// por el mapa, o las coordenadas (el repartidor se guía por el punto del mapa).
  String _deliveryAddressText() {
    final typed = _addressCtrl.text.trim();
    if (typed.isNotEmpty) return typed;
    final loc = _deliveryLocation;
    if (loc?.address != null) return loc!.address!;
    if (loc != null) {
      return 'Punto en el mapa (${loc.point.latitude.toStringAsFixed(6)}, ${loc.point.longitude.toStringAsFixed(6)})';
    }
    return '';
  }

  /// Aplica un punto elegido (GPS o mapa) y rellena la dirección si el cliente no la editó.
  void _applyLocation(DeliveryLocation loc) {
    _deliveryLocation = loc;
    _gpsFailure = null;
    final current = _addressCtrl.text.trim();
    final suggested = loc.address;
    if (current.isEmpty || current == _autoFilledAddress) {
      _addressCtrl.text = suggested ?? '';
      _autoFilledAddress = suggested;
    }
    if (_error != null && _error!.contains('mapa')) _error = null;
  }

  /// [CU29] Al elegir delivery se ubica al cliente con el GPS y se muestra el punto en el
  /// mapa del checkout, sin obligarlo a escribir una dirección que quizá no conoce.
  Future<void> _autoLocate() async {
    if (_deliveryLocation != null || _autoLocating) return;
    setState(() {
      _autoLocating = true;
      _gpsFailure = null;
    });
    final r = await locateDevice();
    if (!mounted) return;
    if (r.point == null) {
      setState(() {
        _autoLocating = false;
        _gpsFailure = r;
      });
      return;
    }
    final address = await reverseGeocode(r.point!);
    if (!mounted) return;
    setState(() {
      _autoLocating = false;
      // Si mientras tanto el cliente marcó un punto a mano, se respeta el suyo.
      if (_deliveryLocation == null) {
        _applyLocation(DeliveryLocation(r.point!, address));
      }
    });
  }

  Future<void> _pickLocation() async {
    final picked = await Navigator.push<DeliveryLocation>(
      context,
      MaterialPageRoute(
          builder: (_) => LocationPickerView(initial: _deliveryLocation)),
    );
    if (picked == null || !mounted) return;
    setState(() => _applyLocation(picked));
  }

  Widget _deliveryMapCard() {
    final loc = _deliveryLocation;
    final failure = _gpsFailure;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Punto de entrega *',
            style: TextStyle(
                fontWeight: FontWeight.w600, fontSize: 13, color: _ink)),
        const SizedBox(height: 6),
        // Todo el mapa es tocable: abre el mapa completo para ajustar el punto.
        GestureDetector(
          onTap: _pickLocation,
          child: Stack(
            children: [
              DeliveryPointPreview(
                point: loc?.point ?? defaultDeliveryCenter,
                showPin: loc != null,
                height: 170,
              ),
              if (loc == null)
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.55),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: _autoLocating
                        ? const Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              CircularProgressIndicator(color: _brand),
                              SizedBox(height: 8),
                              Text('Buscando tu ubicación…',
                                  style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      color: _ink)),
                            ],
                          )
                        : const Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.touch_app_outlined,
                                  color: _brand, size: 32),
                              SizedBox(height: 4),
                              Text('Toca para marcar tu ubicación',
                                  style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: _ink)),
                            ],
                          ),
                  ),
                ),
              if (loc != null)
                Positioned(
                  right: 8,
                  bottom: 8,
                  child: ElevatedButton.icon(
                    onPressed: _pickLocation,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: _brand,
                      elevation: 2,
                      visualDensity: VisualDensity.compact,
                    ),
                    icon: const Icon(Icons.edit_location_alt_outlined,
                        size: 18),
                    label: const Text('Ajustar punto'),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 6),
        if (loc != null) ...[
          if (loc.address != null)
            Text(loc.address!,
                style: const TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w600, color: _ink)),
          const Text(
            '¿El pin no está en tu puerta? Toca "Ajustar punto" y mueve el mapa.',
            style: TextStyle(fontSize: 12, color: _muted),
          ),
        ] else if (failure != null)
          Row(
            children: [
              const Icon(Icons.gps_off, size: 16, color: Color(0xFFB26A00)),
              const SizedBox(width: 6),
              Expanded(
                child: Text('${failure.error} Marca el punto en el mapa.',
                    style: const TextStyle(fontSize: 12, color: _ink)),
              ),
              TextButton(
                onPressed: () async {
                  if (!failure.needsSettings) {
                    _autoLocate();
                    return;
                  }
                  // Ajustes vuelve al instante: el cliente reintenta al regresar.
                  await openLocationSettingsFor(failure);
                  if (mounted) {
                    setState(() => _gpsFailure = const GpsResult.fail(
                        'Al activar la ubicación toca Reintentar.'));
                  }
                },
                child: Text(
                    failure.needsSettings ? 'Activar GPS' : 'Reintentar'),
              ),
            ],
          ),
      ],
    );
  }

  Widget _sectionHeader(String title, IconData icon) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: _brand),
          const SizedBox(width: 8),
          Text(title,
              style: const TextStyle(
                  fontWeight: FontWeight.bold, fontSize: 14, color: _ink)),
        ],
      ),
    );
  }

  Widget _paymentTile(String type, String label, IconData icon) {
    final sel = _paymentType == type;
    return Expanded(
      child: InkWell(
        onTap: () {
          if (_paypalResult != null && type != 'PAYPAL') {
            _showError('Ya pagaste con PayPal; confirma la compra para registrar tu pedido.');
            return;
          }
          setState(() => _paymentType = type);
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: sel ? const Color(0xFFF6E3DD) : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: sel ? _brand : const Color(0xFFE5DFDC),
                width: sel ? 2 : 1),
          ),
          child: Column(
            children: [
              Icon(icon, color: sel ? _brand : _muted),
              const SizedBox(height: 4),
              Text(label,
                  style: TextStyle(
                      fontWeight: sel ? FontWeight.bold : FontWeight.normal,
                      fontSize: 12,
                      color: sel ? _brand : _ink)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _paymentFields() {
    if (_paymentType == 'TARJETA') {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE5DFDC))),
        child: Column(
          children: [
            DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                isExpanded: true,
                value: _cardBrand,
                items: const [
                  DropdownMenuItem(value: 'VISA', child: Text('VISA')),
                  DropdownMenuItem(
                      value: 'MASTERCARD', child: Text('Mastercard')),
                  DropdownMenuItem(
                      value: 'AMEX', child: Text('American Express')),
                ],
                onChanged: (v) => setState(() => _cardBrand = v ?? 'VISA'),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _cardHolderCtrl,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                  labelText: 'Titular de la tarjeta',
                  isDense: true,
                  border: OutlineInputBorder()),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _cardNumberCtrl,
              keyboardType: TextInputType.number,
              maxLength: 19,
              decoration: const InputDecoration(
                labelText: 'Número de tarjeta',
                counterText: '',
                isDense: true,
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _cardExpiryCtrl,
                    keyboardType: TextInputType.datetime,
                    maxLength: 5,
                    decoration: const InputDecoration(
                        labelText: 'Vence (MM/AA)',
                        counterText: '',
                        isDense: true,
                        border: OutlineInputBorder()),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _cardCvvCtrl,
                    keyboardType: TextInputType.number,
                    obscureText: true,
                    maxLength: 4,
                    decoration: const InputDecoration(
                        labelText: 'CVV',
                        counterText: '',
                        isDense: true,
                        border: OutlineInputBorder()),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    }
    if (_paymentType == 'PAYPAL') {
      final paid = _paypalResult;
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: paid != null ? Colors.green.shade50 : Colors.blue.shade50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color:
                  paid != null ? Colors.green.shade300 : Colors.blue.shade200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Total en divisa: \$${_totalUsd.toStringAsFixed(2)} USD (T.C. ${_exchangeRate.toStringAsFixed(2)} Bs/\$)',
              style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
            ),
            const SizedBox(height: 6),
            Text(
              paid != null
                  ? 'Pago autorizado por PayPal${paid.simulated ? ' (simulación)' : ''}. Ref: ${paid.gatewayReference}'
                  : 'Toca el botón, inicia sesión en PayPal y completa la compra: tu pedido quedará pagado al instante.',
              style: TextStyle(
                  fontSize: 12,
                  color: paid != null
                      ? Colors.green.shade800
                      : Colors.blue.shade900),
            ),
            if (paid == null) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: _paypalBusy || _loading ? null : _processCheckout,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFFFC439),
                    foregroundColor: const Color(0xFF003087),
                    disabledBackgroundColor: const Color(0xFFFFE08A),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                  ),
                  icon: _paypalBusy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF003087)))
                      : const Icon(Icons.account_balance_wallet_outlined),
                  label: Text(
                    _paypalBusy ? 'Abriendo PayPal…' : 'Pagar con PayPal (\$${_totalUsd.toStringAsFixed(2)} USD)',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ],
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
          color: Colors.teal.shade50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.teal.shade200)),
      child: const Row(
        children: [
          Icon(Icons.qr_code_scanner, color: Colors.teal, size: 28),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Se generará un código QR interoperable avalado por la red bancaria boliviana.',
              style: TextStyle(color: Colors.teal, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value,
      {Color? color, bool isMuted = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: TextStyle(color: isMuted ? _muted : _ink, fontSize: 13)),
          Text(value,
              style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: color ?? _ink,
                  fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildSuccessView() {
    final ord = _successOrder!;
    final numOrder = ord['order_number'] as String? ?? 'ORD-${ord['id']}';
    final inv = ord['invoice'] as Map<String, dynamic>?;
    final payments = (ord['payments'] as List?) ?? const [];

    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: const BoxDecoration(
                      color: Colors.green, shape: BoxShape.circle),
                  child: const Icon(Icons.check, size: 54, color: Colors.white),
                ),
                const SizedBox(height: 20),
                const Text('¡Compra Exitosa!',
                    style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: _ink)),
                const SizedBox(height: 6),
                Text('Orden $numOrder confirmada.',
                    style: const TextStyle(color: _muted, fontSize: 14)),
                const SizedBox(height: 20),

                // Tarjeta de recibo
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFE5DFDC))),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Comprobante',
                              style: TextStyle(color: _muted, fontSize: 13)),
                          Text(
                              inv != null
                                  ? (inv['doc_type'] ?? 'FACTURA')
                                  : 'RECIBO',
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      if (inv != null && inv['control_code'] != null) ...[
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Código Control',
                                style: TextStyle(color: _muted, fontSize: 13)),
                            Text(inv['control_code'],
                                style: const TextStyle(
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12)),
                          ],
                        ),
                      ],
                      if (payments.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Pago',
                                style: TextStyle(color: _muted, fontSize: 13)),
                            Flexible(
                              child: Text(
                                (payments.first['gateway_reference'] ??
                                        payments.first['payment_type'] ??
                                        '')
                                    .toString(),
                                textAlign: TextAlign.end,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    fontFamily: 'monospace', fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ],
                      if (ord['tracking_number'] != null) ...[
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Guía de Despacho',
                                style: TextStyle(color: _muted, fontSize: 13)),
                            Text(ord['tracking_number'],
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: _brand)),
                          ],
                        ),
                      ],
                      if (ord['delivery_address'] != null) ...[
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Destino Entrega',
                                style: TextStyle(color: _muted, fontSize: 13)),
                            Flexible(
                              child: Text(
                                ord['delivery_address'],
                                textAlign: TextAlign.end,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ],
                      const Divider(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('TOTAL PAGADO',
                              style: TextStyle(fontWeight: FontWeight.bold)),
                          Text(
                              'Bs. ${(ord['total_amount'] as num).toDouble().toStringAsFixed(2)}',
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: _brand,
                                  fontSize: 16)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const CustomerOrdersView()));
                    },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: _brand,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14))),
                    child: const Text('Ver Mis Compras (CU24)'),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Volver a la Tienda',
                      style: TextStyle(color: _muted)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
