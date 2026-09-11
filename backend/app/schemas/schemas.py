from pydantic import BaseModel, EmailStr

# Schema for user signup
class UserCreate(BaseModel):
    name: str
    email: str          # <--- Changed from EmailStr to str
    password: str

class UserLogin(BaseModel):
    email: str          # <--- Changed from EmailStr to str
    password: str

# Schema to return user data to React (never return the password!)
class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

# Schema for the login response (contains the JWT token)
class Token(BaseModel):
    access_token: str
    token_type: str


# ... (Keep existing UserCreate, UserLogin, UserResponse, Token)

from datetime import datetime
from typing import Any

class ConversationCreate(BaseModel):
    title: str

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    summary: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    status: str
    message: MessageResponse | None = None
    details: Any | None = None

    class Config:
        from_attributes = True