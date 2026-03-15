from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from app.config import get_settings
from app.services.memory_service import store_reflection
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def extract_and_store_facts(db: AsyncSession, user_id: str, message_content: str):
    """
    [MEMORY SPECIALIST AGENT]
    Analyzes a message to extract any new persistent facts using intelligent reasoning.
    Zero hardcoded keyword parsing.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0)
    
    system_prompt = """You are Callista's Memory Specialist. Extract permanent facts about the user.
    Facts include: names, preferences, work details, family, important dates, life events.
    
    RESPOND IN STRICT JSON:
    {"extracted_facts": [{"category": "Family/Work/etc", "content": "The fact"}]}
    If no facts are found, return {"extracted_facts": []}. Only return JSON."""
    
    prompt = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=f"User Message: {message_content}")
    ]
    response = await llm.ainvoke(prompt)
    
    try:
        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(cleaned)
        
        for fact_obj in data.get("extracted_facts", []):
            category = fact_obj.get("category", "General")
            content = fact_obj.get("content")
            if content:
                await store_reflection(db, user_id, content, category)
                logger.info(f"Memory Agent extracted fact: {content} ({category})")
    except Exception as e:
        logger.error(f"Memory Specialist Agent failed to parse JSON: {e}")
