from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class BusinessProfile(BaseModel):
    """Represents the target business profile for lead generation."""
    company_name: str = Field(..., description="Name of the business entity")
    website: Optional[str] = Field(None, description="Official website URL")
    industry: Optional[str] = Field(None, description="Industry sector the business operates in")
    size_range: Optional[str] = Field(None, description="Estimated number of employees")
    pain_points: List[str] = Field(default_factory=list, description="Identified operational challenges")
    growth_goals: List[str] = Field(default_factory=list, description="Stated or inferred business objectives")


class Message(BaseModel):
    """Represents a single message in the conversation history."""
    role: str = Field(..., description="Role of the sender ('user' or 'assistant')")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time the message was sent")


class ConversationContext(BaseModel):
    """Maintains state and context for an active conversation session."""
    session_id: str = Field(..., description="Unique identifier for the session")
    business_profile: BusinessProfile = Field(
        default_factory=lambda: BusinessProfile(company_name="Unknown"),
        description="Profile of the business being pitched",
    )
    history: List[Message] = Field(default_factory=list, description="Chronological message history")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary workflow state data")


class LeadOutput(BaseModel):
    """Represents the generated actionable lead data extracted from interaction."""
    session_id: str = Field(..., description="Identifier of the origin session")
    contact_name: Optional[str] = Field(None, description="Name of the contact person")
    contact_email: Optional[str] = Field(None, description="Email address for follow-up")
    budget: Optional[str] = Field(None, description="Stated or implied budget")
    interest_level: str = Field(default="None", description="Assessed interest level")
    qualified: bool = Field(default=False, description="Whether this lead justifies follow-up")
    summary: Optional[str] = Field(None, description="Summary of key interaction points")
    action_items: List[str] = Field(default_factory=list, description="Next steps for sales team")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Lead generation timestamp")


def extract_lead(data: dict, session_id: str) -> LeadOutput:
    """Safely build a LeadOutput from a raw dict, coercing bad values."""
    # Convert "True"/"False" strings to real bool
    qualified_raw = data.get("qualified", False)
    if isinstance(qualified_raw, str):
        qualified = qualified_raw.strip().lower() == "true"
    else:
        qualified = bool(qualified_raw)

    return LeadOutput(
        session_id=session_id,
        contact_name=data.get("contact_name") or None,
        contact_email=data.get("contact_email") or None,
        budget=data.get("budget") or None,
        interest_level=data.get("interest_level") or "None",
        qualified=qualified,
        summary=data.get("summary") or None,
    )
