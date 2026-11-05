# INTERVIEW PREP — AI Chatbot (chatAi)

> Scope: AI-layer deep dive (60%) + full-stack brief (40%). Based entirely on the current codebase.
> How to use: Read §1-§2 for pitch, §3-§6 for AI deep dive, §10 for mock Q&A, §12 for 5-min revision.

---

## Table of Contents

1. [30-Second and 2-Minute Pitch](#1-30-second-and-2-minute-pitch)
2. [Architecture Overview](#2-architecture-overview)
3. [End-to-End Request Lifecycle](#3-end-to-end-request-lifecycle)
4. [AI Layer — State](#4-ai-layer--state)
5. [AI Layer — Graph](#5-ai-layer--graph)
6. [AI Layer — Nodes](#6-ai-layer--nodes)
7. [AI Layer — Tools](#7-ai-layer--tools)
8. [AI Layer — LLM + Checkpointer](#8-ai-layer--llm--checkpointer)
9. [RAG Pipeline](#9-rag-pipeline)
10. [Backend / Auth / DB / Frontend Brief](#10-backend--auth--db--frontend-brief)
11. [Mock Interview Q&A (with Answers)](#11-mock-interview-qa-with-answers)
12. [Tricky Follow-ups, Gotchas & Improvements](#12-tricky-follow-ups-gotchas--improvements)
13. [One-Page Rapid Revision](#13-one-page-rapid-revision)
14. [File Map](#14-file-map)

---

## 1. 30-Second and 2-Minute Pitch

**30-second:**
> "I built chatAi, a full-stack AI chatbot: FastAPI + LangGraph backend, React/Redux frontend, Postgres with pgvector. The AI layer is a stateful LangGraph workflow — summarize → chat (Groq LLM with tool-calling) → tools/memory — with persistent checkpoints per conversation, long-term fact memory, rolling summarization, and RAG over user-uploaded PDFs plus calculator and web search tools."

**2-minute:**
> "Frontend is React + Vite + Redux Toolkit. Users log in (JWT), create conversations, send messages, upload PDFs. Backend is FastAPI with SQLAlchemy async. Every chat turn hits `POST /conversations/{id}/chat`. We save the user message, load long-term memories from Postgres, build a LangChain message list with a persona System prompt, and invoke a LangGraph graph keyed by `thread_id = conversation_id`. The graph has four steps: a summarize node that compacts history when it exceeds 6 messages, a chat node that calls Groq's OpenAI-compatible model with bound tools, a ToolNode that executes calculator / DuckDuckGo search / private PDF search, looping back to chat, and finally a memory node that extracts lasting facts. Checkpoints are stored in Postgres via `AsyncPostgresSaver` so history survives restarts. RAG works by chunking PDFs (1000 chars / 200 overlap), embedding with Gemini `gemini-embedding-001` (3072-dim), storing in pgvector, and querying with cosine distance filtered by `user_id`. Long-term memory is a separate `memories` table re-injected as a System message."

**One-liner for resume:**
> "Built stateful LangGraph agent (summarize→chat→tools→memory) with pgvector RAG, Postgres checkpoints, FastAPI + React."

---

## 2. Architecture Overview

```mermaid
flowchart LR
  FE[React + Redux<br/>ChatPage, api.js] -->|JWT Bearer<br/>POST /conversations/:id/chat| BE[FastAPI<br/>app/main.py<br/>api/endpoints/chat.py]
  BE -->|save/load| PG[(Postgres + pgvector<br/>users, conversations,<br/>messages, memories,<br/>documents, chunks)]
  BE -->|ainvoke state + thread_id| G[LangGraph<br/>graph.py]
  G --> S[summarize_node<br/>nodes/summarize.py]
  S --> C[chat_node<br/>nodes/chat.py<br/>Groq LLM + bind_tools]
  C -->|tool_calls?| T[tools_node<br/>ToolNode(all_tools)]
  T --> C
  C -->|no tools| M[memory_node<br/>nodes/memory.py]
  M --> END
  C <-->|calculator / DDG /<br/>search_user_documents| TOOLS[tools.py]
  TOOLS -->|pgvector query| PG
  G <-->|checkpoint read/write| CKPT[(LangGraph checkpoint tables<br/>AsyncPostgresSaver)]
  UP[POST /documents/upload<br/>pypdf + splitter + Gemini] --> PG
```

**Services (`docker-compose.yml`):**

| Service | Image / Build | Ports | Notes |
|---|---|---|---|
| `backend` | `./backend` | `8003:8000` | mounts `./backend:/code`, needs `.env` |
| `frontend` | `./frontend` | `8081:5173` | Vite dev |
| `db` | `pgvector/pgvector:pg16` | `5435:5432` | `CREATE EXTENSION vector`, healthcheck `pg_isready` |

---

## 3. End-to-End Request Lifecycle

Traced for `POST /conversations/42/chat {"content":"Summarize my PDF and multiply 12*8"}`:

1. **Auth** — `app/api/deps.py:16` `get_current_user()` decodes `Authorization: Bearer <JWT>` with `HS256` + `SECRET_KEY`, loads `User`, returns `SimpleNamespace(id, name, email)` (avoids lazy ORM loads).
2. **Ownership check + save user msg** — `app/api/endpoints/chat.py:45-55`: `SELECT Conversation WHERE id=42 AND user_id=current_user.id` → `404` if not owned → insert `Message(role=user)`.
3. **Load long-term memory** — `chat.py:57-63`: `SELECT Memory WHERE user_id=...` → if rows, prepend `SystemMessage("Here are some facts you remember...")`.
4. **Persona + user message** — `chat.py:65-73`: append persona `SystemMessage("You are ChatAI... MUST use calculator... use search_user_documents...")` + `HumanMessage(content)`.
5. **Set tool user context** — `chat.py:82` `set_active_user_id(current_user.id)` sets a `ContextVar` so the `search_user_documents` tool knows who is calling without passing it through the LLM.
6. **Invoke graph** — `chat.py:75-84`:
   ```python
   config = {"configurable": {"thread_id": str(conv_id)}}
   initial_state = {"messages": langchain_messages, "user_id": current_user.id}
   final_state = await app_graph.ainvoke(initial_state, config=config)
   ```
   `app_graph` was built once at startup (`app/main.py:76`).
7. **Inside graph** (see §5): `summarize_node` (no-op if ≤6 msgs) → `chat_node` (Groq call) → maybe `tools_node` → back to `chat_node` → `memory_node` → `END`. Checkpointer automatically merges persisted history for `thread_id=42` with the new messages.
8. **Persist results** — `chat.py:87-90`: `final_state["messages"][-1].content` is the answer; `final_state.get("extracted_memory")` if non-None is inserted into `memories`. `finally: set_active_user_id(None)` clears ContextVar.
9. **Respond** — `chat.py:97-101` saves `Message(role=assistant)` and returns `{status: completed, message: ...}`. Frontend appends it via Redux (`ChatPage.jsx:163-166`).

**Key insight for interview:** the endpoint only sends *new* messages each turn (`[memory System, persona System, Human]`). Full history comes from the LangGraph checkpointer (`thread_id`), not from re-sending DB `messages`. The SQL `messages` table is for UI history + audit, not for the LLM context directly.

---

## 4. AI Layer — State

File: `backend/app/ai/graph/state.py:8-12`

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    summary: Optional[str]
    extracted_memory: Optional[str]
    user_id: Optional[int]
```

| Field | Type | Purpose |
|---|---|---|
| `messages` | `Annotated[List[BaseMessage], operator.add]` | Conversation history. `operator.add` is a **reducer**: each node returns `{"messages": [...]}` and LangGraph concatenates instead of overwriting. `RemoveMessage` ops also flow through this channel (see summarize). |
| `summary` | `Optional[str]` | Rolling summary string maintained by `summarize_node`. |
| `extracted_memory` | `Optional[str]` | Lasting fact string from `memory_node` (e.g. `"User's name is Koushik"`). Endpoint persists it. |
| `user_id` | `Optional[int]` | Passed in `initial_state` but **not currently consumed inside nodes** — document filtering uses `ContextVar`, not this field. Good talking point. |

**Message types flowing through `messages`:** `SystemMessage` (persona, memories, summary), `HumanMessage` (user), `AIMessage` (LLM, may carry `tool_calls`), `ToolMessage` (tool results), `RemoveMessage` (deletion ops — consumed by checkpointer, not sent to LLM).

**Interview line:** "State is a TypedDict with a reducer annotation. That is how LangGraph supports append-only chat history and delete-ops in a single channel."

---

## 5. AI Layer — Graph

File: `backend/app/ai/graph/graph.py:1-39`

```python
workflow = StateGraph(AgentState)
workflow.add_node("summarize_node", summarize_conversation)
workflow.add_node("chat_node", chat_node)
workflow.add_node("memory_node", memory_node)
tool_node = ToolNode(all_tools)
workflow.add_node("tools_node", tool_node)

workflow.set_entry_point("summarize_node")
workflow.add_edge("summarize_node", "chat_node")

def route_tools(state: AgentState):
    messages = state.get("messages", [])
    if not messages:
        return "memory_node"
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools_node"
    return "memory_node"

workflow.add_conditional_edges("chat_node", route_tools)
workflow.add_edge("tools_node", "chat_node")
workflow.add_edge("memory_node", END)

def build_app_graph(checkpointer):
    return workflow.compile(checkpointer=checkpointer)
```

**Topology in words:**

```
ENTRY -> summarize_node -> chat_node -[tool_calls?]-> tools_node -\
              ^                        \--> memory_node -> END    |
              └──────────────────────────── (loop back) ─────────┘
```

- **Entry:** always `summarize_node`. It is idempotent (returns `{}` when short).
- **Conditional:** `chat_node --route_tools--> tools_node | memory_node`. Inspects `messages[-1].tool_calls`.
- **Loop:** `tools_node -> chat_node` lets the LLM see tool outputs and decide to call more tools or answer.
- **Exit:** `memory_node -> END`.

**What is NOT in the graph (be honest):** `nodes/rag.py` and `nodes/tools.py` are empty files. RAG is implemented as a *tool* (`search_user_documents`), not a dedicated node. `nodes/human_approval.py` implements `human_approval_node` with `interrupt()` but is **never added to the workflow** — dead code / future extension. `services/conversation_service.py` and `services/document_service.py` are also empty; logic lives in endpoints.

---

## 6. AI Layer — Nodes

### 6.1 `summarize_node` — `backend/app/ai/nodes/summarize.py:5-46`

```python
if len(messages) <= 6:
    return {}
old_messages = messages[:-4]
# ... build summary_prompt from old_messages + existing summary ...
response = await llm.ainvoke(summary_prompt)
delete_operations = [RemoveMessage(id=m.id) for m in old_messages if hasattr(m, 'id')]
summary_message = SystemMessage(content=f"Summary of conversation so far: {new_summary}")
return {"messages": delete_operations + [summary_message], "summary": new_summary}
```

- **Trigger:** `>6` messages in checkpoint state. Keeps last 4, summarizes the rest.
- **Mechanism:** Returns `RemoveMessage(id=...)` objects through the `messages` channel — the checkpointer deletes those rows; then a `SystemMessage` with the summary is appended so context is preserved.
- **Chaining summaries:** existing `state["summary"]` is included in the prompt ("update this summary").
- **Skips tool messages** with no string content for the summary text.
- **Cost benefit:** bounds prompt length, reduces tokens on long threads.

### 6.2 `chat_node` — `backend/app/ai/nodes/chat.py:35-45`

```python
llm = get_llm()
messages = _sanitize_messages(state.get("messages", []))
llm_with_tools = llm.bind_tools(all_tools)
response = await llm_with_tools.ainvoke(messages)
return {"messages": [response]}
```

- **Sanitization** (`_sanitize_messages`, lines 8-32): drops non-`BaseMessage`, coerces non-string content, drops empty-content non-tool/non-system messages. Comment says old broken checkpoints had empty placeholders that crash OpenAI payload conversion. If everything is dropped, falls back to raw state.
- **Tool binding:** `llm.bind_tools(all_tools)` enables OpenAI-style function calling. The LLM either returns text or `tool_calls`.
- **Async:** `ainvoke` — non-blocking in FastAPI event loop.

### 6.3 `memory_node` — `backend/app/ai/nodes/memory.py:5-36`

```python
if len(messages) < 2:
    return {"extracted_memory": None}
# ... build extraction_prompt + last 6 turns as "User:/AI:" text ...
response = await llm.ainvoke(prompt_messages)
if "NONE" in response.content:
    return {"extracted_memory": None}
return {"extracted_memory": response.content}
```

- Second LLM call per turn (after the answer). Looks at last 6 messages, asks for lasting facts (`"User's name is X"`).
- Sentinel `"NONE"` means nothing to save. Otherwise the endpoint (`chat.py:90`) inserts a `Memory` row.
- **Limitations to mention:** no dedup, no embedding similarity check, substring `"NONE"` check is brittle (e.g. fact containing "NONE" would be dropped), extra LLM latency on every turn.

### 6.4 `human_approval_node` (unwired) — `backend/app/ai/nodes/human_approval.py:26-57`

- Builds `interrupt({"message": "Do you approve...", "tool": tool_name})` from last message's first `tool_calls[0]["name"]`.
- `interrupt()` pauses the graph; resuming requires `Command(resume=...)` from frontend — not implemented. Returns `ToolMessage("user rejected...")` on `False`.
- **Interview answer:** "It's implemented but not in the graph. To wire it I'd insert it between `chat_node` and `tools_node` and add a resume endpoint + frontend approval UI."

### 6.5 Empty placeholders

- `nodes/rag.py`: 0 bytes. RAG retrieval is via tool, not node.
- `nodes/tools.py`: 0 bytes. Tool execution is via `ToolNode(all_tools)` in graph.py.

---

## 7. AI Layer — Tools

File: `backend/app/ai/tools/tools.py:1-124`. Exposed as `all_tools = [calculator, duckduckgo_web_search, search_user_documents]`.

### 7.1 `calculator(expression: str)`

- `safe_eval` parses with `ast.parse(expr, mode='eval')` and only allows `Constant`, `BinOp(Add/Sub/Mult/Div/Pow)`, `UnaryOp(USub/UAdd)`. Anything else raises `ValueError`. No `eval()` — safe from code injection.
- Example: `"125 * 42"` → `"The result of 125 * 42 is 5250."`
- Persona prompt forces usage for math questions.

### 7.2 `duckduckgo_web_search(query: str)`

- Uses `ddgs.DDGS().text(query, max_results=3)`, formats `title/body/URL`. Returns `"No search results found."` on empty. Broad `except` returns error string (never throws — so the agent loop continues).
- No API key needed. Good for current events.

### 7.3 `search_user_documents(query, user_id=None)` (async RAG tool — most important)

```python
resolved_user_id = user_id if user_id is not None else _active_user_id.get()
# Gemini embed -> pgvector cosine_distance query, filter by user_id, limit 3
select(DocumentChunk.content).join(Document)
  .where(Document.user_id == resolved_user_id)
  .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
  .limit(3)
```

- **Auth isolation:** `ContextVar _active_user_id` set per-request in `chat.py:82` and cleared in `finally`. Prevents cross-user leakage. LLM never supplies `user_id` directly.
- **Embeddings:** `GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")` needs `GOOGLE_API_KEY`. Query is embedded live; chunks were embedded at upload.
- **Vector search:** `pgvector` `Vector(3072)` column, `cosine_distance` ordering, top-3 chunk contents joined with `\n\n---\n\n`.
- **Failure modes:** no user context → message; no API key → message; no chunks → "No relevant information...".

### Tool wiring

- `chat_node` binds all three; `ToolNode(all_tools)` in graph executes them (handles parallel `tool_calls`, routes results as `ToolMessage`s). `route_tools` loops until no `tool_calls` remain.

---

## 8. AI Layer — LLM + Checkpointer

**LLM — `backend/app/ai/llm.py:5-20`:**

```python
ChatOpenAI(model=settings.GROQ_MODEL or "openai/gpt-oss-20b",
           api_key=settings.GROQ_API_KEY,
           base_url="https://api.groq.com/openai/v1",
           temperature=0.7, streaming=False)
```

- Groq served via OpenAI-compatible endpoint. Raises `ValueError` if `GROQ_API_KEY` missing.
- `temperature=0.7` (balanced), `streaming=False` (frontend polls via REST, shows typing bubble — no SSE/websocket).
- Settings from `app/core/config.py` (pydantic-settings, `.env`): `DATABASE_URL`, `LANGGRAPH_DB_URL`, `GOOGLE_API_KEY`, `GROQ_MODEL`, `SECRET_KEY`.

**Checkpointer — `app/core/database.py:26-54` + `app/main.py:72-76`:**

- `AsyncPostgresSaver(conn=AsyncConnectionPool(conninfo=LANGGRAPH_DB_URL, open=False, kwargs={"autocommit": True}))`. `autocommit=True` is the fix for `CREATE INDEX CONCURRENTLY ... ActiveSqlTransaction` errors during `checkpointer.setup()`.
- `init_langgraph_checkpointer()` opens pool + runs `setup()` (creates checkpoint tables) at startup; then `app.state.app_graph = build_app_graph(checkpointer)`.
- `thread_id = str(conversation_id)` isolates history per conversation. Restart-safe: history lives in Postgres, not RAM.

---

## 9. RAG Pipeline

**Ingest — `app/api/endpoints/documents.py:44-143` (`POST /documents/upload`):**

1. Validate `.pdf`, non-empty, `GOOGLE_API_KEY` set.
2. Save with UUID filename to `backend/uploads/`.
3. `pypdf.PdfReader` extract text per page → join. Delete file + `400` if unreadable.
4. `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, separators=["\n\n","\n",". "," ",""])`.
5. `GoogleGenerativeAIEmbeddings(gemini-embedding-001).embed_query(chunk)` per chunk (sequential — slow for large PDFs, mention as improvement).
6. Insert `Document(user_id, name, file_path)` + `DocumentChunk(document_id, content, embedding Vector(3072))` in one transaction. Returns `{success, document_id, chunks_created, filename}`.

**Query (at chat time):** LLM decides (via persona instruction) to call `search_user_documents` when the user mentions files/PDFs/documents → tool embeds query → pgvector top-3 filtered by `user_id` → chunks become `ToolMessage` → LLM grounds answer.

**Schema:** `DocumentChunk.embedding = Vector(3072)` (`app/models/document_chunk.py:14`). Must match `gemini-embedding-001` output dim or inserts fail.

**What RAG does NOT do:** no citations/URLs returned, no hybrid (keyword+vector) search, no re-ranking, no per-document filtering (only per-user).

---

## 10. Backend / Auth / DB / Frontend Brief

**API (`backend/app/api/endpoints/`):**

| Endpoint | File | Auth | Notes |
|---|---|---|---|
| `POST /auth/signup` | `auth.py:13` | No | bcrypt hash, unique email check |
| `POST /auth/login` | `auth.py:39` | No | returns `{access_token, token_type:bearer}`, 7-day expiry |
| `POST /conversations/` | `conversations.py:14` | Yes | create title |
| `GET /conversations/` | `conversations.py:30` | Yes | own convs, newest first |
| `POST /conversations/{id}/messages` | `conversations.py:43` | Yes | raw save (non-AI path) |
| `GET /conversations/{id}/messages` | `conversations.py:71` | Yes | ordered asc for UI |
| `PATCH /conversations/{id}` | `conversations.py:95` | Yes | rename title |
| `POST /conversations/{id}/chat` | `chat.py:37` | Yes | full AI flow (§3) |
| `POST /documents/upload` | `documents.py:44` | Yes | PDF RAG ingest (§9) |

**Auth/Security:** `security.py` — `passlib bcrypt` with 72-byte truncation guard, `jose HS256` JWT. `deps.py` — `HTTPBearer` (not OAuth2 form), `SimpleNamespace` return.

**DB models (`app/models/`):** `User(id,name,email,password_hash)`, `Conversation(id,user_id,title,summary,created)`, `Message(id,conversation_id,role,user|assistant|tool,content)`, `Memory(id,user_id,content)`, `Document(id,user_id,name,file_path)`, `DocumentChunk(id,document_id,content,embedding Vector(3072))`. Tables auto-created via `Base.metadata.create_all` + `CREATE EXTENSION vector` (`main.py:67-69`).

**Frontend (`frontend/src/`):**

- `services/api.js` — axios `baseURL = VITE_API_URL || onrender`, Bearer interceptor, `login/signup/createConversation/getConversations/getMessages/sendChatMessage/uploadDocument(multipart)`.
- `features/chat/chatSlice.js` — `messagesByConversation{}`, `messages`, `input`, `isAiTyping`, optimistic `appendUserMessage` with `temp-` id.
- `pages/ChatPage/ChatPage.jsx` — fetches convs/msgs, `handleSend` (optimistic user msg → `sendChatMessage` → `appendAssistantMessage`), `handleUploadDocument` (FormData → status string), logout.
- `components/ChatWindow/ChatWindow.jsx` — auto-scroll, typing bubble. `App.jsx` — `/login` + protected `/chat` routes.

---

## 11. Mock Interview Q&A (with Answers)

**A1. Walk me through the LangGraph topology.**
> Entry `summarize_node` → `chat_node` → conditional `route_tools`: if last AIMessage has `tool_calls` go to `tools_node` (then loop back to `chat_node`), else `memory_node` → `END`. Compiled with Postgres checkpointer. See `graph.py:9-35`.

**A2. What is `AgentState` and why `Annotated[..., operator.add]`?**
> TypedDict with `messages`, `summary`, `extracted_memory`, `user_id`. `operator.add` is the reducer so `{"messages":[x]}` appends instead of overwriting across nodes — required for multi-step history + `RemoveMessage` ops.

**A3. How does the graph remember history across requests?**
> `AsyncPostgresSaver` keyed by `thread_id=str(conversation_id)`. Each `ainvoke` loads prior checkpoint, merges new state, writes back. SQL `messages` table is for UI; LLM context comes from checkpoints.

**A4. What does `summarize_node` do exactly? When does it fire?**
> Fires when `len(messages)>6`. Summarizes all but last 4 via LLM, emits `RemoveMessage`s + a summary `SystemMessage`, stores `summary`. Keeps prompts bounded.

**A5. What is `RemoveMessage`?**
> Special LangChain message that instructs the checkpointer to delete a message ID from persisted state. Returned through the `messages` channel alongside the new summary message.

**A6. How does tool-calling work end-to-end?**
> `chat_node` does `llm.bind_tools(all_tools)`. If LLM returns `tool_calls`, `route_tools` sends to `ToolNode`, which executes and returns `ToolMessage`s, then loops to `chat_node` for a grounded answer. Repeats until no calls.

**A7. What tools exist and when are they used?**
> `calculator` (math, AST-safe), `duckduckgo_web_search` (current info, top 3), `search_user_documents` (private PDFs via pgvector). Persona prompt nudges: math→calculator, file questions→doc search.

**A8. How is cross-user document leakage prevented?**
> `search_user_documents` filters `Document.user_id == resolved_user_id` where ID comes from request-scoped `ContextVar`, not from LLM output. Set/cleared per request in `chat.py:82-95`.

**A9. Why `ContextVar` instead of passing `user_id` in state?**
> `AgentState.user_id` is set but nodes don't read it; tools run inside `ToolNode` with only LLM-provided args. `ContextVar` propagates implicit request context safely in async code without trusting the model to echo the ID.

**A10. How does long-term memory work?**
> `memory_node` extracts facts from last 6 turns with a second LLM call; sentinel `NONE` = skip. Endpoint persists to `memories` table; next turn's prompt prepends them as System message. Short-term = checkpoint history; long-term = Postgres facts.

**A11. Why two LLM calls per turn (chat + memory)? Cost/latency tradeoff?**
> Yes — memory extraction doubles LLM cost/latency on fact-bearing turns. Cheaper: run async/background, only every N turns, or use smaller model / regex pre-filter.

**A12. What LLM and endpoint?**
> `ChatOpenAI` pointed at Groq `https://api.groq.com/openai/v1`, default `openai/gpt-oss-20b`, `temp 0.7`, `streaming=False`. Key from `GROQ_API_KEY`.

**A13. How are PDFs ingested?**
> UUID save → `pypdf` extract → `RecursiveCharacterTextSplitter(1000/200)` → per-chunk Gemini `gemini-embedding-001` → `Document` + `DocumentChunk(Vector(3072))` rows.

**A14. How is the vector query written?**
> `SELECT chunk.content JOIN Document WHERE user_id=X ORDER BY embedding.cosine_distance(query_emb) LIMIT 3`. pgvector extension required.

**A15. What happens if `GROQ_API_KEY` / `GOOGLE_API_KEY` is missing?**
> Groq: `get_llm()` raises `ValueError`; `chat.py` catches all exceptions and returns fallback `"I could not reach the AI model right now."` (also saves it as assistant msg — debatable). Google: upload returns `500`, doc-search tool returns error string to LLM.

**A16. What is `_sanitize_messages` for?**
> Drops stale empty placeholder messages from old checkpoints that crash OpenAI conversion; coerces non-string content. Falls back to raw messages if all filtered.

**A17. Why `autocommit=True` on the LangGraph pool?**
> `checkpointer.setup()` runs `CREATE INDEX CONCURRENTLY` which Postgres forbids inside a transaction. Autocommit avoids `ActiveSqlTransaction`.

**A18. Where is `human_approval` used?**
> Nowhere — implemented with `interrupt()` but not added to graph. To use: `chat_node → human_approval_node → tools_node`, plus a resume API (`Command(resume=...)`) and frontend approve/reject UI.

**A19. Why are `rag.py` / `tools.py` (nodes) and `conversation_service.py` / `document_service.py` empty?**
> Incomplete refactor or placeholders. RAG lives as a tool; services logic lives in endpoints. I'd either implement them or delete to avoid confusion — good to admit in interview.

**A20. How does auth work?**
> Signup hashes with bcrypt (72B guard); login returns HS256 JWT (7d, `sub=user.id`); `HTTPBearer` validates per request; ownership enforced by `WHERE user_id=current_user.id` on every conversation query.

**A21. How does the frontend handle sending?**
> Optimistic: appends `temp-` user message, sets `isAiTyping`, `POST .../chat`, appends returned assistant message. Errors append a fallback assistant bubble. No streaming — typing indicator only.

**A22. How would you add streaming?**
> Set `streaming=True`, use `app_graph.astream_events` + SSE (`StreamingResponse`) in FastAPI, consume with `EventSource`/fetch reader in `ChatWindow`, update Redux incrementally.

**A23. How would you add citations for RAG?**
> Return `(content, document_id, chunk_id)` from tool, pass through `ToolMessage.artifact`, render sources in `ChatMessage`, optionally store in `Message` metadata column.

**A24. What breaks at scale?**
> Sequential per-chunk embedding on upload; memory LLM call every turn; unbounded `memories` re-injection (prompt bloat); no pagination on messages; fallback saves error text as real history (pollutes checkpoints).

**A25. How are embeddings dimensioned?**
> `Vector(3072)` must equal `gemini-embedding-001` output. Mismatch → insert error. Changing models requires migration + re-embed.

**A26. What if the LLM hallucinates a `user_id` arg to `search_user_documents`?**
> Tool prefers explicit arg if provided (`user_id if not None`), else ContextVar. Hardening: ignore LLM-supplied `user_id` entirely and always use ContextVar.

**A27. Sync vs async?**
> Endpoints, nodes, tools (doc search), checkpointer are all `async` (`ainvoke`, `AsyncSession`, `AsyncPostgresSaver`) — safe under FastAPI event loop; no blocking calls except `DDGS` sync search and `pypdf` parse (could offload to threadpool).

**A28. How do you test this?**
> Unit: `safe_eval` cases, `route_tools` branching, `_sanitize_messages`, `memory NONE` handling. Integration: mock LLM + in-memory checkpointer, fake embeddings, pgvector testcontainer. Manual: upload PDF → ask → verify top chunks.

---

## 12. Tricky Follow-ups, Gotchas & Improvements

**Gotchas to mention proactively:**

1. `memory_node` `"NONE" in content` substring check — a fact containing "NONE" is silently dropped. Use exact match / structured output.
2. Error fallback in `chat.py:91-93` saves `"I could not reach..."` as a real assistant message → pollutes checkpoints and future summaries. Better: don't persist, return error status.
3. `AgentState.user_id` is written but never read — dead field; either use it in nodes or remove.
4. `upload` embeds chunks sequentially — slow; batch `embed_documents` + background task (Celery/ARQ) + progress UI.
5. No dedup on `memories` — repeated facts bloat prompts; add embedding similarity check or upsert.
6. `duckduckgo_web_search` is sync inside async graph — can block loop; wrap in `asyncio.to_thread`.
7. `ToolMessage(tool_call_id="rejected")` in human_approval uses a fake ID — real resume needs actual call IDs.

**If asked "what would you improve in 2 weeks":**

- Wire `human_approval_node` for destructive/high-risk tools + resume endpoint.
- Move RAG to a proper node with query rewriting + hybrid search + citations.
- Streaming via SSE, per-document scope, message pagination, background ingest.
- Eval harness: golden Q&A over sample PDFs, tool-use accuracy, summary faithfulness.

**Defensive lines:**

- "RAG-as-tool was a pragmatic choice: fewer nodes, LLM decides retrieval. A dedicated node gives more control over when/how retrieval happens."
- "I kept services thin and logic in endpoints for speed; next step is extracting `conversation_service`/`document_service`."

---

## 13. One-Page Rapid Revision

| Layer | Key fact |
|---|---|
| State | `messages: Annotated[List, operator.add]` appends; `summary/extracted_memory/user_id` optional |
| Graph | `summarize→chat→(tools↺\|memory)→END`, `route_tools` checks `tool_calls` |
| summarize | `>6` msgs → keep 4, `RemoveMessage` + summary SystemMsg |
| chat | sanitize → `bind_tools` → `ainvoke` → return `[response]` |
| memory | last 6 turns → facts or `NONE` → saved to `memories`, re-injected next turn |
| Tools | calculator (AST), DDG top-3, `search_user_documents` (pgvector top-3, `user_id` filter, ContextVar) |
| LLM | Groq OpenAI-compat, `openai/gpt-oss-20b`, `0.7`, no streaming |
| Checkpoint | `AsyncPostgresSaver`, `thread_id=conv_id`, `autocommit=True` for migrations |
| RAG ingest | pypdf → splitter 1000/200 → Gemini 3072-dim → `document_chunks` |
| RAG query | embed query → `cosine_distance` → top-3 own chunks |
| Chat endpoint | save user → load memories → `[mem, persona, human]` → `ainvoke` → save AI + memory |
| Auth | bcrypt + HS256 JWT 7d + `HTTPBearer`, ownership `WHERE user_id` |
| Frontend | Redux optimistic send, `isAiTyping`, axios Bearer, no SSE |
| Unwired | `human_approval` (interrupt), empty `nodes/rag.py`, `nodes/tools.py`, services |
| DB | Postgres+pgvector, `Vector(3072)`, `CREATE EXTENSION vector` |

---

## 14. File Map

```
backend/app/ai/graph/state.py          AgentState
backend/app/ai/graph/graph.py          StateGraph, route_tools, build_app_graph
backend/app/ai/nodes/chat.py           chat_node + sanitize
backend/app/ai/nodes/summarize.py      rolling summary + RemoveMessage
backend/app/ai/nodes/memory.py         fact extraction
backend/app/ai/nodes/human_approval.py interrupt flow (unwired)
backend/app/ai/nodes/rag.py            EMPTY (RAG is a tool)
backend/app/ai/nodes/tools.py          EMPTY (ToolNode used instead)
backend/app/ai/tools/tools.py          calculator, DDG, search_user_documents, ContextVar
backend/app/ai/llm.py                  Groq ChatOpenAI
backend/app/api/endpoints/chat.py      AI orchestration endpoint
backend/app/api/endpoints/documents.py PDF ingest + chunk + embed
backend/app/api/endpoints/auth.py      signup/login JWT
backend/app/api/endpoints/conversations.py CRUD messages/conversations
backend/app/api/deps.py                HTTPBearer -> SimpleNamespace user
backend/app/core/config.py             pydantic-settings (.env)
backend/app/core/database.py           async engine + LangGraph checkpointer pool
backend/app/core/security.py           bcrypt + jose JWT
backend/app/models/                   users, conversations, messages, memories, documents, chunks
backend/app/main.py                    startup: create_all + checkpointer.setup + compile graph
frontend/src/services/api.js           axios + auth + chat/upload calls
frontend/src/features/chat/chatSlice.js messages cache + typing state
frontend/src/pages/ChatPage/ChatPage.jsx send/upload/select flow
docker-compose.yml                     backend:8003, frontend:8081, pgvector:5435
```

> Tip: open `graph.py` + `state.py` + `tools.py` + `chat.py` (endpoint) side-by-side — 90% of AI questions come from those four.
