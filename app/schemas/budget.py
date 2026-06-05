import uuid
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    item_id: str = Field(description="Unique slug for the line item.")
    label: str = Field(description="Human-readable name.")
    amount: float = Field(description="Amount of the cost.")
    frequency: Literal["one_time", "monthly"] = Field(description="Frequency of the cost.")
    notes: Optional[str] = Field(None, description="Important caveats or assumptions.")
    source_url: Optional[str] = Field(None, description="URL where cost figure was found.")


class BudgetCategory(BaseModel):
    category_name: Literal["pre_move", "relocation", "property", "setup", "administrative", "monthly_living", "buffer"] = Field(description="Category classification name.")
    category_total: float = Field(description="Sum of all items in category.")
    line_items: List[LineItem] = Field(default_factory=list, description="Array of line items in this category.")


class BudgetSchema(BaseModel):
    destination_country: str = Field(description="Destination country.")
    visa_type: str = Field(description="Visa type applied for.")
    currency_code: str = Field(description="ISO 4217 code for budget costs.")
    total_one_time_costs: float = Field(description="Total of one-time costs.")
    total_monthly_ongoing_costs: float = Field(description="Total of monthly ongoing costs.")
    buffer_fund_amount: float = Field(description="Buffer fund calculated as 15% of one-time costs.")
    categories: List[BudgetCategory] = Field(default_factory=list, description="List of budget categories.")


class BudgetChatResponse(BaseModel):
    session_id: uuid.UUID = Field(description="UUID of session.")
    stage: str = Field(description="Current stage (collecting or complete).")
    message: Optional[str] = Field(None, description="Conversational text to display when stage is collecting.")
    budget: Optional[BudgetSchema] = Field(None, description="Present when stage is complete.")
    stream: bool = Field(False, description="Always false for non-streaming.")


class BudgetUpdateRequest(BaseModel):
    session_id: uuid.UUID = Field(description="Session UUID.")
    instruction: str = Field(..., max_length=1000, description="Instruction describing what to change.")
    current_budget: BudgetSchema = Field(..., description="Current budget object.")


class BudgetUpdateResponse(BaseModel):
    session_id: uuid.UUID = Field(description="Session UUID.")
    budget: BudgetSchema = Field(..., description="Modified budget.")
