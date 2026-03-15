import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:screenshot/screenshot.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';
import 'package:camera/camera.dart';
import '../services/vision_service.dart';
import '../services/api_client.dart';
import '../services/assistant_service.dart';
import '../services/security_service.dart';
import '../services/background_service.dart';
import '../widgets/call_concierge_overlay.dart';
import '../widgets/visual_feedback.dart';
import '../widgets/floating_assistant.dart';
import 'dashboard_screen.dart';
import 'package:logging/logging.dart';

final _logger = Logger('ChatScreen');

// ─────────────────────────────────────────────────────────────────────────────
// Glassmorphism Helper
// ─────────────────────────────────────────────────────────────────────────────
class _GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final double opacity;
  const _GlassCard({required this.child, this.padding, this.opacity = 0.08});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(opacity),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.12), width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.25),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Animated Orb Background
// ─────────────────────────────────────────────────────────────────────────────
class _OrbBackground extends StatefulWidget {
  final bool isListening;
  final bool isThinking;
  const _OrbBackground({this.isListening = false, this.isThinking = false});

  @override
  _OrbBackgroundState createState() => _OrbBackgroundState();
}

class _OrbBackgroundState extends State<_OrbBackground> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(seconds: 5))..repeat();
    _anim = Tween<double>(begin: 0, end: 2 * pi).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.isListening
        ? const Color(0xFFEF4444)
        : widget.isThinking
            ? const Color(0xFF8B5CF6)
            : const Color(0xFF6366F1);

    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) {
        return CustomPaint(
          painter: _OrbPainter(_anim.value, color),
          child: const SizedBox.expand(),
        );
      },
    );
  }
}

class _OrbPainter extends CustomPainter {
  final double angle;
  final Color color;
  _OrbPainter(this.angle, this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height * 0.18;
    final r = size.width * 0.38;
    final Paint p = Paint()
      ..shader = RadialGradient(
        colors: [color.withOpacity(0.22), Colors.transparent],
        radius: 0.8,
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r));
    canvas.drawCircle(Offset(cx + cos(angle) * 20, cy + sin(angle * 0.8) * 12), r, p);

    // Secondary orb
    final Paint p2 = Paint()
      ..shader = RadialGradient(
        colors: [const Color(0xFF7C3AED).withOpacity(0.15), Colors.transparent],
        radius: 0.9,
      ).createShader(Rect.fromCircle(center: Offset(size.width * 0.8, size.height * 0.85), radius: r * 0.7));
    canvas.drawCircle(Offset(size.width * 0.8, size.height * 0.85), r * 0.7, p2);
  }

  @override
  bool shouldRepaint(_OrbPainter old) => old.angle != angle || old.color != color;
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat Bubble
// ─────────────────────────────────────────────────────────────────────────────
class _ChatBubble extends StatelessWidget {
  final Map<String, dynamic> msg;
  const _ChatBubble({required this.msg});

