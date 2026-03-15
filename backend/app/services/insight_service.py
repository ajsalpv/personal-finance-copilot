import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy import text
from app.database import async_session_factory
from app.services import notification_service
from app.ai.agents.insight_agent import InsightAgent

logger = logging.getLogger(__name__)

async def detect_anomalies(user_id: str) -> None:
    """
    Scans recent transactions and uses the InsightAgent to detect behavioral anomalies.
    Replaces the hardcoded >200% threshold with LLM reasoning.
    """
    async with async_session_factory() as db:
        # 1. Gather Data context
        three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
        avg_query = text("""
            SELECT category, AVG(amount) as avg_amount
            FROM transactions WHERE user_id = :uid AND transaction_type = 'expense' 
            AND date >= :start_date AND category IS NOT NULL GROUP BY category
        """)
        result = await db.execute(avg_query, {"uid": user_id, "start_date": three_months_ago})
        averages = {row[0]: float(row[1]) for row in result.fetchall()}
        
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        recent_query = text("""
            SELECT id, amount, category, merchant_name, date, note
            FROM transactions WHERE user_id = :uid AND transaction_type = 'expense'
            AND date >= :start_date AND category IS NOT NULL
        """)
        recent_result = await db.execute(recent_query, {"uid": user_id, "start_date": month_start})
        recent_txns = [dict(row._mapping) for row in recent_result.fetchall()]
        
        if not recent_txns:
            return

        # 2. Delegate to InsightAgent for Reasoning
        # Convert objects to JSON-serializable for the agent
        transactions_data = []
        for t in recent_txns:
            transactions_data.append({
                "id": str(t["id"]),
                "amount": float(t["amount"]),
                "category": t["category"],
                "merchant": t["merchant_name"],
                "date": t["date"].isoformat()
            })

        anomalies = await InsightAgent.detect_anomalies(transactions_data, averages)

        # 3. Handle Findings
        for threat in anomalies:
            msg = threat.get("message", "Unusual spending activity detected.")
            severity = threat.get("severity", "medium")
            
            # Idempotency check
            exist_check = await db.execute(
                text("SELECT 1 FROM insights WHERE user_id = :uid AND message = :msg"),
                {"uid": user_id, "msg": msg}
            )
            if not exist_check.first():
                await db.execute(
                    text("INSERT INTO insights (user_id, insight_type, message) VALUES (:uid, 'anomaly', :msg)"),
                    {"uid": user_id, "msg": msg}
                )
                await db.commit()
                
                emoji = "🚨" if severity in ["critical", "high"] else "💡"
                await notification_service.create_notification(
                    db, user_id, "anomaly_alert", f"{emoji} Spend Insight", msg
                )

async def generate_monthly_forecast(user_id: str) -> None:
    """Calculates spending velocity and uses LLM to reason about month-end results."""
    try:
        from app.services import budget_service
        async with async_session_factory() as db:
            statuses = await budget_service.get_budget_status(db, user_id)
            if not statuses:
                return
                
            now = datetime.now(timezone.utc)
            user_context = {
                "day_of_month": now.day,
                "month_name": now.strftime("%B"),
                "year": now.year,
                "is_weekend": now.weekday() >= 5
            }
            
            # Delegate to InsightAgent
            forecasts = await InsightAgent.generate_forecast(statuses, user_context)
            
            for f in forecasts:
                msg = f.get("message")
                priority = f.get("priority", "low")
                if not msg: continue
                
                # Store if not already exists (basic deduplication by message)
                chk = await db.execute(text("SELECT 1 FROM insights WHERE user_id = :u AND message = :m"), {"u": user_id, "m": msg})
                if not chk.first():
                    await db.execute(
                        text("INSERT INTO insights (user_id, insight_type, message) VALUES (:uid, 'forecast', :msg)"),
                        {"uid": user_id, "msg": msg}
                    )
                    await db.commit()
                    
                    if priority == "high":
                        await notification_service.create_notification(
                            db, user_id, "forecast_warning", "📉 Budget Forecast", msg
                        )
    except Exception as e:
        logger.error(f"Error in generate_monthly_forecast agent loop: {e}")
