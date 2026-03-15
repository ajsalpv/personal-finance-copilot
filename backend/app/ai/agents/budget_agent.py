"""
Budget Advisory Agent — LLM-Powered Spend Sentiment Analysis
Provides intelligent coaching instead of just percentage math.
"""
import logging
import json
from typing import Dict, Any, List
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class BudgetAdvisoryAgent:
    @staticmethod
    async def analyze_budget_status(category: str, limit: float, spent: float) -> str:
        """
        [BUDGET ADVISORY AGENT]
        Analyzes the spending vs budget and provides a Jarvis-like coaching advice.
        """
        percentage = (spent / limit * 100) if limit > 0 else 0
        
        system_prompt = """You are Callista's Financial Wellness Coach. 
Instead of just stating numbers, provide a highly intelligent "Spend Sentiment" analysis.

Reasoning:
- 0-50%: Commend the user for discipline.
- 50-90%: Gentle caution, mention velocity.
- 90-100%: Urgent alert, suggest specific trade-offs.
- >100%: Remedial advice, ask for the "story" behind the spike to learn if it's an investment or impulse.

RESPOND IN JARVIS-LIKE PROSE (max 2 sentences). Include a "SENTIMENT: Conservative/Balanced/Aggressive/Critical" tag."""

        user_input = f"Category: {category}\nBudget: {limit}\nSpent: {spent} ({percentage:.1f}%)"

        return await _call_groq(system_prompt, user_input)
