# ChatAI — Conversational Platform with RAG + LangGraph Memory

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-blue)
![LangChain](https://img.shields.io/badge/LangChain-Tools-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)

> Every conversation is a compiled LangGraph graph — summarized, grounded in your documents, and checkpointed to survive restarts.

**Live demo (frontend):** https://chat-ai-chi-umber.vercel.app
**Backend API:** https://chatai-6p1l.onrender.com
**Repo:** https://github.com/koushikkorada355/chatAi

Chatbots lose context as they grow, hallucinate about user documents, and bolt auth on last. ChatAI fixes all three in one assistant loop: JWT-secured FastAPI APIs over PostgreSQL, a compiled LangGraph StateGraph for reasoning, and PDF RAG over a `document_chunks` pgvector layer.

---

## ✨ Features

**For recruiters / reviewers:**
- Streaming-style conversational UI (React + Vite + Redux Toolkit) with login, protected `/chat` route, multi-conversation sidebar.
- Long conversations stay coherent — automatic summarization compresses aging history.
- Answers grounded in **your PDFs**, not guesses — upload, chunk, embed, retrieve top-3 chunks.
- Real tools, not fake demos: safe calculator, DuckDuckGo web search, per-user document search.
- Production concerns: JWT auth, per-user data isolation, Postgres checkpointer for LangGraph, Docker Compose for one-command run.

**For developers:**
- `POST /conversations/{conv_id}/chat` invokes a compiled graph with `thread_id = conv_id`.
- Short-term memory: recent turns injected per request; long-term memory: `memories` table facts injected as `SystemMessage`.
- Conditional routing: `chat_node` → `tools_node` (if `tool_calls`) → back to `chat_node` → `memory_node` → `END`.
- pgvector cosine-distance search scoped by `user_id` (`search_user_documents`).
- Alembic migrations + `CREATE EXTENSION vector` on startup.

---

## 🧰 Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Uvicorn, SQLAlchemy (async), Alembic, Pydantic Settings, python-jose + passlib/bcrypt (JWT) |
| AI | LangGraph StateGraph + Postgres checkpointer, LangChain Core, langchain-openai / langchain-google-genai, DDGS web search, pypdf + text-splitters |
| DB | PostgreSQL 16 + `pgvector/pgvector:pg16`, models: `users`, `conversations`, `messages`, `memories`, `documents`, `document_chunks` |
| Frontend | React 18, React Router 6, Redux Toolkit + React-Redux, Axios, Vite 5 |
| Infra | Docker + Docker Compose (backend, frontend, db) |

---

## 🏗️ How It Works

```
User message
  → save to messages (role=user)
  → load user memories → SystemMessage("facts you remember…")
  → SystemMessage("You are ChatAI… use calculator / search_user_documents…")
  → graph.ainvoke({messages, user_id}, {thread_id: conv_id})

Graph:
  summarize_node → chat_node → [tool_calls? tools_node → chat_node : memory_node] → END
  → save assistant message + extracted_memory
  → return { status: "completed", message }
```

Key nodes in `backend/app/ai/nodes/`: `chat.py`, `summarize.py`, `memory.py`, `rag.py`, `human_approval.py`, `tools.py`.
Tools in `backend/app/ai/tools/tools.py`: `calculator` (AST-safe eval), `duckduckgo_web_search`, `search_user_documents` (pgvector, user-scoped).

API routers in `backend/app/main.py`:
- `GET /` — health check
- `/auth` — register / login (JWT)
- `/conversations` — CRUD conversations + `POST /conversations/{id}/chat`
- `/documents` — PDF upload, list, search context

Frontend routes in `frontend/src/App.jsx`: `/login` (public), `/chat` (protected), `/` → `/chat`.

---

## 🚀 Quickstart

### Option A — Docker (recommended)

Prerequisites: Docker + Docker Compose.

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Backend (FastAPI + Swagger) | http://localhost:8003 — docs at `/docs` |
| Frontend (Vite) | http://localhost:8081 |
| Postgres (pgvector) | localhost:5435 |

> Note: `docker-compose.yml` maps `8003:8000` and `8081:5173`.

### Option B — Local (without Docker)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head   # or rely on create_all on startup
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

---

## 📁 Project Structure

```
ai-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, routers, startup (vector ext + checkpointer + graph)
│   │   ├── ai/
│   │   │   ├── graph/graph.py      # StateGraph: summarize → chat → tools/memory
│   │   │   ├── graph/state.py      # AgentState
│   │   │   ├── nodes/              # chat, summarize, memory, rag, human_approval, tools
│   │   │   ├── tools/tools.py      # calculator, ddg search, search_user_documents
│   │   │   └── llm.py
│   │   ├── api/endpoints/          # auth, conversations, chat, documents
│   │   ├── models/                 # user, conversation, message, memory, document, document_chunk
│   │   ├── services/               # document_service (chunk + embed)
│   │   └── core/                   # config, database
│   ├── migrations/ + alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # /login, /chat (ProtectedRoute)
│   │   ├── pages/ (LoginPage, ChatPage)
│   │   ├── features/, store.js     # Redux auth slice
│   │   ├── services/api.js         # Axios + setAuthToken
│   │   └── components/
│   └── package.json + Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🔍 Key Files to Inspect

- Graph wiring: `backend/app/ai/graph/graph.py`, `backend/app/ai/graph/state.py`
- Chat endpoint: `backend/app/api/endpoints/chat.py`
- Tools: `backend/app/ai/tools/tools.py`
- Auth + DB: `backend/app/main.py`, `backend/app/core/`
- Frontend auth flow: `frontend/src/App.jsx`, `frontend/src/routes/ProtectedRoute.jsx`, `frontend/src/services/api.js`

---

## 👤 Author

**Sai Koushik Korada** — AI Full Stack Engineer
- GitHub: https://github.com/koushikkorada355
- LinkedIn: https://www.linkedin.com/in/koushik-korada-02187a305/
- Portfolio repo: `koushikkorada.tech`
