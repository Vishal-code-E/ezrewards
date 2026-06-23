import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncpg

from app.dependencies.auth import require_admin
from app.database import get_db
from app.schemas.reports import WalletTransactionFilters, ExportFormat
from app.services.reports.wallet_transaction_service import (
    get_wallet_transaction_report,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/wallet/transactions",
    summary="Wallet Transaction Report",
    description="Full wallet ledger — every credit and debit with running balance. Admin only.",
)
async def wallet_transaction_report(
    type:       Optional[str] = Query(None, description="Credit|Debit"),
    status:     Optional[str] = Query(None, description="Completed|Failed|Pending Payment"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    page:       int           = Query(1,  ge=1),
    page_size:  int           = Query(25, ge=1, le=250),
    export:     ExportFormat  = Query(ExportFormat.json),

    current_user: dict               = Depends(require_admin),
    db:           asyncpg.Connection = Depends(get_db),
):
    filters = WalletTransactionFilters(
        type       = type,
        status     = status,
        start_date = date.fromisoformat(start_date) if start_date else None,
        end_date   = date.fromisoformat(end_date)   if end_date   else None,
        page       = page,
        page_size  = page_size,
        export     = export,
    )

    result = await get_wallet_transaction_report(
        current_user["workspace_id"], filters, db
    )

    if export == ExportFormat.csv:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "type", "amount", "balance_after",
            "payment_method", "status", "created_by", "created_at",
        ])
        writer.writeheader()
        writer.writerows([row.model_dump() for row in result.data])
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="wallet_transactions_{date.today()}.csv"'
            },
        )

    return result