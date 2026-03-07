# 🧠 Nova AI Life Assistant

A **privacy-first** personal AI assistant that manages finances, tasks, knowledge, files, and life analytics.

> Your own private Jarvis — fully controlled by you.

## ✨ Features

- 💰 **Finance Tracking** — Income, expenses, budgets, spending analytics
- 📋 **Task Manager** — Tasks, reminders, priorities, recurrence
- 🧠 **Life Memory** — Store & recall personal knowledge with encryption
- 📅 **Daily Timeline** — Automatic life log of all your activities
- 📁 **File Storage** — Upload receipts, bills, documents to Supabase Storage
- 🔔 **Notifications** — Budget warnings, task reminders, insights
- 🤖 **Telegram Bot** — Quick logging via chat commands
- 🎙️ **Voice Auth** — Only YOUR voice can control the assistant
- 🔐 **AES-256 Encryption** — Sensitive data encrypted at rest
- 📤 **Data Export** — CSV, JSON, encrypted backup

## 🛠️ Tech Stack

- **Backend:** Python / FastAPI
- **Database:** PostgreSQL (Supabase)
- **Storage:** Supabase Storage
- **Auth:** JWT + Voice Fingerprint (resemblyzer)
- **Encryption:** AES-256-GCM
- **Bot:** python-telegram-bot
- **AI:** LangChain + Groq (Phase 2+)

## 🚀 Quick Start

```bash
# 1. Create virtual environment
cd backend
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your credentials

# 4. Run database migration
# Copy migrations/001_initial_schema.sql → Supabase SQL Editor → Run

# 5. Start server
python -m uvicorn app.main:app --reload --port 8000
```

API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📱 Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/expense 250 lunch` | Log expense |
| `/income 5000 salary` | Log income |
| `/balance` | Monthly summary |
| `/budget` | Budget status |
| `/task call mom` | Create task |
| `/remember passport expires 2028` | Store memory |
| `/recall passport` | Search memories |
| `/timeline` | Today's events |

## 🔐 Security

- AES-256 encryption for UPI IDs, names, notes, memories
- JWT token authentication
- Voice fingerprint verification
- Row Level Security on all tables
- Owner-only Telegram bot access
- HTTPS/TLS for all communication

## 📦 Development Phases

- [x] **Phase 1** — Core System (FastAPI + Supabase + Telegram)
- [ ] **Phase 2** — AI Automation (LangGraph agents, OCR, NLP)
- [ ] **Phase 3** — Intelligence (Insights, anomaly detection)
- [ ] **Phase 4** — Mobile App (Flutter)
- [ ] **Phase 5** — Voice Assistant (Wake word, speech recognition)
