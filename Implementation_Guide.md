# MyFutureAbroad — Complete AI Integration Implementation Guide

---

## Critical Rules the Coding AI Must Never Violate

1. Never expose the Gemini API key to the frontend. It must only exist as a server-side environment variable read by FastAPI.
2. Never return raw Gemini error messages to the frontend. Always wrap errors in a consistent error envelope with a safe human-readable message.
3. Never assume the Gemini response is valid JSON without parsing and validating it. Always handle malformed responses explicitly.
4. Never store financial figures without their original currency code. Every monetary value in the database and in every API response must be accompanied by a currency_code field.
5. Never make a Gemini API call without a timeout. All Gemini calls must time out after 60 seconds and return a 504 error if exceeded.
6. Never allow CORS to accept wildcard origins in production. CORS must be restricted to the exact frontend domain specified in the environment variable.
7. Never create a new DB session outside of the dependency injection pattern. All database access must go through the FastAPI dependency.
8. Never silently swallow exceptions. Every exception must be logged with its full traceback before a response is returned.
9. Never write a prompt that instructs Gemini to invent or estimate visa fees, income thresholds, or legal requirements if it cannot find a live source. The prompt must instruct Gemini to explicitly state when official data is unavailable.
10. Never skip response validation on structured JSON returned by Gemini. Every Gemini JSON response must be validated against its expected schema before being returned to the frontend or written to the database.
11. Every endpoint that writes to the database must be wrapped in a transaction. On any exception, the transaction must roll back completely.
12. The frontend TypeScript code must never hardcode the FastAPI base URL. It must always read it from the environment variable NEXT_PUBLIC_API_BASE_URL.

---

## Project Folder Structure

The backend is built and delivered as a completely standalone Python project in its own repository. It has no dependency on, and no knowledge of, the client's existing Next.js codebase. The backend is completed, tested, and deployed first. Only after all endpoints are verified working does the client's frontend developer integrate by pointing their fetch calls at the live API base URL.

The frontend integration steps are handled separately in Phase 10 as a handoff document — a precise set of instructions the client's TypeScript developer follows to wire the existing site to the finished API. No frontend files are created, modified, or referenced during Phases 0 through 9.

The backend folder structure is as follows. Every file and folder listed here is new and created from scratch.

```
myfutureabroad-backend/              root of the new standalone repository
├── app/
│   ├── main.py                      FastAPI app entry point, CORS, router registration, global exception handlers
│   ├── config.py                    reads and validates all environment variables on startup
│   ├── database.py                  SQLAlchemy async engine, session factory, declarative Base
│   ├── dependencies.py              FastAPI dependency functions — get_db and any future shared deps
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py               ChatSession ORM model
│   │   ├── message.py               ChatMessage ORM model
│   │   └── cache.py                 ContentCache ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py                  Pydantic request/response models shared across all chat features
│   │   ├── visa.py                  Pydantic models for visa page structured output
│   │   ├── country.py               Pydantic models for country page structured output
│   │   ├── budget.py                Pydantic models for budget structured output
│   │   └── checklist.py             Pydantic models for checklist structured output
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── visa_finder.py           /visa-finder endpoints
│   │   ├── visa_pages.py            /visas endpoints
│   │   ├── country_pages.py         /countries endpoints
│   │   ├── budget.py                /budget endpoints
│   │   ├── checklist.py             /checklist endpoints
│   │   └── chatbot.py               /chatbot endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini.py                all Gemini API interaction — the only file that calls the Gemini SDK
│   │   └── currency.py              wraps the client's existing currency exchange API
│   └── prompts/
│       ├── __init__.py
│       ├── visa_finder.py           system prompt for the visa finder conversation
│       ├── visa_page.py             prompt template for visa page generation
│       ├── country_page.py          prompt template for country page generation
│       ├── budget.py                system prompt for the budget tool conversation
│       ├── checklist.py             system prompt for the checklist tool conversation
│       └── chatbot.py               system prompt for the general chatbot
├── alembic/
│   ├── env.py                       Alembic config pointing at the same DATABASE_URL and Base
│   └── versions/                    auto-generated migration files live here
├── alembic.ini
├── requirements.txt
├── .env                             all environment variables — never committed to version control
└── .env.example                     a copy of .env with values blanked out — committed to the repo as documentation
```

---

## Phase 0 — Backend Foundation

### Environment Variables Introduced in This Phase

GEMINI_API_KEY — the API key for Google Gemini, obtained from Google AI Studio. Required. The application must refuse to start if this is not set.

DATABASE_URL — full PostgreSQL connection string in the format postgresql+asyncpg://user:password@host:port/dbname. Required. The application must refuse to start if this is not set.

ALLOWED_ORIGINS — a comma-separated list of frontend origins that CORS should permit, for example https://beta.myfutureabroad.com,http://localhost:3000. Required.

GEMINI_MODEL — the exact Gemini model string to use for all API calls. Default value if not set is gemini-2.5-pro. Optional.

GEMINI_TIMEOUT_SECONDS — integer number of seconds before a Gemini API call is considered timed out. Default value if not set is 60. Optional.

CACHE_TTL_SECONDS — integer number of seconds a cached Gemini response for visa or country pages remains valid before being regenerated. Default value if not set is 86400 (24 hours). Optional.

### Dependencies

No previous phases. This phase has no dependencies.

### Files to Create

app/main.py — creates the FastAPI application instance, registers all routers, configures CORS middleware using the ALLOWED_ORIGINS environment variable split by comma, and adds a global exception handler that catches all unhandled exceptions, logs the full traceback, and returns a 500 response with the body shape described in the error envelope below.

app/config.py — reads all environment variables listed above using pydantic-settings. On instantiation, validates that GEMINI_API_KEY and DATABASE_URL are present and non-empty. If either is missing, raises a startup error with a message identifying which variable is absent. Parses ALLOWED_ORIGINS into a Python list by splitting on comma. Parses GEMINI_TIMEOUT_SECONDS and CACHE_TTL_SECONDS into integers with the defaults stated above.

app/database.py — creates an async SQLAlchemy engine using the DATABASE_URL from config. Creates an async session factory bound to that engine. Defines the declarative Base that all ORM models inherit from. Defines a create_all function that creates all tables defined on Base if they do not already exist, to be called at application startup.

app/dependencies.py — defines a get_db async generator dependency that yields an async database session and guarantees the session is closed after the request regardless of whether an exception occurred.

requirements.txt — lists all Python packages needed: fastapi, uvicorn with standard extras, sqlalchemy with asyncio extras, asyncpg, alembic, pydantic-settings, google-generativeai, httpx, and python-dotenv.

### Database Tables

No application tables are created in this phase. The database connection is established and the schema creation mechanism is in place.

### Verification Checklist

Start the FastAPI application with uvicorn. Confirm the application starts without errors. Confirm that accessing the /docs endpoint returns the Swagger UI. Remove GEMINI_API_KEY from the environment and restart — confirm the application refuses to start and prints an error identifying the missing variable. Restore GEMINI_API_KEY. Send a request to any nonexistent path and confirm a 404 is returned. Trigger an unhandled exception by temporarily adding a route that raises a bare exception — confirm a 500 is returned with the standard error envelope shape.

