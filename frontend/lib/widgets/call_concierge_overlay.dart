import 'package:flutter/material.dart';
import 'visual_feedback.dart';

class CallConciergeOverlay extends StatelessWidget {
  final String callerName;
  final String purpose;
  final bool isRecording;
  final VoidCallback onDismiss;

  const CallConciergeOverlay({
    super.key,
    required this.callerName,
    this.purpose = 'Analyzing call context...',
    this.isRecording = true,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.black.withOpacity(0.85),
      child: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.85,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: Colors.indigoAccent.withOpacity(0.3), width: 1),
            boxShadow: [
              BoxShadow(color: Colors.indigoAccent.withOpacity(0.2), blurRadius: 40, spreadRadius: 5),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.phone_in_talk_rounded, color: Colors.greenAccent, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'CALLISTA CONCIERGE',
                    style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 2),
                  ),
                ],
              ),
              const SizedBox(height: 30),
              const CircleAvatar(
                radius: 40,
                backgroundColor: Color(0xFF0F172A),
                child: Icon(Icons.person_rounded, color: Colors.white24, size: 50),
              ),
              const SizedBox(height: 16),
              Text(
                callerName,
                style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                purpose,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white60, fontSize: 14),
              ),
              const SizedBox(height: 40),
              CallistaGlow(isListening: isRecording, isThinking: false),
              const SizedBox(height: 30),
              ElevatedButton.icon(
                onPressed: onDismiss,
                icon: const Icon(Icons.close_rounded),
                label: const Text('Back to Dashboard'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white12,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
