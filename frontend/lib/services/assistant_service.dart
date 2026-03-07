import 'package:url_launcher/url_launcher.dart';
import 'package:logging/logging.dart';

final _logger = Logger('AssistantService');

class AssistantService {
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

  static Future<void> _answerCallWithCallista() async {
    _logger.info("Callista is taking over the call...");
    // This would transition to a CallScreen or background concierge service
  }

  static Future<void> _scanCurrentScreen() async {
    _logger.info("Callista is scanning the screen...");
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