---

## Phase 1 — Database Models and Migrations

### Dependencies

Phase 0 must be complete and the database connection must be verified working.

### Files to Create

app/models/session.py — defines the ChatSession ORM model.

app/models/message.py — defines the ChatMessage ORM model.

app/models/cache.py — defines the ContentCache ORM model.

alembic/env.py — configures Alembic to use the same DATABASE_URL from config and the same Base from database.py so that auto-generated migrations reflect the ORM models.

### Database Tables

Table name: chat_sessions

Columns:
- id: UUID, primary key, generated automatically using uuid4 on insert, not nullable
- feature: VARCHAR(50), not nullable — must be one of the following values: visa_finder, budget, checklist, chatbot. Stores which feature this conversation belongs to.
- created_at: TIMESTAMP WITH TIME ZONE, not nullable, defaults to the current UTC time on insert
- updated_at: TIMESTAMP WITH TIME ZONE, not nullable, defaults to the current UTC time on insert, automatically updated to current UTC time on any update to this row

No foreign keys on this table.

Table name: chat_messages

Columns:
- id: UUID, primary key, generated automatically using uuid4 on insert, not nullable
- session_id: UUID, not nullable, foreign key referencing chat_sessions.id with ON DELETE CASCADE
- role: VARCHAR(20), not nullable — must be one of the following values: user, assistant
- content: TEXT, not nullable — the raw text content of the message
- created_at: TIMESTAMP WITH TIME ZONE, not nullable, defaults to the current UTC time on insert

Indexes: create a non-unique index on session_id to make fetching all messages for a session fast.

Relationship: chat_messages.session_id → chat_sessions.id. When a chat_sessions row is deleted, all chat_messages rows with matching session_id are deleted automatically via cascade.

Table name: content_cache

Columns:
- id: UUID, primary key, generated automatically using uuid4 on insert, not nullable
- cache_key: VARCHAR(255), not nullable, unique — a deterministic string identifying what was cached, for example visa:portugal:d7 or country:spain
- content_json: TEXT, not nullable — the full JSON string of the Gemini-generated structured content
- created_at: TIMESTAMP WITH TIME ZONE, not nullable, defaults to current UTC time on insert
- expires_at: TIMESTAMP WITH TIME ZONE, not nullable — set at insert time to created_at plus CACHE_TTL_SECONDS

Indexes: create a unique index on cache_key. Create a non-unique index on expires_at to allow efficient queries for expired entries.

No foreign keys on this table.

### Verification Checklist

Run the Alembic migration with alembic upgrade head. Connect to the PostgreSQL database directly and confirm all three tables exist with the correct columns and constraints. Confirm the foreign key from chat_messages.session_id to chat_sessions.id exists. Confirm that deleting a row from chat_sessions also deletes all chat_messages rows with the matching session_id. Confirm the unique constraint on content_cache.cache_key prevents inserting two rows with the same key.

---

## Phase 2 — Gemini Service

### Environment Variables Introduced in This Phase

No new environment variables. Uses GEMINI_API_KEY, GEMINI_MODEL, and GEMINI_TIMEOUT_SECONDS from Phase 0.

### Dependencies

Phase 0 must be complete. The Gemini Python SDK must be installed.

### Files to Create

app/services/gemini.py — the single module through which all Gemini API calls are made. This file must not be bypassed by any router or other service.

### Business Logic Rules

The Gemini service exposes two functions that all other parts of the application call.

The first function is for streaming chat responses. It accepts a system prompt string, a list of message objects where each message has a role field (user or assistant) and a content field (string), and a boolean flag indicating whether Google Search grounding should be enabled. It initialises the Gemini client using the GEMINI_API_KEY. It constructs the conversation in the format the Gemini SDK expects. If Google Search grounding is enabled, it adds the GoogleSearch tool to the tools config. It calls the generate_content_stream method on the model specified by GEMINI_MODEL. It yields each text chunk as it arrives from the stream. It enforces the GEMINI_TIMEOUT_SECONDS limit — if the stream does not complete within that time, it raises a GeminiTimeoutError.

The second function is for structured JSON responses. It accepts a system prompt string, a user prompt string, and a boolean flag for Google Search grounding. It calls Gemini with generate_content (non-streaming). It instructs the model via the system prompt to return only valid JSON with no markdown fences, no preamble, and no trailing text. After receiving the response, it extracts the text content, strips any accidental markdown fences, and attempts to parse it as JSON. If parsing fails, it raises a GeminiParseError with the raw response text included in the error. If the call times out, it raises a GeminiTimeoutError. It enforces the GEMINI_TIMEOUT_SECONDS limit.

Both functions must catch all Gemini SDK exceptions and re-raise them as one of three custom exception types defined in this file: GeminiTimeoutError (for timeout), GeminiParseError (for malformed JSON), and GeminiServiceError (for all other Gemini failures). No raw Gemini SDK exceptions should propagate outside this file.

The main.py global exception handler must be updated in this phase to specifically handle GeminiTimeoutError and return a 504 with message "The AI service took too long to respond. Please try again.", GeminiParseError and return a 502 with message "The AI service returned an unexpected response format.", and GeminiServiceError and return a 502 with message "The AI service is currently unavailable."

### Error Cases

If GEMINI_API_KEY is invalid or expired, the Gemini SDK raises an authentication error. This must be caught and re-raised as GeminiServiceError.

If the Gemini API returns a safety block on the response, the response text will be empty or the candidates list will have a finish_reason of SAFETY. This must be detected and raised as GeminiServiceError with a message indicating the content was blocked.

If the network connection to Gemini is lost mid-stream, an httpx or SDK network error will occur. This must be caught and re-raised as GeminiServiceError.

### Verification Checklist

Write a temporary test route in main.py that calls the structured JSON function with a simple prompt asking Gemini to return a JSON object with a single field called "status" with value "ok". Call this route and confirm a valid JSON object is returned. Call the route with an invalid GEMINI_API_KEY and confirm a 502 is returned. Temporarily set GEMINI_TIMEOUT_SECONDS to 1 and call a complex prompt — confirm a 504 is returned. Remove the test route after verification.

---

## Phase 3 — Visa Pages Feature

### Environment Variables Introduced in This Phase

No new environment variables.

### Dependencies

Phases 0, 1, and 2 must be complete and verified.

### Files to Create

app/prompts/visa_page.py — contains the prompt template for generating a structured visa page. The template accepts two variables: country_name and visa_name. The prompt instructs Gemini to search for the current official requirements for the specified visa from the official government immigration authority for that country. It instructs Gemini to return only a valid JSON object with no markdown, no preamble, and no trailing text. It lists every field the JSON must contain and describes what each field should hold. It instructs Gemini that if it cannot find official current data for a specific field, it must set that field to null and set a field called data_confidence to "partial". If all fields are found from official sources, data_confidence must be set to "full". It instructs Gemini never to invent or estimate figures.

app/schemas/visa.py — defines Pydantic models for the visa page response.

