import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import select, insert, desc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

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
                select(1), # Placeholder to ensure DB connectivity
            )
            # Using actual SQLAlchemy core for reliability
            from sqlalchemy.sql import text
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
        from sqlalchemy.sql import text
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
        Detects if the user has traveled to a new city compared to their 
        most frequent location in the last 7 days.
        """
        from sqlalchemy.sql import text
        
        # 1. Get current (most recent) city
        current_res = await db.execute(
            text("SELECT city FROM location_history WHERE user_id = :user_id ORDER BY timestamp DESC LIMIT 1"),
            {"user_id": user_id}
        )
        current_city_row = current_res.fetchone()
        if not current_city_row or not current_city_row[0]:
            return None
        
        current_city = current_city_row[0]

        # 2. Get most frequent city in last 7 days
        freq_query = text("""
            SELECT city, COUNT(*) as count
            FROM location_history
            WHERE user_id = :user_id AND timestamp > :seven_days_ago
            GROUP BY city
            ORDER BY count DESC
            LIMIT 1
        """)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        freq_res = await db.execute(freq_query, {"user_id": user_id, "seven_days_ago": seven_days_ago})
        home_city_row = freq_res.fetchone()
        
        if not home_city_row:
            return None
            
        home_city = home_city_row[0]

        if current_city != home_city:
            return {
                "is_traveling": True,
                "current_city": current_city,
                "home_base": home_city,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return None
