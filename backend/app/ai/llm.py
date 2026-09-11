from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_llm():
    api_key = (settings.GROQ_API_KEY or "").strip()
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Add it to Docker environment or backend/.env before using the AI."
        )

    model_name = (settings.GROQ_MODEL or "openai/gpt-oss-20b").strip()

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.7,
        streaming=False,
    )