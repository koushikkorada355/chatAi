import ast
import operator
from contextvars import ContextVar

from ddgs import DDGS
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk

_active_user_id: ContextVar[int | None] = ContextVar("active_user_id", default=None)


def set_active_user_id(user_id: int | None) -> None:
    _active_user_id.set(user_id)


# Map string operators to actual Python math functions
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval(expr):
    node = ast.parse(expr, mode='eval').body
    return _eval_ast(node)


def _eval_ast(node):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        return OPERATORS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_ast(node.operand)
        return OPERATORS[type(node.op)](operand)
    else:
        raise ValueError(f"Unsupported operation: {type(node)}")


@tool
def calculator(expression: str) -> str:
    """
    Useful for answering math questions.
    Input should be a standard mathematical expression (e.g., "125 * 42", "100 / 5", "15 + 20").
    """
    try:
        result = safe_eval(expression)
        return f"The result of {expression} is {result}."
    except Exception as e:
        return f"Error calculating: {expression}. Error: {str(e)}"


@tool
def duckduckgo_web_search(query: str) -> str:
    """
    Useful for searching the web for current information, news, or facts you don't know.
    Input should be a clear search query.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

        if not results:
            return "No search results found."

        formatted_results = []
        for i, res in enumerate(results, 1):
            formatted_results.append(f"{i}. {res['title']}\n   {res['body']}\n   URL: {res['href']}")

        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error searching the web: {e}"


@tool
async def search_user_documents(query: str, user_id: int | None = None) -> str:
    """
    Search within the current authenticated user's uploaded PDF documents for the most relevant text.
    The tool filters results by user_id to prevent cross-user access.
    """
    resolved_user_id = user_id if user_id is not None else _active_user_id.get()
    if resolved_user_id is None:
        return "No authenticated user context is available for document search."

    if not settings.GOOGLE_API_KEY:
        return "Google API key is not configured for document search."

    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=settings.GOOGLE_API_KEY,
    )
    query_embedding = embeddings.embed_query(query)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentChunk.content)
            .join(Document)
            .where(Document.user_id == resolved_user_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(3)
        )
        chunks = result.scalars().all()

    if not chunks:
        return "No relevant information was found in the user's uploaded documents."

    return "\n\n---\n\n".join(chunks)


# List of tools the AI can use
all_tools = [calculator, duckduckgo_web_search, search_user_documents]