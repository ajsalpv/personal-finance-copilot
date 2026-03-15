import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  // Production URL on Render
  static const String baseUrl = 'https://personal-finance-copilot.onrender.com/api';
  
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('jwt_token');
  }

  static Future<void> setToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('jwt_token', token);
  }

  static Future<Map<String, String>> _getHeaders() async {
    final token = await getToken();
    if (token != null) {
      return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };
    }
    return {'Content-Type': 'application/json'};
  }

  // --- Health Check ---
  static Future<bool> pingServer() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/ping')).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // --- Auth ---
  static Future<Map<String, dynamic>> login(String email, String password) async {
    final url = Uri.parse('$baseUrl/auth/login');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await setToken(data['access_token']);
      return data;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Login failed');
    }
  }

  static Future<Map<String, dynamic>> register(String name, String email, String password) async {
    final url = Uri.parse('$baseUrl/auth/register');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name, 'email': email, 'password': password}),
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = jsonDecode(response.body);
      await setToken(data['access_token']);
      return data;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Registration failed');
    }
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt_token');
  }

  // --- AI Chat ---
  static Future<Map<String, dynamic>> sendChatMessage(String message, {String? threadId}) async {
    final url = Uri.parse('$baseUrl/chat/message');
    final headers = await _getHeaders();
    
    final body = {
      'message': message,
      if (threadId != null) 'thread_id': threadId,
    };

    final response = await http.post(
      url,
      headers: headers,
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to send message: ${response.statusCode}');
    }
  }

  // --- Transactions / Stats ---
  static Future<List<dynamic>> getDailyStats({int days = 30}) async {
    final url = Uri.parse('$baseUrl/transactions/stats/daily?days=$days');
    final headers = await _getHeaders();
    
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get stats: ${response.statusCode}');
    }
  }

  // --- Vision ---
  static Future<String> analyzeImage(List<int> bytes, {String? prompt}) async {
    final url = Uri.parse('$baseUrl/vision/analyze');
    final token = await getToken();
    
    var request = http.MultipartRequest('POST', url);
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    
    request.files.add(http.MultipartFile.fromBytes(
      'image',
      bytes,
      filename: 'upload.jpg',
    ));
    
    if (prompt != null) request.fields['prompt'] = prompt;

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['analysis'];
    } else {
      throw Exception('Vision analysis failed: ${response.statusCode}');
    }
  }

  // --- Chat History ---
  static Future<List<dynamic>> getChatHistory() async {
    final url = Uri.parse('$baseUrl/chat/history');
    final headers = await _getHeaders();
    
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['history'];
    } else {
      throw Exception('Failed to load chat history: ${response.statusCode}');
    }
  }

  static Future<bool> clearChatHistory() async {
    final url = Uri.parse('$baseUrl/chat/history');
    final headers = await _getHeaders();
    
    final response = await http.delete(url, headers: headers);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['success'] ?? true;
    } else {
      throw Exception('Failed to clear chat history: ${response.statusCode}');
    }
  }

  static Future<bool> deleteSelectedMessages(List<String> messageIds) async {
    final url = Uri.parse('$baseUrl/chat/delete-messages');
    final headers = await _getHeaders();
    
    final response = await http.post(
      url, 
      headers: headers,
      body: jsonEncode({'message_ids': messageIds}),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['success'] ?? true;
    } else {
      throw Exception('Failed to delete selected messages: ${response.statusCode}');
    }
  }

  // --- Location Intelligence ---
  static Future<void> logLocation(double lat, double lng, {String? city, String? locality}) async {
    final url = Uri.parse('$baseUrl/locations/log');
    final headers = await _getHeaders();
    
    final response = await http.post(
      url,
      headers: headers,
      body: jsonEncode({
        'latitude': lat,
        'longitude': lng,
        'city': city,
        'locality': locality,
      }),
    );

    if (response.statusCode != 200) {
      print('Warning: Failed to log location');
    }
  }

  static Future<Map<String, dynamic>> checkTravelAnomaly() async {
    final url = Uri.parse('$baseUrl/locations/anomaly');
    final headers = await _getHeaders();
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) return jsonDecode(response.body);
    return {'anomaly': {'is_traveling': false}};
  }

  // --- Strategic Intelligence ---
  static Future<List<dynamic>> getIntelligenceAdvisories() async {
    final url = Uri.parse('$baseUrl/intelligence/advisories');
    final headers = await _getHeaders();
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['advisories'] ?? [];
    }
    return [];
  }

  static Future<Map<String, dynamic>> getEmergencyReport(String region) async {
    final url = Uri.parse('$baseUrl/intelligence/emergency?region=$region');
    final headers = await _getHeaders();
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load emergency report');
  }
}
