import logging
import httpx
import os
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class NewsIntelligenceService:
    @staticmethod
    async def fetch_global_risks() -> List[Dict[str, Any]]:
        """
        [NEWS MONITORING AGENT]
        Fetches trending global news related to economy, war, and energy.
        """
        try:
            # Simulated multi-source ingestion
            return [
                {
                    "title": "Middle East supply chains disrupted as conflict escalates",
                    "category": "geopolitics",
                    "source": "Global News Network",
                    "region": "Middle East",
                    "severity": 0.85,
                    "keywords": ["oil", "petrol", "supply chain", "shipping"]
                },
                {
                    "title": "RBI signals potential interest rate hike amid rising inflation in India",
                    "category": "economy",
                    "source": "Financial Express",
                    "region": "India",
                    "severity": 0.65,
                    "keywords": ["inflation", "rbi", "interest rate", "loan"]
                },
                {
                    "title": "Heavy monsoon predicted for Southern India; Kerala on orange alert",
                    "category": "climate",
                    "source": "MET Department",
                    "region": "India/Kerala",
                    "severity": 0.90,
                    "keywords": ["rain", "kerala", "flood", "agriculture"]
                },
                {
                    "title": "New central subsidy for electric vehicles announced in India",
                    "category": "policy",
                    "source": "GovT Business",
                    "region": "India",
                    "severity": 0.40,
                    "keywords": ["subsidy", "ev", "electric car", "green energy"]
                }
            ]
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    @staticmethod
    async def analyze_impact(news_data: List[Dict[str, Any]], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [IMPACT ANALYSIS AGENT]
        Analyzes how global/national events translate to local effects in India/Kerala.
        """
        advisories = []
        for event in news_data:
            impact_desc = ""
            confidence = event['severity'] * 100 # Simple confidence mapping
            
            if "oil" in event['keywords']:
                impact_desc = "Direct impact on Crude Oil supply chains. Expect LPG and Petrol price hikes in India in 1-2 weeks."
            elif "inflation" in event['keywords']:
                impact_desc = "Local inflation indicators rising. Borrowing costs and daily grocery prices may increase."
            elif "kerala" in event['keywords'].lower() or "rain" in event['keywords']:
                impact_desc = "High risk of travel disruption and resource shortages in Kerala due to weather."
            elif "subsidy" in event['keywords']:
                impact_desc = "New policy incentive detected. High potential for personal savings on green tech."
            
            if impact_desc:
                advisories.append({
                    "event": event['title'],
                    "impact": impact_desc,
                    "region": event['region'],
                    "confidence": f"{int(confidence)}%",
                    "suggestion": NewsIntelligenceService._generate_advisory(event),
                    "severity": event['severity']
                })
        
        return advisories

    @staticmethod
    async def filter_relevance(advisories: List[Dict[str, Any]], user_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [RELEVANCE FILTER AGENT]
        Prioritizes alerts based on user's location and spending habits.
        """
        filtered = []
        user_cats = user_stats.get("top_categories", [])
        user_city = user_context.get("current_city", "Unknown")

        for advisory in advisories:
            priority = "medium"
            
            # Location relevance (e.g. Kerala)
            if "Kerala" in advisory['region'] or user_city in advisory['region']:
                priority = "high"
            
            # Spending relevance (e.g. high Fuel spend)
            if any(kw in str(user_cats).lower() for kw in ["fuel", "petrol", "lpg"]):
                if "oil" in str(advisory['event']).lower():
                    priority = "critical"
            
            advisory['priority'] = priority
            filtered.append(advisory)
            
        return sorted(filtered, key=lambda x: x['severity'], reverse=True)

    @staticmethod
    def _generate_advisory(event: Dict[str, Any]) -> str:
        """[PERSONAL ADVISORY AGENT]"""
        kws = event['keywords']
        if "oil" in kws:
            return "Consider booking your LPG refill early and refilling your vehicle within 48 hours."
        if "rain" in kws:
            return "Avoid non-essential long-distance travel in Kerala. Ensure power banks and basic groceries are stocked."
        if "inflation" in kws:
            return "Review your recurring subscriptions and optimize food delivery spending."
        if "subsidy" in kws:
            return "Check eligibility for the new EV scheme if you were planning a vehicle purchase."
        return "Stay tuned for system updates on this event."

    @staticmethod
    async def get_cost_of_living_index() -> Dict[str, Any]:
        """[COST OF LIVING INTELLIGENCE]"""
        # Simulated price tracking for essential items in India
        return {
            "period": "March 2026",
            "items": [
                {"name": "Petrol", "trend": "+4.2%", "status": "Rising", "impact": "High"},
                {"name": "LPG (14.2kg)", "trend": "+2.0%", "status": "Rising", "impact": "Medium"},
                {"name": "Cooking Oil", "trend": "-1.5%", "status": "Stable", "impact": "Low"},
                {"name": "Electricity", "trend": "0.0%", "status": "Stable", "impact": "None"}
            ],
            "prediction": "Overall cost of living in India expected to rise by 1.2% this quarter."
        }
