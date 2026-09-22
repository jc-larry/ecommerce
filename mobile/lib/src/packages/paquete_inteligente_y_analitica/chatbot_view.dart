import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../paquete_seguridad_usuarios/auth_service.dart';
import '../paquete_catalogo_y_tiendas/catalog_api.dart';
import '../paquete_catalogo_y_tiendas/product_detail_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU33] Asistente Virtual Inteligente y Consejero de Estilo (App Móvil).
/// Permite al cliente conversar en lenguaje natural con el bot de IA,
/// solicitar recomendaciones de outfits, consejos de combinación y productos sugeridos.
class ChatbotView extends StatefulWidget {
  const ChatbotView({super.key});

  @override
  State<ChatbotView> createState() => _ChatbotViewState();
}

class _ChatMessage {
  final String text;
  final bool isUser;
  final List<dynamic>? suggestedProducts;
  final List<String>? suggestedActions;
  final DateTime timestamp;

  _ChatMessage({
    required this.text,
    required this.isUser,
    this.suggestedProducts,
    this.suggestedActions,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

class _ChatbotViewState extends State<ChatbotView> {
  final TextEditingController _msgCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _isSending = false;
  String? _sessionToken;

  final List<String> _quickPrompts = [
    '¿Qué blusas elegantes tienen?',
    'Recomiéndame un outfit para fiesta',
    '¿Qué prendas de lino tienen?',
    '¿Cuáles son sus sucursales?',
    '¿Cómo funciona el envío a domicilio?',
  ];

  @override
  void initState() {
    super.initState();
    _messages.add(
      _ChatMessage(
        text: '¡Hola! 👋 Soy tu estilista y asistente inteligente de FashionStore 👗✨. ¿En qué prenda, ocasión o estilo estás pensando hoy?',
        isUser: false,
        suggestedActions: [
          'Ver vestidos',
          'Ver blusas',
          'Rastrear un paquete',
          'Sucursales y horarios',
        ],
      ),
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage(String text) async {
    final query = text.trim();
    if (query.isEmpty) return;

    _msgCtrl.clear();
    setState(() {
      _messages.add(_ChatMessage(text: query, isUser: true));
      _isSending = true;
    });
    _scrollToBottom();

    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/analytics/chatbot/message');
      final res = await http.post(
        url,
        headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          'Content-Type': 'application/json; charset=UTF-8',
        },
        body: jsonEncode({
          'message': query,
          'session_token': _sessionToken,
        }),
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        _sessionToken = data['session_token'];
        final reply = data['reply'] ?? 'He recibido tu consulta.';
        final products = data['suggested_products'] as List?;
        final actions = (data['suggested_actions'] as List?)?.map((e) => e.toString()).toList();

        setState(() {
          _messages.add(_ChatMessage(
            text: reply,
            isUser: false,
            suggestedProducts: products,
            suggestedActions: actions,
          ));
          _isSending = false;
        });
      } else {
        setState(() {
          _messages.add(_ChatMessage(
            text: 'Disculpa, ocurrió un inconveniente temporal (Código ${res.statusCode}). Por favor intenta con otra pregunta.',
            isUser: false,
          ));
          _isSending = false;
        });
      }
    } catch (e) {
      setState(() {
        _messages.add(_ChatMessage(
          text: 'No fue posible conectar con el servidor (${AuthService.apiBaseUrl}). Verifica que el backend esté activo en la misma red Wi-Fi.',
          isUser: false,
        ));
        _isSending = false;
      });
    }

    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F6F4),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: _ink,
        title: const Row(
          children: [
            CircleAvatar(
              radius: 16,
              backgroundColor: Color(0xFFF6E3DD),
              child: Icon(Icons.auto_awesome, size: 18, color: _brand),
            ),
            SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Estilista FashionStore', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink)),
                Text('Consejero IA en tiempo real', style: TextStyle(fontSize: 11, color: Colors.green, fontWeight: FontWeight.w500)),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // Chips de preguntas sugeridas
          if (_messages.length <= 2)
            SizedBox(
              height: 48,
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                scrollDirection: Axis.horizontal,
                itemCount: _quickPrompts.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) {
                  return ActionChip(
                    label: Text(_quickPrompts[i], style: const TextStyle(fontSize: 12, color: _ink)),
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFFECE6E2)),
                    onPressed: () => _sendMessage(_quickPrompts[i]),
                  );
                },
              ),
            ),

          // Lista de mensajes de chat
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final m = _messages[index];
                return _buildMessageBubble(m);
              },
            ),
          ),

          if (_isSending)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              alignment: Alignment.centerLeft,
              child: const Row(
                children: [
                  SizedBox(width: 14, height: 14, child: CircularProgressIndicator(color: _brand, strokeWidth: 2)),
                  SizedBox(width: 8),
                  Text('FashionStore IA está buscando las mejores prendas...', style: TextStyle(fontSize: 12, color: _muted, fontStyle: FontStyle.italic)),
                ],
              ),
            ),

          // Input de envío
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Color(0xFFECE6E2))),
            ),
            child: SafeArea(
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _msgCtrl,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: const InputDecoration(
                        hintText: 'Pregúntame sobre blusas, vestidos, envíos o tallas...',
                        hintStyle: TextStyle(fontSize: 13, color: _muted),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                      ),
                      onSubmitted: _sendMessage,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send_rounded, color: _brand),
                    onPressed: () => _sendMessage(_msgCtrl.text),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(_ChatMessage m) {
    return Align(
      alignment: m.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.88),
        child: Column(
          crossAxisAlignment: m.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: m.isUser ? _brand : Colors.white,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(m.isUser ? 16 : 4),
                  bottomRight: Radius.circular(m.isUser ? 4 : 16),
                ),
                border: m.isUser ? null : Border.all(color: const Color(0xFFECE6E2)),
                boxShadow: [
                  BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 6, offset: const Offset(0, 2)),
                ],
              ),
              child: Text(
                m.text,
                style: TextStyle(
                  color: m.isUser ? Colors.white : _ink,
                  fontSize: 13.5,
                  height: 1.35,
                ),
              ),
            ),

            // Acciones sugeridas
            if (m.suggestedActions != null && m.suggestedActions!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: m.suggestedActions!.map((act) {
                  return InkWell(
                    onTap: () => _sendMessage(act),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF6E3DD),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(act, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: _brand)),
                    ),
                  );
                }).toList(),
              ),
            ],

            // Prendas sugeridas por la IA con imágenes y acceso directo al producto
            if (m.suggestedProducts != null && m.suggestedProducts!.isNotEmpty) ...[
              const SizedBox(height: 10),
              SizedBox(
                height: 165,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: m.suggestedProducts!.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 10),
                  itemBuilder: (context, i) {
                    final p = m.suggestedProducts![i];
                    final imgUrl = p['image_url'] as String?;
                    final price = (p['price'] ?? p['base_price'] ?? 0);
                    return InkWell(
                      onTap: () {
                        if (p['id'] != null) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => ProductDetailView(productId: p['id'] as int),
                            ),
                          );
                        }
                      },
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        width: 130,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFFECE6E2)),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.03),
                              blurRadius: 6,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ClipRRect(
                              borderRadius: const BorderRadius.vertical(top: Radius.circular(14)),
                              child: SizedBox(
                                height: 95,
                                width: double.infinity,
                                child: imgUrl != null && imgUrl.isNotEmpty
                                    ? Image.network(
                                        CatalogApi.resolveImage(imgUrl),
                                        fit: BoxFit.cover,
                                        errorBuilder: (_, __, ___) => Container(
                                          color: const Color(0xFFF6E3DD),
                                          child: const Icon(Icons.broken_image_outlined, color: _muted, size: 28),
                                        ),
                                      )
                                    : Container(
                                        color: const Color(0xFFF6E3DD),
                                        child: const Icon(Icons.checkroom, color: _brand, size: 28),
                                      ),
                              ),
                            ),
                            Padding(
                              padding: const EdgeInsets.all(8),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    p['name'] ?? 'Prenda',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: _ink),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Bs. ${price is num ? price.toStringAsFixed(2) : price.toString()}',
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _brand),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