app/routers/visa_pages.py — defines the two visa page endpoints.

### Visa Page JSON Schema

The structured JSON that Gemini must return, and that the API must validate and return to the frontend, contains exactly the following fields:

- visa_name: string, the official name of the visa programme
- country: string, the full country name
- country_code: string, ISO 3166-1 alpha-2 two-letter country code in uppercase
- summary: string, a one-paragraph plain-English description of the visa
- target_applicant: string, a plain-English description of who this visa is designed for
- minimum_monthly_income_amount: number or null, the minimum required monthly income in the original currency
- minimum_monthly_income_currency: string or null, the ISO 4217 three-letter currency code for the income figure
- minimum_savings_amount: number or null
- minimum_savings_currency: string or null
- minimum_age: integer or null
- maximum_age: integer or null
- criminal_record_check_required: boolean
- health_insurance_required: boolean
- documents_required: array of strings, each string is one required document
- other_requirements: array of strings, each string is one additional requirement not covered by the structured fields
- application_fee_amount: number or null
- application_fee_currency: string or null
- processing_time_min_days: integer or null
- processing_time_max_days: integer or null
- validity_months: integer or null, the initial validity period in months
- renewable: boolean or null
- path_to_residency: string or null, plain-English description of the path to permanent residency or citizenship if one exists
- source_url: string or null, the URL of the primary official government source used
- data_confidence: string, either "full" or "partial"
- generated_at: string, ISO 8601 UTC datetime of when this was generated

### Endpoints

Endpoint 1: GET /visas/{country_slug}/{visa_slug}

Path parameters:
- country_slug: string — the country name in lowercase with spaces replaced by hyphens, for example "portugal" or "costa-rica"
- visa_slug: string — the visa name in lowercase with spaces replaced by hyphens, for example "d7-passive-income-visa"

Query parameters:
- currency: string, optional — a three-letter ISO 4217 currency code. If provided, the response will include converted monetary amounts alongside the original amounts. If not provided, only original amounts are returned.
- refresh: boolean, optional, default false — if true, the cache is bypassed and Gemini is called fresh regardless of whether a cached entry exists and is still valid.

Business logic rules:
1. Construct the cache_key as "visa:{country_slug}:{visa_slug}".
2. Query the content_cache table for a row where cache_key matches and expires_at is greater than the current UTC time.
3. If a valid cache row is found and refresh is false, parse the content_json from that row as JSON and proceed to the currency conversion step.
4. If no valid cache row is found, or refresh is true, call the Gemini structured JSON function with the visa page prompt template, passing country_name derived from country_slug (replace hyphens with spaces, title case) and visa_name derived from visa_slug (replace hyphens with spaces, title case).
5. Validate the returned JSON against the visa page schema. If validation fails, return 502 with message "The AI service returned an invalid visa data structure."
6. Write the valid JSON to the content_cache table. If a cache row with this cache_key already exists, update its content_json, created_at, and expires_at. If it does not exist, insert a new row.
7. If the currency query parameter is provided, call the currency service to convert minimum_monthly_income_amount, minimum_savings_amount, and application_fee_amount from their original currency codes to the requested currency. Add three additional fields to the response: minimum_monthly_income_converted_amount, minimum_savings_converted_amount, and application_fee_converted_amount, plus a converted_currency field with the target currency code.
8. Return the final response.

Response shape for GET /visas/{country_slug}/{visa_slug} — all fields from the visa page JSON schema listed above, plus, if currency conversion was requested: minimum_monthly_income_converted_amount (number or null), minimum_savings_converted_amount (number or null), application_fee_converted_amount (number or null), converted_currency (string).

Error cases:
- country_slug or visa_slug contains characters other than lowercase letters, digits, and hyphens: return 400 with message "Invalid path parameter format."
- Gemini call fails with GeminiServiceError: return 502 with message "Unable to retrieve visa information at this time."
- Gemini call times out: return 504 with message "The AI service took too long to respond. Please try again."
- Gemini returns invalid JSON: return 502 with message "The AI service returned an unexpected response format."
- Currency conversion fails: return the response without converted amounts and include a field currency_conversion_error set to true.

Validation rules:
- country_slug must match the regex pattern ^[a-z0-9-]+$. If not, return 400, "Invalid country slug format."
- visa_slug must match the regex pattern ^[a-z0-9-]+$. If not, return 400, "Invalid visa slug format."
- If currency is provided, it must be exactly 3 uppercase letters. If not, return 400, "Currency code must be a 3-letter ISO 4217 code."

---

Endpoint 2: GET /visas/{country_slug}

Path parameters:
- country_slug: string — the country name in lowercase with hyphens

Business logic rules:
1. Construct the cache_key as "visas_list:{country_slug}".
2. Check the content_cache for a valid non-expired entry.
3. If found, return the cached list.
4. If not found, call the Gemini structured JSON function with a prompt that instructs Gemini to search for all major long-stay visa programmes available for the specified country and return a JSON array. Each item in the array must contain: visa_name (string), visa_slug (string — the visa name lowercased with spaces replaced by hyphens), summary (string, one sentence), target_applicant (string, one sentence), and minimum_monthly_income_amount (number or null) and minimum_monthly_income_currency (string or null).
5. Validate the response is a JSON array where every item contains at minimum a visa_name and visa_slug field.
6. Cache the result under "visas_list:{country_slug}".
7. Return the array.

Response shape: an object with a single field visas containing an array of objects. Each object contains: visa_name, visa_slug, summary, target_applicant, minimum_monthly_income_amount, minimum_monthly_income_currency.

Error cases follow the same pattern as Endpoint 1.

### Verification Checklist

Call GET /visas/portugal/d7-passive-income-visa and confirm a valid response is returned with all schema fields present. Call the same endpoint again and confirm the response is served from cache (add a cache_hit boolean field to the response to make this testable — true if served from cache, false if freshly generated). Call with an invalid country_slug containing a space and confirm a 400 is returned. Call with refresh=true and confirm Gemini is called again. Call GET /visas/portugal and confirm a list of visa objects is returned. Confirm each item in the list has at minimum visa_name and visa_slug.

---

## Phase 4 — Country Pages Feature

### Dependencies

Phases 0, 1, 2, and 3 must be complete.

### Files to Create

app/prompts/country_page.py — prompt template accepting country_name. Instructs Gemini to search for current, accurate information about the specified country from official government sources, reputable expat publications, official tax authority websites, and international indices. Returns only a valid JSON object matching the country page schema. Instructs Gemini to set data_confidence to "partial" if any field could not be verified from a reliable source, and "full" if all fields were sourced reliably.

app/schemas/country.py — Pydantic models for the country page response.

app/routers/country_pages.py — defines the country page endpoints.

### Country Page JSON Schema

The structured JSON Gemini must return contains exactly the following fields:

