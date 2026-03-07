from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from app.config import get_settings
from app.services.memory_service import store_reflection, get_long_term_memory
from sqlalchemy.ext.asyncio import AsyncSession
import json

settings = get_settings()

def get_memory_specialist_prompt():
    return SystemMessage(
        content=(
            "You are Callista's Memory Specialist. Your role is to manage and recall personal facts about the user.\n\n"
            "YOUR OBJECTIVE:\n"
            "1. EXTRACT: Identify and extract permanent facts (names, preferences, work details, family, important dates).\n"
            "2. RETRIEVE: Provide relevant long-term context when requested.\n\n"
            "FORMATTING:\n"
            "If extracting a fact, respond with: FACT:[Category]|[Content]\n"
            "Example: FACT:Family|User's daughter is named Emma.\n"
            "Example: FACT:Preference|User likes dark mode and indigo accents."
        )
    )

async def extract_and_store_facts(db: AsyncSession, user_id: str, message_content: str):
    """Analyzes a message to extract any new persistent facts."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0)
    prompt = [
        get_memory_specialist_prompt(),
        SystemMessage(content=f"Analyze this message for new facts: {message_content}")
    ]
    response = await llm.ainvoke(prompt)
    
    if "FACT:" in response.content:
        for line in response.content.split("\n"):
            if line.startswith("FACT:"):
                try:
                    parts = line.replace("FACT:", "").split("|")
                    if len(parts) == 2:
                        category, fact = parts[0].strip(), parts[1].strip()
                        await store_reflection(db, user_id, fact, category)
                except:
                    continue
