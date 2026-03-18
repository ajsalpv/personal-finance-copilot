import 'dart:isolate';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:logging/logging.dart';

final _logger = Logger('BackgroundService');

class BackgroundVoiceHandler extends TaskHandler {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isInitialized = false;

  @override
  Future<void> onStart(DateTime timestamp, SendPort? sendPort) async {
    _logger.info("Background Voice Listener Started");
    _isInitialized = await _speech.initialize();
  }

  @override
  Future<void> onRepeatEvent(DateTime timestamp, SendPort? sendPort) async {
    if (!_isInitialized) return;

    if (!_speech.isListening) {
      await _speech.listen(
        onResult: (val) {
          final text = val.recognizedWords.toLowerCase();
          final wakeWords = [
            'salve callista', 'salve zafira',
            'kalos callista', 'kalos zafira',
            'zdravo callista', 'zdravo zafira',
            'bonjour callista', 'bonjour zafira',
            'ya callista', 'ya zafira',
            'wake up', 'jarvis', 'callista', 'zafira'
          ];

          if (wakeWords.any((word) => text.contains(word))) {
            _logger.info("Wake word detected in background!");
            FlutterForegroundTask.launchApp();
            sendPort?.send('WAKE_WORD_DETECTED');
          } else if (text.contains('open camera') || text.contains('show me')) {
            _logger.info("Camera command detected in background!");
            FlutterForegroundTask.launchApp();
            sendPort?.send('OPEN_CAMERA_DETECTED');
          }
        },
        listenFor: const Duration(seconds: 10),
      );
    }
  }

  @override
  Future<void> onDestroy(DateTime timestamp, SendPort? sendPort) async {
    _speech.stop();
  }
}

class AssistantBackgroundService {
  static void init() {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        id: 101,
        channelId: 'callista_assistant',
        channelName: 'Callista Assistant Service',
        channelDescription: 'Listening for Callista wake word',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        iconData: const NotificationIconData(
          resType: ResourceType.mipmap,
          resPrefix: ResourcePrefix.ic,
          name: 'launcher',
        ),
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: true,
        playSound: false,
      ),
      foregroundTaskOptions: const ForegroundTaskOptions(
        interval: 5000,
        isOnceEvent: false,
        autoRunOnBoot: true,
        allowWakeLock: true,
      ),
    );
  }

  static Future<void> start() async {
    if (await FlutterForegroundTask.isRunningService) {
      return;
    }
    await FlutterForegroundTask.startService(
      notificationTitle: 'Callista is Listening',
      notificationText: 'Say "Callista" to get help',
      callback: startCallback,
    );
  }

  static Future<void> stop() async {
    await FlutterForegroundTask.stopService();
  }
}

@pragma('vm:entry-point')
void startCallback() {
  FlutterForegroundTask.setTaskHandler(BackgroundVoiceHandler());
}