- country: string, full country name
- country_code: string, ISO 3166-1 alpha-2 uppercase
- capital_city: string
- official_language: array of strings
- currency_code: string, ISO 4217
- summary: string, two to three paragraph plain-English overview of the country as an expat destination
- climate_description: string
- climate_type: string, one of: tropical, subtropical, mediterranean, temperate, continental, arid, polar
- population: integer or null
- expat_community_size: string, one of: large, moderate, small, minimal
- english_widely_spoken: boolean
- safety_index_score: number or null, the Numbeo Safety Index score if available
- healthcare_quality: string, one of: excellent, good, adequate, limited
- public_healthcare_accessible_to_expats: boolean or null
- cost_of_living_index: number or null, Numbeo Cost of Living Index if available
- average_monthly_rent_city_centre_1bed_amount: number or null
- average_monthly_rent_city_centre_1bed_currency: string or null
- tax_system_type: string, one of: territorial, worldwide, remittance, flat, exempt
- income_tax_rate_description: string, plain-English description of the income tax bands or rate
- capital_gains_tax_description: string or null
- wealth_tax: boolean or null
- pension_income_tax_treatment: string or null
- tax_treaty_with_uk: boolean or null
- tax_treaty_with_us: boolean or null
- path_to_permanent_residency_description: string
- path_to_citizenship_description: string or null
- eu_member: boolean
- schengen_area: boolean
- visa_on_arrival_for_eu_citizens: boolean or null
- visa_on_arrival_for_us_citizens: boolean or null
- visa_on_arrival_for_uk_citizens: boolean or null
- banking_ease_for_expats: string, one of: easy, moderate, difficult
- internet_speed_mbps_average: number or null
- source_urls: array of strings, URLs of sources used
- data_confidence: string, either "full" or "partial"
- generated_at: string, ISO 8601 UTC datetime

### Endpoints

Endpoint 1: GET /countries/{country_slug}

Path parameters:
- country_slug: string, lowercase with hyphens

Query parameters:
- currency: string, optional, 3-letter ISO 4217 code
- refresh: boolean, optional, default false

Business logic rules:
1. Validate country_slug matches ^[a-z0-9-]+$.
2. Construct cache_key as "country:{country_slug}".
3. Check content_cache for valid non-expired entry. If found and refresh is false, use cached content.
4. If not cached or refresh is true, derive country_name from country_slug (replace hyphens with spaces, title case) and call Gemini structured JSON function with country page prompt.
5. Validate response against country page schema. If invalid, return 502.
6. Write to cache.
7. If currency is provided, convert average_monthly_rent_city_centre_1bed_amount from the stored currency to the requested currency. Add converted_rent_amount and converted_currency fields to the response.
8. Return the response including a cache_hit boolean field.

Response shape: all fields from the country page JSON schema, plus cache_hit (boolean), and if currency conversion was requested: converted_rent_amount (number or null), converted_currency (string).

Validation and error cases follow the same patterns as Phase 3.

---

Endpoint 2: GET /countries

Query parameters:
- none required

Business logic rules:
1. Check content_cache for a valid entry with cache_key "countries_list".
2. If cached, return the cached array.
3. If not cached, call Gemini structured JSON function with a prompt instructing it to return a JSON array of all major expat destination countries. Each item must contain: country (string), country_slug (string), country_code (string), summary (one sentence string), eu_member (boolean), cost_of_living_index (number or null), climate_type (string).
4. Validate the response is a JSON array where every item has at minimum country, country_slug, and country_code.
5. Cache the result under "countries_list".
6. Return the array.

Response shape: object with field countries containing an array of objects each with: country, country_slug, country_code, summary, eu_member, cost_of_living_index, climate_type.

### Verification Checklist

Call GET /countries and confirm a JSON array is returned with multiple country objects. Call GET /countries/portugal and confirm all schema fields are present in the response. Confirm cache_hit is false on first call and true on second call. Call GET /countries/invalid slug with a space in the slug and confirm 400. Call with currency=GBP and confirm converted_rent_amount appears in the response.

---

## Phase 5 — Currency Service

### Environment Variables Introduced in This Phase

CURRENCY_API_BASE_URL — the base URL of the existing currency exchange API already built into the frontend project. The client must provide this. Required if currency conversion is used.

CURRENCY_API_KEY — the API key for the currency exchange API, if the existing implementation requires one. Optional — only required if the existing API requires authentication.

### Dependencies

Phases 0, 1, 2, 3, and 4 must be complete. The currency exchange API must be accessible from the backend server.

### Files to Create

app/services/currency.py — wraps the existing currency exchange API.

### Business Logic Rules

The currency service exposes a single function that accepts an amount (number), a from_currency (three-letter ISO 4217 string), and a to_currency (three-letter ISO 4217 string), and returns the converted amount as a float rounded to two decimal places.

If from_currency equals to_currency, return the original amount without making an API call.

If the amount is null or zero, return null without making an API call.

The function must call the existing currency exchange API at CURRENCY_API_BASE_URL. The exact endpoint path and request format must be discovered by reading the existing frontend code before implementing. The function must not assume a specific third-party API format.

The function must time out after 10 seconds. If the call times out, it raises a CurrencyServiceError.

If the external API returns a non-200 status, the function raises CurrencyServiceError with the status code and response body included in the error message.

The main.py global handler must catch CurrencyServiceError and return the visa or country response without converted amounts, with a field currency_conversion_error set to true. It must not return a 5xx for currency failures — the primary data must still be returned.

### Error Cases

External currency API returns 400: raise CurrencyServiceError, message "Invalid currency code pair."
External currency API returns 429: raise CurrencyServiceError, message "Currency service rate limit reached."
External currency API unreachable: raise CurrencyServiceError, message "Currency service unavailable."
Timeout after 10 seconds: raise CurrencyServiceError, message "Currency service timed out."

### Verification Checklist

Call GET /visas/portugal/d7-passive-income-visa?currency=GBP. Confirm the response includes converted amounts and a converted_currency field of "GBP". Call with currency=XYZ (invalid code). Confirm the response still returns the visa data but includes currency_conversion_error set to true. Temporarily point CURRENCY_API_BASE_URL at an unreachable URL. Confirm the visa data is still returned with currency_conversion_error set to true.

---

## Phase 6 — Visa Finder Chatbot

### Dependencies

Phases 0, 1, 2, and 5 must be complete.

### Files to Create

app/prompts/visa_finder.py — the system prompt for the Visa Finder conversation.

app/schemas/chat.py — Pydantic models shared by all chat features.

app/routers/visa_finder.py — the Visa Finder endpoints.

### System Prompt Rules for Visa Finder

The prompt must instruct Gemini to act as an expert expat visa advisor for the website MyFutureAbroad. It must define the following conversation stages in order:

Stage 1 — Intent. Ask the user where they want to move (specific country, region, or continent) and why (retire, work remotely, employment, family, study, investment). Ask only one question at a time. Do not proceed to Stage 2 until both the destination preference and the reason for moving are clear.

Stage 2 — Qualifying questions. Based on the reason for moving, ask the relevant questions. For retirement: monthly income from all sources, total savings, age, whether they have existing health insurance, desired lifestyle type (city, rural, coastal), tax sensitivity (are they specifically seeking a low-tax environment), language preferences, and climate preferences. For remote work: monthly income, employment type (employed by a company, self-employed, or company director), nationality, and whether they are bringing dependants. For investment: available investment capital, whether the goal is residency or citizenship, and timeline. For other purposes: ask the questions most relevant to visa eligibility for that purpose. Ask at most two questions per message. Do not repeat questions already answered.

