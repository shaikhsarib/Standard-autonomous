from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from src.models.lead import BusinessProfile

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationContext(BaseModel):
    session_id: str
    business_profile: BusinessProfile
    history: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
