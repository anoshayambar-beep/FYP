import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const _baseUrlKey = 'baseUrl';
  static const String defaultBaseUrl = 'http://127.0.0.1:5000';

  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_baseUrlKey) ?? defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_baseUrlKey, value);
  }

  static Uri _u(String baseUrl, String path) {
    final b = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$b$p');
  }

  static Future<Map<String, String>> _headers() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('jwt_token');
    if (token != null) {
      return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };
    }
    return {'Content-Type': 'application/json'};
  }

  static Future<Map<String, dynamic>> getJson(String path) async {
    final baseUrl = await getBaseUrl();
    final headers = await _headers();
    
    final separator = path.contains('?') ? '&' : '?';
    final bustedPath = '$path${separator}_t=${DateTime.now().millisecondsSinceEpoch}';

    final res = await http.get(_u(baseUrl, bustedPath), headers: headers).timeout(const Duration(seconds: 30));
    if (res.statusCode < 200 || res.statusCode >= 300) {
      if (res.statusCode == 401 || res.statusCode == 403) {
        throw Exception('Unauthorized');
      }
      throw Exception('HTTP ${res.statusCode}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> postJson(String path, Map<String, dynamic> body) async {
    final baseUrl = await getBaseUrl();
    final headers = await _headers();
    final res = await http
        .post(
          _u(baseUrl, path),
          headers: headers,
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 30));
    if (res.statusCode < 200 || res.statusCode >= 300) {
      if (res.statusCode == 401 || res.statusCode == 403) {
        throw Exception('Unauthorized');
      }
      throw Exception('HTTP ${res.statusCode}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}

