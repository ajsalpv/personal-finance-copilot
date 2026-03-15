from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.auth import get_current_user
from app.database import get_db
from app.services.news_intelligence import NewsIntelligenceService
from app.services.emergency_service import EmergencyService
from app.services.transaction_service import get_transactions
from datetime import datetime, timezone, timedelta

router = APIRouter()

@router.get("/advisories")
async def get_predictive_advisories(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch personalized geopolitical and economic advisories powered by AI."""
    try:
        user_id = str(current_user["id"])
        
        # Build user context for the LLM
        user_context = {
            "location": "Kerala, India",
            "top_categories": ["fuel", "groceries", "tech", "transport"],
            "current_city": "Kochi"
        }
        
        # AI-powered pipeline: Fetch → Analyze (LLM) → Filter
        news = await NewsIntelligenceService.fetch_global_risks()
        advisories = await NewsIntelligenceService.analyze_impact(news, user_context)
        filtered = await NewsIntelligenceService.filter_relevance(advisories, user_context)
        
        return {"advisories": filtered}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emergency")
async def get_emergency_alerts(
    region: str = "India/Kerala",
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch local emergency and readiness alerts."""
    try:
        report = await EmergencyService.get_local_readiness(region)
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-of-living")
async def get_col_index(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch current cost of living trends for essentials."""
    try:
        index = await NewsIntelligenceService.get_cost_of_living_index()
        return {"index": index}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
