import 'package:flutter/material.dart';
import 'screens/chat_screen.dart';

void main() {
  runApp(const NovaApp());
}

class NovaApp extends StatelessWidget {
  const NovaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Private AI Assistant',
      theme: ThemeData.dark().copyWith(
        primaryColor: Colors.blueAccent,
        scaffoldBackgroundColor: Colors.black,
      ),
      home: ChatScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
