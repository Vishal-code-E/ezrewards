import uuid
from fastapi import APIRouter, Depends
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import ChatMessage, ChatResponse
from app.services.chat_service import process_chat_message

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/chat/reports",
    summary="Report Chatbot",
    description="Natural language interface over all report data. Admin only.",
)
async def report_chat(
    body:         ChatMessage,
    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
) -> ChatResponse:

    result = await process_chat_message(
        message      = body.message,
        workspace_id = current_user["workspace_id"],
        db           = db,
    )

    return ChatResponse(
        answer     = result["answer"],
        tool_used  = result["tool_used"],
        request_id = f"req_{uuid.uuid4().hex[:8]}",
    )