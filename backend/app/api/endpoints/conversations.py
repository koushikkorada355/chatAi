from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.schemas import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse

router = APIRouter()

# 1. Create a new conversation
@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conv_data: ConversationCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: object = Depends(get_current_user) # <--- Requires Login
):
    new_conv = Conversation(
        user_id=current_user.id,
        title=conv_data.title
    )
    db.add(new_conv)
    await db.commit()
    await db.refresh(new_conv)
    return new_conv

# 2. Get all conversations for the logged-in user
@router.get("/", response_model=list[ConversationResponse])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: object = Depends(get_current_user)
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    return result.scalars().all()

# 3. Save a message to a conversation
@router.post("/{conv_id}/messages", response_model=MessageResponse)
async def create_message(
    conv_id: int,
    msg_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: object = Depends(get_current_user)
):
    # 1. Verify the conversation belongs to the current user
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 2. Save the user's message
    new_message = Message(
        conversation_id=conv_id,
        role="user",
        content=msg_data.content
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return new_message

# 4. Get all messages in a conversation
@router.get("/{conv_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: object = Depends(get_current_user)
):
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    return msg_result.scalars().all()


# 5. Update a conversation (e.g., change title)
@router.patch("/{conv_id}", response_model=ConversationResponse)
async def update_conversation(
    conv_id: int,
    conv_data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: object = Depends(get_current_user)
):
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Update allowed fields (title for now)
    conversation.title = conv_data.title
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation