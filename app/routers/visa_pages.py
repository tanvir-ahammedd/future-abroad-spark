import re
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.dependencies import get_db
from app.models.cache import ContentCache
from app.services.gemini import generate_structured_json
from app.services.currency import convert_currency, CurrencyServiceError
from app.prompts.visa_page import SYSTEM_PROMPT_TEMPLATE
from app.schemas.visa import VisaDetailResponse, VisaListResponse, VisaListItem

logger = logging.getLogger("app.routers.visa_pages")

router = APIRouter(prefix="/visas", tags=["Visa Pages"])

# Regex formats for slugs and currencies
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")

def validate_slug(slug: str, name: str) -> None:
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(status_code=400, detail=f"Invalid {name} format.")

def slug_to_title(slug: str) -> str:
    # Replace hyphens with spaces and title case
    return slug.replace("-", " ").title()


@router.get("/{country_slug}/{visa_slug}", response_model=VisaDetailResponse)
async def get_visa_details(
    country_slug: str,
    visa_slug: str,
    currency: Optional[str] = Query(None, description="Optional ISO 4217 currency code for display conversion."),
    refresh: bool = Query(False, description="Bypass the cache and force fresh generation from AI."),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Returns full structured visa requirements page.
    Utilizes localized content caching and stubbed currency exchange values.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Normalize slugs to lowercase before validation
    country_slug = country_slug.lower()
    visa_slug = visa_slug.lower()
    
    # 1. Validation Rules
    validate_slug(country_slug, "country slug")
    validate_slug(visa_slug, "visa slug")
    
    if currency:
        # Strict validation before uppercasing to enforce uppercase requirement
        if not CURRENCY_PATTERN.match(currency):
            raise HTTPException(status_code=400, detail="Currency code must be a 3-letter ISO 4217 code.")
        currency = currency.strip().upper()

    cache_key = f"visa:{country_slug}:{visa_slug}"
    now = datetime.now(timezone.utc)
    
    # Derive human readable title names from slugs
    country_name = slug_to_title(country_slug)
    visa_name = slug_to_title(visa_slug)

    cache_hit = False
    raw_data = None

    # 2. Check localized PostgreSQL database cache
    try:
        if not refresh:
            stmt = select(ContentCache).where(ContentCache.cache_key == cache_key)
            res = await db.execute(stmt)
            cache_row = res.scalars().first()
            
            if cache_row and cache_row.expires_at > now:
                raw_data = json.loads(cache_row.content_json)
                cache_hit = True
                logger.info(f"Cache HIT for cache key: {cache_key}")
    except Exception as e:
        logger.error(f"Database cache lookup failed: {e}")
        # Proceed to fetch freshly from Gemini if cache lookup fails

    # 3. Cache MISS or refresh required -> Call Gemini Service
    if raw_data is None:
        logger.info(f"Cache MISS or forced refresh for cache key: {cache_key}. Fetching from Gemini...")
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(country_name=country_name, visa_name=visa_name)
        user_prompt = f"Perform the search for the {visa_name} requirements in {country_name} and generate the structured JSON report."
        
        try:
            raw_data = generate_structured_json(system_prompt, user_prompt, enable_search_grounding=True)
            # Ensure generated_at is set to current time
            raw_data["generated_at"] = now.isoformat()
        except Exception as e:
            logger.error(f"Gemini generation failed for {visa_name} ({country_name}): {e}")
            raise e  # Global exception handlers will intercept and output correct Standard Error Envelopes
            
        # 4. JSON Schema Validation
        # Verify structure contains key fields before writing to cache
        required_keys = ["visa_name", "country", "country_code", "data_confidence"]
        if not all(k in raw_data for k in required_keys):
            raise HTTPException(status_code=502, detail="The AI service returned an invalid visa data structure.")

        # 5. Persist to localized content cache
        try:
            expires_at = now + timedelta(seconds=settings.CACHE_TTL_SECONDS)
            stmt = select(ContentCache).where(ContentCache.cache_key == cache_key)
            res = await db.execute(stmt)
            cache_row = res.scalars().first()
            
            if cache_row:
                cache_row.content_json = json.dumps(raw_data)
                cache_row.created_at = now
                cache_row.expires_at = expires_at
            else:
                cache_row = ContentCache(
                    cache_key=cache_key,
                    content_json=json.dumps(raw_data),
                    created_at=now,
                    expires_at=expires_at
                )
                db.add(cache_row)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed writing cache record for {cache_key}: {e}")
            # Do not block response delivery if database write fails

    # 6. Process currency conversions if requested
    converted_fields = {}
    if currency:
        try:
            from_monthly = raw_data.get("minimum_monthly_income_currency")
            amt_monthly = raw_data.get("minimum_monthly_income_amount")
            converted_monthly = await convert_currency(amt_monthly, from_monthly, currency)

            from_savings = raw_data.get("minimum_savings_currency")
            amt_savings = raw_data.get("minimum_savings_amount")
            converted_savings = await convert_currency(amt_savings, from_savings, currency)

            from_fee = raw_data.get("application_fee_currency")
            amt_fee = raw_data.get("application_fee_amount")
            converted_fee = await convert_currency(amt_fee, from_fee, currency)

            converted_fields = {
                "minimum_monthly_income_converted_amount": converted_monthly,
                "minimum_savings_converted_amount": converted_savings,
                "application_fee_converted_amount": converted_fee,
                "converted_currency": currency,
                "currency_conversion_error": False
            }
        except CurrencyServiceError as ce:
            logger.warning(f"Currency conversion failed for request: {ce}")
            converted_fields = {
                "currency_conversion_error": True
            }

    # 7. Package and Return direct resource response
    response_payload = {
        "request_id": request_id,
        "cache_hit": cache_hit,
        **raw_data,
        **converted_fields
    }
    
    return response_payload


@router.get("/{country_slug}", response_model=VisaListResponse)
async def list_country_visas(
    country_slug: str,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Returns a listing of all major visa programmes available for a specific country.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    country_slug = country_slug.lower()
    validate_slug(country_slug, "country slug")
    
    cache_key = f"visas_list:{country_slug}"
    now = datetime.now(timezone.utc)
    country_name = slug_to_title(country_slug)

    cache_hit = False
    list_data = None

    # Check cache
    try:
        stmt = select(ContentCache).where(ContentCache.cache_key == cache_key)
        res = await db.execute(stmt)
        cache_row = res.scalars().first()
        
        if cache_row and cache_row.expires_at > now:
            list_data = json.loads(cache_row.content_json)
            cache_hit = True
            logger.info(f"Cache HIT for visas list cache key: {cache_key}")
    except Exception as e:
        logger.error(f"Database list cache lookup failed: {e}")

    # Generate if cache miss
    if list_data is None:
        logger.info(f"Cache MISS for visas list cache key: {cache_key}. Fetching from Gemini...")
        sys_prompt = (
            f"You are a visa listing assistant for MyFutureAbroad. Search for all major long-stay visa programmes available for {country_name}.\n"
            "You must return ONLY a valid JSON object matching the detailed schema described below:\n"
            "{\n"
            "  \"visas\": [\n"
            "    {\n"
            "      \"visa_name\": \"string, official program name\",\n"
            "      \"visa_slug\": \"string, the name lowercased with spaces replaced by hyphens\",\n"
            "      \"summary\": \"string, one-sentence plain-English description\",\n"
            "      \"target_applicant\": \"string, one-sentence target description\",\n"
            "      \"minimum_monthly_income_amount\": number or null,\n"
            "      \"minimum_monthly_income_currency\": \"string or null, ISO 4217 code\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Never estimate figures. Return pure JSON only."
        )
        user_prompt = f"Generate the list of major visas for {country_name}."
        
        try:
            list_data = generate_structured_json(sys_prompt, user_prompt, enable_search_grounding=True)
            
            # Robust wrapping if Gemini returns an array directly
            if isinstance(list_data, list):
                list_data = {"visas": list_data}
        except Exception as e:
            logger.error(f"Gemini listing failed for {country_name}: {e}")
            raise e
            
        # JSON Schema Validation
        if "visas" not in list_data or not isinstance(list_data["visas"], list):
            raise HTTPException(status_code=502, detail="The AI service returned an invalid visa list structure.")
            
        # Ensure every item in list contains visa_name and visa_slug
        for item in list_data["visas"]:
            if "visa_name" not in item or "visa_slug" not in item:
                raise HTTPException(status_code=502, detail="The AI service returned an invalid visa list structure.")

        # Persist to Cache
        try:
            expires_at = now + timedelta(seconds=settings.CACHE_TTL_SECONDS)
            stmt = select(ContentCache).where(ContentCache.cache_key == cache_key)
            res = await db.execute(stmt)
            cache_row = res.scalars().first()
            
            if cache_row:
                cache_row.content_json = json.dumps(list_data)
                cache_row.created_at = now
                cache_row.expires_at = expires_at
            else:
                cache_row = ContentCache(
                    cache_key=cache_key,
                    content_json=json.dumps(list_data),
                    created_at=now,
                    expires_at=expires_at
                )
                db.add(cache_row)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed writing cache list record for {cache_key}: {e}")

    return {
        "request_id": request_id,
        "cache_hit": cache_hit,
        "visas": list_data.get("visas", [])
    }
