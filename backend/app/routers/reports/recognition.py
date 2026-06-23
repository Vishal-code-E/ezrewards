import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import RecognitionReportFilters, ExportFormat
from app.services.reports.recognition_service import get_recognition_activity_report

router = APIRouter(
    dependencies=[Depends(require_admin)]
)


@router.get(
    "/recognition",
    summary="Recognition Activity Report",
    description="Overall recognition stats — participation rate, top badge, trends. Admin only.",
)
async def recognition_activity_report(
    department:   Optional[str] = Query(None),
    badge_id:     Optional[str] = Query(None),
    sender_id:    Optional[str] = Query(None),
    recipient_id: Optional[str] = Query(None),
    start_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:     Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:         int           = Query(1,    ge=1),
    page_size:    int           = Query(25,   ge=1, le=250),
    export:       ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    from datetime import date

    filters = RecognitionReportFilters(
        department   = department,
        badge_id     = badge_id,
        sender_id    = sender_id,
        recipient_id = recipient_id,
        start_date   = date.fromisoformat(start_date) if start_date else None,
        end_date     = date.fromisoformat(end_date)   if end_date   else None,
        page         = page,
        page_size    = page_size,
        export       = export,
    )

    workspace_id = current_user["workspace_id"]
    result = await get_recognition_activity_report(workspace_id, filters, db)

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "sender_name", "sender_department",
            "recipient_name", "recipient_dept",
            "badge_name", "message", "created_at",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        from datetime import date
        filename = f"recognitions_{workspace_id}_{date.today()}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return result