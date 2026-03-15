"""
Categorization Agent — LLM-Powered Transaction Labeling
Uses semantic reasoning to map merchant names and notes to categories.
"""
import logging
import json
from typing import Dict, List, Any, Optional
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class CategorizationAgent:
    @staticmethod
    async def categorize_transaction(
        merchant: Optional[str], 
        note: Optional[str], 
        amount: float,
        existing_categories: List[str]
    ) -> str:
        """
        [CATEGORIZATION AGENT]
        Analyzes transaction metadata and returns the most appropriate category name.
        """
        system_prompt = f"""You are a Financial Expert for Callista AI.
Look at the transaction data and map it to the MOST RELEVANT category from the list provided.

Allowed Categories: {existing_categories}

Reasoning:
- "Zomato" or "Swiggy" -> "Food & Dining"
- "Uber" or "Petrol" -> "Transport"
- "Netflix" -> "Entertainment"
- If it's a large amount to a generic name -> Check the note.
- If unsure, pick the closest match or "Uncategorized".

RESPOND IN STRICT JSON:
{{
  "category": "category name",
  "confidence": "XX%",
  "reasoning": "Short justification"
}}
Only return JSON."""

        user_input = f"""
        Merchant: {merchant}
        Note: {note}
        Amount: {amount}
        """

        raw_response = await _call_groq(system_prompt, user_input)
        
        try:
            cleaned = raw_response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            
            # Find the first { and last }
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]
                
            data = json.loads(cleaned)
            cat = data.get("category")
            if cat in existing_categories:
                return cat
            # Try to handle capitalization or slight mismatches
            for valid_cat in existing_categories:
                if valid_cat.lower() == str(cat).lower():
                    return valid_cat
            return "Uncategorized"
        except Exception as e:
            logger.error(f"Categorization Agent failed: {e}")
            return "Uncategorized"
