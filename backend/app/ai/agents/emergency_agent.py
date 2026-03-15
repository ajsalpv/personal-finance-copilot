"""
Emergency Agent — LLM-Powered Regional Risk & Policy Analysis
Replaces hardcoded rule-based logic with dynamic AI reasoning.
"""
import logging
import json
from typing import Dict, List, Any
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class EmergencyAgent:
    @staticmethod
    async def analyze_regional_risks(region: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        [EMERGENCY INTELLIGENCE AGENT]
        Analyzes raw regional data and generates intelligent, contextual alerts.
        """
        system_prompt = """You are a Disaster Preparedness & Regional Risk Agent for Callista AI.
Your goal is to analyze raw environmental, infrastructure, and health data for a specific region and generate 
INTELLIGENT, high-confidence alerts.

DO NOT use hardcoded rules. Reason about the data:
- If rain is predicted in a landslide-prone area (like Kerala) -> High severity.
- If a supply bottleneck is mentioned -> Suggest specific stock-up items.
- If national health indicators are normal -> Reassure the user.

RESPOND IN STRICT JSON:
{
  "active_alerts": [
    {
      "type": "weather/resource/health/security",
      "severity": "critical/high/medium/low",
      "title": "Clear, informative title",
      "description": "Intelligent analysis of the risk",
      "confidence": "XX%",
      "prep": ["List of specific, actionable prep steps"]
    }
  ],
  "overall_status": "String describing the general regional climate"
}
Only return JSON."""

        # In a real app, this would fetch from MET/Gov APIs.
        # We simulate the RAW INPUT which the AI will then REASON about.
        raw_input = f"""
        Region: {region}
        User Context: {json.dumps(user_context)}
        Raw Data Signals:
        - MET Signal: 200mm rainfall predicted in next 24h for Western Ghats.
        - Supply Signal: LPG transport strike starting in 3 days.
        - Health Signal: Zero active outbreaks reported.
        """

        raw_response = await _call_groq(system_prompt, raw_input)
        
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            
            data = json.loads(cleaned)
            return {
                "region": region,
                "active_alerts": data.get("active_alerts", []),
                "overall_status": data.get("overall_status", "Stable")
            }
        except Exception as e:
            logger.error(f"Emergency Agent failed to parse JSON: {e}")
            return {
                "region": region,
                "active_alerts": [],
                "overall_status": "Status Unavailable"
            }

    @staticmethod
    async def analyze_policy_updates(region: str) -> List[Dict[str, Any]]:
        """
        [POLICY INTELLIGENCE AGENT]
        Analyzes major government policy changes and reasons about their impact.
        """
        system_prompt = """You are a Government Policy Analyst Agent for Callista AI.
Look at the latest policy signals for the given region and reason about the FINANCIAL impact on a common citizen.

RESPOND IN STRICT JSON:
[
  {
    "policy": "Name of the policy",
    "impact": "Detailed reasoning of the financial/legal impact",
    "date": "Timeline of effect"
  }
]
Only return JSON."""

        # Simulate raw incoming policy feeds
        raw_input = f"""
        Region: {region}
        Policy Signals:
        - Central Cabinet: New fuel subsidy under consideration for next month.
        - RBI Bulletin: Digital Rupee (e-Rupee) adoption milestones and incentives for merchants.
        - Tax Dept: New simplified GST filing for small business owners.
        """

        raw_response = await _call_groq(system_prompt, raw_input)
        
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Policy Agent failing: {e}")
            return []
