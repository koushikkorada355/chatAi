from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from psycopg_pool import AsyncConnectionPool
import logging
import psycopg

# LangGraph async saver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

# --- Existing SQLAlchemy Setup ---
engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# --- LangGraph Checkpointer Setup ---
# Create the async connection pool (closed by default).
# KEY FIX: Pass `autocommit: True` to the underlying psycopg connections
# so that CREATE INDEX CONCURRENTLY doesn't trigger ActiveSqlTransaction errors.
langgraph_pool = AsyncConnectionPool(
    conninfo=settings.LANGGRAPH_DB_URL, 
    open=False,
    kwargs={"autocommit": True}  # <-- This fixes the transaction error
)
checkpointer = AsyncPostgresSaver(conn=langgraph_pool)


async def init_langgraph_checkpointer():
    """Open the langgraph async pool and run any required checkpointer setup."""
    # 1. Open the async pool so the saver can acquire connections
    await langgraph_pool.open()

    # 2. Ask the saver to perform its setup/migrations
    try:
        logger.info("Running LangGraph checkpointer.setup() to create tables...")
        await checkpointer.setup()
    except Exception as exc:
        if isinstance(exc, psycopg.errors.ActiveSqlTransaction):
            logger.error(
                "LangGraph migrations attempted to run inside a transaction. "
                "Apply the LangGraph SQL migrations manually with psql (outside a transaction).",
                exc_info=True,
            )
        else:
            logger.exception("Failed to run LangGraph checkpointer.setup(): %s", exc)
        raise

    logger.info("✅ LangGraph Async Checkpointer initialized!")