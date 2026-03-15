"""
Insight Agent — LLM-Powered Financial Analysis & Anomaly Detection
Replaces static thresholds with intelligent behavioral reasoning.
"""
import logging
import json
from typing import Dict, List, Any
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class InsightAgent:
    @staticmethod
    async def detect_anomalies(transactions: List[Dict[str, Any]], user_history: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [ANOMALY DETECTION AGENT]
        Analyzes transaction patterns to find outliers that are TRULY unusual,
        accounting for time, category, and historical behavior.
        """
        system_prompt = """You are a Financial Forensic Agent for Callista AI.
Your task is to analyze a list of recent transactions and identify anomalies.

DO NOT use simple fixed percentage thresholds. Use reasoning:
- A ₹5000 spend on "Food" might be normal for a wedding but an anomaly for a Tuesday.
- Multiple small, identical charges at a gas station might indicate a double-billing error.
- A sudden shift in merchant type at 3 AM is a high-priority anomaly.

RESPOND IN STRICT JSON:
[
  {
    "type": "anomaly",
    "message": "Human-friendly explanation of why this is unusual",
    "severity": "critical/high/medium/low",
    "transaction_id": "ID if applicable"
  }
]
Only return JSON."""

        user_input = f"""
        Recent Transactions: {json.dumps(transactions)}
        User Historical averages: {json.dumps(user_history)}
        """

        raw_response = await _call_groq(system_prompt, user_input)
        
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Insight Agent (Anomaly) failed: {e}")
            return []

    @staticmethod
    async def generate_forecast(budget_status: List[Dict[str, Any]], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [FORECASTING AGENT]
        Predicts month-end outcomes and provides intelligent warnings.
        """
        system_prompt = """You are a Strategic Budgeting Agent for Callista AI.
Look at the user's current budget spending and pace. Predict if they will break their budget.

Reasoning:
- "Velocity" isn't just (spent/days). Account for weekend vs weekday patterns.
- If a user usually spends 80% of their "Entertainment" budget in the first week, don't warn them yet.

RESPOND IN STRICT JSON:
[
  {
    "type": "forecast",
    "message": "Friendly, foresight-driven warning or encouragement",
    "priority": "high/medium/low",
    "projected_spend": 0.0,
    "limit": 0.0,
    "category": "Category name"
  }
]
Only return JSON."""

        user_input = f"""
        Budget Status: {json.dumps(budget_status)}
        Time Context: {json.dumps(user_context)}
        """

        raw_response = await _call_groq(system_prompt, user_input)
        
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Insight Agent (Forecast) failed: {e}")
            return []
