# Resume — [Your Name]

## About

I am a software developer focused on building AI-driven chat applications and full-stack web services. I work with Python (FastAPI), React (Vite), and modern tooling to implement production-ready features including LLM integrations, RAG, memory, and conversational graph flows.

## What I Use

- **Languages:** Python, JavaScript (ES6+), SQL
- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Frontend:** React, Vite, JSX, CSS
- **AI / LLM:** OpenAI-compatible LLMs, custom graph-based conversation flows, RAG (retrieval-augmented generation)
- **Dev & Ops:** Docker, docker-compose, Git
- **Databases & Storage:** PostgreSQL (via SQLAlchemy), local file uploads

## What I Implemented (Key Projects & Features)

- Built an AI chat backend with FastAPI and modular node-based conversation graph (see `backend/app/ai/graph/graph.py`).
- Implemented LLM integration and orchestration in `backend/app/ai/llm.py` for prompt handling and response streaming.
- Created RAG and document chunking support in `backend/app/models` and services in `backend/app/services/document_service.py`.
- Added conversational memory and human-approval nodes in `backend/app/ai/nodes/` to manage multi-turn state and moderation.
- Implemented frontend chat UI using React (components under `frontend/src/components`) with a streaming chat input and message window.
- Set up containerized development with `docker-compose.yml` and separate Dockerfiles for backend and frontend.

Detailed Feature Breakdowns

- **Short-term (Working) Memory:** I implemented per-session chat history capture and immediate context management so the LLM receives relevant recent messages. The short-term memory is maintained in-memory while a conversation is active and fed into prompts to preserve turn-taking, clarifications, and follow-ups.

- **Long-term Memory:** I added mechanisms to persist salient conversation artifacts (summaries, key facts, user preferences) to a durable store. These artifacts are encoded as embeddings and indexed in a vector store (local or external) so they can be retrieved later to inform future conversations and personalize responses.

- **Summarization:** To keep long threads manageable and to produce persistent memories, I implemented automatic summarization utilities. Long conversations are periodically summarized into concise memory objects (e.g., persona, important facts, ongoing tasks). Summarizers are implemented as nodes in the conversation graph so they can be triggered on configurable thresholds (message count, time, or explicit actions).

- **Retrieval-Augmented Generation (RAG):** Document uploads and indexed content are split into chunks, embedded, and stored for retrieval. The RAG pipeline retrieves relevant chunks for a query, conditions the LLM with the retrieved context, and produces grounded answers with citations where applicable. See `backend/app/services/document_service.py` and `backend/app/models` for chunking and indexing logic.

- **Conversation Graph & Node System:** The system uses a modular graph where each node represents a processing step (e.g., `chat`, `memory`, `rag`, `summarize`, `human_approval`, `tools`). Nodes can be composed to form flows such as: ingest user message → retrieve long-term memory → inject short-term history → run RAG retrieval → run LLM → post-process (summarize, store memory) → return response. This graph-based design makes adding new behaviors straightforward and testable. See `backend/app/ai/graph/graph.py` and `backend/app/ai/nodes/` for implementations.

- **Human Approval & Moderation:** I added a human-approval node type that can pause automated replies and surface a candidate response for review. This supports higher-risk operations or policy-sensitive outputs.

- **Tooling & Extensibility:** Tool nodes allow external actions (HTTP calls, DB operations, or custom scripts) to be orchestrated inside a conversation flow. The tools layer separates side effects from pure LLM logic for safer operation.

How to Present This Work

- For interviews or portfolio pages, highlight each of the detailed features above and point reviewers to the corresponding files under `backend/app/ai/` and `backend/app/services/`.
- If you'd like, I can convert this into a one-page resume statement per role (e.g., "AI Engineer — built RAG pipeline, long-term memory, graph-based orchestration") and generate a PDF-ready markdown.

## Notable Files to Review

- Backend AI core: backend/app/ai/llm.py
- Conversation graph and state: backend/app/ai/graph/graph.py, backend/app/ai/graph/state.py
- Node implementations: backend/app/ai/nodes/
- API endpoints: backend/app/api/endpoints/
- Frontend app and components: frontend/src/

## How to Use `README.md`

The repository `README.md` contains project overview and run instructions. Keep `resume.md` updated with new features you implement (add bullets under "What I Implemented"). Link to any important files or PRs that show the work.

---

If you'd like, I can: update this with your real name/contact, create a trimmed professional resume version, or generate a PDF-ready markdown to share externally.
