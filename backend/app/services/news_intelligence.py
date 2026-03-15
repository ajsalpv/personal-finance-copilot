import logging
import httpx
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Note: In a real production environment, you'd use a paid API like NewsAPI.org or GNews.
# For this implementation, we'll use a robust placeholder system that can be easily connected 
# to a real API Key.

class NewsIntelligenceService:
    @staticmethod
    async def fetch_global_risks() -> List[Dict[str, Any]]:
        """
        Fetches trending global news related to economy, war, and energy.
        """
        try:
            # Placeholder for real News API integration
            # api_key = os.getenv("NEWS_API_KEY")
            # url = f"https://newsapi.org/v2/top-headlines?category=business&q=war+oil+economy&apiKey={api_key}"
            
            # Simulated real-time geopolitical feed for demonstration
            return [
                {
                    "title": "Tensions rise in Middle East; Crude Oil prices surge by 4%",
                    "category": "economy",
                    "region": "global",
                    "impact_level": "high",
                    "keywords": ["oil", "petrol", "fuel", "inflation"]
                },
                {
                    "title": "New GST regulations announced for digital services in India",
                    "category": "legal",
                    "region": "India",
                    "impact_level": "medium",
                    "keywords": ["tax", "gst", "subscriptions", "netflix"]
                },
                {
                    "title": "Global Tech Layoffs: Major firms restructure for AI-first model",
                    "category": "career",
                    "region": "global",
                    "impact_level": "medium",
                    "keywords": ["jobs", "salary", "tech", "ai"]
                }
            ]
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    @staticmethod
    async def analyze_risk_impact(user_transactions: List[Dict[str, Any]], news_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Correlates news events with user's spending patterns and locations.
        """
        advisories = []
        user_categories = {t['category'].lower() for t in user_transactions}
        
        for event in news_data:
            match = False
            for kw in event['keywords']:
                if kw in user_categories or any(kw in str(t.get('merchant_name', '')).lower() for t in user_transactions):
                    match = True
                    break
            
            if match:
                advisories.append({
                    "event": event['title'],
                    "impact": f"Based on your high spending in '{event['category']}', this event might increase your monthly expenses.",
                    "suggestion": NewsIntelligenceService._get_suggestion(event),
                    "impact_level": event['impact_level']
                })
        
        return advisories

    @staticmethod
    def _get_suggestion(event: Dict[str, Any]) -> str:
        kws = event['keywords']
        if "fuel" in kws or "oil" in kws:
            return "Consider refueling today before the price hike ripples through local distributors."
        if "gst" in kws or "tax" in kws:
            return "Review your active subscriptions to see if any price updates are coming."
        if "jobs" in kws:
            return "Ensure your emergency fund covers at least 6 months of current expenses."
        return "Keep an eye on this event for further developments."
