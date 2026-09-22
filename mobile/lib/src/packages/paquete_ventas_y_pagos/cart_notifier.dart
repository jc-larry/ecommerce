import 'package:flutter/foundation.dart';

/// [CU17] Estado compartido del carrito en la app móvil.
///
/// El carrito vive en una pestaña del `IndexedStack` de `StoreShell`, que se construye una sola
/// vez; sin este aviso no se enteraría de las prendas añadidas desde el detalle o el probador.
class CartNotifier {
  CartNotifier._();

  /// Se incrementa cada vez que el carrito cambia en el servidor; quien lo escucha recarga.
  static final ValueNotifier<int> changes = ValueNotifier<int>(0);

  /// Unidades en el carrito, para el contador de la barra inferior.
  static final ValueNotifier<int> itemsCount = ValueNotifier<int>(0);

  static void notifyChanged() => changes.value++;

  static void updateFrom(Map<String, dynamic>? cart) {
    itemsCount.value = (cart?['items_count'] as num?)?.toInt() ?? 0;
  }
}
