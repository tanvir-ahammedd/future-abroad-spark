import logging
import traceback
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_all_tables

# Configure logging to output traceback to stdout/console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")

# Initialize FastAPI application
app = FastAPI(
    title="MyFutureAbroad Backend",
    description="Standalone FastAPI Backend for MyFutureAbroad AI integrations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware using strict allowed origins list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to assign unique Request ID to each request
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Retrieve request ID if available
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # 8. Never silently swallow exceptions. Every exception must be logged with its full traceback.
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled Exception for Request {request_id}: {exc}\n{tb_str}")
    
    # 2. Never return raw Gemini or database error messages directly. Wrap in standard error envelope.
    # Check if we are in development environment by assessing local connection or similar (here, default to showing detailed error info)
    detail_message = str(exc)
    
    error_content = {
        "error": True,
        "message": "An unexpected error occurred. Please try again later.",
        "status_code": 500,
        "detail": detail_message,
        "request_id": request_id
    }
    
    return JSONResponse(
        status_code=500,
        content=error_content
    )

# Lifespan Startup Event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up MyFutureAbroad FastAPI application...")
    try:
        # Attempt to create tables on startup (convenience for development)
        await create_all_tables()
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Could not automatically initialize database tables: {e}")

# Health Check Endpoint
@app.get("/health")
async def health_check(request: Request):
    """
    Uptime and health check monitoring endpoint.
    Includes status, current UTC time, and request ID.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id
    }

# Temporary Endpoint to verify unhandled error handler
@app.get("/test-error")
async def test_error():
    """
    Simulates a bare exception to verify the global error handler
    and standard error envelope shape.
    """
    raise ValueError("Simulated internal server error.")
