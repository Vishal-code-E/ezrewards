import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import RecognitionReceivedFilters, ExportFormat
from app.services.reports.recognition_received_service import (
    get_recognition_received_report,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/recognition/received",
    summary="Recognition Received Report",
    description="Ranks employees by recognitions received. Shows most recognised employees. Admin only.",
)
async def recognition_received_report(
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:       int           = Query(1,  ge=1),
    page_size:  int           = Query(25, ge=1, le=250),
    export:     ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = RecognitionReceivedFilters(
        department = department,
        start_date = date.fromisoformat(start_date) if start_date else None,
        end_date   = date.fromisoformat(end_date)   if end_date   else None,
        page       = page,
        page_size  = page_size,
        export     = export,
    )

    result = await get_recognition_received_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "display_name", "department", "role",
            "recognitions_received", "unique_senders",
            "last_received_at", "most_received_badge",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="recognition_received_{date.today()}.csv"'
            },
        )

    return result