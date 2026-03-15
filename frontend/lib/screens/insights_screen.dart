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
      // Simulation of multi-agent intelligence results
      setState(() {
        _advisories = [
          {
            "event": "War in Middle East escalates",
            "impact": "Direct pressure on Crude Oil supply chains. Expected LPG and Petrol price hikes in India.",
            "suggestion": "Consider booking your LPG refill early and refilling your vehicle within 48 hours.",
            "level": "Critical",
            "confidence": "85%",
            "priority": "high",
            "region": "Global/India"
          },
          {
            "event": "Heavy monsoon predicted for Southern India",
            "impact": "High risk of travel disruption and resource shortages in Kerala due to weather.",
            "suggestion": "Avoid non-essential long-distance travel in Kerala. Ensure power banks and basic groceries are stocked.",
            "level": "Warning",
            "confidence": "90%",
            "priority": "high",
            "region": "Kerala"
          },
          {
            "event": "New central subsidy for electric vehicles",
            "impact": "New policy incentive detected. High potential for personal savings on green tech.",
            "suggestion": "Check eligibility for the new EV scheme if you were planning a vehicle purchase.",
            "level": "Opportunity",
            "confidence": "70%",
            "priority": "medium",
            "region": "India"
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
      backgroundColor: const Color(0xFF0F172A),
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
              const Text('Active Intelligence Advisories', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
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
        gradient: LinearGradient(
          colors: [Colors.redAccent.withOpacity(0.1), Colors.orangeAccent.withOpacity(0.05)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
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
            'Callista multi-agent system has detected ${_advisories.length} signals intersecting with your profile.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildAdvisoryCard(Map<String, dynamic> advisory) {
    Color statusColor;
    IconData statusIcon;
    
    switch (advisory['level']) {
      case 'Critical':
        statusColor = Colors.redAccent;
        statusIcon = Icons.warning_amber_rounded;
        break;
      case 'Warning':
        statusColor = Colors.orangeAccent;
        statusIcon = Icons.info_outline_rounded;
        break;
      case 'Opportunity':
        statusColor = Colors.greenAccent;
        statusIcon = Icons.stars_rounded;
        break;
      default:
        statusColor = Colors.blueAccent;
        statusIcon = Icons.lightbulb_outline_rounded;
    }

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
                  color: statusColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  advisory['level'].toUpperCase(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                "Confidence: ${advisory['confidence']}",
                style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 10, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Text(
                advisory['region'],
                style: TextStyle(color: Colors.white10, fontSize: 10),
              ),
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
              Icon(statusIcon, color: statusColor, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  advisory['suggestion'],
                  style: TextStyle(color: statusColor, fontSize: 14, fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