  @override
  Widget build(BuildContext context) {
    final isUser = msg['role'] == 'user';
    final text = msg['text'] as String? ?? '';
    final memoryRecalled = msg['memory_recalled'] == true;
    final width = MediaQuery.of(context).size.width;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: EdgeInsets.only(
          bottom: 14,
          left: isUser ? width * 0.15 : 0,
          right: isUser ? 0 : width * 0.15,
        ),
        child: Column(
          crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            // Avatar + bubble row
            Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (!isUser) ...[
                  Container(
                    width: 32,
                    height: 32,
                    margin: const EdgeInsets.only(right: 8, bottom: 2),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.5), blurRadius: 8)],
                    ),
                    child: const Icon(Icons.auto_awesome, color: Colors.white, size: 16),
                  ),
                ],
                Container(
                  constraints: BoxConstraints(maxWidth: width * 0.68),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    gradient: isUser
                        ? const LinearGradient(
                            colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          )
                        : null,
                    color: isUser ? null : Colors.white.withOpacity(0.07),
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(20),
                      topRight: const Radius.circular(20),
                      bottomLeft: Radius.circular(isUser ? 20 : 4),
                      bottomRight: Radius.circular(isUser ? 4 : 20),
                    ),
                    border: isUser
                        ? null
                        : Border.all(color: Colors.white.withOpacity(0.1), width: 1),
                    boxShadow: [
                      BoxShadow(
                        color: isUser
                            ? const Color(0xFF6366F1).withOpacity(0.35)
                            : Colors.black.withOpacity(0.2),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      )
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        text,
                        style: TextStyle(
                          color: isUser ? Colors.white : Colors.white.withOpacity(0.92),
                          fontSize: 15,
                          height: 1.45,
                          letterSpacing: 0.1,
                        ),
                      ),
                      if (memoryRecalled) ...[
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFF818CF8).withOpacity(0.2),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: const Color(0xFF818CF8).withOpacity(0.4)),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.psychology_alt_rounded, size: 11, color: Color(0xFF818CF8)),
                              SizedBox(width: 4),
                              Text(
                                'Memory Recall',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Color(0xFF818CF8),
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Typing Indicator
// ─────────────────────────────────────────────────────────────────────────────
class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();

  @override
  _TypingIndicatorState createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator> with TickerProviderStateMixin {
  late List<AnimationController> _ctls;

  @override
  void initState() {
    super.initState();
    _ctls = List.generate(3, (i) {
      final c = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
      Future.delayed(Duration(milliseconds: i * 160), () {
        if (mounted) c.repeat(reverse: true);
      });
      return c;
    });
  }

  @override
  void dispose() {
    for (final c in _ctls) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomRight: Radius.circular(20),
            bottomLeft: Radius.circular(4),
          ),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(
            3,
            (i) => AnimatedBuilder(
              animation: _ctls[i],
              builder: (_, __) => Transform.translate(
                offset: Offset(0, -4 * _ctls[i].value),
                child: Container(
                  width: 7,
                  height: 7,
                  margin: EdgeInsets.only(right: i < 2 ? 5 : 0),
                  decoration: BoxDecoration(
                    color: const Color(0xFF818CF8).withOpacity(0.7 + 0.3 * _ctls[i].value),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Screen
// ─────────────────────────────────────────────────────────────────────────────
class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<Map<String, dynamic>> _messages = [];
  final List<dynamic> _alternates = [];
  String? _threadId;

  bool _isLoading = false;
  bool _isBackgroundListening = false;
  bool _showOverlay = false;
  final ScreenshotController _screenshotController = ScreenshotController();

  // Vision Mode
  CameraController? _cameraController;
  bool _isVisionMode = false;
  bool _isAnalyzingVision = false;

  // Call Concierge
  bool _showCallOverlay = false;
  String _currentCaller = "Unknown Caller";
  String _callPurpose = "Analyzing context...";

  // Voice integration
  late stt.SpeechToText _speech;
  bool _isListening = false;
  late FlutterTts _flutterTts;
  bool _isTtsEnabled = true;

  // Input bar animation
  late AnimationController _inputFocusCtrl;
  late Animation<double> _inputGlow;

  final FocusNode _inputFocus = FocusNode();

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _initTts();
    _initSharing();
    AssistantService.screenshotController = _screenshotController;

    _inputFocusCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 300));
    _inputGlow = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _inputFocusCtrl, curve: Curves.easeOut),
    );
    _inputFocus.addListener(() {
      if (_inputFocus.hasFocus) {
        _inputFocusCtrl.forward();
      } else {
        _inputFocusCtrl.reverse();
      }
    });

    // Initial welcome message (or load history)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadHistory();
    });
  }

  void _loadHistory() async {
    setState(() => _isLoading = true);
    try {
      final history = await ApiClient.getChatHistory();
      if (history.isNotEmpty) {
        setState(() {
          _messages.clear();
          for (var msg in history) {
            _messages.add({
              'role': msg['role'],
              'text': msg['text'],
              'memory_recalled': msg['memory_recalled'] ?? false,
            });
          }
          if (history.any((m) => m['thread_id'] != null)) {
            _threadId = history.last['thread_id'];
          }
        });
        _scrollToBottom();
      } else {
        setState(() {
          _messages.add({
            'role': 'bot',
            'text': 'Callista systems online. Multi-Agent Supervisor active. Ready to assist you, Sir.',
          });
        });
      }
    } catch (e) {
      _logger.severe('Failed to load history: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _clearHistory() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Clear Chat?', style: TextStyle(color: Colors.white)),
        content: const Text('This will permanently delete all messages from the server.', style: TextStyle(color: Colors.white70)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      setState(() => _isLoading = true);
      try {
        await ApiClient.clearChatHistory();
        setState(() {
          _messages.clear();
          _threadId = null;
          _messages.add({
            'role': 'bot',
            'text': 'History cleared. Systems reset. How can I help you now?',
          });
        });
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      } finally {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _inputFocusCtrl.dispose();
    _inputFocus.dispose();
    _cameraController?.dispose();
    _flutterTts.stop();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _toggleVisionMode() async {
    if (_isVisionMode) {
      await _cameraController?.dispose();
      setState(() => _isVisionMode = false);
    } else {
      final cameras = await availableCameras();
      if (cameras.isNotEmpty) {
        _cameraController = CameraController(cameras[0], ResolutionPreset.medium);
        await _cameraController!.initialize();
        setState(() => _isVisionMode = true);
      }
    }
  }

  void _analyzeCameraFrame() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    setState(() {
      _isLoading = true;
      _isAnalyzingVision = true;
    });
    try {
      final XFile image = await _cameraController!.takePicture();
      final bytes = await image.readAsBytes();
      final response = await _sendToVisionBackend(bytes);
      setState(() {
        _messages.add({'role': 'user', 'text': '[Vision Analysis Requested]'});
        _messages.add({'role': 'bot', 'text': response});
      });
      _flutterTts.speak(response);
    } catch (e) {
      setState(() {
        _messages.add({'role': 'bot', 'text': 'Sir, I encountered an issue with the visual sensors.'});
      });
    }
    setState(() {
      _isLoading = false;
      _isAnalyzingVision = false;
    });
    _scrollToBottom();
  }

  void _analyzeScreen() async {
    setState(() {
      _isLoading = true;
      _showOverlay = true;
    });
    File? file;
    if (_isVisionMode && _cameraController != null) {
      file = await VisionService.captureCameraFrame(_cameraController!);
    } else {
      file = await VisionService.captureScreen(_screenshotController);
    }
    if (file != null) {
      setState(() {
        _messages.add({'role': 'user', 'text': _isVisionMode ? '[Camera Scan]' : '[Screen Scan]'});
        _messages.add({
          'role': 'bot',
          'text': 'I see ${_isVisionMode ? "the scene" : "your screen"}. How can I help you analyze this?',
          'memory_recalled': true
        });
      });
    }
    setState(() {
      _isLoading = false;
      _showOverlay = false;
    });
    _scrollToBottom();
  }

  Future<String> _sendToVisionBackend(List<int> bytes) async {
    try {
      return await ApiClient.analyzeImage(bytes);
    } catch (e) {
      _logger.severe('Vision backend error: $e');
      return "I encountered an error while analyzing the image. Please try again.";
    }
  }

  void _initSharing() {
    ReceiveSharingIntent.instance.getMediaStream().listen((List<SharedMediaFile> value) {
      if (value.isNotEmpty) _processSharedFile(value.first.path);
    });
    ReceiveSharingIntent.instance.getInitialMedia().then((List<SharedMediaFile> value) {
      if (value.isNotEmpty) _processSharedFile(value.first.path);
    });
  }

  void _processSharedFile(String path) {
    setState(() {
      _messages.add({'role': 'user', 'text': '[Shared: $path]'});
      _messages.add({'role': 'bot', 'text': 'Received. Analyzing this for you...'});
    });
    _scrollToBottom();
  }

  void _initTts() async {
    await _flutterTts.setLanguage("en-US");
    await _flutterTts.setPitch(1.05);
    await _flutterTts.setSpeechRate(0.52);
  }

  void _toggleBackgroundListening() async {
    if (_isBackgroundListening) {
      await AssistantBackgroundService.stop();
    } else {
      await AssistantService.requestPermissions();
      await AssistantBackgroundService.start();
    }
    setState(() => _isBackgroundListening = !_isBackgroundListening);
  }

  void _listen() async {
    if (!_isListening) {
      bool available = await _speech.initialize(
        onStatus: (val) {
          if (val == 'done') setState(() => _isListening = false);
        },
        onError: (val) => setState(() => _isListening = false),
      );
      if (available) {
        setState(() {
          _isListening = true;
          _showOverlay = true;
        });
        _speech.listen(
          onResult: (val) {
            setState(() => _textController.text = val.recognizedWords);
            if (val.finalResult) _sendMessage();
          },
        );
      }
    } else {
      setState(() {
        _isListening = false;
        _showOverlay = false;
      });
      _speech.stop();
    }
  }

  void _sendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _inputFocus.unfocus();

    setState(() {
      if (_isListening) _isListening = false;
      _messages.add({'role': 'user', 'text': text});
      _textController.clear();
      _isLoading = true;
      _showOverlay = true;
    });
    _scrollToBottom();

    try {
      final response = await ApiClient.sendChatMessage(text, threadId: _threadId);
      final reply = response['reply'] as String;
      final memoryRecalled = response['memory_recalled'] as bool? ?? false;

      setState(() {
        _threadId = response['thread_id'];
        _messages.add({'role': 'bot', 'text': reply, 'memory_recalled': memoryRecalled});
        _isLoading = false;
        _showOverlay = false;
      });
      _scrollToBottom();

      if (reply.startsWith('COMMAND:')) {
        if (SecurityService.isSensitiveCommand(reply)) {
          bool verified = await SecurityService.verifyIdentity();
          if (!verified) return;
        }
        await AssistantService.handleCommand(reply);
      }
      if (_isTtsEnabled && !reply.startsWith('COMMAND:')) {
        await _flutterTts.speak(reply);
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _showOverlay = false;
        _messages.add({'role': 'bot', 'text': '⚠️ Unable to reach Callista servers. Please check your connection.'});
      });
      _scrollToBottom();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF080C14),
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.6), blurRadius: 12)],
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'CALLISTA',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2.5,
                  ),
                ),
                Text(
                  'AI Life Assistant',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.45),
                    fontSize: 10,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          _AppBarIcon(
            icon: _isVisionMode ? Icons.videocam_rounded : Icons.videocam_off_rounded,
            active: _isVisionMode,
            activeColor: const Color(0xFF10B981),
            onTap: _toggleVisionMode,
          ),
          _AppBarIcon(
            icon: Icons.phone_in_talk_rounded,
            active: _showCallOverlay,
            activeColor: const Color(0xFF10B981),
            onTap: () => setState(() => _showCallOverlay = !_showCallOverlay),
          ),
          _AppBarIcon(
            icon: _isBackgroundListening ? Icons.hearing_rounded : Icons.hearing_disabled_rounded,
            active: _isBackgroundListening,
            activeColor: const Color(0xFF6366F1),
            onTap: _toggleBackgroundListening,
          ),
          _AppBarIcon(
            icon: _isTtsEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded,
            active: _isTtsEnabled,
            activeColor: const Color(0xFF6366F1),
            onTap: () => setState(() => _isTtsEnabled = !_isTtsEnabled),
          ),
          _AppBarIcon(
            icon: Icons.delete_sweep_rounded,
            active: false,
            activeColor: Colors.redAccent,
            onTap: _clearHistory,
          ),
          const SizedBox(width: 4),
        ],
      ),
      drawer: _buildDrawer(context),
      body: Screenshot(
        controller: _screenshotController,
        child: Stack(
          children: [
            // Animated orb background
            _OrbBackground(isListening: _isListening, isThinking: _isLoading),

            // Vision camera preview
            if (_isVisionMode && _cameraController != null && _cameraController!.value.isInitialized)
              Positioned.fill(
                child: Opacity(
                  opacity: 0.35,
                  child: CameraPreview(_cameraController!),
                ),
              ),

            // Main content
            Column(
              children: [
                // Safe area for transparent app bar
                SizedBox(height: MediaQuery.of(context).padding.top + kToolbarHeight + 8),

                // Status strip
                _StatusStrip(
                  isListening: _isListening,
                  isThinking: _isLoading,
                  isVision: _isVisionMode,
                ),

                // Messages
                Expanded(
                  child: ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                    itemCount: _messages.length + (_isLoading ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _messages.length && _isLoading) {
                        return const _TypingIndicator();
                      }
                      return _ChatBubble(msg: _messages[index]);
                    },
                  ),
                ),

                // Input bar
                _InputBar(
                  controller: _textController,
                  focusNode: _inputFocus,
                  glowAnim: _inputGlow,
                  isListening: _isListening,
                  onSend: _sendMessage,
                  onMic: _listen,
                  onScan: _analyzeScreen,
                ),

                SizedBox(height: MediaQuery.of(context).padding.bottom),
              ],
            ),

            // Overlays
            if (_isVisionMode)
              Positioned(
                bottom: 110,
                left: 0,
                right: 0,
                child: Center(
                  child: GestureDetector(
                    onTap: _analyzeCameraFrame,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                        ),
                        borderRadius: BorderRadius.circular(30),
                        boxShadow: [
                          BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.5), blurRadius: 20),
                        ],
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.psychology_rounded, color: Colors.white, size: 20),
                          SizedBox(width: 8),
                          Text('Analyze Scene', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

            if (_showOverlay)
              FloatingAssistantOverlay(
                isListening: _isListening,
                isThinking: _isLoading,
                onClose: () => setState(() {
                  _showOverlay = false;
                  _isListening = false;
                  _speech.stop();
                }),
              ),

            if (_showCallOverlay)
              CallConciergeOverlay(
                callerName: _currentCaller,
                purpose: _callPurpose,
                onDismiss: () => setState(() => _showCallOverlay = false),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context) {
    return Drawer(
      backgroundColor: const Color(0xFF0F172A),
      child: Column(
        children: [
          Container(
            padding: EdgeInsets.only(top: MediaQuery.of(context).padding.top + 20, bottom: 30),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF1E1B4B), Color(0xFF312E81)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Center(
              child: Column(
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                      ),
                      boxShadow: [
                        BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.6), blurRadius: 20),
                      ],
                    ),
                    child: const Icon(Icons.auto_awesome, color: Colors.white, size: 36),
                  ),
                  const SizedBox(height: 14),
                  const Text(
                    'CALLISTA',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 3,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Your Personal AI Assistant',
                    style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
          _DrawerItem(
            icon: Icons.chat_bubble_rounded,
            label: 'Assistant Chat',
            active: true,
            onTap: () => Navigator.pop(context),
          ),
          _DrawerItem(
            icon: Icons.bar_chart_rounded,
            label: 'Financial Dashboard',
            onTap: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => DashboardScreen()));
            },
          ),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              'Callista v2.0 • Secure & Private',
              style: TextStyle(color: Colors.white.withOpacity(0.2), fontSize: 11),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-Widgets
