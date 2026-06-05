import json
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.dependencies import get_db
from app.models.session import ChatSession
from app.models.message import ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, SessionHistoryResponse, ChatMessageItem
from app.prompts.visa_finder import SYSTEM_PROMPT
from app.services.gemini import generate_chat_stream

logger = logging.getLogger("app.routers.visa_finder")

router = APIRouter(prefix="/visa-finder", tags=["Visa Finder Chatbot"])


@router.post("/chat", response_model=ChatResponse)
async def visa_finder_chat(
    request_body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Handles conversational interactions for qualifying and suggesting visas.
    Uses Google Search grounding and saves history in the database.
    """
    # 1. Feature mismatch validation
    if request_body.feature != "visa_finder":
        raise HTTPException(status_code=400, detail="Feature mismatch. This endpoint is for visa_finder only.")

    # 2. Message validations
    if not request_body.message or not request_body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(request_body.message) > 2000:
        raise HTTPException(status_code=400, detail="Message exceeds maximum length of 2000 characters.")

    # 3. Validate existing session if provided
    session = None
    session_id = request_body.session_id
    if session_id:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.feature != "visa_finder":
            raise HTTPException(status_code=400, detail="Session belongs to a different feature.")

    # 4. Load session history if session exists
    history = []
    if session_id:
        try:
            stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
            res = await db.execute(stmt)
            messages_db = res.scalars().all()
            history = [{"role": msg.role, "content": msg.content} for msg in messages_db]
        except Exception as e:
            logger.error(f"Failed to load chat history for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to load chat history.")

    # 5. Append new user message to conversation payload
    history.append({"role": "user", "content": request_body.message})

    # 6. Call Gemini
    response_text = ""
    try:
        for chunk in generate_chat_stream(SYSTEM_PROMPT, history, enable_search_grounding=True):
            response_text += chunk
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        raise e

    # 7. Parse and validate Gemini JSON response
    cleaned_text = response_text.strip()
    first_brace = cleaned_text.find("{")
    last_brace = cleaned_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned_text = cleaned_text[first_brace:last_brace + 1]

    try:
        parsed_response = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {response_text}. Error: {e}")
        raise HTTPException(status_code=502, detail="The AI service returned an unexpected response format.")

    stage = parsed_response.get("stage")
    if stage not in ["collecting", "results"]:
        raise HTTPException(status_code=502, detail="The AI service returned an invalid conversation stage.")

    if stage == "collecting":
        msg_text = parsed_response.get("message")
        if not msg_text or not isinstance(msg_text, str) or not msg_text.strip():
            raise HTTPException(status_code=502, detail="The AI service returned an empty or invalid message.")
    elif stage == "results":
        visas = parsed_response.get("visas")
        if not isinstance(visas, list) or len(visas) == 0:
            raise HTTPException(status_code=502, detail="The AI service returned an invalid or empty visas list.")
        for item in visas:
            if not isinstance(item, dict) or "country" not in item or "visa_name" not in item or "match_rating" not in item:
                raise HTTPException(status_code=502, detail="The AI service returned an invalid visa match structure.")

    # 8. Transactionally create/update session and save message pair in a single block
    try:
        if not session_id:
            # Create new session atomically
            session = ChatSession(feature="visa_finder")
            db.add(session)
            await db.flush()  # Populates session.id
            session_id = session.id
        else:
            # Update updated_at
            session = await db.merge(session)
            session.updated_at = datetime.now(timezone.utc)
            db.add(session)

        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=request_body.message
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=json.dumps(parsed_response)
        )
        db.add(user_msg)
        db.add(assistant_msg)
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save conversation to database: {e}")
        raise HTTPException(status_code=500, detail="Failed to save conversation. Please try again.")

    return ChatResponse(
        session_id=session_id,
        stage=stage,
        message=parsed_response.get("message") if stage == "collecting" else None,
        visas=parsed_response.get("visas") if stage == "results" else None,
        stream=False
    )


@router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the message history for a given Visa Finder chat session.
    """
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.feature != "visa_finder":
        raise HTTPException(status_code=400, detail="Session belongs to a different feature.")
        
    try:
        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        res = await db.execute(stmt)
        messages_db = res.scalars().all()
    except Exception as e:
        logger.error(f"Failed to retrieve chat messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load chat session history.")
        
    messages = [
        ChatMessageItem(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at
        ) for msg in messages_db
    ]
    
    return SessionHistoryResponse(
        session_id=session.id,
        feature=session.feature,
        created_at=session.created_at,
        messages=messages
    )
