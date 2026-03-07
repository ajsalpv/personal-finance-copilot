import 'dart:io';
import 'package:native_screenshot/native_screenshot.dart';
import 'package:path_provider/path_provider.dart';
import 'package:logging/logging.dart';

final _logger = Logger('VisionService');

class VisionService {
  /// Captures a screenshot of the current screen.
  static Future<File?> captureScreen() async {
    try {
      final String? path = await NativeScreenshot.takeScreenshot();
      if (path != null) {
        _logger.info('Screenshot captured at: $path');
        return File(path);
      }
    } catch (e) {
      _logger.severe('Failed to capture screenshot: $e');
    }
    return null;
  }

  /// Placeholder for extracting a frame from the camera.
  /// This will be used when the user opens the camera for Callista.
  static Future<File?> captureCameraFrame() async {
    // Note: This requires the camera controller from the UI.
    // For now, it returns a placeholder or uses image_picker as a fallback.
    _logger.info('Camera frame capture triggered.');
    return null;
  }

  /// Saves image data to a temporary file for analysis.
  static Future<File> saveTempImage(List<int> bytes) async {
    final tempDir = await getTemporaryDirectory();
    final file = File('${tempDir.path}/callista_vision_${DateTime.now().millisecondsSinceEpoch}.jpg');
    await file.writeAsBytes(bytes);
    return file;
  }
}
