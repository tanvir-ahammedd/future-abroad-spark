import json
import uuid
import logging
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.dependencies import get_db
from app.models.session import ChatSession
from app.models.message import ChatMessage
from app.schemas.chat import ChatbotRequest, ChatbotResponse, SessionHistoryResponse, ChatMessageItem
from app.prompts.chatbot import SYSTEM_PROMPT
from app.services.gemini import generate_chat_stream

logger = logging.getLogger("app.routers.chatbot")

router = APIRouter(prefix="/chatbot", tags=["General Chatbot"])

ALLOWED_STATIC_REDIRECTS = {"/visas", "/countries", "/budget", "/checklist"}
SPECIFIC_VISA_REDIRECT_PATTERN = re.compile(r"^/visas/[a-z0-9-]+/[a-z0-9-]+$")

def is_valid_redirect(path: str) -> bool:
    if path in ALLOWED_STATIC_REDIRECTS:
        return True
    if SPECIFIC_VISA_REDIRECT_PATTERN.match(path):
        return True
    return False

@router.post("/chat", response_model=ChatbotResponse)
async def chatbot_chat(
    request_body: ChatbotRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Handles conversational interactions for general expat inquiries.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # 1. Feature validation (done by Pydantic but double checking)
    if request_body.feature != "chatbot":
        raise HTTPException(status_code=400, detail="Feature mismatch. This endpoint is for chatbot only.")

    # 2. Message validations
    if not request_body.message or not request_body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(request_body.message) > 2000:
        raise HTTPException(status_code=400, detail="Message exceeds maximum length of 2000 characters.")

    # 3. Placement validation
    if request_body.placement is not None and request_body.placement not in ("home_page", "floating_widget"):
        raise HTTPException(status_code=400, detail="Invalid placement value.")

    # 4. Validate existing session if provided
    session = None
    session_id = request_body.session_id
    if session_id:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.feature != "chatbot":
            raise HTTPException(status_code=400, detail="Session belongs to a different feature.")

    # 5. Load session history if session exists
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

    # 6. Append new user message to conversation payload
    history.append({"role": "user", "content": request_body.message})

    # Prepare temp history for API call by prepending current_page system note if provided
    api_history = list(history)
    if request_body.current_page:
        latest_msg = api_history[-1]
        api_history[-1] = {
            "role": "user",
            "content": f"[System Note: User is currently on page: {request_body.current_page}]\n{latest_msg['content']}"
        }

    # 7. Call Gemini
    response_text = ""
    try:
        for chunk in generate_chat_stream(SYSTEM_PROMPT, api_history, enable_search_grounding=True):
            response_text += chunk
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        raise e

    # 8. Parse and validate Gemini JSON response
    cleaned_text = response_text.strip()
    first_brace = cleaned_text.find("{")
    last_brace = cleaned_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned_text = cleaned_text[first_brace:last_brace + 1]

    try:
        parsed_response = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Gemini response as JSON, wrapping as default message. Raw: {response_text}")
        parsed_response = {
            "message": response_text.strip(),
            "redirect": None,
            "sources": []
        }

    message_content = parsed_response.get("message", "").strip()
    if not message_content:
        message_content = response_text.strip() or "I'm sorry, I couldn't generate a response."

    redirect_path = parsed_response.get("redirect")
    if redirect_path:
        if not is_valid_redirect(redirect_path):
            logger.warning(f"Invalid redirect path returned by Gemini: {redirect_path}. Setting to null.")
            redirect_path = None

    sources_list = parsed_response.get("sources", [])
    if not isinstance(sources_list, list):
        sources_list = []
    else:
        sources_list = [str(src) for src in sources_list]

    # 9. Transactionally create/update session and save message pair in a single block
    try:
        if not session_id:
            # Create new session atomically
            session = ChatSession(feature="chatbot")
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
            content=json.dumps({
                "message": message_content,
                "redirect": redirect_path,
                "sources": sources_list
            })
        )
        db.add(user_msg)
        db.add(assistant_msg)
        
        await db.commit()
    except Exception as e:
        import traceback
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"Failed to save conversation to database: {e}\n{tb_str}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save conversation. Please try again.")

    return ChatbotResponse(
        session_id=session_id,
        message=message_content,
        redirect=redirect_path,
        sources=sources_list,
        request_id=request_id
    )

@router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the message history for a given Chatbot session.
    """
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.feature != "chatbot":
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
