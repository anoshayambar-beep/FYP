import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String baseUrl = 'http://127.0.0.1:5000'; // Make sure this is accessible from device/emulator

  // Logs in user, saves token & role to SharedPreferences
  static Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final currentBaseUrl = prefs.getString('baseUrl') ?? 'http://127.0.0.1:5000';

      final response = await http.post(
        Uri.parse('$currentBaseUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('jwt_token', data['token']);
        await prefs.setString('user_role', data['role']);
        await prefs.setString('username', data['username']);

        return {'success': true, 'role': data['role']};
      } else {
        final data = jsonDecode(response.body);
        return {'success': false, 'message': data['error'] ?? 'Login failed'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  // Registers a new user
  static Future<Map<String, dynamic>> register(String username, String password, String role, String email) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final currentBaseUrl = prefs.getString('baseUrl') ?? 'http://127.0.0.1:5000';

      final response = await http.post(
        Uri.parse('$currentBaseUrl/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
          'role': role,
          'email': email,
        }),
      );

      final data = jsonDecode(response.body);
      if (response.statusCode == 201) {
        return {'success': true, 'message': data['msg'] ?? data['message']};
      } else {
        return {'success': false, 'message': data['error'] ?? 'Registration failed'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  // Forgot password feature removed as per user request

  // Gets the current token
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('jwt_token');
  }

  // Gets the current role
  static Future<String?> getRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('user_role');
  }

  // Checks if user is admin
  static Future<bool> isAdmin() async {
    final role = await getRole();
    return role == 'admin';
  }

  // Logs out user
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt_token');
    await prefs.remove('user_role');
    await prefs.remove('username');
  }
}
