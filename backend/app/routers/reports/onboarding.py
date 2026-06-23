import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import OnboardingReportFilters, ExportFormat
from app.services.reports.onboarding_service import get_onboarding_report

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/onboarding",
    summary="Employee Onboarding Report",
    description="Invite-to-activation funnel for every employee. Admin only.",
)
async def onboarding_report(
    status:     Optional[str] = Query(None, description="Pending|Accepted|Expired|Cancelled"),
    source:     Optional[str] = Query(None, description="csv|single_invite"),
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:       int           = Query(1,  ge=1),
    page_size:  int           = Query(25, ge=1, le=250),
    export:     ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = OnboardingReportFilters(
        status     = status,
        source     = source,
        department = department,
        start_date = date.fromisoformat(start_date) if start_date else None,
        end_date   = date.fromisoformat(end_date)   if end_date   else None,
        page       = page,
        page_size  = page_size,
        export     = export,
    )

    result = await get_onboarding_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "email", "display_name", "department", "role",
            "invite_status", "member_status", "source",
            "invite_count", "invited_at", "expires_at",
            "activated_at", "days_to_activate",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="onboarding_{date.today()}.csv"'
            },
        )

    return result