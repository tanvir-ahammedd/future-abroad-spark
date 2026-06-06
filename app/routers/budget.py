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
from app.schemas.budget import BudgetChatResponse, BudgetUpdateRequest, BudgetUpdateResponse, BudgetSchema
from app.prompts.budget import SYSTEM_PROMPT, UPDATE_PROMPT_TEMPLATE
from app.services.gemini import generate_chat_stream, generate_structured_json

logger = logging.getLogger("app.routers.budget")

router = APIRouter(prefix="/budget", tags=["Budget Tool"])


def recalculate_budget_totals(budget_data: dict) -> dict:
    """
    Recalculates category totals, total_one_time_costs, total_monthly_ongoing_costs,
    and buffer_fund_amount (15% of total one-time costs, rounded to nearest integer)
    in the backend to ensure mathematical consistency.
    """
    one_time_sum = 0.0
    monthly_sum = 0.0

    categories = budget_data.get("categories", [])
    for cat in categories:
        cat_total = 0.0
        line_items = cat.get("line_items", [])
        for item in line_items:
            amt = float(item.get("amount") or 0.0)
            freq = item.get("frequency")
            cat_total += amt
            if freq == "one_time":
                one_time_sum += amt
            elif freq == "monthly":
                monthly_sum += amt
        cat["category_total"] = round(cat_total, 2)

    budget_data["total_one_time_costs"] = round(one_time_sum, 2)
    budget_data["total_monthly_ongoing_costs"] = round(monthly_sum, 2)
    budget_data["buffer_fund_amount"] = float(round(one_time_sum * 0.15))
    return budget_data


@router.post("/chat", response_model=BudgetChatResponse)
async def budget_chat(
    request_body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Handles conversational interactions for qualifying the user's needs and building their budget.
    """
    # 1. Feature mismatch validation
    if request_body.feature != "budget":
        raise HTTPException(status_code=400, detail="Feature mismatch. This endpoint is for budget only.")

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
        if session.feature != "budget":
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
    if stage not in ["collecting", "complete"]:
        raise HTTPException(status_code=502, detail="The AI service returned an invalid conversation stage.")

    budget_payload = None
    if stage == "collecting":
        msg_text = parsed_response.get("message")
        if not msg_text or not isinstance(msg_text, str) or not msg_text.strip():
            raise HTTPException(status_code=502, detail="The AI service returned an empty or invalid message.")
    elif stage == "complete":
        budget_payload = parsed_response.get("budget")
        if not budget_payload or not isinstance(budget_payload, dict):
            raise HTTPException(status_code=502, detail="The AI service returned an invalid or empty budget object.")
        
        # Validate structure against schema by attempting to instantiate BudgetSchema
        try:
            # Recalculate totals first
            budget_payload = recalculate_budget_totals(budget_payload)
            # Schema validate
            BudgetSchema(**budget_payload)
        except Exception as e:
            logger.error(f"Budget validation failed: {e}. Payload: {budget_payload}")
            raise HTTPException(status_code=502, detail="The AI service returned an invalid budget structure.")

    # 8. Transactionally create/update session and save message pair in a single block
    try:
        if not session_id:
            # Create new session atomically
            session = ChatSession(feature="budget")
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

    return BudgetChatResponse(
        session_id=session_id,
        stage=stage,
        message=parsed_response.get("message") if stage == "collecting" else None,
        budget=budget_payload,
        stream=False
    )


@router.post("/update", response_model=BudgetUpdateResponse)
async def budget_update(
    request_body: BudgetUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles user instructions to update an already generated budget.
    """
    session_id = request_body.session_id

    # 1. Validate session
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.feature != "budget":
        raise HTTPException(status_code=400, detail="Session belongs to a different feature.")

    # 2. Instruction validation
    if not request_body.instruction or not request_body.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction cannot be empty.")
    if len(request_body.instruction) > 1000:
        raise HTTPException(status_code=400, detail="Instruction exceeds maximum length of 1000 characters.")

    # 3. Call Gemini (without search grounding)
    system_prompt = "You are a relocation budget specialist for MyFutureAbroad. Modify the budget JSON based on the user's instruction."
    user_prompt = UPDATE_PROMPT_TEMPLATE.format(
        current_budget=request_body.current_budget.model_dump_json(),
        instruction=request_body.instruction
    )

    try:
        raw_response = generate_structured_json(system_prompt, user_prompt, enable_search_grounding=False)
    except Exception as e:
        logger.error(f"Gemini budget update failed: {e}")
        raise e

    # 4. Schema validation and recalculations
    try:
        # Recalculate totals
        recalculated_budget = recalculate_budget_totals(raw_response)
        # Validate structure against BudgetSchema
        validated_budget = BudgetSchema(**recalculated_budget)
    except Exception as e:
        logger.error(f"Updated budget validation failed: {e}. Payload: {raw_response}")
        raise HTTPException(status_code=502, detail="The AI service returned an invalid budget structure.")

    # 5. Persist instruction and modified budget inside database transaction
    try:
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=request_body.instruction
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=validated_budget.model_dump_json()
        )
        db.add(user_msg)
        db.add(assistant_msg)

        session = await db.merge(session)
        session.updated_at = datetime.now(timezone.utc)
        db.add(session)

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save budget update transaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to save conversation. Please try again.")

    return BudgetUpdateResponse(
        session_id=session_id,
        budget=validated_budget
    )


@router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the message history for a given Budget session.
    """
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.feature != "budget":
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
