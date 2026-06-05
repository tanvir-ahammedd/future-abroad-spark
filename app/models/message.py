import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Must store either: user, assistant
    role = Column(
        String(20),
        nullable=False
    )
    
    content = Column(
        Text,
        nullable=False
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    

    # Reference back to session parent
    session = relationship(
        "ChatSession",
        back_populates="messages"
    )

# Create a non-unique index on session_id for high-performance session history lookups
Index("ix_chat_messages_session_id", ChatMessage.session_id)