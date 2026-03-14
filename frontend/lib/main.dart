import 'package:flutter/material.dart';
import 'services/background_service.dart';
import 'services/api_client.dart';
import 'screens/chat_screen.dart';
import 'screens/boot_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Background Service
  AssistantBackgroundService.init();
  
  // Check for existing token
  final token = await ApiClient.getToken();
  
  runApp(NovaApp(isLoggedIn: token != null));
}

class NovaApp extends StatelessWidget {
  final bool isLoggedIn;
  const NovaApp({super.key, required this.isLoggedIn});

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
      home: BootScreen(isLoggedIn: isLoggedIn),
      debugShowCheckedModeBanner: false,
    );
  }
}
