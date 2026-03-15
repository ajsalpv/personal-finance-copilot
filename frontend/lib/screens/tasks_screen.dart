import 'package:flutter/material.dart';
import '../services/api_client.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  bool _isLoading = true;
  List<dynamic> _tasks = [];
  final TextEditingController _taskController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchTasks();
  }

  Future<void> _fetchTasks() async {
    setState(() => _isLoading = true);
    try {
      // Fetch tasks from existing service
      // final tasks = await ApiClient.getTasks();
      // For now, using mock data integrated with real backend structure
      setState(() {
        _tasks = [
          {"id": 1, "title": "Buy LPG Cylinder", "completed": false, "priority": "high"},
          {"id": 2, "title": "Renew Netflix Subscription", "completed": true, "priority": "medium"},
          {"id": 3, "title": "Review March Expenses", "completed": false, "priority": "low"},
        ];
      });
    } catch (e) {
      print("Error fetching tasks: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _addTask() async {
    if (_taskController.text.isEmpty) return;
    // await ApiClient.addTask(_taskController.text);
    _taskController.clear();
    _fetchTasks();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Reminders & Tasks', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.sort_rounded),
            onPressed: () {},
          ),
        ],
      ),
      body: Column(
        children: [
          _buildInputArea(),
          Expanded(
            child: _isLoading 
                ? const Center(child: CircularProgressIndicator())
                : _buildTaskList(),
          ),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(16),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _taskController,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                hintText: 'What needs to be done?',
                hintStyle: TextStyle(color: Colors.white38),
                border: InputBorder.none,
              ),
              onSubmitted: (_) => _addTask(),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.add_circle_rounded, color: Color(0xFF6366F1), size: 32),
            onPressed: _addTask,
          ),
        ],
      ),
    );
  }

  Widget _buildTaskList() {
    if (_tasks.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.task_alt_rounded, size: 64, color: Colors.white.withOpacity(0.1)),
            const SizedBox(height: 16),
            Text('No pending tasks, Sir.', style: TextStyle(color: Colors.white.withOpacity(0.4))),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _tasks.length,
      itemBuilder: (context, index) {
        final task = _tasks[index];
        final completed = task['completed'] as bool;
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.05)),
          ),
          child: ListTile(
            leading: Checkbox(
              value: completed,
              activeColor: const Color(0xFF6366F1),
              onChanged: (val) {},
              shape: Theme.of(context).platform == TargetPlatform.android ? const CircleBorder() : null,
            ),
            title: Text(
              task['title'],
              style: TextStyle(
                color: completed ? Colors.white38 : Colors.white,
                decoration: completed ? TextDecoration.lineThrough : null,
              ),
            ),
            trailing: _buildPriorityChip(task['priority']),
          ),
        );
      },
    );
  }

  Widget _buildPriorityChip(String priority) {
    Color color;
    switch (priority) {
      case 'high': color = Colors.redAccent; break;
      case 'medium': color = Colors.orangeAccent; break;
      default: color = Colors.tealAccent;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        priority.toUpperCase(),
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
      ),
    );
  }
}

