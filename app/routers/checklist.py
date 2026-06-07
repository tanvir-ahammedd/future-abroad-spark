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
from app.schemas.chat import ChatRequest, SessionHistoryResponse, ChatMessageItem
from app.schemas.checklist import (
    ChecklistChatResponse, ChecklistUpdateRequest, ChecklistUpdateResponse, ChecklistSchema
)
from app.prompts.checklist import SYSTEM_PROMPT, UPDATE_PROMPT_TEMPLATE
from app.services.gemini import generate_chat_stream, generate_structured_json

logger = logging.getLogger("app.routers.checklist")

router = APIRouter(prefix="/checklist", tags=["Checklist Tool"])


def normalize_checklist_data(data: dict) -> dict:
    """
    Defensively normalizes checklist keys, categories, statuses, and phase IDs
    to match the Pydantic schema literals and prevent 502 validation failures.
    """
    valid_phases = {
        "six_months_before", "three_months_before", "one_month_before", "two_weeks_before",
        "moving_week", "first_month_after", "three_months_after", "six_months_after", "ongoing"
    }
    valid_categories = {
        "documents", "legal", "financial", "property", "logistics", "healthcare", "administrative", "personal"
    }
    valid_statuses = {"not_started", "in_progress", "done"}

    phases = data.get("phases", [])
    if not isinstance(phases, list):
        data["phases"] = []
        return data

    normalized_phases = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        phase_id = phase.get("phase_id")
        if phase_id not in valid_phases:
            phase["phase_id"] = "ongoing"
        
        items = phase.get("items", [])
        if not isinstance(items, list):
            phase["items"] = []
            normalized_phases.append(phase)
            continue
        
        normalized_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            
            category = item.get("category")
            if category not in valid_categories:
                # Map close matching or default to personal
                if category == "education":
                    item["category"] = "personal"
                else:
                    item["category"] = "personal"
            
            status = item.get("status")
            if status not in valid_statuses:
                item["status"] = "not_started"
            
            if "country_specific" not in item:
                item["country_specific"] = False
            else:
                item["country_specific"] = bool(item["country_specific"])
                
            normalized_items.append(item)
            
        phase["items"] = normalized_items
        normalized_phases.append(phase)
        
    data["phases"] = normalized_phases
    return data


