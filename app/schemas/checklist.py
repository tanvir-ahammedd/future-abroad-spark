import uuid
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

class ChecklistItem(BaseModel):
    item_id: str = Field(description="Unique slug/id for the checklist item.")
    title: str = Field(description="Short action title.")
    description: str = Field(description="Detailed description of what to do.")
    status: Literal["not_started", "in_progress", "done"] = Field(default="not_started", description="Status of the task.")
    category: Literal[
        "documents", "legal", "financial", "property", "logistics", "healthcare", "administrative", "personal"
    ] = Field(description="Category of the task.")
    country_specific: bool = Field(description="Whether the item is specific to the country.")
    notes: Optional[str] = Field(None, description="Important caveats or details.")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_clean = v.strip().lower()
        valid = {"documents", "legal", "financial", "property", "logistics", "healthcare", "administrative", "personal"}
        if v_clean not in valid:
            if v_clean == "education":
                return "personal"
            return "personal"
        return v_clean

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_clean = v.strip().lower().replace("-", "_")
        valid = {"not_started", "in_progress", "done"}
        if v_clean not in valid:
            return "not_started"
        return v_clean


class ChecklistPhase(BaseModel):
    phase_id: Literal[
        "six_months_before", "three_months_before", "one_month_before", "two_weeks_before",
        "moving_week", "first_month_after", "three_months_after", "six_months_after", "ongoing"
    ] = Field(description="Slug for the phase timeline.")
    phase_label: str = Field(description="Human readable label for the phase timeline.")
    items: List[ChecklistItem] = Field(default_factory=list, description="List of checklist items under this phase.")

    @field_validator("phase_id", mode="before")
    @classmethod
    def normalize_phase_id(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_clean = v.strip().lower().replace("-", "_")
        valid = {
            "six_months_before", "three_months_before", "one_month_before", "two_weeks_before",
            "moving_week", "first_month_after", "three_months_after", "six_months_after", "ongoing"
        }
        if v_clean not in valid:
            return "ongoing"
        return v_clean


class ChecklistSchema(BaseModel):
    destination_country: str = Field(description="Target destination country.")
    move_date_reference: str = Field(description="User specified move date reference.")
    phases: List[ChecklistPhase] = Field(default_factory=list, description="Phases of the relocation.")


class ChecklistChatResponse(BaseModel):
    session_id: uuid.UUID = Field(description="UUID of session.")
    stage: str = Field(description="Current stage (collecting or complete).")
    message: Optional[str] = Field(None, description="Conversational text to display when stage is collecting.")
    checklist: Optional[ChecklistSchema] = Field(None, description="Present when stage is complete.")
    stream: bool = Field(False, description="Always false for non-streaming.")


class ChecklistUpdateRequest(BaseModel):
    session_id: uuid.UUID = Field(description="Session UUID.")
    instruction: str = Field(..., max_length=1000, description="Instruction describing what to change.")
    current_checklist: ChecklistSchema = Field(..., description="Current checklist object.")


class ChecklistUpdateResponse(BaseModel):
    session_id: uuid.UUID = Field(description="Session UUID.")
    checklist: ChecklistSchema = Field(..., description="Modified checklist.")
