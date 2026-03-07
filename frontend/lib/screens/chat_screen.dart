import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';
import '../widgets/floating_assistant.dart';
import '../services/security_service.dart';

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final List<Map<String, String>> _messages = [];
  String? _threadId;
  bool _isLoading = false;
  bool _isBackgroundListening = false;
  bool _showOverlay = false;
  
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
    
    // Initial welcome message
    _messages.add({
      'role': 'bot',
      'text': 'Callista systems stabilized. Ready to facilitate your day, Sir.',
    });
  }

  void _initSharing() {
    // Listen for shared media while app is running
    ReceiveSharingIntent.getMediaStream().listen((List<SharedMediaFile> value) {
      if (value.isNotEmpty) {
        _processSharedFile(value.first.path);
      }
    });

    // Listen for shared media while app is closed
    ReceiveSharingIntent.getInitialMedia().then((List<SharedMediaFile> value) {
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
      await requestAssistantPermissions();
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
      
      setState(() {
        _threadId = response['thread_id'];
        _messages.add({'role': 'bot', 'text': reply});
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
      body: Stack(
        children: [
          Column(
            children: [
              Expanded(
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
                        child: Text(
                          msg['text'] ?? '',
                          style: const TextStyle(color: Colors.white, fontSize: 16, height: 1.4),
                        ),
                      ),
                    );
                  },
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
        ],
      ),
    );
  }
}
