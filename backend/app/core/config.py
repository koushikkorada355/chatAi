from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "fallback_secret_key"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    LANGGRAPH_DB_URL: str
    GOOGLE_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()