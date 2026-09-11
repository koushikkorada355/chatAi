from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(3072), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