Stage 3 — Preferences. Ask what other factors matter to them beyond the visa requirements (expat community size, English spoken, healthcare quality, safety, proximity to airports, specific country features). Ask if there are any deal-breakers (must be EU, must have path to citizenship, must allow bringing a pet, etc.).

Stage 4 — Results. Once Stages 1, 2, and 3 are complete, use Google Search to find current visa programmes that match the user's profile. Evaluate each programme against all collected requirements. Return a JSON object with a field called stage set to "results" and a field called visas containing an array of match objects.

The prompt must instruct Gemini that while in Stages 1, 2, and 3 it must return a JSON object with field stage set to "collecting" and field message containing its next conversational response as a plain string.

The prompt must instruct Gemini it must always return valid JSON and nothing else. It must never return plain text outside a JSON structure.

### Chat Request and Response Shapes

All chat endpoints share the same request shape.

Request body fields:
- session_id: string or null — UUID of an existing session. If null, a new session is created.
- message: string, required, not empty, maximum 2000 characters — the user's latest message.
- feature: string, required — must be one of: visa_finder, budget, checklist, chatbot.

When session_id is null, the backend creates a new row in chat_sessions with the appropriate feature value and returns the new session_id in the response. All subsequent messages in the same conversation must include this session_id.

The backend loads all previous messages for the session from chat_messages ordered by created_at ascending and passes them to Gemini as the conversation history. It appends the new user message to this history before calling Gemini. After receiving the Gemini response, it saves both the user message and the assistant message to chat_messages.

Response body fields for all chat endpoints:
- session_id: string, UUID of the session (new or existing)
- stage: string — the current conversation stage returned by Gemini (collecting or results)
- message: string or null — the conversational text to display when stage is "collecting"
- visas: array or null — present only when stage is "results", contains the ranked visa match objects
- stream: boolean — always false for non-streaming responses (streaming is handled by a separate endpoint)

Each visa match object in the visas array contains:
- country: string
- country_slug: string
- visa_name: string
- visa_slug: string
- match_rating: string, one of: excellent, good, ordinary
- match_reasoning: string, one sentence explaining why this rating was given
- key_requirements: array of strings, the two or three most important eligibility requirements
- minimum_monthly_income_amount: number or null
- minimum_monthly_income_currency: string or null

### Endpoints

Endpoint: POST /visa-finder/chat

Request body: session_id (string or null), message (string), feature must equal "visa_finder" — if any other value is sent, return 400 "Feature mismatch. This endpoint is for visa_finder only."

Validation rules:
- message must not be empty. If empty, return 400 "Message cannot be empty."
- message must not exceed 2000 characters. If exceeded, return 400 "Message exceeds maximum length of 2000 characters."
- If session_id is provided and does not exist in the chat_sessions table, return 404 "Session not found."
- If session_id is provided and the session's feature column does not equal "visa_finder", return 400 "Session belongs to a different feature."

Business logic rules:
1. If session_id is null, insert a new row in chat_sessions with feature = "visa_finder". Use the new row's id as session_id for this request.
2. Load all rows from chat_messages where session_id matches, ordered by created_at ascending.
3. Build the message history list from these rows, mapping role and content.
4. Append the new user message to the history.
5. Call the Gemini streaming-capable function with the Visa Finder system prompt, the full message history, and Google Search grounding enabled.
6. Parse the Gemini response as JSON. Validate it has a stage field. If parsing fails, return 502.
7. If stage is "collecting", validate the message field is present and is a non-empty string.
8. If stage is "results", validate the visas field is a non-empty array and each item has at minimum country, visa_name, and match_rating.
9. Save the user message to chat_messages with role "user".
10. Save the assistant response (the full JSON string) to chat_messages with role "assistant".
11. Update chat_sessions.updated_at to current UTC time.
12. Return the response.

Error cases:
- Session not found: 404 "Session not found."
- Gemini times out: 504 "The AI service took too long to respond. Please try again."
- Gemini returns invalid JSON: 502 "The AI service returned an unexpected response format."
- Gemini service error: 502 "The AI service is currently unavailable."
- Database error on save: 500 "Failed to save conversation. Please try again."

Endpoint: GET /visa-finder/session/{session_id}

Path parameters:
- session_id: string, UUID format

Business logic rules:
1. Look up the session in chat_sessions. If not found, return 404 "Session not found."
2. If the session's feature is not "visa_finder", return 400 "Session belongs to a different feature."
3. Load all messages from chat_messages for this session, ordered by created_at ascending.
4. Return the session and its messages.

Response fields:
- session_id: string
- feature: string
- created_at: string, ISO 8601
- messages: array of objects, each with id (string), role (string), content (string), created_at (string ISO 8601)

### Verification Checklist

Send POST /visa-finder/chat with session_id null and message "I want to retire somewhere warm in Europe." Confirm a valid JSON response is returned with stage "collecting" and a follow-up question in the message field. Confirm a new session_id is returned. Send a second message to the same session_id answering the follow-up question. Confirm the session history is being maintained correctly by calling GET /visa-finder/session/{session_id} and confirming both messages appear. Continue the conversation through all stages until a results response is received. Confirm the visas array is present and each item has a match_rating of excellent, good, or ordinary. Send a message with an empty string and confirm a 400 is returned. Send a message with a nonexistent session_id and confirm a 404 is returned.

---

## Phase 7 — Budget Tool

### Dependencies

Phases 0, 1, 2, and 6 must be complete. Phase 5 (currency service) should be complete for accurate budget figures.

### Files to Create

app/prompts/budget.py — system prompt for the Budget Tool conversation.

app/schemas/budget.py — Pydantic models for the budget response.

app/routers/budget.py — budget endpoints.

### System Prompt Rules for Budget Tool

The prompt must instruct Gemini to act as a relocation budget specialist for MyFutureAbroad. It defines the following stages:

Stage 1 — Basics. Collect: destination country, visa type the user is applying for, number of people moving (solo, couple, or family with number of children), country of origin, and approximate move date or timeline. Ask one or two questions per message.

Stage 2 — Moving logistics. Collect: whether they plan to rent or buy property, whether they own property to sell before moving, how many possessions they are shipping (none, a few boxes, full household), whether they have pets, whether they have a vehicle to ship or will buy locally.

Stage 3 — Lifestyle. Collect: expected housing type and area (city centre, suburbs, rural), expected lifestyle level (budget, comfortable, or premium), whether children need international schooling, and whether they will use public or private healthcare.

Stage 4 — Generate budget. Once all three collection stages are complete, use Google Search to find current accurate costs for the destination (rental prices, shipping costs, visa fees, insurance, school fees if applicable). Generate a complete itemised budget in JSON format.

During Stages 1, 2, and 3, Gemini must return JSON with stage set to "collecting" and message containing the next question as plain text.

