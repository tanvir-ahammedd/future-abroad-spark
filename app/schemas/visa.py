from typing import List, Optional
from pydantic import BaseModel, Field

class VisaDetailResponse(BaseModel):
    # Top level request tracking
    request_id: str = Field(description="Unique ID generated per API request for debugging and tracking.")
    cache_hit: bool = Field(default=False, description="True if the response was served from cache, False if freshly generated.")
    
    # Core schema fields from Gemini
    visa_name: str = Field(description="The official name of the visa programme.")
    country: str = Field(description="The full country name.")
    country_code: str = Field(description="ISO 3166-1 alpha-2 two-letter country code in uppercase.")
    summary: str = Field(description="A one-paragraph plain-English description of the visa.")
    target_applicant: str = Field(description="A plain-English description of who this visa is designed for.")
    minimum_monthly_income_amount: Optional[float] = Field(None, description="The minimum required monthly income in original currency.")
    minimum_monthly_income_currency: Optional[str] = Field(None, description="ISO 4217 three-letter currency code for income.")
    minimum_savings_amount: Optional[float] = Field(None, description="The minimum required savings in original currency.")
    minimum_savings_currency: Optional[str] = Field(None, description="ISO 4217 three-letter currency code for savings.")
    minimum_age: Optional[int] = Field(None, description="The minimum age required, if applicable.")
    maximum_age: Optional[int] = Field(None, description="The maximum age allowed, if applicable.")
    criminal_record_check_required: bool = Field(description="True if clean criminal record background check is explicitly required.")
    health_insurance_required: bool = Field(description="True if health insurance is explicitly required.")
    documents_required: List[str] = Field(default_factory=list, description="Array of required documents.")
    other_requirements: List[str] = Field(default_factory=list, description="Array of other additional requirements.")
    application_fee_amount: Optional[float] = Field(None, description="The official application fee in original currency.")
    application_fee_currency: Optional[str] = Field(None, description="ISO 4217 three-letter currency code for application fee.")
    processing_time_min_days: Optional[int] = Field(None, description="Minimum estimated processing time in days.")
    processing_time_max_days: Optional[int] = Field(None, description="Maximum estimated processing time in days.")
    validity_months: Optional[int] = Field(None, description="The initial validity period of the visa in months.")
    renewable: Optional[bool] = Field(None, description="True if renewable, False if not.")
    path_to_residency: Optional[str] = Field(None, description="Path to permanent residency or citizenship if one exists.")
    source_url: Optional[str] = Field(None, description="The URL of the primary official government source used.")
    data_confidence: str = Field(description="Either 'full' or 'partial'.")
    generated_at: str = Field(description="ISO 8601 UTC datetime of when this was generated.")
    
    # Currency conversion fields (present only when conversion requested)
    minimum_monthly_income_converted_amount: Optional[float] = Field(None, description="Converted monthly income.")
    minimum_savings_converted_amount: Optional[float] = Field(None, description="Converted savings amount.")
    application_fee_converted_amount: Optional[float] = Field(None, description="Converted application fee.")
    converted_currency: Optional[str] = Field(None, description="ISO 4217 code of converted currency.")
    currency_conversion_error: Optional[bool] = Field(None, description="True if conversion was requested but failed.")


class VisaListItem(BaseModel):
    visa_name: str = Field(description="The official name of the visa programme.")
    visa_slug: str = Field(description="The visa name in lowercase with spaces replaced by hyphens.")
    summary: str = Field(description="A one-sentence plain-English description.")
    target_applicant: str = Field(description="A one-sentence plain-English description of the target applicant.")
    minimum_monthly_income_amount: Optional[float] = Field(None, description="Minimum monthly income required in original currency.")
    minimum_monthly_income_currency: Optional[str] = Field(None, description="ISO 4217 code for income.")


class VisaListResponse(BaseModel):
    request_id: str = Field(description="Unique ID generated per API request.")
    cache_hit: bool = Field(default=False, description="True if served from cache.")
    visas: List[VisaListItem] = Field(default_factory=list, description="Array of visa summaries.")
