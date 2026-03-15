import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'dart:ui';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  double _totalBalance = 0;
  double _monthlyExpenses = 0;
  List<dynamic> _recentInsights = [];

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    try {
      // Simulate/Fetch aggregated data
      final history = await ApiClient.getChatHistory();
      // For now we'll derive some stats or wait for specialized endpoints
      setState(() {
        _totalBalance = 124550.0; // Mock data for now
        _monthlyExpenses = 45200.0;
        _recentInsights = [
          {"type": "risk", "msg": "Global oil prices rising. Fuel hike likely next week."},
          {"type": "budget", "msg": "You've spent 85% of your Entertainment budget."},
        ];
      });
    } catch (e) {
      print("Error loading dashboard: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Background Gradient
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
          ),
          
          SafeArea(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const SizedBox(height: 20),
                _buildHeader(),
                const SizedBox(height: 30),
                _buildBalanceCard(),
                const SizedBox(height: 24),
                _buildSectionTitle("Strategic Intelligence"),
                const SizedBox(height: 12),
                _buildIntelligenceFeed(),
                const SizedBox(height: 24),
                _buildSectionTitle("Quick Actions"),
                const SizedBox(height: 12),
                _buildActionGrid(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Good Afternoon, Sir',
              style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 16),
            ),
            const Text(
              'Callista Command',
              style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: const Icon(Icons.person_outline_rounded, color: Colors.white),
        ),
      ],
    );
  }

  Widget _buildBalanceCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6366F1).withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Current Liquidity',
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
          const SizedBox(height: 8),
          Text(
            '₹${_totalBalance.toStringAsFixed(0)}',
            style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: 1),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildStatItem("Monthly Spend", "₹${_monthlyExpenses.toStringAsFixed(0)}"),
              _buildStatItem("Savings Rate", "14.2%"),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white60, fontSize: 12)),
        Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
    );
  }

  Widget _buildIntelligenceFeed() {
    return Column(
      children: _recentInsights.map((insight) {
        final isRisk = insight['type'] == 'risk';
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isRisk ? Colors.redAccent.withOpacity(0.3) : Colors.white.withOpacity(0.1),
            ),
          ),
          child: Row(
            children: [
              Icon(
                isRisk ? Icons.warning_amber_rounded : Icons.tips_and_updates_rounded,
                color: isRisk ? Colors.redAccent : Colors.amberAccent,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  insight['msg'],
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildActionGrid() {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      childAspectRatio: 1.5,
      children: [
        _buildActionCard(Icons.add_shopping_cart_rounded, "Log Expense", Colors.tealAccent),
        _buildActionCard(Icons.savings_rounded, "Add Income", Colors.lightBlueAccent),
        _buildActionCard(Icons.camera_alt_rounded, "Scan Receipt", Colors.orangeAccent),
        _buildActionCard(Icons.mic_rounded, "Voice Command", Color(0xFF8B5CF6)),
      ],
    );
  }

  Widget _buildActionCard(IconData icon, String label, Color color) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