// ─────────────────────────────────────────────────────────────────────────────
class _AppBarIcon extends StatelessWidget {
  final IconData icon;
  final bool active;
  final Color activeColor;
  final VoidCallback onTap;

  const _AppBarIcon({
    required this.icon,
    required this.active,
    required this.activeColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
        padding: const EdgeInsets.all(7),
        decoration: BoxDecoration(
          color: active ? activeColor.withOpacity(0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          border: active ? Border.all(color: activeColor.withOpacity(0.4), width: 1) : null,
        ),
        child: Icon(icon, color: active ? activeColor : Colors.white.withOpacity(0.35), size: 20),
      ),
    );
  }
}

class _StatusStrip extends StatelessWidget {
  final bool isListening;
  final bool isThinking;
  final bool isVision;

  const _StatusStrip({this.isListening = false, this.isThinking = false, this.isVision = false});

  @override
  Widget build(BuildContext context) {
    if (!isListening && !isThinking && !isVision) return const SizedBox.shrink();

    final label = isListening
        ? '🎙 Listening...'
        : isThinking
            ? '✦ Callista is thinking...'
            : '📷 Vision Mode Active';

    final color = isListening
        ? const Color(0xFFEF4444)
        : isThinking
            ? const Color(0xFF8B5CF6)
            : const Color(0xFF10B981);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 0.4),
        textAlign: TextAlign.center,
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final Animation<double> glowAnim;
  final bool isListening;
  final VoidCallback onSend;
  final VoidCallback onMic;
  final VoidCallback onScan;

