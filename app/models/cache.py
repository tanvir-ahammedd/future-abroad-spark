import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class ContentCache(Base):
    __tablename__ = "content_cache"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # E.g. visa:portugal:d7-passive-income-visa or country:spain
    cache_key = Column(
        String(255),
        nullable=False,
        unique=True
    )
    
    content_json = Column(
        Text,
        nullable=False
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False
    )
    

# Indexes for fast key lookups and expired TTL cleanups
Index("ux_content_cache_cache_key", ContentCache.cache_key, unique=True)
Index("ix_content_cache_expires_at", ContentCache.expires_at)
