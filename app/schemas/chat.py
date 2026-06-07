import uuid
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: Optional[uuid.UUID] = Field(None, description="UUID of an existing session. If null, a new session is created.")
    message: str = Field(..., description="The user's latest message.")
    feature: str = Field(..., description="Must be one of: visa_finder, budget, checklist, chatbot.")


class VisaMatchItem(BaseModel):
    country: str = Field(description="Full country name.")
    country_slug: str = Field(description="Lowercase country name with hyphens.")
    visa_name: str = Field(description="Official name of the visa programme.")
    visa_slug: str = Field(description="Lowercase visa name with hyphens.")
    match_rating: str = Field(description="Must be one of: excellent, good, ordinary.")
    match_reasoning: str = Field(description="One sentence explaining why this rating was given.")
    key_requirements: List[str] = Field(default_factory=list, description="Two or three most important eligibility requirements.")
    minimum_monthly_income_amount: Optional[float] = Field(None, description="Minimum monthly income required in original currency.")
    minimum_monthly_income_currency: Optional[str] = Field(None, description="ISO 4217 code for income currency.")


class ChatResponse(BaseModel):
    session_id: uuid.UUID = Field(description="UUID of the session (new or existing)")
    stage: str = Field(description="The current conversation stage (collecting or results)")
    message: Optional[str] = Field(None, description="Conversational text to display when stage is 'collecting'")
    visas: Optional[List[VisaMatchItem]] = Field(None, description="Present only when stage is 'results', contains the ranked visa match objects")
    stream: bool = Field(False, description="Always false for non-streaming responses")


class ChatMessageItem(BaseModel):
    id: uuid.UUID = Field(description="Unique message ID.")
    role: str = Field(description="Role of the message author (user or assistant).")
    content: str = Field(description="Message content.")
    created_at: datetime = Field(description="Message creation timestamp.")


class SessionHistoryResponse(BaseModel):
    session_id: uuid.UUID = Field(description="Session UUID.")
    feature: str = Field(description="Feature name.")
    created_at: datetime = Field(description="Session creation timestamp.")
    messages: List[ChatMessageItem] = Field(default_factory=list, description="List of messages in the session.")


class ChatbotRequest(BaseModel):
    session_id: Optional[uuid.UUID] = Field(None, description="UUID of an existing session. If null, a new session is created.")
    message: str = Field(..., description="The user's latest message.")
    feature: Literal["chatbot"] = Field("chatbot", description="Must be 'chatbot'.")
    placement: Optional[str] = Field(None, description="Optional placement identifier.")
    current_page: Optional[str] = Field(None, description="Optional URL path of the current page.")


class ChatbotResponse(BaseModel):
    session_id: uuid.UUID = Field(description="UUID of the session (new or existing)")
    message: str = Field(description="Conversational response from the chatbot.")
    redirect: Optional[str] = Field(None, description="A relative URL path if a redirect is warranted.")
    sources: List[str] = Field(default_factory=list, description="URLs of any sources used in forming the answer.")
    request_id: str = Field("", description="Unique request identifier for support/debugging.")
