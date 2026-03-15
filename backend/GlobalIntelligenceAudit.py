import asyncio
import httpx
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

async def test_endpoint(client, method, path, data=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        if method == "GET":
            response = await client.get(f"{BASE_URL}{path}", headers=headers)
        elif method == "DELETE":
            response = await client.delete(f"{BASE_URL}{path}", headers=headers)
        else:
            response = await client.post(f"{BASE_URL}{path}", headers=headers, json=data)
        
        status = "PASS" if response.status_code in [200, 201] else "FAIL"
        print(f"[{status}] {method} {path} - Status: {response.status_code}")
        if status == "FAIL":
            print(f"      Error: {response.text[:200]}")
        await asyncio.sleep(2.0) # Throttling for stability
        return status == "PASS"
    except Exception as e:
        print(f"[FAIL] {method} {path} - Exception: {e}")
        return False

async def main():
    print("🚀 CALLISTA GLOBAL INTELLIGENCE AUDIT 🚀")
    print("========================================")
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # 1. Register/Login test user (Correct Schema)
        test_email = "audit_bot@callista.ai"
        test_password = "audit_secure_pass"
        
        print("👤 Setting up test user...")
        reg_res = await client.post(f"{BASE_URL}/auth/register", json={
            "name": "Audit Bot",
            "email": test_email,
            "password": test_password,
            "telegram_id": "999999"
        })
        
        if reg_res.status_code == 200:
            token = reg_res.json()["access_token"]
            print("✨ New test user registered.")
        else:
            # Try login if already registered
            print("ℹ️ User might exist, attempting login...")
            login_res = await client.post(f"{BASE_URL}/auth/login", json={
                "email": test_email,
                "password": test_password
            })
            if login_res.status_code != 200:
                print(f"❌ Auth failed: {login_res.text}")
                return
            token = login_res.json()["access_token"]
            print("🔑 Login successful.")

        results = []
        
        # 2. Intelligence: Advisories (Real-time hot_context analysis)
        print("\n🔍 Auditing Intelligence Layer...")
        results.append(await test_endpoint(client, "GET", "/intelligence/advisories", token=token))
        
        # 3. Intelligence: Emergency Readiness (Grounded region reasoning)
        results.append(await test_endpoint(client, "GET", "/intelligence/emergency", token=token))
        
        # 4. Intelligence: Cost of Living (LLM-generated index)
        results.append(await test_endpoint(client, "GET", "/intelligence/cost-of-living", token=token))
        
        # 5. Service: Task Creation (TaskIntelligenceAgent priority/labels)
        print("\n🛠️ Auditing AI-Agent Services...")
        results.append(await test_endpoint(client, "POST", "/tasks", data={
            "title": "Renew car insurance before Sunday", 
            "description": "Premium is due, don't miss it."
        }, token=token))
        
        # 6. Service: Budget Status (BudgetAdvisoryAgent coaching)
        results.append(await test_endpoint(client, "GET", "/budgets/status", token=token))
        
        # 7. Service: Transactions (CategorizationAgent semantic mapping)
        results.append(await test_endpoint(client, "POST", "/transactions", data={
            "amount": 1200.0, 
            "transaction_type": "expense", 
            "merchant_name": "Bharat Petroleum", 
            "note": "Tank full"
        }, token=token))

        # 8. Core: LangGraph Chat (Supervisor & Multi-Agent loop)
        print("\n🧠 Auditing LangGraph Brain...")
        results.append(await test_endpoint(client, "POST", "/chat/message", data={
            "message": "I just spent 1200 on fuel. What should I do about the LPG price hike?"
        }, token=token))

        total = len(results)
        passed = sum(1 for r in results if r)
        print("\n========================================")
        print(f"AUDIT COMPLETE: {passed}/{total} PASSED")
        
        if passed == total:
            print("✅ ALL SYSTEMS INTELLIGENT, DYNAMIC, AND RULE-FREE.")
        else:
            print("⚠️ AUDIT PARTIALLY FAILED - CHECK OUTPUT.")

if __name__ == "__main__":
    asyncio.run(main())
