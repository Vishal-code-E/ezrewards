import anthropic
import logging
import json
import uuid
from datetime import date

from app.config import settings
import asyncpg

logger = logging.getLogger(__name__)

# ── Tool definitions — one per report service ─────────────────────────────────

REPORT_TOOLS = [
    {
        "name": "get_invitation_report",
        "description": "Get invitation status counts — accepted, pending, expired, cancelled, and activation rate. Use when asked about invitations, pending invites, how many employees have joined, or onboarding status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: Pending, Accepted, Expired, or Cancelled"
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department name"
                },
            },
        },
    },
    {
        "name": "get_recognition_activity_report",
        "description": "Get overall recognition statistics — total recognitions, participation rate, top badge, average per employee. Use when asked about recognition culture, participation rates, or recognition trends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Filter by department name"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
            },
        },
    },
    {
        "name": "get_recognition_given_report",
        "description": "Get employees ranked by number of recognitions they have given. Use when asked about top recognizers, most active senders, or who is giving the most recognition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Filter by department name"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
            },
        },
    },
    {
        "name": "get_recognition_received_report",
        "description": "Get employees ranked by number of recognitions they have received. Use when asked about most recognized employees, top recipients, or who gets the most appreciation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Filter by department name"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
            },
        },
    },
    {
        "name": "get_seat_usage_report",
        "description": "Get purchased seats vs active users, available seats, and utilization percentage. Use when asked about seat usage, capacity, how many seats are available, or how many employees are active.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_redemption_report",
        "description": "Get voucher redemption data — total redemptions, success rate, failed redemptions, and total value redeemed. Use when asked about voucher redemptions, gift cards, or reward spending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: Completed, Failed, or Pending"
                },
                "voucher_brand": {
                    "type": "string",
                    "description": "Filter by brand: Amazon, Swiggy, Myntra, etc."
                },
            },
        },
    },
    {
        "name": "get_wallet_report",
        "description": "Get current wallet balance, total recharged, total consumed, average monthly spend, and projected empty date. Use when asked about wallet balance, credits, burn rate, or when the wallet will run out.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_wallet_transaction_report",
        "description": "Get full wallet ledger — every credit and debit with amounts and running balance. Use when asked about wallet history, recent transactions, or specific wallet activity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "Filter by transaction type: Credit or Debit"
                },
            },
        },
    },
    {
        "name": "get_payment_report",
        "description": "Get subscription payment history — invoices, amounts paid, GST, and failed payments. Use when asked about billing, payments, invoices, or subscription charges.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: Paid, Failed, or Pending"
                },
            },
        },
    },
]


# ── Tool executor — calls the matching service function ───────────────────────

async def execute_tool(
    tool_name: str,
    tool_input: dict,
    workspace_id: str,
    db: asyncpg.Connection,
) -> dict:
    """
    Routes the tool call Claude made to the actual service function.
    workspace_id is always injected here — never from the LLM input.
    """
    from datetime import date as date_type

    # Import all services
    from app.services.reports.invitation_service import get_invitation_report
    from app.services.reports.recognition_service import get_recognition_activity_report
    from app.services.reports.recognition_given_service import get_recognition_given_report
    from app.services.reports.recognition_received_service import get_recognition_received_report
    from app.services.reports.seat_usage_service import get_seat_usage_report
    from app.services.reports.redemption_service import get_redemption_report
    from app.services.reports.wallet_service import get_wallet_report
    from app.services.reports.wallet_transaction_service import get_wallet_transaction_report
    from app.services.reports.payment_service import get_payment_report
    from app.schemas.reports import (
        BaseReportFilters,
        InvitationReportFilters,
        RecognitionReportFilters,
        RecognitionGivenFilters,
        RecognitionReceivedFilters,
        RedemptionReportFilters,
        WalletTransactionFilters,
        PaymentReportFilters,
    )

    def parse_date(d):
        return date_type.fromisoformat(d) if d else None

    # ── Route to correct service ──────────────────────────────────────────────
    if tool_name == "get_invitation_report":
        result = await get_invitation_report(
            workspace_id,
            InvitationReportFilters(
                status     = tool_input.get("status"),
                department = tool_input.get("department"),
            ),
            db,
        )

    elif tool_name == "get_recognition_activity_report":
        result = await get_recognition_activity_report(
            workspace_id,
            RecognitionReportFilters(
                department = tool_input.get("department"),
                start_date = parse_date(tool_input.get("start_date")),
                end_date   = parse_date(tool_input.get("end_date")),
            ),
            db,
        )

    elif tool_name == "get_recognition_given_report":
        result = await get_recognition_given_report(
            workspace_id,
            RecognitionGivenFilters(
                department = tool_input.get("department"),
                start_date = parse_date(tool_input.get("start_date")),
                end_date   = parse_date(tool_input.get("end_date")),
            ),
            db,
        )

    elif tool_name == "get_recognition_received_report":
        result = await get_recognition_received_report(
            workspace_id,
            RecognitionReceivedFilters(
                department = tool_input.get("department"),
                start_date = parse_date(tool_input.get("start_date")),
                end_date   = parse_date(tool_input.get("end_date")),
            ),
            db,
        )

    elif tool_name == "get_seat_usage_report":
        result = await get_seat_usage_report(
            workspace_id,
            BaseReportFilters(),
            db,
        )

    elif tool_name == "get_redemption_report":
        result = await get_redemption_report(
            workspace_id,
            RedemptionReportFilters(
                status        = tool_input.get("status"),
                voucher_brand = tool_input.get("voucher_brand"),
            ),
            db,
        )

    elif tool_name == "get_wallet_report":
        result = await get_wallet_report(
            workspace_id,
            BaseReportFilters(),
            db,
        )

    elif tool_name == "get_wallet_transaction_report":
        result = await get_wallet_transaction_report(
            workspace_id,
            WalletTransactionFilters(
                type = tool_input.get("type"),
            ),
            db,
        )

    elif tool_name == "get_payment_report":
        result = await get_payment_report(
            workspace_id,
            PaymentReportFilters(
                status = tool_input.get("status"),
            ),
            db,
        )

    else:
        return {"error": f"Unknown tool: {tool_name}"}

    return result.model_dump()


