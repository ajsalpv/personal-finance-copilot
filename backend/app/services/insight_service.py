import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy import text
from app.database import async_session_factory
from app.services import notification_service

logger = logging.getLogger(__name__)

async def detect_anomalies(user_id: str) -> None:
    """
    Scans recent transactions for the user and detects anomalies based on historical averages.
    If an anomaly > 200% of category average is found, an insight/notification is created.
    """
    async with async_session_factory() as db:
        # Get category averages for the last 3 months
        three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        avg_query = text("""
            SELECT category, AVG(amount) as avg_amount
            FROM transactions 
            WHERE user_id = :uid 
              AND transaction_type = 'expense' 
              AND date >= :start_date
              AND category IS NOT NULL
            GROUP BY category
        """)
        
        result = await db.execute(avg_query, {"uid": user_id, "start_date": three_months_ago})
        averages = {row[0]: row[1] for row in result.fetchall()}
        
        if not averages:
            return # Not enough data
            
        # Check current month transactions
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        recent_query = text("""
            SELECT id, amount, category, merchant_name, date
            FROM transactions
            WHERE user_id = :uid
              AND transaction_type = 'expense'
              AND date >= :start_date
              AND category IS NOT NULL
        """)
        
        recent_result = await db.execute(recent_query, {"uid": user_id, "start_date": month_start})
        recent_txns = recent_result.fetchall()
        
        for txn in recent_txns:
            cat = txn[2]
            amount = float(txn[1])
            avg = float(averages.get(cat, 0))
            
            # Anomaly condition: Spend is > 200% of average OR simply very high outlier
            if avg > 100 and amount > (avg * 2):
                msg = f"Anomaly detected: ₹{amount:.0f} spent on {cat}. This is {(amount/avg):.1f}x higher than your usual average of ₹{avg:.0f}."
                
                # Check if we already notified about this exact transaction
                exist_check = await db.execute(
                    text("SELECT 1 FROM insights WHERE user_id = :uid AND message = :msg"),
                    {"uid": user_id, "msg": msg}
                )
                if not exist_check.first():
                    # Create insight
                    await db.execute(
                        text("INSERT INTO insights (user_id, insight_type, message) VALUES (:uid, 'anomaly', :msg)"),
                        {"uid": user_id, "msg": msg}
                    )
                    await db.commit()
                    
                    # Notify user
                    await notification_service.create_notification(
                        db, user_id, "anomaly_alert", "🚨 Spend Anomaly", msg
                    )

async def generate_monthly_forecast(user_id: str) -> None:
    """Calculates spending velocity and logs an insight if the user is trending to break budgets."""
    try:
        from app.services import budget_service
        async with async_session_factory() as db:
            statuses = await budget_service.get_budget_status(db, user_id)
            
            now = datetime.now(timezone.utc)
            import calendar
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            days_passed = now.day
            
            for status in statuses:
                limit = status["monthly_limit"]
                spent = status["spent"]
                cat = status["category"]
                
                if spent == 0 or days_passed == 0:
                    continue
                    
                daily_velocity = spent / days_passed
                projected_spend = daily_velocity * days_in_month
                
                if projected_spend > limit * 1.1: # Trending 10% over budget
                    msg = f"Forecast Alert: At your current rate, you will spend ₹{projected_spend:.0f} on {cat} this month (Limit: ₹{limit:.0f})."
                    
                    # Store insight
                    await db.execute(
                        text("INSERT INTO insights (user_id, insight_type, message) VALUES (:uid, 'forecast', :msg)"),
                        {"uid": user_id, "msg": msg}
                    )
                    await db.commit()
    except Exception as e:
        logger.error(f"Error in generate_monthly_forecast: {e}")