@router.post("/chat", response_model=ChecklistChatResponse)
async def checklist_chat(
    request_body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Handles conversational interactions for qualifying the user's needs and building their relocation checklist.
    """
    # 1. Feature mismatch validation
    if request_body.feature != "checklist":
        raise HTTPException(status_code=400, detail="Feature mismatch. This endpoint is for checklist only.")

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
        if session.feature != "checklist":
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
        logger.warning(f"Failed to parse Gemini response as JSON, wrapping as collecting stage message. Raw: {response_text}")
        parsed_response = {
            "stage": "collecting",
            "message": response_text.strip()
        }

    stage = parsed_response.get("stage")
    if stage == "collecting":
        msg_text = parsed_response.get("message", "").strip()
        if msg_text.startswith("{") and msg_text.endswith("}"):
            try:
                inner_json = json.loads(msg_text)
                if isinstance(inner_json, dict) and (inner_json.get("stage") == "complete" or "checklist" in inner_json):
                    logger.info("Recovered nested complete checklist response from collecting stage message.")
                    parsed_response = inner_json
                    stage = parsed_response.get("stage", "complete")
            except Exception as pe:
                logger.debug(f"Message started/ended with braces but failed to parse as nested JSON: {pe}")

    if stage not in ["collecting", "complete"]:
        raise HTTPException(status_code=502, detail="The AI service returned an invalid conversation stage.")

    checklist_payload = None
    if stage == "collecting":
        msg_text = parsed_response.get("message")
        if not msg_text or not isinstance(msg_text, str) or not msg_text.strip():
            raise HTTPException(status_code=502, detail="The AI service returned an empty or invalid message.")
    elif stage == "complete":
        checklist_payload = parsed_response.get("checklist")
        if not checklist_payload or not isinstance(checklist_payload, dict):
            raise HTTPException(status_code=502, detail="The AI service returned an invalid or empty checklist object.")
        
        # Normalize checklist structure/literals defensively
        checklist_payload = normalize_checklist_data(checklist_payload)
        
        # Schema validate
        try:
            validated_checklist = ChecklistSchema(**checklist_payload)
        except Exception as e:
            logger.error(f"Checklist validation failed: {e}. Payload: {checklist_payload}")
            raise HTTPException(status_code=502, detail="The AI service returned an invalid checklist structure.")

        # Business rule check: If the phases array is empty or contains no items across all phases, return 502
        total_items = 0
        for phase in validated_checklist.phases:
            total_items += len(phase.items)
        if total_items == 0:
            raise HTTPException(status_code=502, detail="The AI service returned an empty checklist.")

    # 8. Transactionally create/update session and save message pair in a single block
    try:
        if not session_id:
            session = ChatSession(feature="checklist")
            db.add(session)
            await db.flush()  # Populates session.id
            session_id = session.id
        else:
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

    return ChecklistChatResponse(
        session_id=session_id,
        stage=stage,
        message=parsed_response.get("message") if stage == "collecting" else None,
        checklist=checklist_payload,
        stream=False
    )


@router.post("/update", response_model=ChecklistUpdateResponse)
async def checklist_update(
    request_body: ChecklistUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles user instructions to update an already generated checklist.
    """
    session_id = request_body.session_id

    # 1. Validate session
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.feature != "checklist":
        raise HTTPException(status_code=400, detail="Session belongs to a different feature.")

    # 2. Instruction validation
    if not request_body.instruction or not request_body.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction cannot be empty.")
    if len(request_body.instruction) > 1000:
        raise HTTPException(status_code=400, detail="Instruction exceeds maximum length of 1000 characters.")

    # 3. Call Gemini (without search grounding)
    system_prompt = "You are a relocation checklist specialist for MyFutureAbroad. Modify the checklist JSON based on the user's instruction."
    user_prompt = UPDATE_PROMPT_TEMPLATE.format(
        current_checklist=request_body.current_checklist.model_dump_json(),
        instruction=request_body.instruction
    )

    try:
        raw_response = generate_structured_json(system_prompt, user_prompt, enable_search_grounding=False)
    except Exception as e:
        logger.error(f"Gemini checklist update failed: {e}")
        raise e

    # 4. Normalize and validate schema
    raw_response = normalize_checklist_data(raw_response)
    try:
        validated_checklist = ChecklistSchema(**raw_response)
    except Exception as e:
        logger.error(f"Updated checklist validation failed: {e}. Payload: {raw_response}")
        raise HTTPException(status_code=502, detail="The AI service returned an invalid checklist structure.")

    # 5. Verify that no existing item_id was changed or modified by Gemini
    # Collect all original item_ids and their titles
    original_item_map = {}
    for phase in request_body.current_checklist.phases:
        for item in phase.items:
            original_item_map[item.title.strip().lower()] = item.item_id

    # Check the updated checklist
    for phase in validated_checklist.phases:
        for item in phase.items:
            title_lower = item.title.strip().lower()
            if title_lower in original_item_map:
                if item.item_id != original_item_map[title_lower]:
                    logger.error(f"Item ID modified. Expected {original_item_map[title_lower]} for '{item.title}', got {item.item_id}")
                    raise HTTPException(status_code=502, detail="The AI service modified an existing checklist item ID.")

    # 6. Persist instruction and modified checklist inside database transaction
    try:
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=request_body.instruction
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=validated_checklist.model_dump_json()
        )
        db.add(user_msg)
        db.add(assistant_msg)

        session = await db.merge(session)
        session.updated_at = datetime.now(timezone.utc)
        db.add(session)

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save checklist update transaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to save conversation. Please try again.")

    return ChecklistUpdateResponse(
        session_id=session_id,
        checklist=validated_checklist
    )


@router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the message history for a given Checklist session.
    """
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.feature != "checklist":
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
