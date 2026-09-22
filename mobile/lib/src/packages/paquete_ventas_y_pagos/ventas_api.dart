import 'dart:convert';
import 'package:http/http.dart' as http;
import '../paquete_seguridad_usuarios/auth_service.dart';
import 'cart_notifier.dart';

/// [CU17 / CU18 / CU20 / CU24] Cliente HTTP de Ventas y Pagos para la app móvil:
/// Carrito, checkout omnicanal polimórfico, facturación fiscal IVA 13% e historial de compras.
class VentasApi {
  static const Duration _timeout = Duration(seconds: 15);

  static Future<Map<String, String>> _headers({bool json = true}) async {
    final token = await AuthService.getToken();
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Decodifica en UTF-8: FastAPI no declara charset y `r.body` rompería tildes y eñes.
  static dynamic _decode(http.Response r) => jsonDecode(utf8.decode(r.bodyBytes));

  /// Mensaje de error apto para el cliente a partir de la respuesta del backend.
  static String _errorDetail(http.Response r, String fallback) {
    if (r.statusCode == 401 || r.statusCode == 403) {
      return 'Inicia sesión para usar tu carrito.';
    }
    try {
      final d = (_decode(r) as Map)['detail'];
      if (d is String && d.isNotEmpty) return d;
    } catch (_) {}
    return fallback;
  }

  /// Respuesta exitosa de un endpoint que devuelve el carrito: sincroniza contador y vistas.
  static Map<String, dynamic> _cartChanged(http.Response r) {
    final cart = _decode(r) as Map<String, dynamic>;
    CartNotifier.updateFrom(cart);
    CartNotifier.notifyChanged();
    return {'ok': true, 'data': cart};
  }

  /// [CU17] Obtener el carrito digital del usuario autenticado.
  static Future<Map<String, dynamic>?> fetchCart() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/sales/cart'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode == 200) {
        final cart = _decode(r) as Map<String, dynamic>;
        CartNotifier.updateFrom(cart);
        return cart;
      }
      if (r.statusCode == 401 || r.statusCode == 403) CartNotifier.updateFrom(null);
      return null;
    } catch (_) {
      return null;
    }
  }

  /// [CU17] Añadir prenda al carrito con control estricto de existencias físicas.
  static Future<Map<String, dynamic>> addToCart(int variantId, int quantity) async {
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/sales/cart/items'),
            headers: await _headers(),
            body: jsonEncode({'variant_id': variantId, 'quantity': quantity}),
          )
          .timeout(_timeout);
      if (r.statusCode == 200) return _cartChanged(r);
      return {'ok': false, 'detail': _errorDetail(r, 'No se pudo agregar la prenda.')};
    } catch (_) {
      return {'ok': false, 'detail': 'Sin conexión con el servidor. Intenta de nuevo.'};
    }
  }

  /// [CU17] Actualizar cantidad de un ítem en el carrito.
  static Future<Map<String, dynamic>> updateCartItem(int itemId, int quantity) async {
    try {
      final r = await http
          .put(
            Uri.parse('${AuthService.apiBaseUrl}/sales/cart/items/$itemId'),
            headers: await _headers(),
            body: jsonEncode({'quantity': quantity}),
          )
          .timeout(_timeout);
      if (r.statusCode == 200) return _cartChanged(r);
      return {'ok': false, 'detail': _errorDetail(r, 'Error al modificar cantidad.')};
    } catch (_) {
      return {'ok': false, 'detail': 'Sin conexión con el servidor. Intenta de nuevo.'};
    }
  }

  /// [CU17] Eliminar un ítem del carrito.
  static Future<Map<String, dynamic>> removeCartItem(int itemId) async {
    try {
      final r = await http
          .delete(
            Uri.parse('${AuthService.apiBaseUrl}/sales/cart/items/$itemId'),
            headers: await _headers(),
          )
          .timeout(_timeout);
      if (r.statusCode == 200) return _cartChanged(r);
      return {'ok': false, 'detail': _errorDetail(r, 'No se pudo quitar la prenda.')};
    } catch (_) {
      return {'ok': false, 'detail': 'Sin conexión con el servidor. Intenta de nuevo.'};
    }
  }

  /// [CU17] Vaciar completamente el carrito de compras.
  static Future<Map<String, dynamic>> clearCart() async {
    try {
      final r = await http
          .delete(
            Uri.parse('${AuthService.apiBaseUrl}/sales/cart/clear'),
            headers: await _headers(),
          )
          .timeout(_timeout);
      if (r.statusCode == 200) return _cartChanged(r);
      return {'ok': false, 'detail': _errorDetail(r, 'No se pudo vaciar el carrito.')};
    } catch (_) {
      return {'ok': false, 'detail': 'Sin conexión con el servidor. Intenta de nuevo.'};
    }
  }

  /// [CU18 / CU20] Procesar compra omnicanal con medio de pago polimórfico y comprobante fiscal.
  /// Tolera la verificación con PayPal (lado servidor), por eso el plazo es mayor.
  static Future<Map<String, dynamic>> checkout(Map<String, dynamic> payload) async {
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/sales/checkout'),
            headers: await _headers(),
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 40));
      if (r.statusCode == 201) {
        // El backend vacía el carrito ONLINE al confirmar la compra.
        CartNotifier.updateFrom(null);
        CartNotifier.notifyChanged();
        return {'ok': true, 'data': _decode(r)};
      }
      return {'ok': false, 'detail': _errorDetail(r, 'No se pudo completar la compra.')};
    } catch (_) {
      return {
        'ok': false,
        'detail': 'No se recibió respuesta del servidor. Revisa "Mis compras" antes de reintentar.',
      };
    }
  }

  /// [CU24] Historial de compras y pedidos del cliente.
  static Future<List<dynamic>> fetchMyOrders() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/sales/orders/my-orders'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode == 200) {
        return jsonDecode(utf8.decode(r.bodyBytes)) as List<dynamic>;
      }
    } catch (_) {}
    return [];
  }

  /// [CU22 / CU24] Devoluciones y cambios registrados sobre las compras del cliente.
  static Future<List<dynamic>> fetchMyReturns() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/sales/returns/my'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode == 200) {
        return jsonDecode(utf8.decode(r.bodyBytes)) as List<dynamic>;
      }
    } catch (_) {}
    return [];
  }

  /// [CU24] Detalle de una compra específica con comprobante fiscal.
  static Future<Map<String, dynamic>?> fetchOrder(int id) async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/sales/orders/$id'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode == 200) {
      return jsonDecode(r.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Obtener sucursales físicas disponibles para despacho/retiro.
  static Future<List<dynamic>> fetchBranches() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/branches'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode == 200) {
      return jsonDecode(r.body) as List<dynamic>;
    }
    return [];
  }

  /// [CU31] Obtener zonas de entrega y tarifas de flete para delivery.
  static Future<List<dynamic>> fetchDeliveryZones() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/logistics/zones?active_only=true'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode == 200) {
        return jsonDecode(utf8.decode(r.bodyBytes)) as List<dynamic>;
      }
    } catch (_) {}
    return [];
  }
}
