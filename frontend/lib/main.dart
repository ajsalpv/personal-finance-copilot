import 'package:permission_handler/permission_handler.dart';
import 'services/background_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Background Service
  AssistantBackgroundService.init();
  
  runApp(const NovaApp());
}

Future<void> requestAssistantPermissions() async {
  await [
    Permission.microphone,
    Permission.contacts,
    Permission.phone,
    Permission.location,
    Permission.notification,
  ].request();
}

class NovaApp extends StatelessWidget {
  const NovaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Callista',
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF6366F1), // Deep Indigo
        scaffoldBackgroundColor: const Color(0xFF0F172A), // Onyx
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6366F1),
          brightness: Brightness.dark,
        ),
      ),
      home: ChatScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
