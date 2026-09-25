import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// [CU01-CU04] Servicio de autenticación para la app móvil.
/// Consume la API REST de FastAPI del paquete `paquete_seguridad_usuarios`.
class AuthService {
  // === Configuración del backend ===================================================
  // Prioridad: 1) API_BASE_URL (URL completa)  2) API_HOST + API_PORT.
  //
  // DESPLIEGUE (producción): pasar la URL pública completa, p. ej.
  //   flutter run  --dart-define=API_BASE_URL=https://fashionstore-api.tudominio.com/api/v1
  //   flutter build apk --dart-define=API_BASE_URL=https://fashionstore-api.tudominio.com/api/v1
  //
  // DESARROLLO (detección inteligente según plataforma):
  //   - Desktop Windows/Mac/Linux o Web → 127.0.0.1
  //   - Celular físico en la misma red Wi-Fi → 10.10.150.139 (IP actual de la PC)
  //   - Emulador Android → 10.0.2.2 o 10.10.150.139
  static const String _baseUrlOverride =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');
  static const String _envHost =
      String.fromEnvironment('API_HOST', defaultValue: '');
  static const String _port =
      String.fromEnvironment('API_PORT', defaultValue: '8000');

  /// Detecta automáticamente el host adecuado según dónde esté corriendo la app
  static String get _defaultHost {
    if (kIsWeb) return '127.0.0.1';
    try {
      if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
        return '127.0.0.1';
      }
    } catch (_) {}
    // Dispositivo móvil (Android / iOS): IP de la PC en la red Wi-Fi actual
    return '10.10.150.139';
  }

  static String get _host => _envHost.isNotEmpty ? _envHost : _defaultHost;

  static String? _customApiBaseUrl;

  static const String _prefCustomUrl = 'custom_api_base_url';
  // Servidor compilado en el APK con el que se guardó la URL personalizada.
  static const String _prefCustomUrlBuild = 'custom_api_base_url_build';

  /// Servidor que trae compilado este APK (vía --dart-define o detección automática).
  static String get _compiledBaseUrl =>
      _baseUrlOverride.isNotEmpty ? _baseUrlOverride : 'http://$_host:$_port/api/v1';

  /// Base pública de la API (la usan también otras vistas, p. ej. el catálogo).
  static String get apiBaseUrl {
    if (_customApiBaseUrl != null && _customApiBaseUrl!.isNotEmpty) {
      return _customApiBaseUrl!;
    }
    return _compiledBaseUrl;
  }

  static String get _baseUrl => '$apiBaseUrl/auth';
  static const Duration _timeout = Duration(seconds: 15);

  static String normalizeApiBaseUrl(String value) {
    var clean = value.trim();
    while (clean.endsWith('/')) {
      clean = clean.substring(0, clean.length - 1);
    }
    if (!clean.contains('://')) {
      clean = 'http://$clean';
    }
    final uri = Uri.tryParse(clean);
    if (uri == null ||
        (uri.scheme != 'http' && uri.scheme != 'https') ||
        uri.host.isEmpty) {
      throw const FormatException('Ingresa una IP o URL válida.');
    }
    if (!uri.path.endsWith('/api/v1') && !uri.path.contains('/api/')) {
      clean = '$clean/api/v1';
    }
    return clean;
  }

  /// Cargar URL personalizada guardada en preferencias (si existe).
  ///
  /// Solo vale para el APK con el que se guardó: al instalar encima un APK compilado para
  /// otro servidor, Android conserva los datos de la app y la URL vieja taparía la nueva,
  /// así que se descarta y manda la del APK.
  static Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_prefCustomUrl);
      if (saved == null || saved.trim().isEmpty) return;
      if (prefs.getString(_prefCustomUrlBuild) != _compiledBaseUrl) {
        await prefs.remove(_prefCustomUrl);
        await prefs.remove(_prefCustomUrlBuild);
        return;
      }
      _customApiBaseUrl = saved.trim();
    } catch (_) {}
  }

  /// Permite cambiar dinámicamente la IP/URL del backend desde la app sin cables.
  static Future<void> setCustomBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    final clean = normalizeApiBaseUrl(url);
    _customApiBaseUrl = clean;
    await prefs.setString(_prefCustomUrl, clean);
    await prefs.setString(_prefCustomUrlBuild, _compiledBaseUrl);
  }

  /// Probar conectividad con el backend
  static Future<bool> testConnection([String? urlToTest]) async {
    String target;
    try {
      target = normalizeApiBaseUrl(
        urlToTest != null && urlToTest.trim().isNotEmpty ? urlToTest : apiBaseUrl,
      );
    } on FormatException {
      return false;
    }
    try {
      final r = await http.get(Uri.parse('$target/branches')).timeout(const Duration(seconds: 4));
      return r.statusCode == 200;
    } catch (_) {
      try {
        final r = await http.get(Uri.parse(target.replaceAll('/api/v1', '/docs'))).timeout(const Duration(seconds: 4));
        return r.statusCode == 200;
      } catch (_) {
        return false;
      }
    }
  }

  static Map<String, dynamic> _fail(String message) => {'success': false, 'message': message};

  static Map<String, dynamic> _parseError(http.Response r, String fallback) {
    try {
      final body = jsonDecode(r.body);
      return _fail(body is Map && body['detail'] != null ? body['detail'].toString() : fallback);
    } catch (_) {
      return _fail('$fallback (código ${r.statusCode})');
    }
  }

  static Map<String, dynamic> _networkError(Object e) {
    if (e is SocketException || e is HttpException) {
      return _fail(
        'No se pudo conectar con el servidor ($apiBaseUrl). Verifica que el backend '
        'esté corriendo y que la dirección sea la correcta para tu dispositivo '
        '(--dart-define=API_HOST o API_BASE_URL).',
      );
    }
    return _fail('El servidor no respondió a tiempo. Inténtalo de nuevo.');
  }

  // --- [CU01] Iniciar sesión ---
  static Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/login'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email, 'password': password}),
          )
          .timeout(_timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('token', data['access_token']);
        await prefs.setString('user', jsonEncode(data['user']));
        await prefs.setStringList('roles', List<String>.from(data['roles'] ?? const []));
        return {'success': true, 'data': data};
      }
      return _parseError(response, 'Correo o contraseña incorrectos');
    } catch (e) {
      return _networkError(e);
    }
  }

  // --- [CU02] Cerrar sesión ---
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token');
    if (token != null) {
      try {
        await http.post(
          Uri.parse('$_baseUrl/logout'),
          headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
        ).timeout(_timeout);
      } catch (_) {}
    }
    await prefs.remove('token');
    await prefs.remove('user');
    await prefs.remove('roles');
  }

  // --- [CU03] Recuperar credenciales ---
  static Future<Map<String, dynamic>> recover(String email) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/recover'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email}),
          )
          .timeout(_timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'message': data['message'],
          // Solo presente si el backend corre sin SMTP (modo desarrollo).
          'devResetLink': data['dev_reset_link'],
        };
      }
      return _parseError(response, 'No se pudo enviar el enlace de recuperación');
    } catch (e) {
      return _networkError(e);
    }
  }

  // El restablecimiento de la contraseña (reset-password) se realiza en la página
  // web que abre el enlace del correo, no dentro de la app.

  // --- [CU04] Auto-registro de cliente ---
  static Future<Map<String, dynamic>> register({
    required String firstName,
    required String lastName,
    required String email,
    required String phone,
    required String password,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/register'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'first_name': firstName,
              'last_name': lastName,
              'email': email,
              'phone': phone,
              'password': password,
            }),
          )
          .timeout(_timeout);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return {'success': true, 'data': data};
      }
      return _parseError(response, 'No se pudo registrar la cuenta');
    } catch (e) {
      return _networkError(e);
    }
  }

  // --- Utilidades ---
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token');
  }

  static Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null;
  }

  /// Roles del usuario autenticado (guardados al iniciar sesión).
  static Future<List<String>> getRoles() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList('roles') ?? const [];
  }

  /// Datos básicos del usuario autenticado (nombre, correo) o null.
  static Future<Map<String, dynamic>?> getUser() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('user');
    if (raw == null) return null;
    try {
      return jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  /// Roles que operan desde el panel web (Casa Matriz, sucursal y proveedor), no desde la app.
  static const List<String> webOnlyRoles = ['SUPERADMIN', 'ADMINISTRADOR', 'ENCARGADO', 'CAJERO', 'PROVEEDOR'];

  /// [Rol REPARTIDOR] La app abre su panel de entregas en lugar de la tienda.
  static Future<bool> isRepartidor() async => (await getRoles()).contains('REPARTIDOR');

  /// True si el usuario es personal interno o proveedor (su portal es la web).
  static Future<bool> isWebOnlyUser() async {
    final roles = await getRoles();
    return !roles.contains('CLIENTE') && roles.any(webOnlyRoles.contains);
  }
}
