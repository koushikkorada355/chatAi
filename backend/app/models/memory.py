from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False) # e.g., "User's name is Koushik"
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())