  const _InputBar({
    required this.controller,
    required this.focusNode,
    required this.glowAnim,
    required this.isListening,
    required this.onSend,
    required this.onMic,
    required this.onScan,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
      child: AnimatedBuilder(
        animation: glowAnim,
        builder: (_, __) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF131C2E),
              borderRadius: BorderRadius.circular(28),
              border: Border.all(
                color: Color.lerp(
                  Colors.white.withOpacity(0.08),
                  const Color(0xFF6366F1).withOpacity(0.5),
                  glowAnim.value,
                )!,
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF6366F1).withOpacity(0.12 * glowAnim.value),
                  blurRadius: 16,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: Row(
              children: [
                // Mic button
                GestureDetector(
                  onLongPressStart: (_) => onMic(),
                  onLongPressEnd: (_) => onMic(),
                  onTap: onMic,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: isListening
                          ? const Color(0xFFEF4444).withOpacity(0.2)
                          : const Color(0xFF6366F1).withOpacity(0.15),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: isListening
                            ? const Color(0xFFEF4444).withOpacity(0.5)
                            : const Color(0xFF6366F1).withOpacity(0.3),
                      ),
                    ),
                    child: Icon(
                      isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                      color: isListening ? const Color(0xFFEF4444) : const Color(0xFF818CF8),
                      size: 20,
                    ),
                  ),
                ),

                const SizedBox(width: 8),

                // Text field
                Expanded(
                  child: TextField(
                    controller: controller,
                    focusNode: focusNode,
                    style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.3),
                    maxLines: 3,
                    minLines: 1,
                    decoration: InputDecoration(
                      hintText: 'Ask Callista anything...',
                      hintStyle: TextStyle(color: Colors.white.withOpacity(0.25), fontSize: 14),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(vertical: 8),
                    ),
                    onSubmitted: (_) => onSend(),
                  ),
                ),

                // Scan icon
                GestureDetector(
                  onTap: onScan,
                  child: Padding(
                    padding: const EdgeInsets.all(8),
                    child: Icon(
                      Icons.document_scanner_rounded,
                      color: Colors.white.withOpacity(0.3),
                      size: 20,
                    ),
                  ),
                ),

                // Send button
                GestureDetector(
                  onTap: onSend,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(color: const Color(0xFF6366F1).withOpacity(0.4), blurRadius: 10),
                      ],
                    ),
                    child: const Icon(Icons.arrow_upward_rounded, color: Colors.white, size: 18),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _DrawerItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _DrawerItem({
    required this.icon,
    required this.label,
    this.active = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: active ? const Color(0xFF6366F1).withOpacity(0.2) : Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: active ? const Color(0xFF818CF8) : Colors.white.withOpacity(0.4), size: 20),
      ),
      title: Text(
        label,
        style: TextStyle(
          color: active ? Colors.white : Colors.white.withOpacity(0.6),
          fontSize: 14,
          fontWeight: active ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      onTap: onTap,
    );
  }
}
