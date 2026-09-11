import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import engine, Base, init_langgraph_checkpointer, checkpointer
# Importing the models here ensures Base knows about them before create_all runs
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.memory import Memory
from app.models.document import Document
from app.models.document_chunk import DocumentChunk

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.conversations import router as conv_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.documents import router as documents_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(conv_router, prefix="/conversations", tags=["Conversations"])
app.include_router(chat_router, prefix="/conversations", tags=["Chat"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])


@app.on_event("startup")
async def startup():
    max_retries = 30
    retry_delay_seconds = 2

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            break
        except Exception as exc:
            if attempt == max_retries:
                raise RuntimeError(
                    "Database is not ready after multiple retries. "
                    "Check the Postgres container and DATABASE_URL."
                ) from exc

            print(
                f"Database not ready yet (attempt {attempt}/{max_retries}), "
                f"retrying in {retry_delay_seconds}s..."
            )
            await asyncio.sleep(retry_delay_seconds)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Application tables created successfully!")

    await init_langgraph_checkpointer()

    from app.ai.graph.graph import build_app_graph

    app.state.app_graph = build_app_graph(checkpointer)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "Server is running and connected to PostgreSQL."
    }