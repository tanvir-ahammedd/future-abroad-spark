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
from app.prompts.country_page import SYSTEM_PROMPT_TEMPLATE
from app.schemas.country import CountryDetailResponse, CountryListResponse, CountryListItem

logger = logging.getLogger("app.routers.country_pages")

router = APIRouter(prefix="/countries", tags=["Country Pages"])

# Regex formats for slugs and currencies
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")

def validate_slug(slug: str, name: str) -> None:
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(status_code=400, detail=f"Invalid {name} format.")

def slug_to_title(slug: str) -> str:
    # Replace hyphens with spaces and title case
    return slug.replace("-", " ").title()


@router.get("/{country_slug}", response_model=CountryDetailResponse)
async def get_country_details(
    country_slug: str,
    currency: Optional[str] = Query(None, description="Optional ISO 4217 currency code for display conversion."),
    refresh: bool = Query(False, description="Bypass the cache and force fresh generation from AI."),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Returns full structured country expat profile.
    Utilizes localized content caching and stubbed currency exchange values.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Normalize slug to lowercase before validation
    country_slug = country_slug.lower()
    
    # 1. Validation Rules
    validate_slug(country_slug, "country slug")
    
    if currency:
        # Strict validation before uppercasing to enforce uppercase requirement
        if not CURRENCY_PATTERN.match(currency):
            raise HTTPException(status_code=400, detail="Currency code must be a 3-letter ISO 4217 code.")
        currency = currency.strip().upper()

    cache_key = f"country:{country_slug}"
    now = datetime.now(timezone.utc)
    
    # Derive human readable title name from slug
    country_name = slug_to_title(country_slug)

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
                logger.info(f"Cache HIT for country cache key: {cache_key}")
    except Exception as e:
        logger.error(f"Database cache lookup failed: {e}")
        # Proceed to fetch freshly from Gemini if cache lookup fails

    # 3. Cache MISS or refresh required -> Call Gemini Service
    if raw_data is None:
        logger.info(f"Cache MISS or forced refresh for country cache key: {cache_key}. Fetching from Gemini...")
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(country_name=country_name)
        user_prompt = f"Perform the search for the country profile of {country_name} and generate the structured JSON report."
        
        try:
            raw_data = generate_structured_json(system_prompt, user_prompt, enable_search_grounding=True)
            # Ensure generated_at is set to current time
            raw_data["generated_at"] = now.isoformat()
        except Exception as e:
            logger.error(f"Gemini generation failed for country {country_name}: {e}")
            raise e  # Global exception handlers will intercept and output correct Standard Error Envelopes
            
        # 4. JSON Schema Validation
        # Verify structure contains key fields before writing to cache
        required_keys = ["country", "country_code", "capital_city", "data_confidence"]
        if not all(k in raw_data for k in required_keys):
            raise HTTPException(status_code=502, detail="The AI service returned an invalid country data structure.")

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
            from_rent = raw_data.get("average_monthly_rent_city_centre_1bed_currency")
            amt_rent = raw_data.get("average_monthly_rent_city_centre_1bed_amount")
            converted_rent = await convert_currency(amt_rent, from_rent, currency)

            converted_fields = {
                "converted_rent_amount": converted_rent,
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


@router.get("", response_model=CountryListResponse)
async def list_countries(
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Returns a listing of all major expat destination countries.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    cache_key = "countries_list"
    now = datetime.now(timezone.utc)

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
            logger.info(f"Cache HIT for countries list cache key: {cache_key}")
    except Exception as e:
        logger.error(f"Database list cache lookup failed: {e}")

    # Generate if cache miss
    if list_data is None:
        logger.info(f"Cache MISS for countries list cache key: {cache_key}. Fetching from Gemini...")
        sys_prompt = (
            "You are a country listing assistant for MyFutureAbroad. Search for all major expat destination countries globally.\n"
            "You must return ONLY a valid JSON object matching the detailed schema described below:\n"
            "{\n"
            "  \"countries\": [\n"
            "    {\n"
            "      \"country\": \"string, full country name\",\n"
            "      \"country_slug\": \"string, the name lowercased with spaces replaced by hyphens\",\n"
            "      \"country_code\": \"string, ISO 3166-1 alpha-2 uppercase\",\n"
            "      \"summary\": \"string, one-sentence plain-English description\",\n"
            "      \"eu_member\": boolean,\n"
            "      \"cost_of_living_index\": number or null,\n"
            "      \"climate_type\": \"string\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Never estimate figures. Return pure JSON only."
        )
        user_prompt = "Generate the list of major expat destination countries."
        
        try:
            list_data = generate_structured_json(sys_prompt, user_prompt, enable_search_grounding=True)
            
            # Robust wrapping if Gemini returns an array directly
            if isinstance(list_data, list):
                list_data = {"countries": list_data}
        except Exception as e:
            logger.error(f"Gemini country listing failed: {e}")
            raise e
            
        # JSON Schema Validation
        if "countries" not in list_data or not isinstance(list_data["countries"], list):
            raise HTTPException(status_code=502, detail="The AI service returned an invalid country list structure.")
            
        # Ensure every item in list contains country, country_slug, and country_code
        for item in list_data["countries"]:
            if "country" not in item or "country_slug" not in item or "country_code" not in item:
                raise HTTPException(status_code=502, detail="The AI service returned an invalid country list structure.")

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
        "countries": list_data.get("countries", [])
    }