# ── Main chat function ────────────────────────────────────────────────────────

async def process_chat_message(
    message: str,
    workspace_id: str,
    db: asyncpg.Connection,
) -> dict:
    """
    Tool Calling chatbot — Option 1 architecture.

    Flow:
      1. Call Claude with user message + 9 tool definitions
      2. Claude picks the right tool + params
      3. We execute the tool (calling real service function)
      4. Pass result back to Claude
      5. Claude formats natural language answer
      6. Return answer to admin
    """

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    today = date.today().strftime("%d %B %Y")

    system_prompt = f"""You are EzRewards Report Assistant — an AI that helps HR admins 
query their employee recognition and rewards data instantly.

Today's date: {today}
Workspace ID: {workspace_id}

Rules:
- Always use exactly one tool to answer the question
- Be concise — admins want numbers and names, not paragraphs
- If data shows 0 results, say so clearly and suggest why
- Never make up numbers — only use data from tool results
- Format numbers clearly: use ₹ for currency, % for rates
- If the question is ambiguous, pick the most likely intent and answer it
- Do not apply a status/type filter to a report tool unless the user explicitly named that status/type — fetch the unfiltered report so your summary reflects the complete picture (e.g. don't filter to "Paid" when asked a general payment health question, since that would hide failed or pending records)"""

    # ── Step 1: First Claude call — tool selection ────────────────────────────
    logger.info(f"Chat request | workspace={workspace_id} | message={message[:50]}")

    response = client.messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 1024,
        system     = system_prompt,
        tools      = REPORT_TOOLS,
        messages   = [{"role": "user", "content": message}],
    )

    # ── Handle case where Claude answers without a tool ───────────────────────
    if response.stop_reason == "end_turn":
        answer = next(
            (b.text for b in response.content if hasattr(b, "text")), 
            "I couldn't find relevant data for that question."
        )
        return {
            "answer":    answer,
            "tool_used": None,
        }

    # ── Step 2: Extract tool call ─────────────────────────────────────────────
    tool_use_block = next(
        (b for b in response.content if b.type == "tool_use"), None
    )

    if not tool_use_block:
        return {
            "answer":    "I wasn't able to identify which report to query. Could you rephrase?",
            "tool_used": None,
        }

    tool_name  = tool_use_block.name
    tool_input = tool_use_block.input

    logger.info(f"Tool selected: {tool_name} | params: {tool_input}")

    # ── Step 3: Execute the tool ──────────────────────────────────────────────
    # workspace_id comes from JWT — never from Claude's tool_input
    tool_result = await execute_tool(tool_name, tool_input, workspace_id, db)

    # ── Step 4: Second Claude call — format the answer ────────────────────────
    final_response = client.messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 512,
        system     = system_prompt,
        tools      = REPORT_TOOLS,
        messages   = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type":        "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content":     json.dumps(tool_result, default=str),
                    }
                ],
            },
        ],
    )

    answer = next(
        (b.text for b in final_response.content if hasattr(b, "text")),
        "I received the data but couldn't format a response."
    )

    logger.info(f"Chat response | workspace={workspace_id} | tool={tool_name}")

    return {
        "answer":    answer,
        "tool_used": tool_name,
    }