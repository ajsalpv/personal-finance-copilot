import 'dart:io';
import 'package:screenshot/screenshot.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'package:logging/logging.dart';

final _logger = Logger('VisionService');

class VisionService {
  /// Captures a screenshot of the current screen using the provided controller.
  static Future<File?> captureScreen(ScreenshotController controller) async {
    try {
      final imageBytes = await controller.capture();
      if (imageBytes != null) {
        final file = await saveTempImage(imageBytes);
        _logger.info('Screenshot captured at: ${file.path}');
        return file;
      }
    } catch (e) {
      _logger.severe('Failed to capture screenshot: $e');
    }
    return null;
  }

  /// Extracts a frame from the provided camera controller.
  static Future<File?> captureCameraFrame(CameraController controller) async {
    try {
      if (!controller.value.isInitialized) return null;
      final XFile image = await controller.takePicture();
      _logger.info('Camera frame captured: ${image.path}');
      return File(image.path);
    } catch (e) {
      _logger.severe('Failed to capture camera frame: $e');
    }
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
