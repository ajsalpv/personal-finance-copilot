import asyncio
import os
import json
import sys

# Path setup to import from app
sys.path.append(os.path.abspath(r'a:\Personal projects\Personal Finance Copilot\backend'))

from app.ai.agent import process_message

async def test_agent_routing():
    print("--- TESTING AGENT ROUTING ---")
    
    # Test 1: Language Learning
    print("\nTest 1: Language Learning Routing...")
    try:
        resp1 = await process_message("test_thread", "test_user", "How do I say 'Hello' in Russian?")
        print(f"Reply: {resp1['reply']}")
        if "Привет" in resp1['reply'] or "Privet" in resp1['reply'] or "Hello" in resp1['reply']:
            print("✅ Language Routing Success")
        else:
            print("❌ Language Routing Failed")
    except Exception as e:
        print(f"❌ Error in Test 1: {e}")

    # Test 2: Phone Alarm Tool
    print("\nTest 2: Phone Alarm Tool Calling...")
    try:
        resp2 = await process_message("test_thread", "test_user", "Wake me up at 7am tomorrow.")
        print(f"Reply: {resp2['reply']}")
        if "COMMAND:ALARM|07:00" in resp2['reply'] or "07:00" in resp2['reply']:
            print("✅ Alarm Tool Success")
        else:
            print("❌ Alarm Tool Failed")
    except Exception as e:
        print(f"❌ Error in Test 2: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent_routing())
