import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import PaymentReportFilters, ExportFormat
from app.services.reports.payment_service import get_payment_report

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/payments",
    summary="Payment History Report",
    description="All subscription payment invoices with GST breakdown. Admin only.",
)
async def payment_report(
    status:         Optional[str] = Query(None, description="Paid|Pending|Failed|Refunded"),
    billing_cycle:  Optional[str] = Query(None, description="monthly|annual"),
    payment_method: Optional[str] = Query(None, description="stripe|bank_transfer"),
    start_date:     Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:       Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:           int           = Query(1,  ge=1),
    page_size:      int           = Query(25, ge=1, le=250),
    export:         ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = PaymentReportFilters(
        status         = status,
        billing_cycle  = billing_cycle,
        payment_method = payment_method,
        start_date     = date.fromisoformat(start_date) if start_date else None,
        end_date       = date.fromisoformat(end_date)   if end_date   else None,
        page           = page,
        page_size      = page_size,
        export         = export,
    )

    result = await get_payment_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "invoice_number", "billing_cycle", "purchased_seats",
            "base_amount", "discount_amount", "gst_amount",
            "final_amount", "payment_method", "status",
            "payment_date", "verified_by",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="payments_{date.today()}.csv"'
            },
        )

    return result