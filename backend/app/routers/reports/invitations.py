import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import InvitationReportFilters, ExportFormat
from app.services.reports.invitation_service import get_invitation_report
import asyncpg

router = APIRouter(
    dependencies=[Depends(require_admin)]   # every route here is Admin-only
)


@router.get(
    "/invitations",
    summary="Invitation Status Report",
    description="Returns invitation status breakdown with summary cards and paginated rows. Admin only.",
)
async def invitation_report(
    # ── Filters as query params ────────────────────────────────────────────
    status:     Optional[str] = Query(None, description="Pending|Accepted|Expired|Cancelled"),
    source:     Optional[str] = Query(None, description="csv|single_invite"),
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:       int           = Query(1,    ge=1),
    page_size:  int           = Query(25,   ge=1, le=250),
    export:     ExportFormat  = Query(ExportFormat.json),

    # ── Dependencies ───────────────────────────────────────────────────────
    current_user: dict        = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    from datetime import date

    filters = InvitationReportFilters(
        status     = status,
        source     = source,
        department = department,
        start_date = date.fromisoformat(start_date) if start_date else None,
        end_date   = date.fromisoformat(end_date)   if end_date   else None,
        page       = page,
        page_size  = page_size,
        export     = export,
    )

    workspace_id = current_user["workspace_id"]

    result = await get_invitation_report(workspace_id, filters, db)

    # ── CSV export ─────────────────────────────────────────────────────────
    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "email", "display_name", "department", "role",
            "status", "source", "invite_count", "invited_by",
            "created_at", "expires_at", "accepted_at",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        from datetime import date
        filename = f"invitations_{workspace_id}_{date.today()}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return result