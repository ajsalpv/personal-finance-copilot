"""
Travel Agent — LLM-Powered Location & Mobility Reasoning
Replaces simple city-mismatch checks with intelligent context.
"""
import logging
import json
from typing import Dict, List, Any, Optional
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class TravelAgent:
    @staticmethod
    async def analyze_location_shift(
        current_location: Dict[str, Any], 
        historical_pattern: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        [TRAVEL REASONING AGENT]
        Analyzes if a new location log is a "Significant Travel Event" 
        vs just a commute or noisy sensor data.
        """
        system_prompt = """You are a Mobility Intelligence Agent for Callista AI.
Look at the user's current location and their 7-day history. Determine if they are "Traveling".

DO NOT use simple "city names don't match" rules. Reason:
- If a user is in Kochi but goes to Ernakulam, that is a local commute.
- If a user is in Kochi and suddenly appears in Bangalore, that is Travel.
- If they are in a new location but it's 11 PM on a weekday, they might be staycationing or on a business trip.

RESPOND IN STRICT JSON:
{
  "is_traveling": true/false,
  "confidence": "XX%",
  "reasoning": "Short explanation of why this is or isn't travel",
  "detected_home_base": "City name",
  "detected_destination": "City name"
}
If is_traveling is false, still return the JSON but with false. Only return JSON."""

        user_input = f"""
        Current Location: {json.dumps(current_location)}
        Recent History: {json.dumps(historical_pattern)}
        User Profile: {json.dumps(user_context)}
        """

        raw_response = await _call_groq(system_prompt, user_input)
        
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            
            data = json.loads(cleaned)
            if data.get("is_traveling"):
                return data
            return None
        except Exception as e:
            logger.error(f"Travel Agent reasoning failed: {e}")
            return None
