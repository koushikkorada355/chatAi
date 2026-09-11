import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: int
    chunks_created: int
    filename: str


def _extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            pages.append(text)
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("No readable text found in the PDF file.")
    return text


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file was provided.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported.")

    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GOOGLE_API_KEY is not configured.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    unique_filename = f"{uuid.uuid4()}.pdf"
    destination = UPLOAD_DIR / unique_filename

    try:
        with destination.open("wb") as f:
            f.write(file_bytes)

        try:
            raw_text = _extract_pdf_text(destination)
        except Exception as exc:
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not read PDF content: {str(exc)}",
            ) from exc

        if not raw_text.strip():
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The PDF file is empty or unreadable.")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(raw_text)
        if not chunks:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No content could be split into chunks.")

        embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=settings.GOOGLE_API_KEY,
        )

        document = Document(
            user_id=current_user.id,
            name=file.filename,
            file_path=str(destination),
        )
        db.add(document)
        await db.flush()

        document_chunks = []
        for chunk in chunks:
            chunk_text = chunk.strip()
            if not chunk_text:
                continue
            vector = embeddings.embed_query(chunk_text)
            document_chunks.append(
                DocumentChunk(
                    document_id=document.id,
                    content=chunk_text,
                    embedding=vector,
                )
            )

        if not document_chunks:
            await db.rollback()
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid chunks were generated from the PDF.")

        db.add_all(document_chunks)
        await db.commit()
        await db.refresh(document)

        return DocumentUploadResponse(
            success=True,
            document_id=document.id,
            chunks_created=len(document_chunks),
            filename=file.filename,
        )
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(exc)}",
        ) from exc
