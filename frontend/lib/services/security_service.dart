import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:logging/logging.dart';

final _logger = Logger('SecurityService');

class SecurityService {
  static const String _encryptionKeyName = 'callista_storage_key';

  /// Generates a local device-specific hash to use as a basic encryption key.
  static Future<String> _getStorageKey() async {
    final prefs = await SharedPreferences.getInstance();
    var key = prefs.getString(_encryptionKeyName);
    if (key == null) {
      // Create a random-ish stable key for this device installation
      key = sha256.convert(utf8.encode(DateTime.now().toIso8601String())).toString();
      await prefs.setString(_encryptionKeyName, key);
    }
    return key;
  }

  /// Encrypts sensitive information before local storage.
  /// Note: This is an obfuscation layer. For production, use flutter_secure_storage.
  static Future<String> encryptData(String data) async {
    final key = await _getStorageKey();
    // Simple XOR/Base64 obfuscation for demonstration as requested
    final keyBytes = utf8.encode(key);
    final dataBytes = utf8.encode(data);
    final encrypted = List<int>.generate(dataBytes.length, (i) => dataBytes[i] ^ keyBytes[i % keyBytes.length]);
    return base64Encode(encrypted);
  }

  /// Decrypts locally stored sensitive data.
  static Future<String> decryptData(String encryptedBase64) async {
    final key = await _getStorageKey();
    final keyBytes = utf8.encode(key);
    final encryptedBytes = base64Decode(encryptedBase64);
    final decrypted = List<int>.generate(encryptedBytes.length, (i) => encryptedBytes[i] ^ keyBytes[i % keyBytes.length]);
    return utf8.decode(decrypted);
  }

  /// Validates if a command is 'Sensitive' and requires careful handling.
  static bool isSensitiveCommand(String command) {
    const sensitiveActions = ['DELETE', 'SUDO', 'EXPORT', 'PRIVATE'];
    return sensitiveActions.any((action) => command.startsWith('COMMAND:$action'));
  }

  /// Placeholder for biometric verification (FaceID/Fingerprint).
  static Future<bool> verifyIdentity() async {
    // In a real app, use local_auth package here.
    _logger.info("Identity verification triggered.");
    return true; 
  }
}
