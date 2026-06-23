import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import RecognitionGivenFilters, ExportFormat
from app.services.reports.recognition_given_service import get_recognition_given_report

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/recognition/given",
    summary="Recognition Given Report",
    description="Ranks employees by recognitions sent. Shows top recognizers. Admin only.",
)
async def recognition_given_report(
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:       int           = Query(1,  ge=1),
    page_size:  int           = Query(25, ge=1, le=250),
    export:     ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    from datetime import date

    filters = RecognitionGivenFilters(
        department = department,
        start_date = date.fromisoformat(start_date) if start_date else None,
        end_date   = date.fromisoformat(end_date)   if end_date   else None,
        page       = page,
        page_size  = page_size,
        export     = export,
    )

    result = await get_recognition_given_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "display_name", "department", "role",
            "recognitions_given", "unique_recipients",
            "last_given_at", "most_used_badge",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        from datetime import date
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="recognition_given_{date.today()}.csv"'},
        )

    return result