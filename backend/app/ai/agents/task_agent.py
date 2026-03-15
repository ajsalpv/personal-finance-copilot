"""
Task Intelligence Agent — LLM-Powered Task Management
Analyzes task content to determine priority, categorization, and reminders.
"""
import logging
import json
from typing import Dict, Any, Optional
from app.services.news_intelligence import _call_groq

logger = logging.getLogger(__name__)

class TaskIntelligenceAgent:
    @staticmethod
    async def analyze_task(title: str, description: Optional[str]) -> Dict[str, Any]:
        """
        [TASK INTELLIGENCE AGENT]
        Analyzes a task and returns an intelligent priority and suggested category.
        """
        system_prompt = """You are a Productivity Specialist Agent for Callista AI.
Analyze the task provided and determine the best priority and a short category label.

Reasoning Guidelines:
- "Critical/High": Deadline is today, relates to bills, health, or urgent work.
- "Medium": General errands, chores, or non-urgent work.
- "Low": Long-term goals, "someday" items, or minor interests.

RESPOND IN STRICT JSON:
{
  "priority": "low/medium/high/critical",
  "category": "String (e.g., Health, Finance, Chores, Work, Social)",
  "reasoning": "Short justification"
}
Only return JSON."""

        user_input = f"Task Title: {title}\nDescription: {description or 'N/A'}"

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
                
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Task Intelligence Agent failed: {e}")
            return {
                "priority": "medium",
                "category": "General",
                "reasoning": "Agent logic failed; using defaults."
            }