In Stage 4, Gemini must return JSON with stage set to "complete" and budget containing the full budget object.

### Budget JSON Schema

The budget object returned in Stage 4 must contain:

- destination_country: string
- visa_type: string
- currency_code: string, the currency in which all amounts are expressed (use the local currency of the destination country)
- total_one_time_costs: number
- total_monthly_ongoing_costs: number
- buffer_fund_amount: number, calculated as 15 percent of total_one_time_costs rounded to the nearest whole number
- categories: array of category objects

Each category object contains:
- category_name: string, one of: pre_move, relocation, property, setup, administrative, monthly_living, buffer
- category_total: number
- line_items: array of line item objects

Each line item object contains:
- item_id: string, a unique slug for this item within the budget, for example "visa_application_fee"
- label: string, human-readable name
- amount: number
- frequency: string, one of: one_time, monthly
- notes: string or null, any important caveats or assumptions
- source_url: string or null, the URL where the cost figure was found

### Endpoints

Endpoint: POST /budget/chat

Request body fields: session_id (string or null), message (string), feature must equal "budget".

Validation rules, business logic for session management, and error cases follow the identical pattern as Phase 6 POST /visa-finder/chat, substituting "budget" for "visa_finder" throughout.

Additional business logic for Stage 4 response: after Gemini returns the budget JSON, validate it against the budget schema. If invalid, return 502. Calculate the buffer_fund_amount in the backend as exactly 15 percent of total_one_time_costs, overriding whatever Gemini returned, to ensure accuracy. Set total_one_time_costs to the sum of all category_total values for categories with line items having frequency "one_time". Set total_monthly_ongoing_costs to the sum of all category_total values for categories with line items having frequency "monthly". These totals must be recalculated by the backend, not trusted from Gemini, to ensure mathematical consistency.

Response fields: session_id (string), stage (string), message (string or null), budget (object or null matching the budget schema), stream (boolean, always false).

Endpoint: POST /budget/update

This endpoint allows the user to modify a budget that has already been generated.

Request body fields:
- session_id: string, required — must exist and belong to the budget feature
- instruction: string, required, maximum 1000 characters — a plain-English instruction describing what to change, for example "Increase the buffer fund to 20 percent" or "Add a line item for language classes at 200 euros per month"
- current_budget: object, required — the full current budget object as it exists in the frontend at the time of the request

Business logic rules:
1. Validate session_id exists and belongs to the budget feature.
2. Validate instruction is non-empty and within 1000 characters.
3. Validate current_budget matches the budget schema.
4. Construct a prompt that includes the full current budget JSON and the instruction, and asks Gemini to return a modified version of the budget. Google Search is not enabled for this call — the existing budget already has the data.
5. Parse and validate the returned budget against the budget schema.
6. Recalculate buffer_fund_amount, total_one_time_costs, and total_monthly_ongoing_costs in the backend as described above, overriding Gemini's figures.
7. Save the instruction as a user message and the resulting budget JSON as an assistant message in chat_messages for this session.
8. Return the updated budget.

Response fields: session_id (string), budget (object matching budget schema).

Error cases:
- session_id not found: 404 "Session not found."
- session belongs to wrong feature: 400 "Session belongs to a different feature."
- current_budget fails schema validation: 400 "Invalid budget structure provided."
- instruction empty: 400 "Instruction cannot be empty."
- instruction exceeds 1000 chars: 400 "Instruction exceeds maximum length of 1000 characters."
- Gemini errors follow the same pattern as Phase 6.

### Verification Checklist

Send POST /budget/chat with session_id null and message "I want to move to Portugal." Continue the conversation answering all stage questions. After the final stage, confirm the response contains stage "complete" and a budget object. Confirm buffer_fund_amount equals exactly 15 percent of total_one_time_costs. Confirm total_one_time_costs equals the sum of all one_time line items. Confirm total_monthly_ongoing_costs equals the sum of all monthly line items. Send POST /budget/update with the returned budget and instruction "Add a line item for pet import at 500 euros one-time." Confirm the updated budget contains the new line item and all totals are recalculated correctly.

---

## Phase 8 — Checklist Tool

### Dependencies

Phases 0, 1, 2, and 6 must be complete.

### Files to Create

app/prompts/checklist.py — system prompt for the Checklist Tool conversation.

app/schemas/checklist.py — Pydantic models for checklist response.

app/routers/checklist.py — checklist endpoints.

### System Prompt Rules for Checklist Tool

The prompt instructs Gemini to act as a relocation checklist specialist. It defines two stages.

Stage 1 — Collection. Collect: destination country, approximate move date (to calculate relative timings), visa type, whether renting or buying, family situation (solo, partner, children with ages, pets), whether they own property to sell, employment situation (keeping remote job, seeking employment abroad, retiring), whether they have a vehicle to deal with. Ask at most two questions per message. Do not proceed until all items are collected.

Stage 2 — Generate checklist. Once collection is complete, use Google Search to find country-specific requirements (e.g. specific document legalisation steps for the destination country, registration requirements after arrival). Return JSON with stage "complete" and a checklist object.

During Stage 1, return JSON with stage "collecting" and message containing the next question.

### Checklist JSON Schema

The checklist object must contain:

- destination_country: string
- move_date_reference: string, the move date or timeline the user provided
- phases: array of phase objects

Each phase object contains:
- phase_id: string, one of: six_months_before, three_months_before, one_month_before, two_weeks_before, moving_week, first_month_after, three_months_after, six_months_after, ongoing
- phase_label: string, human-readable label for this phase
- items: array of checklist item objects

Each checklist item object contains:
- item_id: string, a unique slug for this item, for example "apply_for_nif_number"
- title: string, short action title
- description: string, one to two sentences explaining what to do and why
- status: string, always "not_started" when first generated
- category: string, one of: documents, legal, financial, property, logistics, healthcare, administrative, personal
- country_specific: boolean, true if this item was added because of a specific requirement in the destination country
- notes: string or null

### Endpoints

Endpoint: POST /checklist/chat

Request, validation, session management, and error handling follow the identical pattern as POST /budget/chat, substituting "checklist" for "budget" throughout.

Additional business logic: after Gemini returns the checklist in Stage 2, validate it against the checklist schema. If the phases array is empty or contains no items across all phases, return 502 "The AI service returned an empty checklist."

Response fields: session_id (string), stage (string), message (string or null), checklist (object or null matching checklist schema), stream (boolean, always false).

---

Endpoint: POST /checklist/update

Request body fields:
- session_id: string, required
- instruction: string, required, maximum 1000 characters
- current_checklist: object, required, must match the checklist schema

Business logic rules follow the identical pattern as POST /budget/update, substituting checklist objects for budget objects. After Gemini returns the updated checklist, validate against the checklist schema. The item_id for any existing item must not change in the updated checklist — the backend must verify this and return 502 if any existing item_id was modified by Gemini.

Response fields: session_id (string), checklist (object matching checklist schema).

### Verification Checklist

