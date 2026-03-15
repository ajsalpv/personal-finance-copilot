import 'dart:async';
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import '../services/api_client.dart';
import 'chat_screen.dart';
import 'login_screen.dart';
import 'main_navigation.dart';

class BootScreen extends StatefulWidget {
  final bool isLoggedIn;
  const BootScreen({Key? key, required this.isLoggedIn}) : super(key: key);

  @override
  State<BootScreen> createState() => _BootScreenState();
}

class _BootScreenState extends State<BootScreen> {
  final AudioPlayer _audioPlayer = AudioPlayer();
  Timer? _pollingTimer;
  String _statusMessage = "Initializing Callista Systems...";
  int _attempts = 0;

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  void _startPolling() {
    // Initial immediate ping
    _ping();
    
    // Then poll every 5 seconds
    _pollingTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      _ping();
    });
  }

  Future<void> _ping() async {
    setState(() {
      _attempts++;
      if (_attempts > 2) {
        _statusMessage = "Waking up server... (Cold boots can take 50s)";
      }
    });

    final isOnline = await ApiClient.pingServer();
    if (isOnline) {
      _pollingTimer?.cancel();
      _transitionToApp();
    }
  }

  void _transitionToApp() async {
    setState(() {
      _statusMessage = "Systems Online!";
    });

    try {
      await _audioPlayer.play(AssetSource('f1_beep.wav'), volume: 1.0);
    } catch (e) {
      debugPrint("Audio error: \$e");
    }

    // Short delay to let the user hear the beep and read the status before navigating
    await Future.delayed(const Duration(milliseconds: 1200));

    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => widget.isLoggedIn ? const MainNavigation() : const LoginScreen(),
      ),
    );
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF080C14),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Glowing core
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF6366F1).withOpacity(0.2),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF8B5CF6).withOpacity(0.5),
                    blurRadius: 30,
                    spreadRadius: 10,
                  ),
                ],
              ),
              child: const Center(
                child: SizedBox(
                  width: 30,
                  height: 30,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 40),
            Text(
              _statusMessage,
              style: TextStyle(
                color: Colors.white.withOpacity(0.8),
                fontSize: 16,
                fontWeight: FontWeight.w300,
                letterSpacing: 1.2,
              ),
            ),
            if (_attempts > 6) ...[
              const SizedBox(height: 20),
              TextButton(
                onPressed: () {
                  _pollingTimer?.cancel();
                  Navigator.of(context).pushReplacement(
                    MaterialPageRoute(
                      builder: (_) => widget.isLoggedIn ? const MainNavigation() : const LoginScreen(),
                    ),
                  );
                },
                child: Text(
                  "Skip Wait",
                  style: TextStyle(color: Colors.white.withOpacity(0.5)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
