from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Literals for enum fields
ClimateType = Literal["tropical", "subtropical", "mediterranean", "temperate", "continental", "arid", "polar"]
ExpatCommunitySize = Literal["large", "moderate", "small", "minimal"]
HealthcareQuality = Literal["excellent", "good", "adequate", "limited"]
TaxSystemType = Literal["territorial", "worldwide", "remittance", "flat", "exempt"]
BankingEase = Literal["easy", "moderate", "difficult"]


class CountryDetailResponse(BaseModel):
    # Top level request tracking
    request_id: str = Field(description="Unique ID generated per API request for debugging and tracking.")
    cache_hit: bool = Field(default=False, description="True if the response was served from cache, False if freshly generated.")
    
    # Core schema fields from Gemini
    country: str = Field(description="Full country name.")
    country_code: str = Field(description="ISO 3166-1 alpha-2 uppercase.")
    capital_city: str = Field(description="Capital city.")
    official_language: List[str] = Field(default_factory=list, description="Array of official languages.")
    currency_code: str = Field(description="ISO 4217 currency code.")
    summary: str = Field(description="Two to three paragraph plain-English overview of the country.")
    climate_description: str = Field(description="Plain-English description of the climate.")
    climate_type: ClimateType = Field(description="Climate type enum classification.")
    population: Optional[int] = Field(None, description="Total population.")
    expat_community_size: ExpatCommunitySize = Field(description="Expat community size enum.")
    english_widely_spoken: bool = Field(description="True if English is widely spoken.")
    safety_index_score: Optional[float] = Field(None, description="Numbeo Safety Index score.")
    healthcare_quality: HealthcareQuality = Field(description="Healthcare quality enum classification.")
    public_healthcare_accessible_to_expats: Optional[bool] = Field(None, description="Access to public healthcare.")
    cost_of_living_index: Optional[float] = Field(None, description="Numbeo Cost of Living Index.")
    average_monthly_rent_city_centre_1bed_amount: Optional[float] = Field(None, description="Average monthly rent in city centre in local currency.")
    average_monthly_rent_city_centre_1bed_currency: Optional[str] = Field(None, description="ISO 4217 currency code for monthly rent.")
    tax_system_type: TaxSystemType = Field(description="Tax system classification enum.")
    income_tax_rate_description: str = Field(description="Plain-English description of the income tax bands or rate.")
    capital_gains_tax_description: Optional[str] = Field(None, description="Capital gains tax description.")
    wealth_tax: Optional[bool] = Field(None, description="True if wealth tax exists.")
    pension_income_tax_treatment: Optional[str] = Field(None, description="Taxation treatment on pensions.")
    tax_treaty_with_uk: Optional[bool] = Field(None, description="Double tax treaty with UK.")
    tax_treaty_with_us: Optional[bool] = Field(None, description="Double tax treaty with US.")
    path_to_permanent_residency_description: str = Field(description="Description of the path to permanent residency.")
    path_to_citizenship_description: Optional[str] = Field(None, description="Description of the path to citizenship.")
    eu_member: bool = Field(description="True if EU member.")
    schengen_area: bool = Field(description="True if part of Schengen Zone.")
    visa_on_arrival_for_eu_citizens: Optional[bool] = Field(None, description="Visa on arrival / short stay for EU citizens.")
    visa_on_arrival_for_us_citizens: Optional[bool] = Field(None, description="Visa on arrival / short stay for US citizens.")
    visa_on_arrival_for_uk_citizens: Optional[bool] = Field(None, description="Visa on arrival / short stay for UK citizens.")
    banking_ease_for_expats: BankingEase = Field(description="Ease of opening bank accounts classification.")
    internet_speed_mbps_average: Optional[float] = Field(None, description="Average fixed broadband speed.")
    source_urls: List[str] = Field(default_factory=list, description="URLs of sources used.")
    data_confidence: str = Field(description="Either 'full' or 'partial'.")
    generated_at: str = Field(description="ISO 8601 UTC datetime of generation.")
    
    # Currency conversion fields (present only when conversion requested)
    converted_rent_amount: Optional[float] = Field(None, description="Converted monthly rent amount.")
    converted_currency: Optional[str] = Field(None, description="ISO 4217 code of converted currency.")
    currency_conversion_error: Optional[bool] = Field(None, description="True if conversion was requested but failed.")


class CountryListItem(BaseModel):
    country: str = Field(description="Full country name.")
    country_slug: str = Field(description="The country name in lowercase with hyphens.")
    country_code: str = Field(description="ISO 3166-1 alpha-2 uppercase.")
    summary: str = Field(description="One sentence plain-English description.")
    eu_member: bool = Field(description="True if EU member.")
    cost_of_living_index: Optional[float] = Field(None, description="Numbeo Cost of Living Index if available.")
    climate_type: str = Field(description="Climate type classification.")


class CountryListResponse(BaseModel):
    request_id: str = Field(description="Unique ID generated per API request.")
    cache_hit: bool = Field(default=False, description="True if served from cache.")
    countries: List[CountryListItem] = Field(default_factory=list, description="Array of expat countries summaries.")
