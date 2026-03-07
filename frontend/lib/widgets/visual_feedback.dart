import 'package:flutter/material.dart';
import 'dart:math' as math;

class CallistaGlow extends StatefulWidget {
  final bool isListening;
  final bool isThinking;

  const CallistaGlow({super.key, required this.isListening, required this.isThinking});

  @override
  State<CallistaGlow> createState() => _CallistaGlowState();
}

class _CallistaGlowState extends State<CallistaGlow> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isListening && !widget.isThinking) return const SizedBox.shrink();

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          height: 120,
          width: double.infinity,
          decoration: BoxDecoration(
            gradient: RadialGradient(
              colors: [
                widget.isListening 
                    ? const Color(0xFF6366F1).withOpacity(0.4 * (1 - _controller.value))
                    : const Color(0xFF818CF8).withOpacity(0.3),
                Colors.transparent,
              ],
              stops: const [0.5, 1.0],
            ),
          ),
          child: CustomPaint(
            painter: _WavePainter(
              progress: _controller.value,
              color: widget.isListening ? const Color(0xFF6366F1) : const Color(0xFFC084FC),
              isThinking: widget.isThinking,
            ),
          ),
        );
      },
    );
  }
}

class _WavePainter extends CustomPainter {
  final double progress;
  final Color color;
  final bool isThinking;

  _WavePainter({required this.progress, required this.color, required this.isThinking});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color.withOpacity(0.5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    final path = Path();
    final centerY = size.height / 2;
    
    if (isThinking) {
      // Harmonic circles for "Thinking"
      for (int i = 0; i < 3; i++) {
        final radius = 20.0 + (i * 15.0) + (progress * 10.0);
        canvas.drawCircle(Offset(size.width / 2, centerY), radius, paint..color = color.withOpacity(0.3 * (1 - progress)));
      }
    } else {
      // Dynamic wave for "Listening"
      path.moveTo(0, centerY);
      for (double x = 0; x <= size.width; x++) {
        final y = centerY + math.sin((x / 50) + (progress * 2 * math.pi)) * 20 * math.sin(progress * math.pi);
        path.lineTo(x, y);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
