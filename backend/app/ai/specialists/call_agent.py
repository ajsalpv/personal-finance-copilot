from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from app.config import get_settings

settings = get_settings()

def get_call_concierge_prompt():
    return SystemMessage(
        content=(
            "You are Callista's Call Concierge, a specialized AI agent tasked with answering phone calls on behalf of the user.\n\n"
            "YOUR OBJECTIVE:\n"
            "1. Answer calls intelligently and professionally.\n"
            "2. Identify the caller and the purpose of the call.\n"
            "3. Collect all necessary information (names, numbers, specific requests).\n"
            "4. Classify the importance: 'CRITICAL' (emergencies, immediate family, high-priority business) vs 'ROUTINE'.\n\n"
            "PROTOCOL:\n"
            "- If CRITICAL: Instruct the phone system to alert the user immediately.\n"
            "- If ROUTINE: Inform the caller that the user is currently unavailable and that you have taken a detailed message.\n"
            "- Tone: Polished, premium, and capable. You are an elite digital secretary."
        )
    )

async def process_call_interaction(message: str) -> str:
    """Specialized logic for call handling."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0.7)
    messages = [get_call_concierge_prompt(), SystemMessage(content=f"Caller said: {message}")]
    response = await llm.ainvoke(messages)
    return response.content
