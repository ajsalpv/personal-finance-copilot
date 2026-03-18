import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'dart:convert';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _strictVoiceSecurity = false;
  bool _isEnrolled = false;
  int _samplesCount = 0;
  bool _isRecording = false;

  @override
  void initState() {
    super.initState();
    _checkEnrollment();
  }

  Future<void> _checkEnrollment() async {
    // Mock check for now, would fetch from current_user
    setState(() {
      _isEnrolled = false; // logic here
    });
  }

  Future<void> _startEnrollment() async {
    setState(() => _isRecording = true);
    // Simulate recording 3 samples
    for (int i = 0; i < 3; i++) {
       await Future.delayed(const Duration(seconds: 2));
       setState(() => _samplesCount++);
    }
    setState(() {
      _isRecording = false;
      _isEnrolled = true;
    });
    // In real app, would send audio_base64 to /auth/voice/enroll
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Assistant Settings', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
          ),
        ),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _buildSectionHeader('Voice Identity'),
            _buildPremiumCard(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.mic, color: Colors.indigoAccent),
                    title: const Text('Voice Enrollment'),
                    subtitle: Text(_isEnrolled ? 'Enrolled (Confirmed)' : 'Not Enrolled'),
                    trailing: ElevatedButton(
                      onPressed: _isRecording ? null : _startEnrollment,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _isEnrolled ? Colors.green : Colors.indigoAccent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: Text(_isRecording ? 'Rec...' : _isEnrolled ? 'Re-enroll' : 'Enroll'),
                    ),
                  ),
                  if (_isRecording)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: LinearProgressIndicator(
                        value: _samplesCount / 3.0,
                        backgroundColor: Colors.white10,
                        color: Colors.indigoAccent,
                      ),
                    ),
                  const Divider(color: Colors.white10),
                  SwitchListTile(
                    title: const Text('Strict Voice Security'),
                    subtitle: const Text('Only respond to my verified voice profile'),
                    value: _strictVoiceSecurity,
                    onChanged: (val) => setState(() => _strictVoiceSecurity = val),
                    activeColor: Colors.indigoAccent,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            _buildSectionHeader('Preferences'),
            _buildPremiumCard(
              child: Column(
                children: [
                   ListTile(
                    leading: const Icon(Icons.language, color: Colors.blueAccent),
                    title: const Text('Primary Name'),
                    subtitle: const Text('Callista'),
                    trailing: const Icon(Icons.chevron_right, color: Colors.white24),
                    onTap: () {},
                  ),
                  const Divider(color: Colors.white10),
                   ListTile(
                    leading: const Icon(Icons.smart_toy, color: Colors.purpleAccent),
                    title: const Text('AI Personality'),
                    subtitle: const Text('Elite Concierge / Jarvis'),
                    trailing: const Icon(Icons.chevron_right, color: Colors.white24),
                    onTap: () {},
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 12),
      child: Text(
        title.toUpperCase(),
        style: const TextStyle(
          color: Colors.white54,
          fontSize: 12,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.2,
        ),
      ),
    );
  }

  Widget _buildPremiumCard({required Widget child}) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: child,
      ),
    );
  }
}
