import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.tools import set_active_user_id
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.message import Message
from app.models.user import User
from app.schemas.schemas import ChatResponse, MessageCreate

router = APIRouter()


async def _save_memory_if_present(db: AsyncSession, user_id: int, extracted_memory):
    if not extracted_memory:
        return

    new_memory = Memory(user_id=user_id, content=extracted_memory)
    db.add(new_memory)
    await db.commit()


async def _save_assistant_message(db: AsyncSession, conv_id: int, content: str):
    message = Message(conversation_id=conv_id, role="assistant", content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@router.post("/{conv_id}/chat", response_model=ChatResponse)
async def chat(
    conv_id: int,
    msg_data: MessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = Message(conversation_id=conv_id, role="user", content=msg_data.content)
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    memory_result = await db.execute(select(Memory).where(Memory.user_id == current_user.id))
    user_memories = memory_result.scalars().all()

    langchain_messages = []
    if user_memories:
        memory_text = "\n".join(memory.content for memory in user_memories)
        langchain_messages.append(SystemMessage(content=f"Here are some facts you remember about the user:\n{memory_text}"))

    langchain_messages.append(SystemMessage(content=(
        "You are ChatAI, a highly intelligent and helpful assistant. "
        "You have access to tools like a calculator, web search, and the user's uploaded documents. "
        "If the user asks a math question, you MUST use the calculator tool. "
        "If the user asks about uploaded files, PDFs, documents, or material in their documents, use the search_user_documents tool. "
        "Always provide clear, conversational responses to the user."
    )))

    langchain_messages.append(HumanMessage(content=msg_data.content))

    config = {"configurable": {"thread_id": str(conv_id)}}
    initial_state = {
        "messages": langchain_messages,
        "user_id": current_user.id,
    }

    try:
        set_active_user_id(current_user.id)
        app_graph = request.app.state.app_graph
        final_state = await app_graph.ainvoke(initial_state, config=config)

        messages = final_state.get("messages") or []
        ai_content = messages[-1].content if messages else "I could not reach the AI model right now."
        if not ai_content:
            ai_content = "I could not reach the AI model right now."
        await _save_memory_if_present(db, current_user.id, final_state.get("extracted_memory"))
    except Exception:
        traceback.print_exc()
        ai_content = "I could not reach the AI model right now."
    finally:
        set_active_user_id(None)

    new_ai_msg = await _save_assistant_message(db, conv_id, ai_content)
    return {
        "status": "completed",
        "message": new_ai_msg,
    }