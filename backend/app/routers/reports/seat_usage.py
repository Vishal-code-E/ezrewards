import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import BaseReportFilters, ExportFormat
from app.services.reports.seat_usage_service import get_seat_usage_report

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/seats",
    summary="Active Seat Usage Report",
    description="Purchased seats vs active users, utilization %, department breakdown. Admin only.",
)
async def seat_usage_report(
    page:      int          = Query(1,  ge=1),
    page_size: int          = Query(25, ge=1, le=250),
    export:    ExportFormat = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = BaseReportFilters(
        page      = page,
        page_size = page_size,
        export    = export,
    )

    result = await get_seat_usage_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "department", "active_users",
            "inactive_users", "invited_users",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="seat_usage_{date.today()}.csv"'
            },
        )

    return result