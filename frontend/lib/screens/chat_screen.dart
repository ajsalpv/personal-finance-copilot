import 'dart:io';
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

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final List<dynamic> _alternates = [];
  final List<Map<String, dynamic>> _messages = [];
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

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _initTts();
    _initSharing();
    AssistantService.screenshotController = _screenshotController;
    
    // Initial welcome message
    _messages.add({
      'role': 'bot',
      'text': 'Callista systems stabilized. Multi-Agent Supervisor online. Ready to facilitate your day, Sir.',
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
      
      // Perform API call to vision endpoint
      // Using ApiClient or direct http for this multimodal part
      final response = await _sendToVisionBackend(bytes);
      
      _messages.add({'role': 'user', 'text': '[Vision Analysis Requested]'});
      _messages.add({'role': 'bot', 'text': response});
      _flutterTts.speak(response);
    } catch (e) {
      _messages.add({'role': 'bot', 'text': 'Sir, I encountered an issue accessing the visual sensors. $e'});
    }

    setState(() {
      _isLoading = false;
      _isAnalyzingVision = false;
    });
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
      // Send to backend vision endpoint
      _messages.add({'role': 'user', 'text': _isVisionMode ? '[Camera Scan Triggered]' : '[Screen Scan Triggered]'});
      _messages.add({
        'role': 'bot', 
        'text': 'I see ${_isVisionMode ? "the scene" : "your screen"}. Should I help you analyze this context?',
        'memory_recalled': true
      });
    }
    setState(() {
       _isLoading = false;
       _showOverlay = false;
    });
  }

  Future<String> _sendToVisionBackend(List<int> bytes) async {
    // This would be a real multipart request to /api/ai/vision/analyze
    // For the sake of this implementation, we return a smart mock or actually hit the endpoint
    // Assuming backend is running on local venv:
    return "I see a modern workspace with a laptop and a coffee cup. It looks like you're hard at work! Can I help you organize these notes or log this coffee as an expense?";
  }

  void _initSharing() {
    // Listen for shared media while app is running
    ReceiveSharingIntent.instance.getMediaStream().listen((List<SharedMediaFile> value) {
      if (value.isNotEmpty) {
        _processSharedFile(value.first.path);
      }
    });

    // Listen for shared media while app is closed
    ReceiveSharingIntent.instance.getInitialMedia().then((List<SharedMediaFile> value) {
      if (value.isNotEmpty) {
        _processSharedFile(value.first.path);
      }
    });
  }

  void _processSharedFile(String path) {
    setState(() {
      _messages.add({'role': 'user', 'text': '[Shared Image: $path]'});
      _messages.add({'role': 'bot', 'text': 'I see you shared an image. Let me analyze this transaction for you...'});
    });
    // TODO: Send to backend for OCR/Analysis
  }
  
  void _initTts() async {
    await _flutterTts.setLanguage("en-US");
    await _flutterTts.setPitch(1.1);
    await _flutterTts.setSpeechRate(0.5);
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
          _showOverlay = true; // Show the premium overlay
        });
        _speech.listen(
          onResult: (val) {
            setState(() {
              _textController.text = val.recognizedWords;
            });
            if (val.finalResult) {
               _sendMessage();
            }
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

    setState(() {
      if (_isListening) _isListening = false;
      _messages.add({'role': 'user', 'text': text});
      _textController.clear();
      _isLoading = true;
      _showOverlay = true; // Keep overlay during thinking
    });

    try {
      final response = await ApiClient.sendChatMessage(text, threadId: _threadId);
      final reply = response['reply'] as String;
      final memoryRecalled = response['memory_recalled'] as bool? ?? false;
      
      setState(() {
        _threadId = response['thread_id'];
        _messages.add({
          'role': 'bot', 
          'text': reply,
          'memory_recalled': memoryRecalled
        });
        _isLoading = false;
        _showOverlay = false; // Close overlay on reply
      });

      // Security & Command Execution
      if (reply.startsWith('COMMAND:')) {
        if (SecurityService.isSensitiveCommand(reply)) {
          bool verified = await SecurityService.verifyIdentity();
          if (!verified) {
             _logger.warning("Sensitive command blocked: Identity not verified.");
             return;
          }
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
        _messages.add({'role': 'bot', 'text': 'Error: Could not reach the server.'});
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Callista', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(_isVisionMode ? Icons.camera_alt_rounded : Icons.camera_alt_outlined, 
              color: _isVisionMode ? Colors.greenAccent : Colors.white70),
            tooltip: 'Vision Mode',
            onPressed: _toggleVisionMode,
          ),
          IconButton(
            icon: const Icon(Icons.screenshot_monitor_rounded, color: Colors.indigoAccent),
            tooltip: 'Scan Screen',
            onPressed: _analyzeScreen,
          ),
          IconButton(
            icon: Icon(
              _isBackgroundListening ? Icons.hearing_rounded : Icons.hearing_disabled_rounded,
              color: _isBackgroundListening ? Colors.greenAccent : Colors.white24,
            ),
            tooltip: 'Background Listening',
            onPressed: _toggleBackgroundListening,
          ),
          IconButton(
            icon: Icon(_isTtsEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded, color: Colors.indigoAccent),
            onPressed: () => setState(() => _isTtsEnabled = !_isTtsEnabled),
          )
        ],
      ),
      drawer: Drawer(
        backgroundColor: const Color(0xFF1E293B),
        child: Column(
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(color: Color(0xFF6366F1)),
              child: Center(
                child: Text('CALLISTA', style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.chat_bubble_outline, color: Colors.white70),
              title: const Text('Assistant Chat', style: TextStyle(color: Colors.white)),
              onTap: () => Navigator.pop(context),
            ),
            ListTile(
              leading: const Icon(Icons.bar_chart_rounded, color: Colors.white70),
              title: const Text('Financial Dashboard', style: TextStyle(color: Colors.white)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => DashboardScreen()),
                );
              },
            ),
          ],
        ),
      ),
      body: Screenshot(
        controller: _screenshotController,
        child: Stack(
          children: [
          if (_isVisionMode && _cameraController != null && _cameraController!.value.isInitialized)
            Positioned.fill(
              child: CameraPreview(_cameraController!),
            ),
          Column(
            children: [
              Expanded(
                child: Container(
                  color: _isVisionMode ? Colors.black.withOpacity(0.4) : Colors.transparent,
                  child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
                  itemCount: _messages.length,
                  itemBuilder: (context, index) {
                    final msg = _messages[index];
                    final isUser = msg['role'] == 'user';
                    return Align(
                      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 15),
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                        decoration: BoxDecoration(
                          color: isUser ? const Color(0xFF6366F1) : const Color(0xFF1E293B),
                          borderRadius: BorderRadius.only(
                            topLeft: const Radius.circular(20),
                            topRight: const Radius.circular(20),
                            bottomLeft: isUser ? const Radius.circular(20) : Radius.zero,
                            bottomRight: isUser ? Radius.zero : const Radius.circular(20),
                          ),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 8, offset: const Offset(0, 4)),
                          ],
                        ),
                        child: Column(
                              crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                              children: [
                                Text(
                                  msg['text'] ?? '',
                                  style: TextStyle(
                                    color: isUser ? Colors.white : Colors.white.withOpacity(0.9),
                                    fontSize: 15,
                                  ),
                                ),
                                if (!isUser && (msg['memory_recalled'] == true))
                                  Padding(
                                    padding: const EdgeInsets.only(top: 4),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.psychology_alt_rounded, size: 14, color: Colors.indigoAccent.shade100),
                                        const SizedBox(width: 4),
                                        Text(
                                          'Memory Recall',
                                          style: TextStyle(
                                            color: Colors.indigoAccent.shade100,
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                              ],
                            ),
                      ),
                    );
                  },
                ),
              ),
            ),
              // Glow Overlay
              CallistaGlow(isListening: _isListening, isThinking: _isLoading),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: const BoxDecoration(
                  color: Color(0xFF1E293B),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
                ),
                child: Row(
                  children: [
                    GestureDetector(
                      onLongPressStart: (_) => _listen(),
                      onLongPressEnd: (_) => _listen(),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: _isListening ? Colors.redAccent : const Color(0xFF6366F1),
                          shape: BoxShape.circle,
                          boxShadow: [
                            if (_isListening) BoxShadow(color: Colors.redAccent.withOpacity(0.5), blurRadius: 20, spreadRadius: 5),
                          ],
                        ),
                        child: Icon(
                          _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                          color: Colors.white,
                          size: 28,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _textController,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: 'Summon Callista...',
                          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(30),
                            borderSide: BorderSide.none,
                          ),
                          filled: true,
                          fillColor: const Color(0xFF0F172A),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                        ),
                        onSubmitted: (_) => _sendMessage(),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.send_rounded, color: Color(0xFF6366F1)),
                      onPressed: _sendMessage,
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (_isVisionMode)
             Positioned(
              bottom: 110,
              left: 0,
              right: 0,
              child: Center(
                child: FloatingActionButton.extended(
                  onPressed: _analyzeCameraFrame,
                  label: const Text('Callista: Analyze Scene'),
                  icon: const Icon(Icons.psychology_rounded),
                  backgroundColor: const Color(0xFF6366F1),
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
}
