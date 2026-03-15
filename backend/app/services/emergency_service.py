import logging
from typing import Dict, List, Any
from app.ai.agents.emergency_agent import EmergencyAgent

logger = logging.getLogger(__name__)

class EmergencyService:
    @staticmethod
    async def get_local_readiness(region: str = "India/Kerala") -> Dict[str, Any]:
        """
        Fetches active emergency alerts by delegating to the EmergencyAgent LLM.
        Zero hardcoded rules remain.
        """
        try:
            # Passing minimal context; in production this would pull real-time stats
            user_context = {"top_categories": ["fuel", "groceries"]}
            return await EmergencyAgent.analyze_regional_risks(region, user_context)
        except Exception as e:
            logger.error(f"Error in EmergencyService readiness: {e}")
            return {
                "region": region,
                "active_alerts": [],
                "overall_status": "Unknown (Service Error)"
            }

    @staticmethod
    async def get_policy_updates(region: str = "India") -> List[Dict[str, Any]]:
        """
        Tracks major government policy changes using the EmergencyAgent LLM.
        Zero hardcoded rules remain.
        """
        try:
            return await EmergencyAgent.analyze_policy_updates(region)
        except Exception as e:
            logger.error(f"Error in Policy updates: {e}")
            return []
