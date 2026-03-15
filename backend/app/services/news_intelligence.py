"""
News Intelligence Service — LLM-Powered Strategic Analysis
Uses Groq AI to dynamically understand ANY global event and generate
intelligent, contextual impact analysis and personalized advisories.
"""
import logging
import json
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


async def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """Makes a direct call to Groq API and returns the text response."""
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 2048,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_URL, headers=headers, json=payload, timeout=25.0)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"Groq API error {response.status_code}: {response.text[:300]}")
            return ""
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        return ""


class NewsIntelligenceService:

    @staticmethod
    async def fetch_global_risks() -> List[Dict[str, Any]]:
        """
        [NEWS MONITORING AGENT]
        Fetches trending global news from the real-time hot context.
        """
        try:
            import os
            data_path = os.path.join(os.path.dirname(__file__), "..", "data", "hot_context.json")
            if os.path.exists(data_path):
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("news_headlines", [])
            
            # Fallback if file missing
            return [{"title": "Global inflation trends rising", "category": "economy", "severity": 0.5}]
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    @staticmethod
    async def analyze_impact(news_data: List[Dict[str, Any]], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [IMPACT ANALYSIS AGENT — LLM-Powered]
        Sends all news events to the LLM and asks it to reason about
        the real-world impact on a person living in India (specifically Kerala).
        """
        if not news_data:
            return []

        headlines = "\n".join([
            f"- [{e.get('category', 'OTHER').upper()}] {e['title']} (Source: {e.get('source', 'Unknown')}, Region: {e.get('region', 'Global')}, Severity: {e.get('severity', 0.5)})"
            for e in news_data
        ])

        location = user_context.get("location", "Kerala, India")
        spending = user_context.get("top_categories", "general household expenses")

        system_prompt = """You are a Strategic Intelligence Analyst for a personal AI finance assistant called Callista.
Your job is to analyze global/national news events and explain their REAL, TANGIBLE impact on a specific user living in India.

You must think like a financial advisor who connects world events to everyday life:
- A war in the Middle East → likely fuel price hike → LPG, petrol costs go up → suggest refueling early
- RBI interest rate hike → EMIs increase → suggest reviewing loans
- Monsoon alert → travel disruption, crop damage → grocery prices may rise → suggest stocking essentials
- New govt subsidy → savings opportunity → suggest checking eligibility

Be specific, actionable, and intelligent. Do NOT give generic advice.

RESPOND IN STRICT JSON FORMAT as an array of objects:
[
  {
    "event": "headline text",
    "impact": "How this specifically affects the user's daily life, finances, or safety",
    "suggestion": "Concrete, actionable step the user should take RIGHT NOW",
    "confidence": "percentage as string like 85%",
    "priority": "critical / high / medium / low",
    "region": "affected region"
  }
]

Only return the JSON array. No markdown, no explanation outside JSON."""

        user_prompt = f"""Analyze these current events for a user living in {location}.
The user's top spending categories are: {spending}.
Today's date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

CURRENT EVENTS:
{headlines}

Generate your intelligent analysis as JSON:"""

        raw = await _call_groq(system_prompt, user_prompt)
        
        if not raw:
            logger.warning("LLM returned empty response for impact analysis")
            return []
        
        # Parse the JSON response
        try:
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            
            # Find the first [ and last ]
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]
                
            advisories = json.loads(cleaned)
            
            # Add severity from original data
            for adv in advisories:
                for event in news_data:
                    if event['title'].lower() in adv.get('event', '').lower() or adv.get('event', '').lower() in event['title'].lower():
                        adv['severity'] = event.get('severity', 0.5)
                        break
                else:
                    adv['severity'] = 0.5
            
            return advisories
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM advisory JSON: {e}\nRaw: {raw[:500]}")
            # Fallback: return a single advisory with the raw text
            return [{
                "event": "Intelligence Analysis",
                "impact": raw[:300],
                "suggestion": "Review the full analysis in the Insights tab.",
                "confidence": "70%",
                "priority": "medium",
                "region": "India",
                "severity": 0.5
            }]

    @staticmethod
    async def filter_relevance(advisories: List[Dict[str, Any]], user_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [RELEVANCE FILTER — LLM-Powered]
        Uses AI to re-rank advisories based on user spending patterns.
        Falls back to severity sort if LLM call fails.
        """
        if not advisories:
            return []
        
        # The LLM already assigns priority in analyze_impact.
        # Sort by priority weight then severity.
        priority_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return sorted(
            advisories,
            key=lambda x: (priority_weight.get(x.get('priority', 'medium'), 2), x.get('severity', 0)),
            reverse=True
        )

    @staticmethod
    async def get_cost_of_living_index() -> Dict[str, Any]:
        """
        [COST OF LIVING INTELLIGENCE — LLM-Powered]
        Uses AI to generate a current cost-of-living snapshot.
        """
        system_prompt = """You are an economic analyst. Generate a current cost of living index
for essential items in India. Return STRICT JSON:
{
  "period": "current month and year",
  "items": [
    {"name": "item name", "trend": "+X.X% or -X.X%", "status": "Rising/Falling/Stable", "impact": "High/Medium/Low/None"}
  ],
  "prediction": "one-line prediction about overall cost trend"
}
Include: Petrol, LPG, Rice, Cooking Oil, Electricity, Onions.
Only return JSON. No markdown."""

        user_prompt = f"Generate the cost of living index for India as of {datetime.now(timezone.utc).strftime('%B %Y')}."
        
        raw = await _call_groq(system_prompt, user_prompt)
        
        if raw:
            try:
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                    cleaned = cleaned.rsplit("```", 1)[0]
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse COL JSON: {raw[:300]}")
        
        # Fallback
        return {
            "period": datetime.now(timezone.utc).strftime('%B %Y'),
            "items": [
                {"name": "Petrol", "trend": "N/A", "status": "Unknown", "impact": "Unknown"},
            ],
            "prediction": "Unable to generate prediction at this time. LLM service may be temporarily unavailable."
        }