Send POST /checklist/chat with session_id null and message "I want to move to Spain." Continue through all collection questions. After final stage, confirm the response contains stage "complete" and a checklist with multiple phases. Confirm each item has a status of "not_started". Confirm country_specific is true for at least one item. Send POST /checklist/update with instruction "Add an item to research international schools in Madrid." Confirm the updated checklist contains the new item with a new unique item_id. Confirm that no existing item_ids changed.

---

## Phase 9 — General Chatbot

### Dependencies

Phases 0, 1, 2, 3, 4, and 6 must be complete.

### Files to Create

app/prompts/chatbot.py — system prompt for the general chatbot.

app/routers/chatbot.py — general chatbot endpoint.

### System Prompt Rules for General Chatbot

The prompt instructs Gemini to act as a knowledgeable, friendly expat advisor on the MyFutureAbroad website. It must:

Define the assistant's scope: it answers questions about countries as expat destinations, visa programmes, the process of moving abroad, cost of living, tax considerations for expats, healthcare abroad, and general relocation logistics.

Define out-of-scope topics: it does not give legal advice, it does not give specific financial investment advice, it does not answer questions unrelated to expat living or relocation. If asked out-of-scope questions, it politely declines and redirects to the relevant topic.

Define service provider recommendations: the prompt must include the full list of service providers from the client's catalogue (this list must be embedded directly in the system prompt — the format is a structured list of provider name, category, and website URL). When a user asks for a service recommendation, the assistant must only recommend providers from this embedded list. It must never recommend providers not in the list.

Define page redirect logic: when the user asks to be directed somewhere on the website or when a specific page would help them, the assistant must include a redirect field in its JSON response containing the relative URL path. Valid redirect paths are: /visas (general visa finder), /countries (country listings), /budget (budget tool), /checklist (checklist tool), and /visas/{country_slug}/{visa_slug} for specific visa pages.

The prompt instructs Gemini to always return JSON with the following structure: message (string, the conversational response), redirect (string or null, a relative URL path if a redirect is warranted), sources (array of strings or empty array, URLs of any sources used in forming the answer). Google Search grounding is enabled for all chatbot calls.

### Endpoint

Endpoint: POST /chatbot/chat

Request body fields: session_id (string or null), message (string, required, max 2000 characters), feature must equal "chatbot", placement (string, optional, one of: home_page, floating_widget — used for logging only, has no effect on response), current_page (string, optional — the current URL path the user is on, included in the conversation context so the assistant can give contextually relevant responses).

Business logic rules:
1. Session creation and message history follow the identical pattern as all other chat endpoints.
2. If current_page is provided, prepend a system note to the conversation context (not to the permanent message history) indicating the user is currently on that page. This note must not be saved to chat_messages.
3. Call Gemini with Google Search enabled and the chatbot system prompt.
4. Parse the response JSON. Validate it has a message field.
5. If redirect is present, validate it is one of the allowed redirect paths. If not a valid path, set redirect to null before returning.
6. Save user and assistant messages to chat_messages.
7. Return response.

Response fields: session_id (string), message (string), redirect (string or null), sources (array of strings).

Validation rules:
- message must not be empty: 400 "Message cannot be empty."
- message must not exceed 2000 characters: 400 "Message exceeds maximum length of 2000 characters."
- placement, if provided, must be one of home_page or floating_widget: 400 "Invalid placement value."
- session must belong to chatbot feature if session_id is provided: 400 "Session belongs to a different feature."

Error cases follow the same pattern as all other chat endpoints.

### Verification Checklist

Send POST /chatbot/chat with message "What are the visa options for retiring in Portugal?" Confirm a JSON response is returned with a message field containing relevant information. Confirm sources is an array with at least one URL. Confirm redirect is null or a valid path. Send "Can you show me the Portugal D7 visa page?" and confirm redirect is set to "/visas/portugal/d7-passive-income-visa" or equivalent. Send "What is the best restaurant in London?" and confirm the assistant declines and redirects the conversation to expat topics. Send a message asking for a removal company recommendation and confirm only a provider from the embedded catalogue is suggested.

---

## Phase 10 — Frontend Integration Handoff

### Dependencies

All backend phases (0 through 9) must be fully complete, deployed to a live URL, and every endpoint in the endpoint reference table must be verified working via the /docs Swagger UI and direct HTTP calls before this phase begins. This phase produces a handoff document for the client's TypeScript developer. No Python code is written in this phase.

### What This Phase Produces

A single handoff document delivered to the client's frontend developer. This document tells them exactly what to add to their existing Next.js codebase to connect it to the finished API. The backend developer's work is done before this phase starts. The backend developer must not touch the client's TypeScript repository.

### Information the Client's Developer Needs Before Starting

Provide the client's developer with the following before they write a single line of TypeScript:

The live base URL of the deployed FastAPI backend. This must be added to the Next.js environment as NEXT_PUBLIC_API_BASE_URL in the .env.local file. It must not have a trailing slash. It must never be hardcoded anywhere in the TypeScript source — every fetch call must read this variable.

The full contents of the .env.example file from the backend repository, so the client's developer understands what is running on the backend side.

The full list of all endpoints from the endpoint reference table at the end of this guide, including the exact request body fields and response fields for each one. The client's developer must not guess at field names — they must match the backend schemas exactly.

A copy of the Swagger UI URL (/docs on the live backend) so the client's developer can inspect and manually test each endpoint before integrating.

### Files the Client's Developer Must Create in the Next.js Project

src/lib/apiClient.ts — a single module that exports one typed async function per backend endpoint. Each function reads NEXT_PUBLIC_API_BASE_URL to build the request URL, sends the correct HTTP method and JSON body, reads the response, and throws a typed error if the HTTP status is not 2xx. The typed error must include the status code and the message field from the error envelope. No Next.js page or component should ever call fetch directly — all API calls must go through this file.

src/types/api.ts — TypeScript interfaces for every request body and response shape. Every field name, type, and nullable status must exactly match the backend Pydantic schema definitions listed in this guide. This file is the contract between the two sides. If the backend schema changes, this file must be updated before any frontend code that uses the changed field is touched.

### Components the Client's Developer Must Create

src/components/chat/ChatWindow.tsx — manages a full chat conversation for one feature. Accepts: feature (one of visa_finder, budget, checklist, chatbot), initialMessage (optional string shown as the first assistant message before the user types), onStructuredResult (callback invoked with the final visa array, budget object, or checklist object when the conversation reaches stage results or complete). Reads session_id from localStorage using the feature-specific key on mount. On each user message, calls the correct apiClient function with the current session_id (or null if none), appends the response to the displayed message list, writes the returned session_id to localStorage, and if the response contains a structured result calls onStructuredResult.

src/components/chat/ChatMessage.tsx — renders a single message bubble. Accepts role (user or assistant) and content (string). For assistant messages, content is the message field from the JSON response, never the raw JSON string.

src/components/chat/ChatInput.tsx — renders the text input and send button. Accepts onSend callback and disabled boolean. Disables input while a response is in flight. Sends on Enter key or button click. Clears the input field after sending.

