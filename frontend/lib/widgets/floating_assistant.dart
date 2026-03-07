import 'package:flutter/material.dart';
import 'visual_feedback.dart';

class FloatingAssistantOverlay extends StatelessWidget {
  final bool isListening;
  final bool isThinking;
  final VoidCallback onClose;

  const FloatingAssistantOverlay({
    super.key,
    required this.isListening,
    required this.isThinking,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.9,
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B).withOpacity(0.95),
            borderRadius: BorderRadius.circular(30),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.5), blurRadius: 30, spreadRadius: 10),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'CALLISTA',
                style: TextStyle(
                  color: Colors.white,
                  letterSpacing: 4,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 10),
              CallistaGlow(isListening: isListening, isThinking: isThinking),
              const SizedBox(height: 10),
              if (isListening)
                const Text(
                  'Listening...',
                  style: TextStyle(color: Colors.white70, fontStyle: FontStyle.italic),
                ),
              if (isThinking)
                const Text(
                  'Callista is thinking...',
                  style: TextStyle(color: Color(0xFF6366F1), fontWeight: FontWeight.bold),
                ),
              IconButton(
                onPressed: onClose,
                icon: const Icon(Icons.close_rounded, color: Colors.white24),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
