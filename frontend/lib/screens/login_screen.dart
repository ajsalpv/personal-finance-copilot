import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'chat_screen.dart';
import 'main_navigation.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Animated background particles
// ─────────────────────────────────────────────────────────────────────────────
class _ParticlePainter extends CustomPainter {
  final double angle;
  _ParticlePainter(this.angle);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final rng = math.Random(42);
    for (int i = 0; i < 35; i++) {
      final x = rng.nextDouble() * size.width;
      final y = rng.nextDouble() * size.height;
      final r = rng.nextDouble() * 2.5 + 0.5;
      final opacity = 0.08 + 0.12 * math.sin(angle + i);
      paint.color = const Color(0xFF818CF8).withOpacity(opacity);
      canvas.drawCircle(Offset(x, y), r, paint);
    }

    // Orb 1
    final p1 = Paint()
      ..shader = RadialGradient(
        colors: [const Color(0xFF6366F1).withOpacity(0.2), Colors.transparent],
      ).createShader(Rect.fromCircle(center: Offset(size.width * 0.15, size.height * 0.25), radius: 180));
    canvas.drawCircle(
      Offset(size.width * 0.15 + math.cos(angle) * 20, size.height * 0.25 + math.sin(angle) * 12),
      180,
      p1,
    );

    // Orb 2
    final p2 = Paint()
      ..shader = RadialGradient(
        colors: [const Color(0xFF8B5CF6).withOpacity(0.18), Colors.transparent],
      ).createShader(Rect.fromCircle(center: Offset(size.width * 0.85, size.height * 0.7), radius: 150));
    canvas.drawCircle(
      Offset(size.width * 0.85 + math.sin(angle) * 15, size.height * 0.7 + math.cos(angle) * 10),
      150,
      p2,
    );
  }

  @override
  bool shouldRepaint(_ParticlePainter old) => old.angle != angle;
}

// ─────────────────────────────────────────────────────────────────────────────
// Login Screen
// ─────────────────────────────────────────────────────────────────────────────
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  bool _isRegister = false;
  bool _isLoading = false;
  bool _obscure = true;
  String? _error;

  late AnimationController _bgCtrl;
  late Animation<double> _bgAnim;

  @override
  void initState() {
    super.initState();
    _bgCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 8))..repeat();
    _bgAnim = Tween<double>(begin: 0, end: 2 * math.pi).animate(_bgCtrl);
  }

  @override
  void dispose() {
    _bgCtrl.dispose();
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _nameCtrl.dispose();
    super.dispose();
  }

  void _submit() async {
    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;
    final name = _nameCtrl.text.trim();

    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Please fill in all fields');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (_isRegister) {
        if (name.isEmpty) {
          setState(() { _error = 'Please enter your name'; _isLoading = false; });
          return;
        }
        await ApiClient.register(name, email, password);
      } else {
        await ApiClient.login(email, password);
      }

      if (mounted) {
        Navigator.of(context).pushReplacement(
          PageRouteBuilder(
            pageBuilder: (_, __, ___) => const MainNavigation(),
            transitionsBuilder: (_, anim, __, child) => FadeTransition(opacity: anim, child: child),
            transitionDuration: const Duration(milliseconds: 600),
          ),
        );
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceAll('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF080C14),
      body: AnimatedBuilder(
        animation: _bgAnim,
        builder: (context, _) {
          return Stack(
            children: [
              CustomPaint(painter: _ParticlePainter(_bgAnim.value), size: Size.infinite),
              SafeArea(
                child: Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 40),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Logo
                        Container(
                          width: 90,
                          height: 90,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: const LinearGradient(
                              colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF6366F1).withOpacity(0.5),
                                blurRadius: 30,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                          child: const Icon(Icons.auto_awesome, color: Colors.white, size: 44),
                        ),
                        const SizedBox(height: 24),
                        const Text(
                          'CALLISTA',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 4,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Your Personal AI Life Assistant',
                          style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 13),
                        ),
                        const SizedBox(height: 44),

                        // Card
                        Container(
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(color: Colors.white.withOpacity(0.08)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              // Tab switcher
                              Container(
                                padding: const EdgeInsets.all(4),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.05),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: Row(
                                  children: [
                                    _Tab(label: 'Sign In', active: !_isRegister, onTap: () => setState(() { _isRegister = false; _error = null; })),
                                    _Tab(label: 'Register', active: _isRegister, onTap: () => setState(() { _isRegister = true; _error = null; })),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 24),

                              if (_isRegister) ...[
                                _InputField(controller: _nameCtrl, hint: 'Full Name', icon: Icons.person_outline_rounded),
                                const SizedBox(height: 14),
                              ],

                              _InputField(controller: _emailCtrl, hint: 'Email Address', icon: Icons.mail_outline_rounded, keyboardType: TextInputType.emailAddress),
                              const SizedBox(height: 14),
                              _InputField(
                                controller: _passwordCtrl,
                                hint: 'Password',
                                icon: Icons.lock_outline_rounded,
                                obscure: _obscure,
                                suffix: IconButton(
                                  icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility, color: Colors.white30, size: 20),
                                  onPressed: () => setState(() => _obscure = !_obscure),
                                ),
                              ),

                              if (_error != null) ...[
                                const SizedBox(height: 14),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                  decoration: BoxDecoration(
                                    color: Colors.redAccent.withOpacity(0.12),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: Colors.redAccent.withOpacity(0.3)),
                                  ),
                                  child: Text(
                                    _error!,
                                    style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 13),
                                  ),
                                ),
                              ],

                              const SizedBox(height: 24),

                              // Submit button
                              GestureDetector(
                                onTap: _isLoading ? null : _submit,
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 200),
                                  height: 52,
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: _isLoading
                                          ? [const Color(0xFF4B5563), const Color(0xFF374151)]
                                          : [const Color(0xFF6366F1), const Color(0xFF8B5CF6)],
                                    ),
                                    borderRadius: BorderRadius.circular(16),
                                    boxShadow: _isLoading
                                        ? []
                                        : [BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.45), blurRadius: 16)],
                                  ),
                                  child: Center(
                                    child: _isLoading
                                        ? const SizedBox(
                                            width: 22,
                                            height: 22,
                                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                                          )
                                        : Text(
                                            _isRegister ? 'Create Account' : 'Sign In',
                                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16),
                                          ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 32),
                        Text(
                          'Secured with AES-256 & JWT',
                          style: TextStyle(color: Colors.white.withOpacity(0.18), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Tab extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _Tab({required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: active ? const Color(0xFF6366F1) : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: active ? Colors.white : Colors.white.withOpacity(0.4),
              fontWeight: active ? FontWeight.w600 : FontWeight.normal,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }
}

class _InputField extends StatelessWidget {
  final TextEditingController controller;
  final String hint;
  final IconData icon;
  final bool obscure;
  final Widget? suffix;
  final TextInputType? keyboardType;

  const _InputField({
    required this.controller,
    required this.hint,
    required this.icon,
    this.obscure = false,
    this.suffix,
    this.keyboardType,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: TextField(
        controller: controller,
        obscureText: obscure,
        keyboardType: keyboardType,
        style: const TextStyle(color: Colors.white, fontSize: 15),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.25), fontSize: 14),
          prefixIcon: Icon(icon, color: Colors.white.withOpacity(0.3), size: 20),
          suffixIcon: suffix,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
      ),
    );
  }
}
