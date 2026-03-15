import 'package:flutter/material.dart';
import '../services/api_client.dart';

class InsightsScreen extends StatefulWidget {
  const InsightsScreen({super.key});

  @override
  State<InsightsScreen> createState() => _InsightsScreenState();
}

class _InsightsScreenState extends State<InsightsScreen> {
  bool _isLoading = true;
  List<dynamic> _advisories = [];

  @override
  void initState() {
    super.initState();
    _loadInsights();
  }

  Future<void> _loadInsights() async {
    setState(() => _isLoading = true);
    try {
      // In a real scenario, this would call get_strategic_advisory tool via a specialized endpoint
      // For now, we simulate the Phase 15 Intelligence Service results
      setState(() {
        _advisories = [
          {
            "event": "War in Middle East escalates",
            "impact": "Direct pressure on Crude Oil supply chains.",
            "suggestion": "Expect LPG and Petrol prices to rise by ₹5-₹8 per litre in the next 14 days.",
            "level": "Critical"
          },
          {
            "event": "India Digital Tax Policy Refresh",
            "impact": "Increased overhead for international SaaS.",
            "suggestion": "Review your 'Other' expense category for hidden subscription increases.",
            "level": "Medium"
          }
        ];
      });
    } catch (e) {
      print("Error loading insights: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // #0F172A
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Strategic Intelligence', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(20),
            children: [
              _buildRiskOverview(),
              const SizedBox(height: 30),
              const Text('Active Geopolitical Threats', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
              const SizedBox(height: 16),
              ..._advisories.map((a) => _buildAdvisoryCard(a)).toList(),
            ],
          ),
    );
  }

  Widget _buildRiskOverview() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.redAccent.withOpacity(0.05),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.redAccent.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          const Icon(Icons.security_rounded, color: Colors.redAccent, size: 48),
          const SizedBox(height: 16),
          const Text(
            'Global Risk Alert: HIGH',
            style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'Callista has detected 2 major global events that directly intersect with your spending habits.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildAdvisoryCard(Map<String, dynamic> advisory) {
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: advisory['level'] == 'Critical' ? Colors.redAccent.withOpacity(0.2) : Colors.blueAccent.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  advisory['level'].toUpperCase(),
                  style: TextStyle(
                    color: advisory['level'] == 'Critical' ? Colors.redAccent : Colors.blueAccent,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const Spacer(),
              const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white24, size: 14),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            advisory['event'],
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            advisory['impact'],
            style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 14),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Divider(color: Colors.white10),
          ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.lightbulb_outline_rounded, color: Colors.amberAccent, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  advisory['suggestion'],
                  style: const TextStyle(color: Colors.amberAccent, fontSize: 14, fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
