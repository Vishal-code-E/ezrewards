import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import EmailNotificationFilters, ExportFormat
from app.services.reports.email_notification_service import (
    get_email_notification_report,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/emails",
    summary="Email Notification Report",
    description="Delivery rates, open rates, and failure breakdown for all system emails. Admin only.",
)
async def email_notification_report(
    status:     Optional[str] = Query(None, description="Sent|Delivered|Bounced|Failed|Opened"),
    email_type: Optional[str] = Query(None, description="invite|recognition_notification|billing_alert|wallet_alert|voucher_delivery"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:       int           = Query(1,  ge=1),
    page_size:  int           = Query(25, ge=1, le=250),
    export:     ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = EmailNotificationFilters(
        status     = status,
        email_type = email_type,
        start_date = date.fromisoformat(start_date) if start_date else None,
        end_date   = date.fromisoformat(end_date)   if end_date   else None,
        page       = page,
        page_size  = page_size,
        export     = export,
    )

    result = await get_email_notification_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "recipient_email", "recipient_name", "email_type",
            "subject", "status", "failure_reason",
            "retry_count", "sent_at", "delivered_at",
            "opened_at", "created_at",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="email_notifications_{date.today()}.csv"'
            },
        )

    return result