src/components/chat/FloatingWidget.tsx — a fixed-position element anchored to the bottom-right corner of the viewport. Renders a button when collapsed. When clicked, opens a ChatWindow with feature set to chatbot and passes the current Next.js pathname as current_page and placement set to floating_widget. Collapses back to the button when closed. Must be rendered in the root layout file so it appears on every page of the site.

src/components/visa/VisaCard.tsx — renders one visa match result. Accepts a single visa match object from the visa finder results array. Displays: the country name, the visa name, the match_rating with a visual colour indicator (green for excellent, amber for good, grey for ordinary), the match_reasoning text, the key_requirements as a short list, and a navigation link to the full visa detail page at /visas/{country_slug}/{visa_slug}.

src/components/visa/VisaDetailPanel.tsx — renders the full visa page for one visa. Accepts a visa detail object matching the visa page response schema. Displays all fields in a structured layout. For every monetary field, shows the original amount and currency code. If converted amounts are present in the response object, shows them alongside the originals. Shows the source_url as a labelled link. Shows generated_at as a "Last updated" label. If data_confidence is partial, shows a prominent disclaimer banner stating the data could not be fully verified and the user should check the official source.

src/components/budget/BudgetTable.tsx — renders the generated budget. Accepts a budget object matching the budget response schema and an onBudgetChange callback. Groups line items by category. Each line item amount is an editable number input — when changed, the component recalculates all category totals, total_one_time_costs, total_monthly_ongoing_costs, and buffer_fund_amount (always 15 percent of total_one_time_costs) locally and calls onBudgetChange with the fully recalculated updated object. Shows the buffer fund as a visually distinct row.

src/components/checklist/ChecklistPanel.tsx — renders the generated checklist. Accepts a checklist object matching the checklist response schema and an onChecklistChange callback. Groups items by phase in chronological order. Each item shows its title, description, and category badge. Each item has a checkbox — toggling it sets status to done or back to not_started and calls onChecklistChange with the updated object.

### Page-Level Wiring the Client's Developer Must Do

The visas page — replace the current page content with a ChatWindow using feature visa_finder and the initial message "Hello, I'm your visa advisor. Tell me where you're thinking of moving and why, and I'll find the best visa options for you." When onStructuredResult fires with the results array, render a grid of VisaCard components below the chat window.

The individual visa detail page at /visas/[country]/[visa] — on page load, call the GET /visas/{country_slug}/{visa_slug} function from apiClient using the route parameters as the slugs. Show a loading skeleton while waiting. Read the key preferred_currency from localStorage — if it exists, pass its value as the currency query parameter. Render a VisaDetailPanel with the returned object.

The countries listing page — on page load, call GET /countries. Render a card grid of country summaries. Each card links to /countries/{country_slug}.

The individual country page at /countries/[country] — on page load, call GET /countries/{country_slug}. Apply the same preferred_currency localStorage logic as the visa detail page. Render the full country profile.

The budget page — render a ChatWindow with feature budget. When onStructuredResult fires, store the budget object in localStorage under the key mfa_budget_latest and render a BudgetTable below the chat. Wire onBudgetChange to update local React state. Add a text input labelled "Ask AI to modify." When the user submits text, call POST /budget/update with the current budget object from state and the instruction text. Update the BudgetTable with the returned budget object and write it to localStorage. On page load, read mfa_budget_latest from localStorage — if it exists, skip the chat and render the BudgetTable immediately with a "Start a new budget" button that clears the key and the session.

The checklist page — identical pattern to the budget page, substituting checklist for budget, the key mfa_checklist_latest, and POST /checklist/update.

The root layout — import FloatingWidget and render it once after the main content slot. It must appear on every page including the home page.

The home page — add a ChatWindow with feature chatbot and placement home_page as a prominent section on the page. This is a separate instance from the floating widget and has its own independent session stored in localStorage under mfa_session_chatbot_home.

### Session Storage Keys the Client's Developer Must Use

All session_id values and structured results must be stored in and read from localStorage. The keys are:

mfa_session_visa_finder — session_id for the visa finder conversation
mfa_session_budget — session_id for the budget conversation
mfa_session_checklist — session_id for the checklist conversation
mfa_session_chatbot — session_id for the floating widget chatbot
mfa_session_chatbot_home — session_id for the home page chatbot instance
mfa_budget_latest — the last generated budget object as a JSON string
mfa_checklist_latest — the last generated checklist object as a JSON string
preferred_currency — the user's selected display currency code (three uppercase letters)

### Verification Checklist for the Client's Developer

After completing all frontend integration work, the client's developer must verify the following before considering integration complete.

The /visas page loads with the initial chat message visible. A full visa finder conversation completes end-to-end and visa cards appear. Clicking a visa card navigates to a detail page that loads all fields. The /countries page loads a grid of country cards. Clicking a country loads the full country profile. Setting preferred_currency to GBP in localStorage and reloading a visa or country page shows converted amounts. The /budget page completes a full conversation and renders an editable budget table. Editing a line item recalculates all totals without an API call. Submitting an AI modification instruction updates the table. Reloading the /budget page restores the last budget without showing the chat. The /checklist page follows the same flow. The floating widget appears on every page. A chatbot conversation completes with a response containing sources. A question that should trigger a redirect returns a redirect field with a valid path and the frontend navigates to it. The home page chatbot instance is independent from the floating widget — each maintains its own session.

---

## Full Endpoint Reference Table

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| GET | /visas/{country_slug}/{visa_slug} | No | Returns full structured visa page data, optionally with currency conversion |
| GET | /visas/{country_slug} | No | Returns a list of all major visa programmes for a country |
| GET | /countries/{country_slug} | No | Returns full structured country profile, optionally with currency conversion |
| GET | /countries | No | Returns a summary list of all available countries |
| POST | /visa-finder/chat | No | Sends a message in the visa finder conversation; returns next question or ranked visa results |
| GET | /visa-finder/session/{session_id} | No | Returns full message history for a visa finder session |
| POST | /budget/chat | No | Sends a message in the budget conversation; returns next question or complete budget object |
| POST | /budget/update | No | Applies a plain-English modification instruction to an existing budget object |
| POST | /checklist/chat | No | Sends a message in the checklist conversation; returns next question or complete checklist object |
| POST | /checklist/update | No | Applies a plain-English modification instruction to an existing checklist object |
| POST | /chatbot/chat | No | Sends a message to the general chatbot; returns a response with optional redirect and sources |
| GET | /chatbot/session/{session_id} | No | Returns full message history for a chatbot session |
| GET | /docs | No | FastAPI auto-generated Swagger UI |
| GET | /health | No | Returns status ok and current UTC time — used for uptime monitoring |

---

## Standard Error Envelope

Every error response from the API must use this exact JSON shape:

- error: boolean, always true
- message: string, a human-readable description of the error safe to display to end users
- status_code: integer, the HTTP status code (mirrors the HTTP response status)
- detail: string or null, additional technical detail for debugging — omit or null in production if it would expose internal information

---

## Standard Success Envelope

Successful responses do not require a wrapper envelope — they return the resource directly. However, every successful response must include a request_id field (a UUID generated per request, for debugging and support) at the top level of the response object. List responses must include a request_id field alongside the data array.
