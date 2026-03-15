import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.agents.travel_agent import TravelAgent

logger = logging.getLogger(__name__)

class LocationService:
    @staticmethod
    async def log_location(
        db: AsyncSession, 
        user_id: str, 
        latitude: float, 
        longitude: float, 
        city: Optional[str] = None, 
        locality: Optional[str] = None
    ):
        """Logs a new location entry for the user."""
        try:
            query = """
                INSERT INTO location_history (user_id, latitude, longitude, city, locality)
                VALUES (:user_id, :latitude, :longitude, :city, :locality)
            """
            await db.execute(
                text(query),
                {
                    "user_id": user_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": city,
                    "locality": locality
                }
            )
            await db.commit()
            logger.info(f"Logged location for user {user_id}: {locality}, {city}")
        except Exception as e:
            logger.error(f"Error logging location: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_recent_locations(db: AsyncSession, user_id: str, limit: int = 10) -> List[Dict]:
        """Retrieves the most recent location entries for a user."""
        query = text("""
            SELECT latitude, longitude, city, locality, timestamp 
            FROM location_history 
            WHERE user_id = :user_id 
            ORDER BY timestamp DESC 
            LIMIT :limit
        """)
        result = await db.execute(query, {"user_id": user_id, "limit": limit})
        return [dict(row._mapping) for row in result]

    @staticmethod
    async def detect_travel_anomaly(db: AsyncSession, user_id: str) -> Optional[Dict]:
        """
        Uses the TravelAgent to intelligently detect if the user is traveling.
        Zero hardcoded "city match" rules remain.
        """
        try:
            # 1. Get current (most recent) location
            current_res = await db.execute(
                text("SELECT city, locality, latitude, longitude, timestamp FROM location_history WHERE user_id = :user_id ORDER BY timestamp DESC LIMIT 1"),
                {"user_id": user_id}
            )
            current_row = current_res.fetchone()
            if not current_row:
                return None
            
            current_loc = {
                "city": current_row[0], 
                "locality": current_row[1], 
                "lat": current_row[2], 
                "lon": current_row[3],
                "time": current_row[4].isoformat()
            }

            # 2. Get 7-day history context
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            history_res = await db.execute(
                text("SELECT city, locality, COUNT(*) as frequency FROM location_history WHERE user_id = :user_id AND timestamp > :start GROUP BY city, locality ORDER BY frequency DESC"),
                {"user_id": user_id, "start": seven_days_ago}
            )
            history = [dict(row._mapping) for row in history_res.fetchall()]

            # 3. Delegate to TravelAgent for LLM reasoning
            user_context = {"top_categories": ["fuel", "travel"]} # Mock
            travel_data = await TravelAgent.analyze_location_shift(current_loc, history, user_context)

            if travel_data:
                return {
                    "is_traveling": True,
                    "current_city": travel_data.get("detected_destination"),
                    "home_base": travel_data.get("detected_home_base"),
                    "reasoning": travel_data.get("reasoning"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Error in detect_travel_anomaly: {e}")
        
        return None
