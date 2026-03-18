import 'package:screenshot/screenshot.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:logging/logging.dart';
import 'package:permission_handler/permission_handler.dart';
import '../services/vision_service.dart';

final _logger = Logger('AssistantService');

class AssistantService {
  static ScreenshotController? screenshotController;

  static Future<void> requestPermissions() async {
    await [
      Permission.microphone,
      Permission.contacts,
      Permission.phone,
      Permission.location,
      Permission.notification,
    ].request();
  }
  /// Interprets and executes system-level commands returned by the AI Agent.
  static Future<void> handleCommand(String fullCommand) async {
    // Commands are formatted as COMMAND:ACTION|PARAM1|PARAM2...
    if (!fullCommand.startsWith('COMMAND:')) return;

    final parts = fullCommand.substring(8).split('|');
    if (parts.isEmpty) return;

    final action = parts[0];

    try {
      switch (action) {
        case 'CALL':
          if (parts.length > 1) {
            await _makeCall(parts[1]);
          }
          break;
        case 'SMS':
          if (parts.length > 2) {
            await _sendSMS(parts[1], parts[2]);
          }
          break;
        case 'EMAIL':
          if (parts.length > 3) {
            await _sendEmail(parts[1], parts[2], parts[3]);
          }
          break;
        case 'MAPS':
          if (parts.length > 1) {
            await _openMaps(parts[1]);
          }
          break;
        case 'SEARCH_CONTACTS':
          if (parts.length > 1) {
            await _searchContacts(parts[1]);
          }
          break;
        case 'ADD_CALENDAR':
          if (parts.length > 2) {
            await _addCalendarEvent(parts[1], parts[2], parts.length > 3 ? parts[3] : '');
          }
          break;
        case 'LIST_CALENDAR':
          await _listCalendarEvents(parts.length > 1 ? parts[1] : '');
          break;
        case 'DEVICE':
          if (parts.length > 2) {
            await _controlDevice(parts[1], parts[2]);
          }
          break;
        case 'ALARM':
          if (parts.length > 1) {
            await _setAlarm(parts[1], parts.length > 2 ? parts[2] : '');
          }
          break;
        case 'REMINDER':
          if (parts.length > 2) {
            await _addReminder(parts[1], parts[2]);
          }
          break;
        case 'SETTING':
          if (parts.length > 2) {
            await _modifySetting(parts[1], parts[2]);
          }
          break;
        case 'ANSWER_CALL':
          await _answerCallWithCallista();
          break;
        case 'SCAN_SCREEN':
          await _scanCurrentScreen();
          break;
        default:
          _logger.warning('Unknown assistant command: $action');
      }
    } catch (e) {
      _logger.severe('Error executing assistant command $action: $e');
    }
  }

  static Future<void> _setAlarm(String timeStr, String label) async {
    _logger.info("Setting alarm for $timeStr with label $label");
    // Standard Android Intent for Alarms
    final Uri url = Uri.parse('intent:#Intent;action=android.intent.action.SET_ALARM;S.android.intent.extra.alarm.MESSAGE=${Uri.encodeComponent(label)};i.android.intent.extra.alarm.HOUR=${timeStr.split(':')[0]};i.android.intent.extra.alarm.MINUTES=${timeStr.split(':')[1]};S.android.intent.extra.alarm.SKIP_UI=true;end');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    } else {
      // Fallback for newer Android versions or if intent fails
      _logger.warning("Could not launch direct intent, trying clock app...");
    }
  }

  static Future<void> _addReminder(String text, String dueTime) async {
    _logger.info("Adding reminder: $text at $dueTime");
    // Reminders are often handled via Calendar or specialized apps
    // For now, we'll route to Calendar Event with a 'Reminder' prefix
    await _addCalendarEvent("Reminder: $text", dueTime, "Phone Reminder");
  }

  static Future<void> _modifySetting(String feature, String value) async {
    _logger.info("Modifying setting $feature to $value");
    // Settings often require specific platform channels. 
    // We will log and potentially trigger a generic 'settings' open.
    final Uri url = Uri.parse('package:com.android.settings'); // Mock/General
    _logger.info("DEVICE SETTING CHANGE: $feature -> $value");
  }

  static Future<void> _answerCallWithCallista() async {
    _logger.info("Callista is taking over the call...");
    // This would transition to a CallScreen or background concierge service
  }

  static Future<void> _scanCurrentScreen() async {
    _logger.info("Callista is scanning the screen...");
    if (screenshotController != null) {
      await VisionService.captureScreen(screenshotController!);
    } else {
      _logger.warning("ScreenshotController not initialized!");
    }
  }

  static Future<void> _controlDevice(String feature, String action) async {
    if (feature.toLowerCase() == 'flashlight') {
      // requires camera/flashlight package, but for now we'll trigger a mock toast/log
      _logger.info("DEVICE CONTROL: Flashlight $action");
    }
  }

  static Future<void> _searchContacts(String query) async {
    // Uses contacts_service packge (trigger search UI or print for now)
    final Uri url = Uri.parse('content://contacts/people/');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  static Future<void> _addCalendarEvent(String title, String startTime, String location) async {
    final Uri url = Uri.parse(
      'content://com.android.calendar/events/insert?'
      'title=${Uri.encodeComponent(title)}'
      '&eventLocation=${Uri.encodeComponent(location)}'
      '&beginTime=${DateTime.parse(startTime).millisecondsSinceEpoch}',
    );
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  static Future<void> _listCalendarEvents(String date) async {
    final Uri url = Uri.parse('content://com.android.calendar/time/');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  static Future<void> _makeCall(String phoneNumber) async {
    final Uri url = Uri.parse('tel:$phoneNumber');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  static Future<void> _sendSMS(String phoneNumber, String message) async {
    final Uri url = Uri.parse('sms:$phoneNumber?body=${Uri.encodeComponent(message)}');
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  static Future<void> _sendEmail(String recipient, String subject, String body) async {
    final Uri url = Uri.parse(
      'mailto:$recipient?subject=${Uri.encodeComponent(subject)}&body=${Uri.encodeComponent(body)}',
    );
    if (await canLaunchUrl(url)) {
      await launchUrl(url);
    }
  }

  static Future<void> _openMaps(String location) async {
    // Standard maps URL that works on both Android and iOS
    final Uri url = Uri.parse('https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(location)}');
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }
}
