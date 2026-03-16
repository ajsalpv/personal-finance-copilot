import requests
import uuid
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

# Use unique credentials for testing to avoid conflict if test is rerun
TEST_EMAIL = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASS = "securepassword123"

def print_result(name, res):
    status = res.status_code
    if 200 <= status < 300:
        print(f"PASS ({status}) - {name}")
    else:
        print(f"FAIL ({status}) - {name}")
        print(f"   Response: {res.text[:200]}")

print("--- Starting End-to-End Verification ---")

# 1. Auth - Register
print("\n[Auth]")
res_reg = requests.post(f"{BASE_URL}/auth/register", json={
    "email": TEST_EMAIL,
    "password": TEST_PASS,
    "name": "Test User",
    "telegram_id": None
})
print_result("Register User", res_reg)

# 2. Auth - Login
res_login = requests.post(f"{BASE_URL}/auth/login", json={
    "email": TEST_EMAIL,
    "password": TEST_PASS
})
print_result("Login User", res_login)

if res_login.status_code != 200:
    print("FATAL: Cannot proceed without auth token.")
    exit(1)

token = res_login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Intelligence / Predictive Advisories
print("\n[Intelligence]")
res_adv = requests.get(f"{BASE_URL}/intelligence/advisories", headers=headers)
print_result("Get Advisories (Predictive)", res_adv)

res_emv = requests.get(f"{BASE_URL}/intelligence/emergency", headers=headers)
print_result("Get Emergency Risk", res_emv)

# 4. Tasks
print("\n[Tasks]")
res_task_c = requests.post(f"{BASE_URL}/tasks/", json={"title": "Test Verification Task"}, headers=headers)
print_result("Create Task", res_task_c)

if res_task_c.status_code == 200:
    task_id = res_task_c.json()["id"]
    res_task_u = requests.patch(f"{BASE_URL}/tasks/{task_id}", json={"status": "completed"}, headers=headers)
    print_result("Update Task", res_task_u)

res_tasks_g = requests.get(f"{BASE_URL}/tasks/", headers=headers)
print_result("List Tasks", res_tasks_g)

# 5. Transactions & Categories
print("\n[Transactions]")
res_cat_c = requests.post(f"{BASE_URL}/categories/", json={"name": "Test Category", "type": "expense", "icon": "test"}, headers=headers)
print_result("Create Category", res_cat_c)

if res_cat_c.status_code == 200:
    cat_name = res_cat_c.json()["name"]
    res_txn_c = requests.post(f"{BASE_URL}/transactions/", json={
        "amount": 100.0,
        "type": "expense",
        "category": cat_name,
        "description": "Test Transaction"
    }, headers=headers)
    print_result("Create Transaction", res_txn_c)

res_txn_g = requests.get(f"{BASE_URL}/transactions/", headers=headers)
print_result("List Transactions", res_txn_g)

res_txn_s = requests.get(f"{BASE_URL}/transactions/summary", headers=headers)
print_result("Transaction Summary", res_txn_s)

# 6. Chat & AI Agents
print("\n[Chat & Agents]")
res_chat_1 = requests.post(f"{BASE_URL}/chat/message", json={
    "message": "Hello Callista, can you list my recent tasks?",
    "thread_id": str(uuid.uuid4())
}, headers=headers)
print_result("LLM Chat & Tool Call", res_chat_1)

res_chat_hist = requests.get(f"{BASE_URL}/chat/history", headers=headers)
print_result("Get Chat History", res_chat_hist)

# 7. Budgets
print("\n[Budgets]")
if res_cat_c.status_code == 200:
    res_budg_c = requests.post(f"{BASE_URL}/budgets/", json={
        "category": cat_name,
        "monthly_limit": 500.0
    }, headers=headers)
    print_result("Create Budget", res_budg_c)

res_budg_s = requests.get(f"{BASE_URL}/budgets/status", headers=headers)
print_result("Budget Status", res_budg_s)

print("\n--- Verification Complete ---")
