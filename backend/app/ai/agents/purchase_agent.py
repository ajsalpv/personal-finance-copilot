"""
Purchase Agent — LLM-Powered Market Analysis
Replaces static price trend lookups with intelligent reasoning.
"""
import logging
import json
from typing import Dict, List, Any
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class PurchaseAgent:
    @staticmethod
    async def analyze_purchase_timing(item_name: str) -> str:
        """
        [PURCHASE ADVISORY AGENT]
        Analyzes the best time to buy a specific high-value item based on 
        seasonal cycles, tech releases, and inflation trends.
        """
        system_prompt = """You are a Strategic Consumer Advisor for Callista AI.
Look at the item requested and reason about the best time to purchase it in the current market context (early 2026).

Reasoning:
- Tech (Phones/Laptops): Cycles of new releases (Sept/Oct), back-to-school sales, etc.
- Appliances: Seasonal demand (ACs in summer, heaters in winter).
- Commodities (Gold): Geopolitical and economic volatility.
- General: Account for current inflation and upcoming sale festivals (like Big Billion Day in India).

RESPOND IN CLEAR, Jarvis-like prose (max 3 sentences). 
Include a "STATUS: BUY/WAIT/SKIP" at the end."""

        user_input = f"User is asking if they should buy: {item_name}"

        raw_response = await _call_groq(system_prompt, user_input)
        return raw_response.strip()
