"""
Emergency Agent — LLM-Powered Regional Risk & Policy Analysis
Replaces hardcoded rule-based logic with dynamic AI reasoning.
Uses real-time data from hot_context.json.
"""
import logging
import json
import os
from typing import Dict, List, Any
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

def _get_hot_context():
    """Reads the latest real-time news/weather/economic context."""
    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "hot_context.json")
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return "No real-time context file readable."
    return "No real-time context found."

class EmergencyAgent:
    @staticmethod
    async def analyze_regional_risks(region: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        [EMERGENCY INTELLIGENCE AGENT]
        Analyzes raw regional data and generates intelligent, contextual alerts.
        """
        system_prompt = """You are a Disaster Preparedness & Regional Risk Agent for Callista AI.
Your goal is to analyze REAL-TIME regional data and generate INTELLIGENT, high-confidence alerts.

Reason about the data:
- Connect weather alerts to local geography (e.g., landslides in Kerala).
- Connect supply chain strikes to daily needs (LPG, petrol, food).
- Only alert on significant risks. Provide reassurance if things are stable.

RESPOND IN STRICT JSON:
{
  "active_alerts": [
    {
      "type": "weather/resource/health/security",
      "severity": "critical/high/medium/low",
      "title": "Clear title",
      "description": "Analysis of the risk",
      "confidence": "XX%",
      "prep": ["Actionable prep steps"]
    }
  ],
  "overall_status": "Summary of regional status"
}
Only return JSON."""

        hot_data = _get_hot_context()
        raw_input = f"""
        Requested Region: {region}
        User Context: {json.dumps(user_context)}
        REAL-TIME HOT CONTEXT FEED:
        {hot_data}
        """

        raw_response = await _call_groq(system_prompt, raw_input)
        
        try:
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            
            # Find the first { and last }
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]
            
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

        hot_data = _get_hot_context()
        raw_input = f"""
        Requested Region: {region}
        REAL-TIME POLICY FEEDS:
        {hot_data}
        """

        raw_response = await _call_groq(system_prompt, raw_input)
        
        try:
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
                
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]
                
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Policy Agent failing: {e}")
            return []
