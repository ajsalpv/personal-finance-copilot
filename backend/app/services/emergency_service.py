import logging
import random
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EmergencyService:
    @staticmethod
    async def get_local_readiness(region: str = "India/Kerala") -> Dict[str, Any]:
        """
        Fetches active emergency alerts for a specific region.
        In production, this would integrate with MET department or Disaster Management APIs.
        """
        # Simulated dynamic risk assessment logic
        alerts = []
        is_kerala = "kerala" in region.lower()
        
        # 1. Weather Logic
        if is_kerala:
            alerts.append({
                "type": "weather",
                "severity": "high",
                "title": "Orange Alert: Heavy Rainfall",
                "description": "Intense rainfall expected in Central/South Kerala over the next 24 hours.",
                "confidence": "92%",
                "prep": [
                    "Avoid mountain travel and coastal areas.",
                    "Ensure secondary power sources (Inverters/Powerbanks) are charged.",
                    "Stock up on 3 days of non-perishable food."
                ]
            })
            
        # 2. Resource/Supply Logic
        alerts.append({
            "type": "resource",
            "severity": "medium",
            "title": "LPG Supply Lag",
            "description": "Logistical delays detected in South India LPG distribution.",
            "confidence": "75%",
            "prep": [
                "Book your next cylinder refill immediately.",
                "Minimize gas-intensive cooking until supply stabilizes."
            ]
        })
        
        # 3. Health Logic
        alerts.append({
            "type": "health",
            "severity": "low",
            "title": "No Critical Outbreaks",
            "description": "National health indicators are within normal seasonal vanity ranges.",
            "confidence": "98%",
            "prep": ["Standard seasonal hygiene is sufficient."]
        })

        return {
            "region": region,
            "active_alerts": alerts,
            "overall_status": "Watchful" if is_kerala else "Stable"
        }

    @staticmethod
    async def get_policy_updates() -> List[Dict[str, Any]]:
        """Tracks major government policy changes affecting finances."""
        return [
            {
                "policy": "New Fuel Subsidy Adjustment",
                "impact": "Potential reduction in petrol prices in India by ₹2.5/L.",
                "date": "Coming Month"
            }
        ]
